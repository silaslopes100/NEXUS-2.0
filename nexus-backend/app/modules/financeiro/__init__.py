"""Módulo Financeiro, Vendas e Integração de Pagamentos do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_permissao, require_role

router = APIRouter(prefix="/financeiro", tags=["Financeiro & Vendas"])


class PedidoLicencaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    itens: Optional[Any] = None
    valor_total: float
    status: str = "pendente"


class PagamentoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    pedido_licenca_id: Optional[str] = None
    compra_disciplina_ead_id: Optional[str] = None
    gateway: str = "asaas"
    asaas_customer_id: Optional[str] = None
    asaas_payment_id: Optional[str] = None
    billing_type: Optional[str] = "PIX"
    valor: float
    status: str = "PENDING"
    boleto_url: Optional[str] = None
    vencimento_em: Optional[date] = None
    pago_em: Optional[datetime] = None


_pedidos_db: Dict[str, Dict[str, Any]] = {}
_pagamentos_db: Dict[str, Dict[str, Any]] = {}


@router.get("/pedidos", response_model=List[PedidoLicencaSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_pedidos_licenca(polo_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, polo_id, escola_id, itens, valor_total, status FROM pedidos_licenca"
            if polo_id:
                sql += " WHERE polo_id = %s"
                cur.execute(sql, (polo_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_pedidos_db.values())


@router.post("/pedidos", response_model=PedidoLicencaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def create_pedido_licenca(dados: PedidoLicencaSchema):
    new_id = str(uuid.uuid4())
    p_dict = dados.model_dump()
    p_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            import json
            sql = "INSERT INTO pedidos_licenca (id, polo_id, escola_id, itens, valor_total, status, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.polo_id, dados.escola_id, json.dumps(dados.itens) if dados.itens else None, dados.valor_total, dados.status))
    except Exception:
        _pedidos_db[new_id] = p_dict
    return p_dict


@router.get("/pagamentos", response_model=List[PagamentoSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_pagamentos(pedido_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, pedido_licenca_id, compra_disciplina_ead_id, gateway, asaas_customer_id, asaas_payment_id, billing_type, valor, status, boleto_url, vencimento_em, pago_em FROM pagamentos"
            if pedido_id:
                sql += " WHERE pedido_licenca_id = %s"
                cur.execute(sql, (pedido_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_pagamentos_db.values())


@router.post("/webhook/asaas")
async def webhook_asaas(payload: Dict[str, Any]):
    event = payload.get("event")
    payment = payload.get("payment", {})
    payment_id = payment.get("id")
    status_pag = payment.get("status")

    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE pagamentos SET status = %s, pago_em = now(), atualizado_em = now() WHERE asaas_payment_id = %s", (status_pag, payment_id))
    except Exception:
        pass

    return {"status": "received", "event": event}
