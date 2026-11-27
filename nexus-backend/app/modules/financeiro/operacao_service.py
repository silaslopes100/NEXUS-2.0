"""Operação comercial (Fase 3): regras de pagamento, checkout, logística, vendas e segunda via.

Reaproveita FinanceiroService (pedidos/status) e CobrancaService (gateways).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.schemas import UserResponse
from app.modules.financeiro import pedidos as regras_pedido
from app.modules.financeiro.cobranca_service import CobrancaService
from app.modules.financeiro.repository import FinanceiroRepositoryInterface, regra_generica
from app.modules.financeiro.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    EnvioCreate,
    EstoqueAjusteRequest,
    EstoqueEntradaRequest,
    EstoqueItemResponse,
    EstoqueListResponse,
    EstoqueMovimentacaoResponse,
    FiltrosPeriodo,
    PagamentoResponse,
    PedidoCreate,
    PedidoResponse,
    PedidoUpdate,
    RegraPagamentoCreate,
    RegraPagamentoResponse,
    RegraPagamentoUpdate,
    VendasKpisResponse,
    VendasSerieItem,
)
from app.modules.financeiro.service import (
    _CAMPOS_ENDERECO,
    _ENDERECO_OBRIGATORIO_LIVRO,
    FinanceiroService,
    escopo_do_usuario,
)

logger = logging.getLogger(__name__)


def _bloquear_troca(pedido: PedidoResponse) -> None:
    """A troca só muda de status por "Troca efetuada"/"Recusar" (que devolvem/creditam as licenças)."""
    if regras_pedido.eh_troca(pedido.tipo):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Use \"Troca efetuada\" ou \"Recusar\" para concluir uma troca")


def _regra_response(regra: Dict[str, Any]) -> RegraPagamentoResponse:
    return RegraPagamentoResponse(**{**regra, "generica": regra_generica(regra)})


class OperacaoService:
    def __init__(self, repo: FinanceiroRepositoryInterface, cobranca: Optional[CobrancaService] = None) -> None:
        self.repo = repo
        self.pedidos = FinanceiroService(repo)
        self.cobranca = cobranca or CobrancaService(repo)

    # ------------------------------------------------------------------
    # Regras de pagamento (3B)
    # ------------------------------------------------------------------

    def listar_regras(self) -> List[RegraPagamentoResponse]:
        return [_regra_response(r) for r in self.repo.list_regras()]

    def _garantir_fallback(self, regra_id: Optional[str], futura: Dict[str, Any]) -> None:
        """Sempre deve restar ao menos uma regra genérica ativa (senão o checkout pode ficar sem regra)."""
        outras = [r for r in self.repo.list_regras() if r["id"] != regra_id and r.get("ativo") and regra_generica(r)]
        if not outras and not (futura.get("ativo") and regra_generica(futura)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mantenha ao menos uma regra ativa sem filtros (todos os Polos, todos os tipos, sem valor mínimo).",
            )

    def criar_regra(self, payload: RegraPagamentoCreate) -> RegraPagamentoResponse:
        return _regra_response(self.repo.create_regra(payload.model_dump()))

    def atualizar_regra(self, regra_id: str, payload: RegraPagamentoUpdate) -> RegraPagamentoResponse:
        atual = self.repo.get_regra(regra_id)
        if not atual:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
        campos = payload.model_dump(exclude_unset=True)
        if "meios_permitidos" in campos and campos["meios_permitidos"] is not None:
            campos["meios_permitidos"] = list(dict.fromkeys(campos["meios_permitidos"]))
        if regra_generica(atual):
            self._garantir_fallback(regra_id, {**atual, **campos})
        return _regra_response(self.repo.update_regra(regra_id, campos))

    def desativar_regra(self, regra_id: str) -> RegraPagamentoResponse:
        return self.atualizar_regra(regra_id, RegraPagamentoUpdate(ativo=False))

    # ------------------------------------------------------------------
    # Checkout (3B)
    # ------------------------------------------------------------------

    def checkout(self, payload: CheckoutRequest, user: UserResponse) -> CheckoutResponse:
        """Cria o pedido e gera a cobrança. Se o gateway falhar, o pedido fica aguardando pagamento."""
        dados_pedido = PedidoCreate(**payload.model_dump(exclude={"meio"}))
        pedido = self.pedidos.criar_pedido(dados_pedido, user)
        try:
            pagamento = self.cobranca.gerar_cobranca(pedido.id, payload.meio, user)
        except HTTPException as exc:
            logger.warning("Checkout: pedido %s criado, cobrança falhou: %s", pedido.numero, exc.detail)
            return CheckoutResponse(pedido=pedido, erro_cobranca=str(exc.detail))
        return CheckoutResponse(pedido=self.pedidos.get_pedido(pedido.id, user), pagamento=pagamento)

    # ------------------------------------------------------------------
    # Pedido: cancelamento e edição (3C)
    # ------------------------------------------------------------------

    def cancelar_pedido(self, pedido_id: str, motivo: str, user: UserResponse) -> PedidoResponse:
        """Cancela o pedido; cobrança pendente é cancelada no gateway antes."""
        pedido = self.pedidos.get_pedido(pedido_id, user)
        _bloquear_troca(pedido)
        pendente = self.repo.get_pagamento_pendente_do_pedido(pedido.id)
        if pendente:
            self.cobranca.cancelar_pagamento(pendente["id"], user)
        observacao = None
        if pedido.status == "pago_aguardando_envio":
            observacao = "Pedido já pago: estorno manual necessário no gateway."
        cancelado = self.pedidos.alterar_status(
            pedido.id, "cancelado", user.id, observacao=observacao,
            campos={"motivo_cancelamento": motivo},
        )
        if regras_pedido.eh_ead(pedido.tipo):  # a compra pendente do aluno EAD sai junto
            from app.modules.ead_vendas.repository import get_vendas_ead_repository

            get_vendas_ead_repository().cancelar_compra_do_pedido(str(pedido.id))
        return cancelado

    def baixa_manual(self, pedido_id: str, para: str, observacao: Optional[str], user: UserResponse) -> PedidoResponse:
        """Pagamento recebido fora do gateway (ex.: PIX manual).

        Cancela a cobrança pendente (evita pagamento em dobro) e, para licença, credita o estoque.
        """
        pedido = self.pedidos.get_pedido(pedido_id, user)
        _bloquear_troca(pedido)
        regras_pedido.validar_transicao_para_tipo(pedido.tipo, pedido.status, para)
        pendente = self.repo.get_pagamento_pendente_do_pedido(pedido.id)
        if pendente and pedido.status == "aguardando_pagamento":
            self.cobranca.cancelar_pagamento(pendente["id"], user)
        pagou = pedido.status == "aguardando_pagamento" and para in ("concluido", "pago_aguardando_envio")
        # O crédito vem antes da troca de status: é idempotente, então se algo falhar a baixa pode ser
        # repetida (com o pedido já concluído e sem crédito, não haveria como refazer).
        if pagou and regras_pedido.credita_licenca(pedido.tipo):  # licença avulsa ou kit
            self.cobranca.creditar_licencas(self.repo.get_pedido(pedido.id), user.id)
        atualizado = self.pedidos.alterar_status(pedido.id, para, user.id, observacao=observacao or "Baixa manual")
        if pagou and regras_pedido.eh_ead(pedido.tipo):  # aluno EAD: libera a disciplina no AVA
            from app.modules.ead_vendas.repository import get_vendas_ead_repository

            get_vendas_ead_repository().liberar_compra_do_pedido(str(pedido.id), None, float(pedido.valor_total))
        return atualizado

    def editar_pedido(self, pedido_id: str, payload: PedidoUpdate, user: UserResponse) -> PedidoResponse:
        pedido = self.pedidos.get_pedido(pedido_id, user)
        if pedido.status in ("enviado", "entregue", "concluido", "cancelado"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Pedido não pode mais ser editado neste status")
        campos: Dict[str, Any] = {}
        alteracoes: List[str] = []
        if payload.endereco is not None:
            base = payload.endereco.model_dump()
            campos.update({f"entrega_{c}": base.get(c) for c in _CAMPOS_ENDERECO})
            alteracoes.append("endereço de entrega")
        if payload.observacao is not None:
            campos["observacao"] = payload.observacao
            alteracoes.append("observação")
        itens = None
        if payload.itens is not None:
            if pedido.status != "aguardando_pagamento":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Itens só podem ser alterados enquanto o pedido aguarda pagamento")
            if self.repo.get_pagamento_pendente_do_pedido(pedido.id):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail="Cancele a cobrança pendente antes de alterar os itens")
            itens = self.pedidos._montar_itens(PedidoCreate(tipo=pedido.tipo, polo_id=pedido.polo_id, itens=payload.itens))
            bruto, desconto, total = regras_pedido.calcular_totais([(i["valor_unitario"], i["quantidade"]) for i in itens])
            campos.update(valor_bruto=bruto, desconto=desconto, valor_total=total)
            alteracoes.append("itens")
        if regras_pedido.tem_envio(pedido.tipo) and payload.endereco is not None:
            faltando = [c for c in _ENDERECO_OBRIGATORIO_LIVRO if not campos.get(f"entrega_{c}")]
            if faltando:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Endereço de entrega incompleto: {', '.join(faltando)}")
        if not alteracoes:
            return pedido
        self.repo.update_pedido(pedido.id, campos, itens, user.id, f"Pedido editado: {', '.join(alteracoes)}")
        return self.pedidos.get_pedido(pedido.id, user)

    # ------------------------------------------------------------------
    # Logística (3C)
    # ------------------------------------------------------------------

    def peso_sugerido(self, pedido: PedidoResponse) -> Optional[int]:
        ids = [i.produto_id for i in pedido.itens if i.produto_id]
        produtos = self.repo.get_produtos_por_ids(ids) if ids else {}
        total = 0
        for i in pedido.itens:
            peso = (produtos.get(i.produto_id or "") or {}).get("peso_g")
            if peso:
                total += int(peso) * int(i.quantidade)
        return total or None

    def marcar_enviado(self, pedido_id: str, payload: EnvioCreate, user: UserResponse) -> PedidoResponse:
        pedido = self.pedidos.get_pedido(pedido_id, user)
        if not regras_pedido.tem_envio(pedido.tipo) or pedido.status != "pago_aguardando_envio":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Só pedidos de livro pagos e aguardando envio podem ser enviados")
        dados = payload.model_dump()
        if dados.get("peso_total_g") is None:
            dados["peso_total_g"] = self.peso_sugerido(pedido)
        self.repo.registrar_envio(pedido.id, dados, user.id)
        rastreio = f" · rastreio {payload.codigo_rastreio}" if payload.codigo_rastreio else ""
        enviado = self.pedidos.alterar_status(
            pedido.id, "enviado", user.id, observacao=f"Enviado por {payload.transportadora}{rastreio}",
        )
        # Baixa no Estoque Central. Estoque insuficiente não bloqueia o envio (o saldo fica negativo),
        # e uma falha aqui não desfaz o envio já registrado: fica no log para o admin ajustar o estoque.
        try:
            self.repo.baixar_estoque_envio(pedido.id, user.id, f"Pedido {pedido.numero} enviado")
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao dar baixa no estoque do pedido %s", pedido.id)
        return enviado

    # ------------------------------------------------------------------
    # Estoque Central de livros (por Disciplina)
    # ------------------------------------------------------------------

    def listar_estoque(self, q: Optional[str], curso_id: Optional[str]) -> EstoqueListResponse:
        itens = [EstoqueItemResponse(**i) for i in self.repo.list_estoque(q=q, curso_id=curso_id)]
        return EstoqueListResponse(total=len(itens), items=itens)

    def _movimentar(self, disciplina_id: str, tipo: str, quantidade: int, observacao: Optional[str],
                    user: UserResponse) -> EstoqueItemResponse:
        item = self.repo.movimentar_estoque(disciplina_id, tipo, quantidade, user.id, (observacao or "").strip() or None)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        return EstoqueItemResponse(**item)

    def entrada_estoque(self, disciplina_id: str, payload: EstoqueEntradaRequest, user: UserResponse) -> EstoqueItemResponse:
        return self._movimentar(disciplina_id, "entrada", payload.quantidade, payload.observacao, user)

    def ajustar_estoque(self, disciplina_id: str, payload: EstoqueAjusteRequest, user: UserResponse) -> EstoqueItemResponse:
        return self._movimentar(disciplina_id, "ajuste", payload.quantidade, payload.observacao, user)

    def movimentacoes_estoque(self, disciplina_id: str) -> List[EstoqueMovimentacaoResponse]:
        return [EstoqueMovimentacaoResponse(**m) for m in self.repo.list_movimentacoes_estoque(disciplina_id)]

    def marcar_entregue(self, pedido_id: str, observacao: Optional[str], user: UserResponse) -> PedidoResponse:
        pedido = self.pedidos.get_pedido(pedido_id, user)
        if pedido.status != "enviado":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Só pedidos enviados podem ser marcados como entregues")
        return self.pedidos.alterar_status(pedido.id, "entregue", user.id, observacao=observacao or "Entrega confirmada")

    # ------------------------------------------------------------------
    # Vendas e boletos (3D)
    # ------------------------------------------------------------------

    def kpis_vendas(self, filtros: FiltrosPeriodo, user: UserResponse) -> VendasKpisResponse:
        dados = self.repo.kpis_vendas(filtros, escopo_do_usuario(user))
        pagos = int(dados.get("pedidos_pagos") or 0)
        receita = round(float(dados.get("receita_paga") or 0), 2)
        return VendasKpisResponse(
            pedidos=int(dados.get("pedidos") or 0),
            pedidos_pagos=pagos,
            receita_paga=receita,
            a_receber=round(float(dados.get("a_receber") or 0), 2),
            vencido=round(float(dados.get("vencido") or 0), 2),
            ticket_medio=round(receita / pagos, 2) if pagos else 0.0,
            receita_licencas=round(float(dados.get("receita_licencas") or 0), 2),
            receita_livros=round(float(dados.get("receita_livros") or 0), 2),
            receita_kits=round(float(dados.get("receita_kits") or 0), 2),
            receita_ead=round(float(dados.get("receita_ead") or 0), 2),
            vendas_ead=int(dados.get("vendas_ead") or 0),
            vendas_ead_livro=int(dados.get("vendas_ead_livro") or 0),
            licencas_vendidas=int(dados.get("licencas_vendidas") or 0),
            livros_vendidos=int(dados.get("livros_vendidos") or 0),
            por_status=dados.get("por_status") or [],
            top_polos=dados.get("top_polos") or [],
        )

    def serie_vendas(self, filtros: FiltrosPeriodo, user: UserResponse) -> List[VendasSerieItem]:
        return [VendasSerieItem(**s) for s in self.repo.serie_vendas(filtros, escopo_do_usuario(user))]

    def segunda_via(self, pagamento_id: str, user: UserResponse) -> PagamentoResponse:
        """Boleto/PIX vencido: cancela a cobrança antiga e gera outra com novo vencimento."""
        pg = self.repo.get_pagamento(pagamento_id)
        if not pg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
        if pg.get("status") != "vencido":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Segunda via só para cobranças vencidas")
        pedido = self.repo.get_pedido(pg.get("pedido_id") or "")
        if not pedido or pedido["status"] != "aguardando_pagamento":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O pedido não está mais aguardando pagamento")
        self.cobranca.cancelar_pagamento(pagamento_id, user)
        meio = pg.get("billing_type") if pg.get("billing_type") in ("BOLETO", "PIX") else "BOLETO"
        return self.cobranca.gerar_cobranca(pedido["id"], meio, user, pg.get("gateway"))
