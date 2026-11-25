"""Regras da ficha cadastral do usuário: edição por seção, inativação, exclusão e histórico.

`FichaServiceMixin` é herdado por `AdminService` (usa `self.repo`, `_require_user`,
`get_usuario`, `update_usuario` e `_sincronizar_corpo_docente`).
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException, status

from app.modules.admin.ficha_schemas import (
    AbaHistorico,
    AcessoUpdate,
    ContatoEmergenciaUpdate,
    DadosPessoaisUpdate,
    EnderecoUpdate,
    HistoricoItem,
    HistoricoResponse,
    IdentificacaoUpdate,
    InativarRequest,
    PodeExcluirResponse,
    VinculoAlunoUpdate,
    VinculoProfessorUpdate,
)
from app.modules.admin.schemas import UsuarioAdminResponse, UsuarioUpdateRequest

# Ações da auditoria que contam como movimentação do usuário.
ACOES_MOVIMENTACAO = (
    "usuario_inativado", "usuario_reativado", "usuario_atualizado",
    "professor_cadastrado", "professor_reativado", "professor_desativado",
)

ROTULO_TRANSFERENCIA = {
    "troca_polo": "Troca de polo/escola",
    "polo_para_ead": "Migração para EAD",
    "ead_para_polo": "Migração para Polo",
    "reingresso": "Reingresso",
}


def _dt(valor: Any) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, time.min)
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def _num(valor: Any) -> Optional[float]:
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _iso(valor: Any) -> Any:
    return valor.isoformat() if isinstance(valor, (date, datetime)) else valor


def _diff(antes: Dict[str, Any], depois: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Só os campos que mudaram, já serializáveis para a auditoria."""
    mudou = [k for k in depois if _iso(antes.get(k)) != _iso(depois.get(k))]
    return {
        "antes": {k: _iso(antes.get(k)) for k in mudou},
        "depois": {k: _iso(depois.get(k)) for k in mudou},
    }


