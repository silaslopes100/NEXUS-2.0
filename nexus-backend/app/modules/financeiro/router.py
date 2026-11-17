"""Rotas do módulo Financeiro (catálogo, pedidos, pagamentos, cobrança, gateways, webhooks e cron)."""
from __future__ import annotations

import hmac
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import ValidationError

from app.core.config import settings
from app.modules.auth.dependencies import get_current_user, require_area, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.financeiro.repository import FinanceiroRepositoryInterface, get_financeiro_repository
from app.modules.financeiro.operacao_service import OperacaoService
from app.modules.financeiro.relatorios import RelatoriosService
from app.modules.financeiro.schemas import (
    Ambiente,
    CheckoutOpcoesResponse,
    CheckoutRequest,
    CheckoutResponse,
    EntregaConfirmar,
    EnvioCreate,
    PedidoUpdate,
    RegraPagamentoCreate,
    RegraPagamentoResponse,
    RegraPagamentoUpdate,
    VendasKpisResponse,
    VendasSerieItem,
    CobrancaRequest,
    FiltrosPeriodo,
    GatewayConfigUpdate,
    GatewayNome,
    PagamentoResponse,
    PagamentoListResponse,
    PedidoCreate,
    PedidoListResponse,
    PedidoResponse,
    PedidoStatusUpdate,
    ProdutoCreate,
    ProdutoListResponse,
    ProdutoResponse,
    ProdutoUpdate,
    SimularPagamentoRequest,
    TipoPedido,
)
from app.modules.financeiro.cobranca_service import CobrancaService
from app.modules.financeiro.service import FinanceiroService, escopo_do_usuario

router = APIRouter(prefix="/financeiro", tags=["Financeiro & Logística"])

# Perfis que consultam pedidos/pagamentos (o escopo é aplicado no service).
_PERFIS_CONSULTA = ["admin", "financeiro", "logistica", "polo", "escola"]


def get_financeiro_service(
    repo: FinanceiroRepositoryInterface = Depends(get_financeiro_repository),
) -> FinanceiroService:
    return FinanceiroService(repo=repo)


def get_cobranca_service(
    repo: FinanceiroRepositoryInterface = Depends(get_financeiro_repository),
) -> CobrancaService:
    return CobrancaService(repo=repo)


def get_operacao_service(
    repo: FinanceiroRepositoryInterface = Depends(get_financeiro_repository),
) -> OperacaoService:
    return OperacaoService(repo=repo)


def filtros_periodo(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    mes: Optional[int] = Query(None, ge=1, le=12),
    semestre: Optional[int] = Query(None, ge=1, le=2),
    ano: Optional[int] = Query(None, ge=2000, le=2100),
    polo_id: Optional[str] = None,
    escola_id: Optional[str] = None,
    modalidade: Optional[str] = Query(None, pattern="^ead$"),
    status_filtro: Optional[str] = Query(None, alias="status"),
    tipo: Optional[TipoPedido] = None,
    pedido_id: Optional[str] = None,
    gateway: Optional[str] = None,
    meio: Optional[str] = Query(None, pattern="^(BOLETO|PIX|CREDIT_CARD)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> FiltrosPeriodo:
    """Filtros padrão do módulo (data início/fim, mês, semestre, ano, Polo, Escola...).

    Polo e Escola não são obrigatórios, para não restringir a busca.
    """
    try:
        return FiltrosPeriodo(
            data_inicio=data_inicio, data_fim=data_fim, mes=mes, semestre=semestre, ano=ano,
            polo_id=polo_id, escola_id=escola_id, modalidade=modalidade, status=status_filtro,
            tipo=tipo, pedido_id=pedido_id, gateway=gateway, meio=meio, limit=limit, offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
        ) from exc


def get_relatorios_service(
    repo: FinanceiroRepositoryInterface = Depends(get_financeiro_repository),
) -> RelatoriosService:
    return RelatoriosService(repo=repo)


# ---------------------------------------------------------------------------
# Exportações e etiqueta (Fase 4) — declaradas antes das rotas /{id}
# ---------------------------------------------------------------------------

_FORMATO = Query("pdf", pattern="^(pdf|xlsx)$", description="pdf ou xlsx")


@router.get("/vendas/exportar", dependencies=[Depends(require_area("financeiro"))])
async def exportar_vendas(
    formato: str = _FORMATO,
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    service: RelatoriosService = Depends(get_relatorios_service),
):
    """Relatório de vendas (KPIs, mensal, top Polos, status e pedidos pagos) com os filtros da tela."""
    return service.vendas(filtros, formato, current_user)


@router.get("/pagamentos/exportar", dependencies=[Depends(require_area("financeiro"))])
async def exportar_pagamentos(
    formato: str = _FORMATO,
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    service: RelatoriosService = Depends(get_relatorios_service),
):
    """Histórico de boletos/PIX com resumo por status."""
    return service.pagamentos(filtros, formato, current_user)


@router.get("/pedidos/exportar", dependencies=[Depends(require_area("financeiro", "logistica"))])
async def exportar_pedidos(
    formato: str = _FORMATO,
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    service: RelatoriosService = Depends(get_relatorios_service),
):
    """Histórico de pedidos (inclui envio/rastreio). No XLSX, aba extra com os itens."""
    return service.pedidos(filtros, formato, current_user)


@router.get("/pedidos/{pedido_id}/etiqueta", dependencies=[Depends(require_area("logistica"))])
async def etiqueta_pedido(
    pedido_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: RelatoriosService = Depends(get_relatorios_service),
):
    """Etiqueta 10×15 (uma página por volume + declaração de conteúdo)."""
    return service.etiqueta(pedido_id, current_user)


# ---------------------------------------------------------------------------
# Produtos (catálogo)
# ---------------------------------------------------------------------------

@router.get(
    "/produtos",
    response_model=ProdutoListResponse,
    dependencies=[Depends(require_role(_PERFIS_CONSULTA))],
)
async def list_produtos(
    tipo: Optional[TipoPedido] = None,
    incluir_inativos: bool = False,
    service: FinanceiroService = Depends(get_financeiro_service),
):
    return service.list_produtos(tipo=tipo, ativo=None if incluir_inativos else True)


@router.post(
    "/produtos",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_area("financeiro"))],
)
async def create_produto(
    payload: ProdutoCreate,
    service: FinanceiroService = Depends(get_financeiro_service),
):
    return service.create_produto(payload)


