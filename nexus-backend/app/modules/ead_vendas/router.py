"""Rotas das vendas EAD: vitrine pública (/ead/vitrine) e loja do aluno EAD (/ead/loja)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import get_client_ip
from app.modules.auth.schemas import LoginResponse
from app.modules.ava.acesso import require_aluno_ead
from app.modules.ead_vendas.repository import get_vendas_ead_repository
from app.modules.ead_vendas.schemas import (
    CheckoutIn,
    InscricaoIn,
    LojaOut,
    PedidoAlunoOut,
    TurmaVitrineDetalheOut,
    TurmaVitrineOut,
)
from app.modules.ead_vendas.service import VendasEadService

vitrine_router = APIRouter(prefix="/ead/vitrine", tags=["Vendas EAD — vitrine pública"])
loja_router = APIRouter(prefix="/ead/loja", tags=["Vendas EAD — loja do aluno"])


def get_service() -> VendasEadService:
    return VendasEadService(get_vendas_ead_repository())


# ---------------------------------------------------------------------------- vitrine (sem login)

@vitrine_router.get("/turmas", response_model=List[TurmaVitrineOut])
async def turmas(service: VendasEadService = Depends(get_service)):
    return service.vitrine()


@vitrine_router.get("/turmas/{turma_id}", response_model=TurmaVitrineDetalheOut)
async def turma(turma_id: str, service: VendasEadService = Depends(get_service)):
    return service.turma(turma_id)


@vitrine_router.post("/inscricao", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def inscricao(payload: InscricaoIn, ip: Optional[str] = Depends(get_client_ip),
                    service: VendasEadService = Depends(get_service)):
    return service.inscrever(payload, ip)


# ---------------------------------------------------------------------------- loja (aluno EAD)

@loja_router.get("", response_model=LojaOut)
async def loja(ctx: Dict[str, Any] = Depends(require_aluno_ead), service: VendasEadService = Depends(get_service)):
    return service.loja(ctx)


@loja_router.post("/turmas/{turma_id}/inscrever", response_model=LojaOut)
async def entrar_na_turma(turma_id: str, ctx: Dict[str, Any] = Depends(require_aluno_ead),
                          service: VendasEadService = Depends(get_service)):
    return service.inscrever_aluno(ctx, turma_id)


@loja_router.post("/checkout", response_model=PedidoAlunoOut, status_code=status.HTTP_201_CREATED)
async def checkout(payload: CheckoutIn, ctx: Dict[str, Any] = Depends(require_aluno_ead),
                   service: VendasEadService = Depends(get_service)):
    return service.checkout(ctx, payload)


@loja_router.get("/pedidos", response_model=List[PedidoAlunoOut])
async def pedidos(ctx: Dict[str, Any] = Depends(require_aluno_ead), service: VendasEadService = Depends(get_service)):
    return service.pedidos(ctx)


@loja_router.get("/pedidos/{pedido_id}", response_model=PedidoAlunoOut)
async def pedido(pedido_id: str, ctx: Dict[str, Any] = Depends(require_aluno_ead),
                 service: VendasEadService = Depends(get_service)):
    return service.pedido(ctx, pedido_id)


@loja_router.post("/pedidos/{pedido_id}/cancelar", response_model=PedidoAlunoOut)
async def cancelar(pedido_id: str, ctx: Dict[str, Any] = Depends(require_aluno_ead),
                   service: VendasEadService = Depends(get_service)):
    return service.cancelar(ctx, pedido_id)
