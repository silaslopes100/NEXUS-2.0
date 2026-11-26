"""Regras das vendas EAD.

Disciplina à venda na loja = liberada pelo calendário da Turma EAD do aluno **e** publicada pelo
admin no AVA (``ava_disciplina_config.publicado`` com aulas). Preço sempre do AVA (R$ 45 padrão),
com o livro físico opcional (R$ 25 padrão, sem licença). Vencido o prazo sem concluir, a
disciplina só volta com novo pagamento (RN-03): a recompra ganha prazo novo a partir da liberação.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.modules.auth.repository import get_auth_repository
from app.modules.auth.schemas import LoginResponse, UserResponse
from app.modules.auth.service import AuthService
from app.modules.carga_horaria import cronograma as cr
from app.modules.carga_horaria.repository import get_carga_horaria_repository
from app.modules.carga_horaria.service import CargaHorariaService, regras_do_calendario
from app.modules.ead_vendas.repository import JaInscrito, PostgresVendasEadRepository, TurmaLotada
from app.modules.ead_vendas.schemas import (
    CheckoutIn,
    DisciplinaLojaOut,
    DisciplinaVitrineOut,
    EnderecoOut,
    InscricaoIn,
    LojaOut,
    PedidoAlunoOut,
    TurmaLojaOut,
    TurmaVitrineDetalheOut,
    TurmaVitrineOut,
)
from app.modules.financeiro import pedidos as regras_pedido
from app.modules.financeiro.cobranca_service import CobrancaService
from app.modules.financeiro.gateways.base import EnderecoPagador, Pagador
from app.modules.financeiro.repository import get_financeiro_repository
from app.modules.financeiro.service import FinanceiroService
from app.modules.polos_escolas.service import cpf_valido, normalizar_cpf

logger = logging.getLogger(__name__)

_PAGOS = {"pago", "paga", "aprovado", "aprovada", "confirmado", "confirmada", "liberado", "liberada", "concluido",
          "paid", "received", "confirmed", "received_in_cash"}
_LIMITE_INSCRICOES_IP = 5      # por janela
_JANELA_INSCRICOES_MIN = 60
_CAMPOS_ENDERECO = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")


def _hoje() -> date:
    return datetime.now(timezone.utc).date()


def _data(valor: Any) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    return valor if isinstance(valor, date) else None


def _vagas_restantes(t: Dict[str, Any]) -> Optional[int]:
    return max(int(t["vagas"]) - int(t.get("total_alunos") or 0), 0) if t.get("vagas") else None


def _turma_vitrine(t: Dict[str, Any]) -> TurmaVitrineOut:
    dados = {k: t.get(k) for k in TurmaVitrineOut.model_fields if k in t}
    dados.update(vagas_restantes=_vagas_restantes(t), total_disciplinas=int(t.get("total_disciplinas") or 0))
    return TurmaVitrineOut(**dados)


class VendasEadService:
    def __init__(self, repo: PostgresVendasEadRepository) -> None:
        self.repo = repo
        self.carga = get_carga_horaria_repository()
        self.fin_repo = get_financeiro_repository()

    # ------------------------------------------------------------------ cronograma

    def _cronograma(self, turma_id: str, curso_id: str, inicio: date, conclusoes: Dict[str, date],
                    hoje: date) -> tuple[Dict[str, Dict[str, Any]], Any]:
        contexto = self.carga.contexto_turma(turma_id) or {}
        regras = regras_do_calendario(contexto.get("calendario"))
        disciplinas = CargaHorariaService(self.carga)._disciplinas_ead(curso_id)
        linhas = cr.cronograma_ead(disciplinas, inicio, regras, conclusoes, hoje)
        return {l["disciplina_id"]: l for l in linhas}, regras

    # ------------------------------------------------------------------ vitrine

    def vitrine(self) -> List[TurmaVitrineOut]:
        return [_turma_vitrine(t) for t in self.repo.turmas_abertas()]

    def _turma_aberta(self, turma_id: str) -> Dict[str, Any]:
        t = self.repo.turma(turma_id)
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma EAD não encontrada ou com matrículas encerradas.")
        return t

    def turma(self, turma_id: str) -> TurmaVitrineDetalheOut:
        t = self._turma_aberta(turma_id)
        hoje = _hoje()
        inicio = max(_data(t.get("data_inicio")) or hoje, hoje)  # quem entra hoje começa hoje (ou no início)
        crono, regras = self._cronograma(t["id"], t["curso_id"], inicio, {}, hoje)
        disciplinas = []
        for d in self.repo.disciplinas_venda(t["curso_id"]):
            linha = crono.get(d["id"], {})
            disciplinas.append(DisciplinaVitrineOut(
                id=d["id"], nome=d["nome"], semestre=d.get("semestre"), carga_horaria=int(d.get("carga_horaria") or 0),
                valor_ead=float(d["valor_ead"]), livro_disponivel=bool(d["livro_disponivel"]),
                valor_livro_ead=float(d["valor_livro_ead"]), prazo_dias=linha.get("prazo_dias"),
                libera_em_prevista=linha.get("liberada_em"),
            ))
        base = _turma_vitrine(t)
        return TurmaVitrineDetalheOut(**base.model_dump(), liberacao=regras.ead_liberacao, disciplinas=disciplinas)

    # ------------------------------------------------------------------ inscrição pública

    def inscrever(self, dados: InscricaoIn, ip: Optional[str]) -> LoginResponse:
        if dados.site:  # honeypot preenchido: robô
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Não foi possível concluir a inscrição.")
        if not dados.aceite_termos:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="É preciso aceitar os termos para se matricular.")
        if ip and self.repo.inscricoes_recentes_do_ip(ip, _JANELA_INSCRICOES_MIN) >= _LIMITE_INSCRICOES_IP:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Muitas inscrições a partir desta rede. Tente novamente mais tarde.")
        cpf = normalizar_cpf(dados.cpf)
        if not cpf_valido(cpf):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CPF inválido.")
        if dados.data_nascimento >= _hoje() or dados.data_nascimento.year < 1900:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Data de nascimento inválida.")
        email = dados.email.strip().lower()
        if self.repo.email_em_uso(email) or self.repo.cpf_em_uso(cpf):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                detail="Você já tem cadastro no NEXUS. Entre com o seu e-mail e senha para se matricular.")
        turma = self._turma_aberta(dados.turma_id)
        if _vagas_restantes(turma) == 0:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="As vagas desta turma esgotaram.")
        perfil_id = self.repo.perfil_aluno_id()
        if not perfil_id:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Inscrições indisponíveis no momento.")
        try:
            criado = self.repo.criar_aluno_inscrito({
                "nome": dados.nome.strip(), "sobrenome": dados.sobrenome.strip(), "email": email, "cpf": cpf,
                "celular": "".join(filter(str.isdigit, dados.celular)), "data_nascimento": dados.data_nascimento,
                "senha_hash": hash_password(dados.senha), "perfil_id": perfil_id,
            }, turma["id"])
        except TurmaLotada:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="As vagas desta turma esgotaram.")
        except LookupError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
        auth_repo = get_auth_repository()
        auth_repo.record_audit_log(usuario_id=criado["usuario_id"], acao="inscricao_ead", entidade="alunos",
                                   entidade_id=criado["aluno_id"],
                                   dados_depois={"turma_id": turma["id"], "turma": turma["nome"]}, ip=ip)
        usuario = auth_repo.get_user_by_email(email)
        if not usuario:  # não deveria acontecer
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Inscrição feita; entre com o seu e-mail.")
        auth_repo.update_user_last_login(criado["usuario_id"])
        return AuthService(auth_repo).emitir_sessao(usuario, ip)

    def inscrever_aluno(self, ctx: Dict[str, Any], turma_id: str) -> LojaOut:
        turma = self._turma_aberta(turma_id)
        try:
            self.repo.inscrever_aluno(ctx["aluno"]["id"], turma["id"])
        except JaInscrito:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Você já está nesta turma.")
        except TurmaLotada:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="As vagas desta turma esgotaram.")
        except LookupError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
        return self.loja(ctx)

    # ------------------------------------------------------------------ loja

    @staticmethod
    def _estado(d: Dict[str, Any], linha: Dict[str, Any], compra: Optional[Dict[str, Any]], ao_vencer: str,
                hoje: date) -> Dict[str, Any]:
        prazo_dias = linha.get("prazo_dias")
        saida: Dict[str, Any] = {"libera_em": linha.get("liberada_em"), "data_limite": linha.get("data_limite"),
                                 "prazo_dias": prazo_dias}
        pago = bool(compra and (compra.get("liberada_em")
                                or (compra.get("status_pagamento") or "").strip().lower() in _PAGOS))
        if pago:
            saida.update(pedido_id=compra.get("pedido_id"), com_livro=bool(compra.get("com_livro")))
            if linha.get("situacao") == "concluida":
                return {**saida, "estado": "concluida"}
            limite = linha.get("data_limite")
            liberada = _data(compra.get("liberada_em"))
            if limite and liberada and liberada > limite and prazo_dias:
                limite = liberada + timedelta(days=int(prazo_dias))
                saida["data_limite"] = limite
            vencida = bool(limite and hoje > limite and ao_vencer != "alertar") or bool(compra.get("reprovado_por_prazo"))
            return {**saida, "estado": "recompra" if vencida else "comprada"}
        if compra and compra.get("status_pagamento") == "pendente" and compra.get("pagamento_status") == "pendente":
            return {**saida, "estado": "pendente", "pedido_id": compra.get("pedido_id"),
                    "com_livro": bool(compra.get("com_livro"))}
        if linha.get("situacao") == "aguardando":
            return {**saida, "estado": "aguardando"}
        if not d.get("publicado") or not int(d.get("total_aulas") or 0):
            return {**saida, "estado": "em_breve"}
        return {**saida, "estado": "disponivel"}

    def _turmas_loja(self, aluno_id: str) -> List[TurmaLojaOut]:
        hoje = _hoje()
        turmas = self.repo.turmas_do_aluno(aluno_id)
        if not turmas:
            return []
        compras: Dict[str, Dict[str, Any]] = {}
        for c in self.repo.compras_do_aluno(aluno_id):  # já vem da mais relevante para a menos
            compras.setdefault(c["disciplina_id"], c)
        saida = []
        for t in turmas:
            disciplinas = self.repo.disciplinas_venda(t["curso_id"])
            conclusoes = {d_id: dt for (_, d_id), dt in
                          self.carga.conclusoes_ava([aluno_id], [d["id"] for d in disciplinas]).items()}
            inicio = CargaHorariaService._inicio_aluno(t.get("data_inicio"), t.get("data_matricula"))
            crono, regras = self._cronograma(t["id"], t["curso_id"], inicio, conclusoes, hoje)
            itens = []
            for d in disciplinas:
                estado = self._estado(d, crono.get(d["id"], {}), compras.get(d["id"]), regras.ead_ao_vencer, hoje)
                itens.append(DisciplinaLojaOut(
                    id=d["id"], nome=d["nome"], semestre=d.get("semestre"), carga_horaria=int(d.get("carga_horaria") or 0),
                    capa_url=d.get("capa_url"), descricao=d.get("descricao_ava"), total_aulas=int(d.get("total_aulas") or 0),
                    valor_ead=float(d["valor_ead"]), livro_disponivel=bool(d["livro_disponivel"]),
                    valor_livro_ead=float(d["valor_livro_ead"]), **estado,
                ))
            saida.append(TurmaLojaOut(id=t["id"], nome=t["nome"], codigo=t.get("codigo"), curso_id=t["curso_id"],
                                      curso_nome=t["curso_nome"], data_inicio=t.get("data_inicio"),
                                      data_fim=t.get("data_fim"), disciplinas=itens))
        return saida

    def loja(self, ctx: Dict[str, Any]) -> LojaOut:
        aluno_id = ctx["aluno"]["id"]
        turmas = self._turmas_loja(aluno_id)
        minhas = {t.id for t in turmas}
        dados = self.repo.dados_aluno(aluno_id) or {}
        return LojaOut(
            nome=ctx["user"].nome,
            turmas=turmas,
            outras_turmas=[t for t in self.vitrine() if t.id not in minhas],
            endereco=EnderecoOut(**{c: dados.get(c) for c in _CAMPOS_ENDERECO}),
        )

    # ------------------------------------------------------------------ checkout

    def _localizar(self, aluno_id: str, disciplina_id: str, turma_id: Optional[str]) -> tuple[TurmaLojaOut, DisciplinaLojaOut]:
        for t in self._turmas_loja(aluno_id):
            if turma_id and t.id != turma_id:
                continue
            for d in t.disciplinas:
                if d.id == disciplina_id:
                    return t, d
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada nas suas turmas EAD.")

    def _pagador(self, dados: Dict[str, Any], endereco: Dict[str, Any]) -> Pagador:
        nome = f"{dados.get('nome') or ''} {dados.get('sobrenome') or ''}".strip()
        cpf = normalizar_cpf(dados.get("cpf") or "")
        if not nome or not cpf_valido(cpf) or not dados.get("email"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Seu cadastro precisa de nome, CPF válido e e-mail para gerar a cobrança. "
                                       "Fale com a secretaria.")
        return Pagador(
            nome=nome, documento=cpf, email=dados.get("email"), telefone=dados.get("telefone"),
            endereco=EnderecoPagador(**{c: endereco.get(c) for c in _CAMPOS_ENDERECO}),
            referencia=str(dados["aluno_id"]),
        )

    def _cancelar_pedido(self, pedido_id: str, motivo: str) -> None:
        try:
            FinanceiroService(self.fin_repo).alterar_status(pedido_id, "cancelado", None, origem="usuario",
                                                            observacao=motivo, campos={"motivo_cancelamento": motivo})
        except HTTPException:
            pass  # já cancelado/pago: nada a fazer
        self.repo.cancelar_compra_do_pedido(pedido_id)

    def checkout(self, ctx: Dict[str, Any], dados: CheckoutIn) -> PedidoAlunoOut:
        user: UserResponse = ctx["user"]
        aluno_id = ctx["aluno"]["id"]
        turma, d = self._localizar(aluno_id, dados.disciplina_id, dados.turma_id)
        mensagens = {
            "pendente": "Já existe um pagamento em aberto para esta disciplina.",
            "comprada": "Você já comprou esta disciplina.",
            "concluida": "Você já concluiu esta disciplina.",
            "aguardando": "Esta disciplina ainda não foi liberada pelo calendário da sua turma.",
            "em_breve": "O conteúdo desta disciplina ainda não foi publicado. Ela fica à venda assim que for.",
        }
        if d.estado not in ("disponivel", "recompra"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail=mensagens.get(d.estado, "Disciplina indisponível."))
        if dados.com_livro and not d.livro_disponivel:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O livro físico não está disponível para esta disciplina.")

        cadastro = self.repo.dados_aluno(aluno_id) or {}
        endereco = {c: cadastro.get(c) for c in _CAMPOS_ENDERECO}
        if dados.endereco:
            endereco = dados.endereco.model_dump()
            endereco["cep"] = "".join(filter(str.isdigit, endereco["cep"]))
            endereco["uf"] = endereco["uf"].upper()
            self.repo.salvar_endereco(cadastro["usuario_id"], endereco)
        if dados.com_livro and not all(endereco.get(c) for c in ("cep", "logradouro", "numero", "cidade", "uf")):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o endereço de entrega do livro.")
        pagador = self._pagador(cadastro, endereco)

        # Cobranças antigas vencidas/canceladas da mesma disciplina saem do caminho.
        for antigo in self.repo.cancelar_compras_abertas(aluno_id, d.id):
            self._cancelar_pedido(antigo, "Substituído por nova compra")

        tipo = "ead_livro" if dados.com_livro else "ead"
        itens = [{"produto_id": None, "disciplina_id": None, "descricao": f"Disciplina EAD — {d.nome}",
                  "quantidade": 1, "valor_unitario": regras_pedido.arredondar(d.valor_ead),
                  "valor_total": regras_pedido.arredondar(d.valor_ead)}]
        if dados.com_livro:
            # disciplina_id no item do livro: a logística baixa o Estoque Central de livros no envio.
            itens.append({"produto_id": None, "disciplina_id": d.id, "descricao": f"Livro físico — {d.nome}",
                          "quantidade": 1, "valor_unitario": regras_pedido.arredondar(d.valor_livro_ead),
                          "valor_total": regras_pedido.arredondar(d.valor_livro_ead)})
        bruto, desconto, total = regras_pedido.calcular_totais([(i["valor_unitario"], i["quantidade"]) for i in itens])
        entrega = {f"entrega_{c}": endereco.get(c) for c in _CAMPOS_ENDERECO} if dados.com_livro else {}
        if dados.com_livro:
            entrega["entrega_nome"] = pagador.nome
            entrega["entrega_telefone"] = pagador.telefone
        pedido_id = self.fin_repo.create_pedido({
            "tipo": tipo, "polo_id": None, "escola_id": None, "aluno_id": aluno_id, "solicitante_id": user.id,
            "status": "aguardando_pagamento", "valor_bruto": bruto, "desconto": desconto, "valor_total": total,
            "observacao": f"Aluno EAD · {turma.nome}", **entrega,
        }, itens, user.id)
        self.repo.criar_compra({"aluno_id": aluno_id, "disciplina_id": d.id, "valor": float(total),
                                "pedido_id": pedido_id, "turma_id": turma.id, "com_livro": dados.com_livro})
        try:
            CobrancaService(self.fin_repo).gerar_cobranca_aluno(pedido_id, dados.meio, pagador, aluno_id)
        except HTTPException:
            self._cancelar_pedido(pedido_id, "Falha ao gerar a cobrança")
            raise
        return self.pedido(ctx, pedido_id)

    # ------------------------------------------------------------------ pedidos

    def pedidos(self, ctx: Dict[str, Any]) -> List[PedidoAlunoOut]:
        return [PedidoAlunoOut(**p) for p in self.repo.pedidos_do_aluno(ctx["aluno"]["id"])]

    def pedido(self, ctx: Dict[str, Any], pedido_id: str) -> PedidoAlunoOut:
        from app.modules.ava.repository import uuid_valido

        linhas = self.repo.pedidos_do_aluno(ctx["aluno"]["id"], pedido_id) if uuid_valido(pedido_id) else []
        if not linhas:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
        return PedidoAlunoOut(**linhas[0])

    def cancelar(self, ctx: Dict[str, Any], pedido_id: str) -> PedidoAlunoOut:
        p = self.pedido(ctx, pedido_id)
        if p.status != "aguardando_pagamento":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Só pedidos aguardando pagamento podem ser cancelados.")
        cobranca = CobrancaService(self.fin_repo)
        if p.pagamento_id and p.pagamento_status in ("pendente", "vencido"):
            cobranca.cancelar_pagamento(p.pagamento_id, ctx["user"])
        self._cancelar_pedido(p.id, "Cancelado pelo aluno")
        return self.pedido(ctx, pedido_id)