@router.put(
    "/produtos/{produto_id}",
    response_model=ProdutoResponse,
    dependencies=[Depends(require_area("financeiro"))],
)
async def update_produto(
    produto_id: str,
    payload: ProdutoUpdate,
    service: FinanceiroService = Depends(get_financeiro_service),
):
    return service.update_produto(produto_id, payload)


# ---------------------------------------------------------------------------
# Pedidos (consulta)
# ---------------------------------------------------------------------------

@router.get(
    "/pedidos",
    response_model=PedidoListResponse,
    dependencies=[Depends(require_role(_PERFIS_CONSULTA))],
)
async def list_pedidos(
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    service: FinanceiroService = Depends(get_financeiro_service),
):
    return service.list_pedidos(filtros, current_user)


@router.post(
    "/pedidos",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def create_pedido(
    payload: PedidoCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: FinanceiroService = Depends(get_financeiro_service),
):
    """Cria o pedido em 'aguardando_pagamento' (a cobrança no gateway entra na Fase 3)."""
    return service.criar_pedido(payload, current_user)


@router.post(
    "/pedidos/{pedido_id}/status",
    response_model=PedidoResponse,
    dependencies=[Depends(require_area("financeiro"))],
)
async def alterar_status_pedido(
    pedido_id: str,
    payload: PedidoStatusUpdate,
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    """Baixa manual de pagamento, conclusão ou cancelamento (com motivo).

    Cancelar também cancela a cobrança pendente; a baixa manual de licença credita o estoque.
    """
    if payload.status == "cancelado":
        return operacao.cancelar_pedido(pedido_id, payload.motivo_cancelamento or "", current_user)
    return operacao.baixa_manual(pedido_id, payload.status, payload.observacao, current_user)


@router.get(
    "/pedidos/{pedido_id}",
    response_model=PedidoResponse,
    dependencies=[Depends(require_role(_PERFIS_CONSULTA))],
)
async def get_pedido(
    pedido_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: FinanceiroService = Depends(get_financeiro_service),
):
    return service.get_pedido(pedido_id, current_user)


@router.put(
    "/pedidos/{pedido_id}",
    response_model=PedidoResponse,
    dependencies=[Depends(require_area("financeiro", "logistica"))],
)
async def editar_pedido(
    pedido_id: str,
    payload: PedidoUpdate,
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    """Edita endereço/observação; itens só enquanto aguarda pagamento e sem cobrança pendente."""
    return operacao.editar_pedido(pedido_id, payload, current_user)


# ---------------------------------------------------------------------------
# Logística (Fase 3C)
# ---------------------------------------------------------------------------

@router.post(
    "/pedidos/{pedido_id}/envio",
    response_model=PedidoResponse,
    dependencies=[Depends(require_area("logistica"))],
)
async def marcar_enviado(
    pedido_id: str,
    payload: EnvioCreate,
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    """Registra o envio (transportadora, rastreio, volumes, peso) e marca o pedido como enviado."""
    return operacao.marcar_enviado(pedido_id, payload, current_user)


@router.post(
    "/pedidos/{pedido_id}/entregue",
    response_model=PedidoResponse,
    dependencies=[Depends(require_area("logistica"))],
)
async def marcar_entregue(
    pedido_id: str,
    payload: Optional[EntregaConfirmar] = None,
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    return operacao.marcar_entregue(pedido_id, payload.observacao if payload else None, current_user)


# ---------------------------------------------------------------------------
# Checkout e regras de pagamento (Fase 3B)
# ---------------------------------------------------------------------------

@router.get(
    "/checkout/opcoes",
    response_model=CheckoutOpcoesResponse,
    dependencies=[Depends(require_role(["admin", "financeiro", "polo", "escola"]))],
)
async def opcoes_checkout(
    tipo: TipoPedido,
    valor: Optional[float] = Query(None, ge=0),
    polo_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: CobrancaService = Depends(get_cobranca_service),
):
    """Meios de pagamento e vencimento oferecidos pela regra aplicável."""
    escopo = escopo_do_usuario(current_user)
    if escopo.polo_id:
        polo_id = escopo.polo_id
    elif escopo.escola_id:
        polo_id = current_user.polo_id
    return service.opcoes_checkout(tipo, polo_id, valor)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
)
async def checkout(
    payload: CheckoutRequest,
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    """Cria o pedido e gera o boleto/PIX. Se o gateway falhar, o pedido fica aguardando pagamento."""
    return operacao.checkout(payload, current_user)


@router.get("/regras", response_model=list[RegraPagamentoResponse], dependencies=[Depends(require_area("financeiro"))])
async def list_regras(operacao: OperacaoService = Depends(get_operacao_service)):
    return operacao.listar_regras()


@router.post(
    "/regras",
    response_model=RegraPagamentoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_area("financeiro"))],
)
async def create_regra(payload: RegraPagamentoCreate, operacao: OperacaoService = Depends(get_operacao_service)):
    return operacao.criar_regra(payload)


@router.put("/regras/{regra_id}", response_model=RegraPagamentoResponse, dependencies=[Depends(require_area("financeiro"))])
async def update_regra(
    regra_id: str, payload: RegraPagamentoUpdate, operacao: OperacaoService = Depends(get_operacao_service),
):
    return operacao.atualizar_regra(regra_id, payload)


@router.post(
    "/regras/{regra_id}/desativar",
    response_model=RegraPagamentoResponse,
    dependencies=[Depends(require_area("financeiro"))],
)
async def desativar_regra(regra_id: str, operacao: OperacaoService = Depends(get_operacao_service)):
    return operacao.desativar_regra(regra_id)


# ---------------------------------------------------------------------------
# Vendas (Fase 3D)
# ---------------------------------------------------------------------------

@router.get("/vendas/kpis", response_model=VendasKpisResponse, dependencies=[Depends(require_area("financeiro"))])
async def vendas_kpis(
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    return operacao.kpis_vendas(filtros, current_user)


@router.get("/vendas/serie", response_model=list[VendasSerieItem], dependencies=[Depends(require_area("financeiro"))])
async def vendas_serie(
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    """Série mensal (pedidos, pagos e receita) pelo mês de criação do pedido."""
    return operacao.serie_vendas(filtros, current_user)


# ---------------------------------------------------------------------------
# Pagamentos (consulta)
# ---------------------------------------------------------------------------

@router.get(
    "/pagamentos",
    response_model=PagamentoListResponse,
    dependencies=[Depends(require_role(_PERFIS_CONSULTA))],
)
async def list_pagamentos(
    filtros: FiltrosPeriodo = Depends(filtros_periodo),
    current_user: UserResponse = Depends(get_current_user),
    service: FinanceiroService = Depends(get_financeiro_service),
):
    return service.list_pagamentos(filtros, current_user)


@router.get(
    "/pagamentos/{pagamento_id}",
    response_model=PagamentoResponse,
    dependencies=[Depends(require_role(_PERFIS_CONSULTA))],
)
async def get_pagamento(
    pagamento_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: CobrancaService = Depends(get_cobranca_service),
):
    return service.get_pagamento(pagamento_id, current_user)


@router.post(
    "/pagamentos/{pagamento_id}/cancelar",
    response_model=PagamentoResponse,
    dependencies=[Depends(require_area("financeiro"))],
)
async def cancelar_pagamento(
    pagamento_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: CobrancaService = Depends(get_cobranca_service),
):
    """Cancela a cobrança no gateway e no NEXUS (o pedido continua aguardando pagamento)."""
    return service.cancelar_pagamento(pagamento_id, current_user)


@router.post(
    "/pagamentos/{pagamento_id}/segunda-via",
    response_model=PagamentoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_area("financeiro"))],
)
async def segunda_via(
    pagamento_id: str,
    current_user: UserResponse = Depends(get_current_user),
    operacao: OperacaoService = Depends(get_operacao_service),
):
    """Cobrança vencida: cancela e gera outra com novo vencimento (mesmo meio)."""
    return operacao.segunda_via(pagamento_id, current_user)


@router.post(
    "/pagamentos/{pagamento_id}/simular",
    dependencies=[Depends(require_role(["admin"]))],
)
async def simular_pagamento(
    pagamento_id: str,
    payload: SimularPagamentoRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: CobrancaService = Depends(get_cobranca_service),
):
    """Simulador (sandbox): confirma, vence ou cancela a cobrança como se fosse um webhook do gateway."""
    return service.simular(pagamento_id, payload.status, current_user)


# ---------------------------------------------------------------------------
# Cobrança de pedido
# ---------------------------------------------------------------------------

@router.post(
    "/pedidos/{pedido_id}/cobranca",
    response_model=PagamentoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "financeiro", "polo", "escola"]))],
)
async def gerar_cobranca(
    pedido_id: str,
    payload: CobrancaRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: CobrancaService = Depends(get_cobranca_service),
):
    """Gera boleto ou PIX no gateway padrão do ambiente (PAYMENT_ENV)."""
    return service.gerar_cobranca(pedido_id, payload.meio, current_user, payload.gateway)


