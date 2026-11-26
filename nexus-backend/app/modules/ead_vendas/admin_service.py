"""Regras da Gestão de Matrículas EAD (admin).

- Matrícula manual: aluno EAD existente ou novo (sem Polo, com convite por e-mail para criar a senha),
  numa Turma EAD aberta, como Regular ou Bolsista. Bolsista recebe as disciplinas sem custo, pelo calendário.
- Liberação manual de disciplina (bolsa, pagamento externo, problema no pagamento, cortesia): compra
  'liberado' de valor zero, com quem liberou e o motivo. Revogável; compra paga no gateway não é.
- Toda ação fica na linha do tempo (movimentações) e no log de auditoria.
"""
from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.core.email import send_student_invite_email
from app.core.security import generate_secure_token, hash_password, hash_token
from app.modules.auth.repository import get_auth_repository
from app.modules.auth.schemas import UserResponse
from app.modules.ead_vendas.admin_repository import PostgresGestaoEadRepository
from app.modules.ead_vendas.admin_schemas import (
    AlunoEadBusca,
    CompraEadAdmin,
    FichaEadOut,
    LiberacaoIn,
    MatriculaCriadaOut,
    MatriculaEadItem,
    MatriculaManualIn,
    MatriculaPatchIn,
    MatriculasEadPage,
    MovimentacaoEad,
    MovimentacoesPage,
    ResumoEadOut,
    TurmaEadOpcao,
)
from app.modules.ead_vendas.repository import JaInscrito, PostgresVendasEadRepository, TurmaLotada
from app.modules.ead_vendas.schemas import PedidoAlunoOut
from app.modules.ead_vendas.service import VendasEadService
from app.modules.polos_escolas.service import INVITE_TOKEN_EXPIRE_HOURS, cpf_valido, normalizar_cpf

_ROTULO_MOTIVO = {
    "bolsa": "Bolsa", "pagamento_externo": "Pagamento externo", "problema_pagamento": "Problema no pagamento",
    "cortesia": "Cortesia", "outro": "Outro",
}


