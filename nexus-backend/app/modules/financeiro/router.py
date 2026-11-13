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
from app.modules.financeiro.schemas import (
    Ambiente,
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
    TipoPedido,
)
from app.modules.financeiro.cobranca_service import CobrancaService
from app.modules.financeiro.service import FinanceiroService

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
            tipo=tipo, pedido_id=pedido_id, limit=limit, offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
        ) from exc


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
    service: FinanceiroService = Depends(get_financeiro_service),
):
    """Baixa manual de pagamento, conclusão ou cancelamento (com motivo)."""
    campos = {"motivo_cancelamento": payload.motivo_cancelamento} if payload.status == "cancelado" else None
    return service.alterar_status(
        pedido_id, payload.status, current_user.id, origem="usuario",
        observacao=payload.observacao or payload.motivo_cancelamento, campos=campos,
    )


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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CobrancaService = Depends(get_cobranca_service),
):
    return service.listar_webhooks(gateway, status_filtro, limit, offset)


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