# ---------------------------------------------------------------------------
# Gateways (configuração)
# ---------------------------------------------------------------------------

@router.get("/gateways", dependencies=[Depends(require_area("financeiro"))])
async def list_gateways(service: CobrancaService = Depends(get_cobranca_service)):
    """Configuração dos gateways por ambiente. Credenciais sempre mascaradas."""
    return service.listar_gateways()


@router.put("/gateways/{gateway}/{ambiente}", dependencies=[Depends(require_role(["admin"]))])
async def salvar_gateway(
    gateway: GatewayNome,
    ambiente: Ambiente,
    payload: GatewayConfigUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: CobrancaService = Depends(get_cobranca_service),
):
    return service.salvar_gateway(gateway, ambiente, payload.model_dump(exclude_unset=True), current_user.id)


@router.post("/gateways/{gateway}/{ambiente}/testar", dependencies=[Depends(require_area("financeiro"))])
async def testar_gateway(
    gateway: GatewayNome,
    ambiente: Ambiente,
    service: CobrancaService = Depends(get_cobranca_service),
):
    return service.testar_gateway(gateway, ambiente)


# ---------------------------------------------------------------------------
# Webhooks (sem JWT: autenticados pela assinatura/token de cada gateway)
# ---------------------------------------------------------------------------

