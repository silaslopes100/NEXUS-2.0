"""Módulo de Transferências Acadêmicas entre Polos e Unidades do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/transferencias", tags=["Transferências Acadêmicas"])


class TransferenciaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    tipo: str = "polo_para_polo"
    polo_origem_id: Optional[str] = None
    polo_destino_id: Optional[str] = None
    solicitado_por: Optional[str] = None
    status: str = "pendente"
    resolvido_em: Optional[datetime] = None


_transferencias_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[TransferenciaSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_transferencias(status_filter: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, aluno_id, tipo, polo_origem_id, polo_destino_id, solicitado_por, status, resolvido_em FROM solicitacoes_transferencia"
            if status_filter:
                sql += " WHERE status = %s"
                cur.execute(sql, (status_filter,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_transferencias_db.values())


@router.post("", response_model=TransferenciaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def solicitar_transferencia(dados: TransferenciaSchema, current_user: UserResponse = Depends(get_current_user)):
    new_id = str(uuid.uuid4())
    t_dict = dados.model_dump()
    t_dict["id"] = new_id
    t_dict["solicitado_por"] = current_user.id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO solicitacoes_transferencia (id, aluno_id, tipo, polo_origem_id, polo_destino_id, solicitado_por, status, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.aluno_id, dados.tipo, dados.polo_origem_id, dados.polo_destino_id, current_user.id, dados.status))
    except Exception:
        _transferencias_db[new_id] = t_dict
    return t_dict


@router.put("/{transferencia_id}/resolver", response_model=TransferenciaSchema, dependencies=[Depends(require_role(["admin"]))])
async def resolver_transferencia(transferencia_id: str, aprovado: bool = True):
    novo_status = "aprovada" if aprovado else "rejeitada"
    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE solicitacoes_transferencia SET status = %s, resolvido_em = now(), atualizado_em = now() WHERE id = %s RETURNING id, aluno_id, tipo, polo_origem_id, polo_destino_id, solicitado_por, status, resolvido_em", (novo_status, transferencia_id))
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception:
        if transferencia_id in _transferencias_db:
            _transferencias_db[transferencia_id]["status"] = novo_status
            _transferencias_db[transferencia_id]["resolvido_em"] = datetime.now(timezone.utc)
            return _transferencias_db[transferencia_id]
    if transferencia_id in _transferencias_db:
        _transferencias_db[transferencia_id]["status"] = novo_status
        _transferencias_db[transferencia_id]["resolvido_em"] = datetime.now(timezone.utc)
        return _transferencias_db[transferencia_id]
    raise HTTPException(status_code=404, detail="Transferência não encontrada")
