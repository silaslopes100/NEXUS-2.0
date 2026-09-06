"""Módulo de Logística e Pedidos de Livros Didáticos do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/pedidos-livros", tags=["Logística & Livros"])


class PedidoLivroItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    disciplina_id: Optional[str] = None
    quantidade: int = 1


class PedidoLivroSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    status: str = "pendente"
    enviado_em: Optional[datetime] = None
    itens: List[PedidoLivroItemSchema] = []


_pedidos_livros_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[PedidoLivroSchema], dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def list_pedidos_livros(polo_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, polo_id, escola_id, status, enviado_em FROM pedidos_livros"
            if polo_id:
                sql += " WHERE polo_id = %s"
                cur.execute(sql, (polo_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_pedidos_livros_db.values())


@router.post("", response_model=PedidoLivroSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def create_pedido_livros(dados: PedidoLivroSchema):
    new_id = str(uuid.uuid4())
    p_dict = dados.model_dump()
    p_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO pedidos_livros (id, polo_id, escola_id, status, enviado_em, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.polo_id, dados.escola_id, dados.status, dados.enviado_em))
            for item in dados.itens:
                cur.execute("INSERT INTO pedidos_livros_itens (id, pedido_livro_id, disciplina_id, quantidade, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, now(), now())", (str(uuid.uuid4()), new_id, item.disciplina_id, item.quantidade))
    except Exception:
        _pedidos_livros_db[new_id] = p_dict
    return p_dict


@router.put("/{pedido_id}/status", response_model=PedidoLivroSchema, dependencies=[Depends(require_role(["admin"]))])
async def update_status_pedido_livro(pedido_id: str, novo_status: str):
    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE pedidos_livros SET status = %s, atualizado_em = now() WHERE id = %s RETURNING id, polo_id, escola_id, status, enviado_em", (novo_status, pedido_id))
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception:
        if pedido_id in _pedidos_livros_db:
            _pedidos_livros_db[pedido_id]["status"] = novo_status
            return _pedidos_livros_db[pedido_id]
    if pedido_id in _pedidos_livros_db:
        _pedidos_livros_db[pedido_id]["status"] = novo_status
        return _pedidos_livros_db[pedido_id]
    raise HTTPException(status_code=404, detail="Pedido não encontrado")