@router.post("/webhooks/{gateway}/{ambiente}", include_in_schema=True)
async def receber_webhook(
    gateway: str,
    ambiente: str,
    request: Request,
    service: CobrancaService = Depends(get_cobranca_service),
):
    corpo = await request.body()
    return service.processar_webhook(gateway, ambiente, dict(request.headers), corpo, dict(request.query_params))


@router.get("/webhooks/eventos", dependencies=[Depends(require_area("financeiro"))])
async def list_webhook_eventos(
    gateway: Optional[str] = None,
    status_filtro: Optional[str] = Query(None, alias="status"),
    payment_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CobrancaService = Depends(get_cobranca_service),
):
    return service.listar_webhooks(gateway, status_filtro, limit, offset, payment_id)


# ---------------------------------------------------------------------------
# Cron (Vercel Cron envia "Authorization: Bearer <CRON_SECRET>")
# ---------------------------------------------------------------------------

@router.get("/cron/reconciliar")
async def cron_reconciliar(
    authorization: Optional[str] = Header(default=None),
    service: CobrancaService = Depends(get_cobranca_service),
):
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="CRON_SECRET não configurado")
    esperado = f"Bearer {settings.CRON_SECRET}"
    if not authorization or not hmac.compare_digest(authorization.encode(), esperado.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    return service.reconciliar()