class GestaoEadService:
    def __init__(self, repo: PostgresGestaoEadRepository, vendas_repo: PostgresVendasEadRepository) -> None:
        self.repo = repo
        self.vendas_repo = vendas_repo
        self.vendas = VendasEadService(vendas_repo)
        self.auth_repo = get_auth_repository()

    def _auditar(self, user: UserResponse, acao: str, aluno_id: str, detalhe: str, ip: Optional[str],
                 extra: Optional[Dict[str, Any]] = None) -> None:
        self.auth_repo.record_audit_log(usuario_id=str(user.id), acao=acao, entidade="alunos", entidade_id=aluno_id,
                                        dados_depois={"detalhe": detalhe, **(extra or {})}, ip=ip)

    # ------------------------------------------------------------------ leitura

    def resumo(self, inicio: Optional[date], fim: Optional[date]) -> ResumoEadOut:
        return ResumoEadOut(**self.repo.resumo(inicio, fim))

    def turmas(self) -> list[TurmaEadOpcao]:
        return [TurmaEadOpcao(**t) for t in self.repo.turmas_ead()]

    def matriculas(self, filtros: Dict[str, Any], limite: int, offset: int) -> MatriculasEadPage:
        total, linhas = self.repo.listar_matriculas(filtros, limite, offset)
        return MatriculasEadPage(total=total, items=[MatriculaEadItem(**l) for l in linhas])

    def movimentacoes(self, filtros: Dict[str, Any], limite: int, offset: int) -> MovimentacoesPage:
        total, linhas = self.repo.movimentacoes(filtros, limite, offset)
        return MovimentacoesPage(total=total, items=[MovimentacaoEad(**l) for l in linhas])

    def buscar_alunos(self, q: str) -> list[AlunoEadBusca]:
        return [AlunoEadBusca(**a) for a in self.repo.buscar_alunos(q)] if len(q.strip()) >= 2 else []

    def _aluno(self, aluno_id: str) -> Dict[str, Any]:
        aluno = self.repo.aluno(aluno_id)
        if not aluno or aluno.get("modalidade") != "ead":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aluno EAD não encontrado.")
        return aluno

    def ficha(self, aluno_id: str) -> FichaEadOut:
        aluno = self._aluno(aluno_id)
        _, matriculas = self.repo.listar_matriculas({"aluno_id": aluno_id}, 50, 0)
        compras = []
        for c in self.repo.compras(aluno_id):
            manual = c.get("origem") in ("manual", "bolsa")
            pendente = c.get("status_pagamento") == "pendente"
            cancelada = (c.get("status_pagamento") or "").lower() in ("cancelado", "cancelada")
            compras.append(CompraEadAdmin(**c, pode_revogar=not cancelada and (manual or pendente)))
        _, movs = self.repo.movimentacoes({"aluno_id": aluno_id}, 100, 0)
        return FichaEadOut(
            aluno_id=aluno["aluno_id"], usuario_id=aluno["usuario_id"], nome=aluno["nome"], email=aluno.get("email"),
            cpf=aluno.get("cpf"), celular=aluno.get("celular"), numero_matricula=aluno.get("numero_matricula"),
            status_aluno=aluno.get("status_aluno"),
            matriculas=[MatriculaEadItem(**m) for m in matriculas],
            turmas=self.vendas._turmas_loja(aluno_id),
            compras=compras,
            pedidos=[PedidoAlunoOut(**p) for p in self.vendas_repo.pedidos_do_aluno(aluno_id)],
            movimentacoes=[MovimentacaoEad(**m) for m in movs],
        )

    # ------------------------------------------------------------------ matrícula manual

    def _turma_aberta(self, turma_id: str) -> Dict[str, Any]:
        turma = self.repo.turma(turma_id)
        if not turma or turma.get("modalidade") != "ead":
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma EAD não encontrada.")
        if not turma.get("aberta"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A turma está concluída ou cancelada.")
        return turma

    def matricular(self, dados: MatriculaManualIn, user: UserResponse, ip: Optional[str]) -> MatriculaCriadaOut:
        turma = self._turma_aberta(dados.turma_id)
        extras = {"origem": "manual", "tipo": dados.tipo, "criado_por": str(user.id),
                  "observacao": (dados.observacao or "").strip() or None, "conferir_vagas": not dados.ignorar_vagas}
        convite: Optional[bool] = None
        try:
            if dados.aluno_id:
                aluno = self._aluno(dados.aluno_id)
                if self.repo.matricula_ativa_no_curso(aluno["aluno_id"], turma["curso_id"]):
                    raise HTTPException(status.HTTP_409_CONFLICT,
                                        detail="O aluno já tem matrícula ativa neste curso. Use “Transferir turma”.")
                aluno_id = aluno["aluno_id"]
                matricula_id = self.vendas_repo.inscrever_aluno(aluno_id, turma["id"], **extras)
            else:
                novo = dados.novo_aluno
                cpf = normalizar_cpf(novo.cpf)
                if not cpf_valido(cpf):
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CPF inválido.")
                if novo.data_nascimento >= date.today():
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Data de nascimento inválida.")
                email = novo.email.strip().lower()
                if self.vendas_repo.email_em_uso(email):
                    raise HTTPException(status.HTTP_409_CONFLICT, detail="Este e-mail já tem cadastro. Busque o aluno existente.")
                if self.vendas_repo.cpf_em_uso(cpf):
                    raise HTTPException(status.HTTP_409_CONFLICT, detail="Este CPF já tem cadastro. Busque o aluno existente.")
                perfil_id = self.vendas_repo.perfil_aluno_id()
                if not perfil_id:
                    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Perfil 'aluno' não configurado.")
                criado = self.vendas_repo.criar_aluno_inscrito({
                    "nome": novo.nome.strip(), "sobrenome": novo.sobrenome.strip(), "email": email, "cpf": cpf,
                    "celular": "".join(filter(str.isdigit, novo.celular or "")) or None,
                    "data_nascimento": novo.data_nascimento,
                    "senha_hash": hash_password(secrets.token_urlsafe(24)), "perfil_id": perfil_id,
                }, turma["id"], **extras)
                aluno_id, matricula_id = criado["aluno_id"], criado["matricula_id"]
                convite = self._convidar(criado["usuario_id"], email, novo.nome.strip(), aluno_id)
        except JaInscrito:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="O aluno já está nesta turma.")
        except TurmaLotada:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail="Turma lotada. Marque “Matricular mesmo com a turma lotada” para continuar.")
        except LookupError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
        self._auditar(user, "ead_matricula_manual", aluno_id,
                      f"{'Bolsista' if dados.tipo == 'bolsista' else 'Regular'} · {turma['nome']}", ip,
                      {"turma_id": turma["id"], "matricula_id": matricula_id})
        return MatriculaCriadaOut(matricula_id=matricula_id, aluno_id=aluno_id, convite_enviado=convite)

    def _convidar(self, usuario_id: str, email: str, nome: str, aluno_id: str) -> bool:
        from app.modules.polos_escolas.repository import get_polos_escolas_repository

        token = generate_secure_token(32)
        get_polos_escolas_repository().create_password_reset(
            usuario_id, hash_token(token), datetime.now(timezone.utc) + timedelta(hours=INVITE_TOKEN_EXPIRE_HOURS))
        aluno = self.repo.aluno(aluno_id) or {}
        try:
            return bool(send_student_invite_email(email, nome, aluno.get("numero_matricula") or "", token,
                                                  INVITE_TOKEN_EXPIRE_HOURS))
        except Exception:  # e-mail fora do ar não desfaz a matrícula
            return False

    def _matricula(self, matricula_id: str) -> Dict[str, Any]:
        m = self.repo.matricula(matricula_id)
        if not m:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Matrícula não encontrada.")
        return m

    def atualizar(self, matricula_id: str, dados: MatriculaPatchIn, user: UserResponse, ip: Optional[str]) -> MatriculaEadItem:
        m = self._matricula(matricula_id)
        if dados.tipo and dados.tipo != m["tipo"]:
            self.repo.atualizar_matricula(m["id"], {"tipo": dados.tipo})
            self._auditar(user, "ead_tipo_alterado", m["aluno_id"],
                          f"{m['tipo'].capitalize()} → {dados.tipo.capitalize()}", ip, {"turma_id": m.get("turma_id")})
        if dados.observacao is not None and dados.observacao != (m.get("observacao") or ""):
            self.repo.atualizar_matricula(m["id"], {"observacao": dados.observacao.strip() or None})
        if dados.turma_id and dados.turma_id != m.get("turma_id"):
            if m["status"] != "ativa":
                raise HTTPException(status.HTTP_409_CONFLICT, detail="Reative a matrícula antes de transferir.")
            nova = self._turma_aberta(dados.turma_id)
            if nova["curso_id"] != m["curso_id"]:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="A transferência é só entre Turmas EAD do mesmo curso.")
            self.repo.transferir(m, nova["id"])
            self._auditar(user, "ead_transferencia", m["aluno_id"], f"{m.get('turma_nome') or '—'} → {nova['nome']}", ip,
                          {"turma_id": nova["id"]})
        return MatriculaEadItem(**self._matricula(matricula_id))

    def cancelar(self, matricula_id: str, motivo: str, user: UserResponse) -> MatriculaEadItem:
        m = self._matricula(matricula_id)
        if m["status"] == "cancelada":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A matrícula já está cancelada.")
        for pedido_id in self.repo.cancelar_matricula(m, motivo.strip(), str(user.id)):
            self.vendas._cancelar_pedido(pedido_id, "Matrícula EAD cancelada")
        return MatriculaEadItem(**self._matricula(matricula_id))

    def reativar(self, matricula_id: str, user: UserResponse, ip: Optional[str]) -> MatriculaEadItem:
        m = self._matricula(matricula_id)
        if m["status"] == "ativa":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A matrícula já está ativa.")
        if self.repo.matricula_ativa_no_curso(m["aluno_id"], m["curso_id"]):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="O aluno já tem outra matrícula ativa neste curso.")
        self.repo.reativar_matricula(m)
        self._auditar(user, "ead_matricula_reativada", m["aluno_id"], m.get("turma_nome") or "", ip,
                      {"turma_id": m.get("turma_id")})
        return MatriculaEadItem(**self._matricula(matricula_id))

    # ------------------------------------------------------------------ liberação manual

    def liberar(self, aluno_id: str, disciplina_id: str, dados: LiberacaoIn, user: UserResponse) -> FichaEadOut:
        self._aluno(aluno_id)
        curso_id = self.repo.curso_da_disciplina(disciplina_id)
        if not curso_id or not self.repo.matricula_ativa_no_curso(aluno_id, curso_id):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="A disciplina não pertence a um curso em que o aluno tem matrícula ativa.")
        if dados.motivo == "outro" and not (dados.texto or "").strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Descreva o motivo da liberação.")
        for pedido_id in self.vendas_repo.cancelar_compras_abertas(aluno_id, disciplina_id):
            self.vendas._cancelar_pedido(pedido_id, "Disciplina liberada manualmente pelo admin")
        self.repo.liberar({"aluno_id": aluno_id, "disciplina_id": disciplina_id, "turma_id": dados.turma_id,
                           "motivo": dados.motivo, "texto": (dados.texto or "").strip() or None,
                           "usuario_id": str(user.id)})
        return self.ficha(aluno_id)

    def revogar(self, compra_id: str, motivo: str, user: UserResponse, ip: Optional[str]) -> FichaEadOut:
        c = self.repo.compra(compra_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Compra não encontrada.")
        situacao = (c.get("status_pagamento") or "").lower()
        if situacao in ("cancelado", "cancelada"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta compra já foi cancelada.")
        if c.get("origem") not in ("manual", "bolsa") and situacao != "pendente":
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail="Compra paga pelo aluno não pode ser revogada aqui: faça o estorno pelo Financeiro.")
        self.repo.revogar(c["id"], str(user.id))
        if c.get("pedido_id") and situacao == "pendente":
            self.vendas._cancelar_pedido(str(c["pedido_id"]), "Cancelado pelo admin (Matrículas EAD)")
        rotulo = "Liberação revogada" if c.get("origem") in ("manual", "bolsa") else "Compra pendente cancelada"
        self._auditar(user, "ead_compra_revogada", str(c["aluno_id"]), f"{rotulo}: {motivo.strip()}", ip,
                      {"turma_id": str(c["turma_id"]) if c.get("turma_id") else None, "compra_id": c["id"]})
        return self.ficha(str(c["aluno_id"]))


ROTULO_MOTIVO = _ROTULO_MOTIVO
