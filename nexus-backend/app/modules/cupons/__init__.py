"""Módulo de Cupons Promocionais e Descontos do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/cupons", tags=["Cupons de Desconto"])


class CupomSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    codigo: str
    percentual_desconto: float
    valido_de: Optional[date] = None
    valido_ate: Optional[date] = None


_cupons_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[CupomSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_cupons():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, codigo, percentual_desconto, valido_de, valido_ate FROM cupons")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_cupons_db.values())


@router.post("", response_model=CupomSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_cupom(dados: CupomSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    c_dict["codigo"] = dados.codigo.strip().upper()
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO cupons (id, codigo, percentual_desconto, valido_de, valido_ate, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, c_dict["codigo"], dados.percentual_desconto, dados.valido_de, dados.valido_ate))
    except Exception:
        _cupons_db[new_id] = c_dict
    return c_dict


@router.get("/validar/{codigo}", response_model=CupomSchema)
async def validar_cupom(codigo: str):
    clean_code = codigo.strip().upper()
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, codigo, percentual_desconto, valido_de, valido_ate FROM cupons WHERE codigo = %s", (clean_code,))
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception:
        for c in _cupons_db.values():
            if c["codigo"] == clean_code:
                return c
    raise HTTPException(status_code=404, detail="Cupom de desconto inválido ou inexistente")