class FichaServiceMixin:
    repo: Any

    # ---------- Auxiliares ----------

    def _auditar_secao(
        self, acao: str, user_id: str, antes: Dict[str, Any], depois: Dict[str, Any],
        actor_user_id: Optional[str], client_ip: Optional[str], entidade: str = "usuarios",
        entidade_id: Optional[str] = None,
    ) -> bool:
        mudancas = _diff(antes, depois)
        if not mudancas["depois"]:
            return False
        self.repo.record_audit_log(
            usuario_id=actor_user_id, acao=acao, entidade=entidade, entidade_id=entidade_id or user_id,
            dados_antes=mudancas["antes"], dados_depois=mudancas["depois"], ip=client_ip,
        )
        return True

    def _atualizar_usuario_secao(
        self, acao: str, user_id: str, novos: Dict[str, Any],
        actor_user_id: Optional[str], client_ip: Optional[str],
    ) -> Dict[str, Any]:
        user = self._require_user(user_id)
        atuais = {**user, **self.repo.get_dados_cadastrais(user_id)}
        antes = {k: atuais.get(k) for k in novos}
        if self._auditar_secao(acao, user_id, antes, novos, actor_user_id, client_ip):
            self.repo.update_user(user_id, novos)
        return user

    def _aluno_do_usuario(self, user_id: str) -> Dict[str, Any]:
        self._require_user(user_id)
        aluno = self.repo.get_aluno_by_usuario_id(user_id)
        if not aluno:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não tem cadastro de aluno")
        return aluno

    def _professor_do_usuario(self, user_id: str) -> Dict[str, Any]:
        self._require_user(user_id)
        professor = self.repo.get_professor_vinculo_by_usuario_id(user_id)
        if not professor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuário não tem cadastro de professor")
        return professor

    # ---------- Seções ----------

    def atualizar_identificacao(
        self, user_id: str, dados: IdentificacaoUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        user = self._require_user(user_id)
        email = dados.email.strip().lower()
        if email != (user.get("email") or "").lower():
            existente = self.repo.get_user_by_email(email)
            if existente and str(existente["id"]) != str(user_id):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"O e-mail '{email}' já está em uso")
        if dados.cpf:
            atual = "".join(filter(str.isdigit, user.get("cpf") or ""))
            if dados.cpf != atual:
                existente = self.repo.get_user_by_cpf(dados.cpf)
                if existente and str(existente["id"]) != str(user_id):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="O CPF informado já está em uso")
        novos = {
            "nome": dados.nome, "sobrenome": dados.sobrenome or "", "email": email,
            "cpf": dados.cpf, "telefone": dados.telefone, "celular": dados.celular,
        }
        self._atualizar_usuario_secao("usuario_identificacao_atualizada", user_id, novos, actor_user_id, client_ip)
        return self.get_usuario(user_id)

    def atualizar_dados_pessoais(
        self, user_id: str, dados: DadosPessoaisUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        novos = dados.model_dump()
        self._atualizar_usuario_secao("usuario_dados_pessoais_atualizados", user_id, novos, actor_user_id, client_ip)
        aluno = self.repo.get_aluno_by_usuario_id(user_id)
        if aluno and _iso(aluno.get("data_nascimento")) != _iso(dados.data_nascimento):
            # O login e as telas de aluno leem alunos.data_nascimento.
            self.repo.update_aluno_campos(str(aluno["id"]), {"data_nascimento": dados.data_nascimento})
        return self.get_usuario(user_id)

    def atualizar_endereco(
        self, user_id: str, dados: EnderecoUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        self._atualizar_usuario_secao(
            "usuario_endereco_atualizado", user_id, dados.model_dump(), actor_user_id, client_ip
        )
        return self.get_usuario(user_id)

    def atualizar_contato_emergencia(
        self, user_id: str, dados: ContatoEmergenciaUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        self._atualizar_usuario_secao(
            "usuario_contato_emergencia_atualizado", user_id, dados.model_dump(), actor_user_id, client_ip
        )
        return self.get_usuario(user_id)

    def atualizar_acesso(
        self, user_id: str, dados: AcessoUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        """Perfil, polo/escola e permissões: reaproveita `update_usuario` (sincroniza o Corpo Docente)."""
        self._require_user(user_id)
        if not dados.perfil_id and not dados.perfil_nome:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o perfil do usuário")
        if dados.perfil_nome and not dados.perfil_id and not self.repo.get_perfil_by_nome(dados.perfil_nome):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Perfil '{dados.perfil_nome}' não encontrado")
        return self.update_usuario(
            user_id=user_id,
            dados=UsuarioUpdateRequest(
                perfil_id=dados.perfil_id, perfil_nome=dados.perfil_nome,
                polo_id=dados.polo_id or "", escola_id=dados.escola_id or "",
                permissoes=dados.permissoes,
            ),
            actor_user_id=actor_user_id,
            client_ip=client_ip,
        )

    def atualizar_vinculo_aluno(
        self, user_id: str, dados: VinculoAlunoUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        aluno = self._aluno_do_usuario(user_id)
        aluno_id = str(aluno["id"])
        if dados.numero_matricula != aluno.get("numero_matricula") and self.repo.numero_matricula_em_uso(
            dados.numero_matricula, aluno_id
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Número de matrícula já está em uso")
        novos = {"numero_matricula": dados.numero_matricula, "data_nascimento": dados.data_nascimento}
        antes = {k: aluno.get(k) for k in novos}
        if self._auditar_secao(
            "aluno_vinculo_atualizado", user_id, antes, novos, actor_user_id, client_ip,
            entidade="alunos", entidade_id=aluno_id,
        ):
            self.repo.update_aluno_campos(aluno_id, novos)
        dados_usuario = self.repo.get_dados_cadastrais(user_id)
        if _iso(dados_usuario.get("data_nascimento")) != _iso(dados.data_nascimento):
            self.repo.update_user(user_id, {"data_nascimento": dados.data_nascimento})
        return self.get_usuario(user_id)

    def atualizar_vinculo_professor(
        self, user_id: str, dados: VinculoProfessorUpdate, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        professor = self._professor_do_usuario(user_id)
        polo_id, escola_id = dados.polo_id, dados.escola_id
        if escola_id:
            from app.modules.polos_escolas.repository import get_polos_escolas_repository

            escola = get_polos_escolas_repository().get_escola(escola_id)
            if not escola:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
            if polo_id and escola.get("polo_id") and str(escola["polo_id"]) != str(polo_id):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="A escola não pertence ao polo informado")
            polo_id = polo_id or (str(escola["polo_id"]) if escola.get("polo_id") else None)
        novos = {
            "polo_id": polo_id, "escola_id": escola_id,
            "valor_hora_aula": dados.valor_hora_aula, "chave_pix": dados.chave_pix, "status": dados.status,
        }
        antes = {k: professor.get(k) for k in novos}
        antes = {k: (str(v) if k in ("polo_id", "escola_id") and v else v) for k, v in antes.items()}
        antes["valor_hora_aula"] = _num(antes["valor_hora_aula"])
        if self._auditar_secao(
            "professor_vinculo_atualizado", user_id, antes, novos, actor_user_id, client_ip,
            entidade="professores", entidade_id=str(professor["id"]),
        ):
            self.repo.update_professor_campos(str(professor["id"]), novos)
        return self.get_usuario(user_id)

    # ---------- Inativação e exclusão ----------

    def inativar_usuario(
        self, user_id: str, dados: InativarRequest, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        if actor_user_id and str(actor_user_id) == str(user_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Não é permitido inativar o próprio usuário")
        user = self._require_user(user_id)
        motivo = dados.motivo.strip()
        self.repo.update_user(user_id, {
            "status": dados.status,
            "inativado_em": datetime.now(timezone.utc),
            "inativado_por": str(actor_user_id) if actor_user_id else None,
            "motivo_inativacao": motivo,
        })
        sessoes = self.repo.revogar_sessoes(user_id)
        self.repo.record_audit_log(
            usuario_id=actor_user_id, acao="usuario_inativado", entidade="usuarios", entidade_id=user_id,
            dados_antes={"status": user.get("status")},
            dados_depois={"status": dados.status, "motivo": motivo, "sessoes_revogadas": sessoes},
            ip=client_ip,
        )
        return self.get_usuario(user_id)

    def reativar_usuario(
        self, user_id: str, actor_user_id: Optional[str], client_ip: Optional[str]
    ) -> UsuarioAdminResponse:
        user = self._require_user(user_id)
        if user.get("status") == "ativo":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="O usuário já está ativo")
        dados = self.repo.get_dados_cadastrais(user_id)
        self.repo.update_user(user_id, {
            "status": "ativo", "inativado_em": None, "inativado_por": None, "motivo_inativacao": None,
        })
        self.repo.record_audit_log(
            usuario_id=actor_user_id, acao="usuario_reativado", entidade="usuarios", entidade_id=user_id,
            dados_antes={"status": user.get("status"), "motivo": dados.get("motivo_inativacao")},
            dados_depois={"status": "ativo"}, ip=client_ip,
        )
        return self.get_usuario(user_id)

    def pode_excluir(self, user_id: str, actor_user_id: Optional[str] = None) -> PodeExcluirResponse:
        self._require_user(user_id)
        if actor_user_id and str(actor_user_id) == str(user_id):
            return PodeExcluirResponse(pode_excluir=False, motivos=["é o seu próprio usuário"])
        aluno = self.repo.get_aluno_by_usuario_id(user_id)
        professor = self.repo.get_professor_vinculo_by_usuario_id(user_id)
        motivos = self.repo.historico_existente(
            user_id,
            str(aluno["id"]) if aluno else None,
            str(professor["id"]) if professor else None,
        )
        return PodeExcluirResponse(pode_excluir=not motivos, motivos=motivos)

    def _exigir_sem_historico(self, user_id: str) -> None:
        resultado = self.pode_excluir(user_id)
        if not resultado.pode_excluir:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Usuário possui histórico (" + ", ".join(resultado.motivos)
                + ") — inative em vez de excluir.",
            )

    # ---------- Frequência RN07 ----------

    def frequencias_do_aluno(self, aluno_id: str, turmas: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Frequência RN07 por turma do aluno: {turma_id: {frequencia_pct, em_risco, minimo_pct}}."""
        from app.modules.carga_horaria.service import CargaHorariaService

        servico = CargaHorariaService()
        resultado: Dict[str, Dict[str, Any]] = {}
        for turma in turmas:
            turma_id = str(turma.get("turma_id") or "")
            if not turma_id:
                continue
            try:
                freq = servico.frequencia(None, turma_id)
            except HTTPException:
                continue
            linha = next((a for a in freq.alunos if str(a.aluno_id) == str(aluno_id)), None)
            if linha is not None:
                resultado[turma_id] = {
                    "frequencia_pct": linha.frequencia_pct,
                    "em_risco": linha.em_risco,
                    "minimo_pct": freq.minimo_pct,
                    "disciplinas": [d.model_dump() for d in linha.disciplinas],
                }
        return resultado

    # ---------- Histórico ----------

    def historico_usuario(self, user_id: str, aba: AbaHistorico, limit: int, offset: int) -> HistoricoResponse:
        self._require_user(user_id)
        aluno = self.repo.get_aluno_by_usuario_id(user_id)
        professor = self.repo.get_professor_vinculo_by_usuario_id(user_id)
        aluno_id = str(aluno["id"]) if aluno else None
        professor_id = str(professor["id"]) if professor else None

        if aba == "auditoria":
            ids = [i for i in (str(user_id), aluno_id, professor_id) if i]
            total, linhas = self.repo.auditoria_de_entidades(ids, None, limit, offset)
            return HistoricoResponse(
                aba=aba, total=total, limit=limit, offset=offset,
                items=[self._item_auditoria(l) for l in linhas],
            )

        montar = {
            "academico": self._historico_academico,
            "financeiro": self._historico_financeiro,
            "movimentacoes": self._historico_movimentacoes,
        }[aba]
        itens = montar(str(user_id), aluno_id, professor_id)
        return HistoricoResponse(
            aba=aba, total=len(itens), limit=limit, offset=offset, items=itens[offset: offset + limit]
        )

    @staticmethod
    def _item_auditoria(l: Dict[str, Any]) -> HistoricoItem:
        return HistoricoItem(
            grupo="auditoria", id=str(l.get("id")) if l.get("id") is not None else None,
            data=_dt(l.get("criado_em")), titulo=str(l.get("acao") or ""),
            detalhe=l.get("usuario_nome") or "Sistema",
            extra={
                "entidade": l.get("entidade"), "ip": l.get("ip"),
                "dados_antes": l.get("dados_antes"), "dados_depois": l.get("dados_depois"),
            },
        )

    def _historico_academico(
        self, user_id: str, aluno_id: Optional[str], professor_id: Optional[str]
    ) -> List[HistoricoItem]:
        itens: List[HistoricoItem] = []
        if aluno_id:
            turmas = self.repo.turmas_do_aluno(aluno_id)
            frequencias = self.frequencias_do_aluno(aluno_id, turmas)
            for t in turmas:
                freq = frequencias.get(str(t.get("turma_id")), {})
                itens.append(HistoricoItem(
                    grupo="turmas", id=t.get("turma_id"), data=_dt(t.get("data_matricula") or t.get("data_inicio")),
                    titulo=t.get("turma_nome") or "Turma", detalhe=t.get("curso_nome"),
                    status="concluida" if t.get("concluida_em") else t.get("status"),
                    valor=freq.get("frequencia_pct"), link="/admin/turmas-calendarios",
                    extra={
                        "data_inicio": _iso(t.get("data_inicio")), "data_fim": _iso(t.get("data_fim")),
                        "em_risco": freq.get("em_risco", False), "minimo_pct": freq.get("minimo_pct"),
                        "disciplinas": freq.get("disciplinas", []),
                    },
                ))
            for n in self.repo.notas_do_aluno(aluno_id):
                itens.append(HistoricoItem(
                    grupo="notas", id=n.get("id"), data=_dt(n.get("data")),
                    titulo=n.get("disciplina_nome") or "Disciplina", detalhe=n.get("turma_nome"),
                    status=n.get("origem"), valor=_num(n.get("valor")),
                ))
            for c in self.repo.certificados_do_aluno(aluno_id):
                itens.append(HistoricoItem(
                    grupo="certificados", id=c.get("id"), data=_dt(c.get("emitido_em")),
                    titulo=c.get("curso_nome") or "Certificado",
                    status="emitido" if c.get("emitido_em") else "pendente",
                ))
            for e in self.repo.estagios_do_aluno(aluno_id):
                itens.append(HistoricoItem(
                    grupo="estagios", id=e.get("id"), data=_dt(e.get("enviado_em")),
                    titulo=f"Estágio — {e.get('etapa') or 'etapa'}", status=e.get("status"),
                    valor=_num(e.get("horas")), link="/admin/estagios",
                ))
        if professor_id:
            for v in self.repo.vinculos_docentes(professor_id):
                itens.append(HistoricoItem(
                    grupo="vinculos", id=v.get("professor_disciplina_id"),
                    titulo=v.get("disciplina_nome") or "Disciplina",
                    detalhe=" · ".join(x for x in (v.get("turma_nome"), v.get("curso_nome")) if x) or None,
                    status="ativo" if v.get("ativo", True) else "inativo",
                    valor=_num(v.get("horas_ministradas")), link="/admin/turmas-calendarios",
                    extra={
                        "carga_horaria": _num(v.get("carga_horaria")),
                        "aulas_previstas": v.get("aulas_previstas"),
                        "aulas_ministradas": int(v.get("aulas_ministradas") or 0),
                    },
                ))
            for a in self.repo.aulas_do_professor(professor_id):
                itens.append(HistoricoItem(
                    grupo="aulas", id=a.get("id"), data=_dt(a.get("data_aula")),
                    titulo=a.get("disciplina_nome") or "Aula",
                    detalhe=f"{a.get('turma_nome') or ''} · aula {a.get('numero_aula') or '—'}".strip(" ·"),
                    status=a.get("tipo"), valor=_num(a.get("horas")),
                ))
        return itens

    def _historico_financeiro(
        self, user_id: str, aluno_id: Optional[str], professor_id: Optional[str]
    ) -> List[HistoricoItem]:
        itens: List[HistoricoItem] = []
        if aluno_id:
            for p in self.repo.pagamentos_do_aluno(aluno_id):
                itens.append(HistoricoItem(
                    grupo="pagamentos", id=p.get("id"), data=_dt(p.get("vencimento_em") or p.get("criado_em")),
                    titulo=p.get("descricao") or "Cobrança", detalhe=p.get("billing_type"),
                    status=p.get("status"), valor=_num(p.get("valor")), link="/admin/financeiro",
                    extra={"pago_em": _iso(p.get("pago_em"))},
                ))
            for l in self.repo.licencas_do_aluno(aluno_id):
                itens.append(HistoricoItem(
                    grupo="licencas", id=l.get("id"), data=_dt(l.get("ativada_em")),
                    titulo=l.get("disciplina_nome") or "Licença", detalhe=l.get("numero_licenca"),
                    status=l.get("status"), link="/admin/licencas",
                ))
        for p in self.repo.pedidos_do_usuario(user_id):
            itens.append(HistoricoItem(
                grupo="pedidos", id=p.get("id"), data=_dt(p.get("criado_em")),
                titulo=f"Pedido {p.get('numero') or ''}".strip(), detalhe=p.get("tipo"),
                status=p.get("status"), valor=_num(p.get("valor_total")), link="/admin/pedidos",
            ))
        return itens

    def _historico_movimentacoes(
        self, user_id: str, aluno_id: Optional[str], professor_id: Optional[str]
    ) -> List[HistoricoItem]:
        itens: List[HistoricoItem] = []
        if aluno_id:
            for t in self.repo.transferencias_do_aluno(aluno_id):
                origem = t.get("escola_origem_nome") or t.get("polo_origem_nome")
                destino = t.get("escola_destino_nome") or t.get("polo_destino_nome")
                itens.append(HistoricoItem(
                    grupo="transferencias", id=t.get("id"), data=_dt(t.get("criado_em")),
                    titulo=ROTULO_TRANSFERENCIA.get(str(t.get("tipo")), str(t.get("tipo") or "Transferência")),
                    detalhe=" → ".join(x for x in (origem, destino) if x) or None,
                    status=t.get("status"), link="/admin/transferencias",
                    extra={
                        "observacao": t.get("observacao"), "motivo_rejeicao": t.get("motivo_rejeicao"),
                        "resolvido_em": _iso(t.get("resolvido_em")),
                    },
                ))
            for d in self.repo.desistencias_do_aluno(aluno_id):
                itens.append(HistoricoItem(
                    grupo="desistencias", id=d.get("id"), data=_dt(d.get("data_marcacao")),
                    titulo="Desistência", detalhe=d.get("motivo"),
                    status="reingresso" if d.get("reingresso_em") else "desistente",
                    extra={"reingresso_em": _iso(d.get("reingresso_em"))},
                ))
        ids = [i for i in (user_id, aluno_id, professor_id) if i]
        _, linhas = self.repo.auditoria_de_entidades(ids, ACOES_MOVIMENTACAO, 200, 0)
        itens.extend(self._item_auditoria(l).model_copy(update={"grupo": "status"}) for l in linhas)
        return sorted(itens, key=lambda i: _ordem(i.data), reverse=True)


def _ordem(valor: Optional[datetime]) -> float:
    if valor is None:
        return float("-inf")
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.timestamp()
