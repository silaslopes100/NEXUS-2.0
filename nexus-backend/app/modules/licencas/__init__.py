"""Módulo de Gestão de Estoque e Atribuição de Licenças do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_permissao, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/licencas", tags=["Licenças & Estoque"])


class EstoqueLicencaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    disciplina_id: Optional[str] = None
    quantidade_total: int = 0
    quantidade_disponivel: int = 0


class LicencaAtribuidaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    disciplina_id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    aluno_id: Optional[str] = None
    quantidade: int = 1
    atribuido_por: Optional[str] = None
    atribuido_em: Optional[datetime] = None


_estoque_db: Dict[str, Dict[str, Any]] = {}
_licencas_db: Dict[str, Dict[str, Any]] = {}


@router.get("/estoque", response_model=List[EstoqueLicencaSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_estoque():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, disciplina_id, quantidade_total, quantidade_disponivel FROM estoque_licencas")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_estoque_db.values())


@router.post("/estoque/adicionar", response_model=EstoqueLicencaSchema, dependencies=[Depends(require_role(["admin"]))])
async def adicionar_estoque(disciplina_id: str, quantidade: int):
    new_id = str(uuid.uuid4())
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO estoque_licencas (id, disciplina_id, quantidade_total, quantidade_disponivel, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, now(), now())
                ON CONFLICT (disciplina_id) DO UPDATE SET
                    quantidade_total = estoque_licencas.quantidade_total + EXCLUDED.quantidade_total,
                    quantidade_disponivel = estoque_licencas.quantidade_disponivel + EXCLUDED.quantidade_disponivel,
                    atualizado_em = now()
                RETURNING id, disciplina_id, quantidade_total, quantidade_disponivel
            """
            cur.execute(sql, (new_id, disciplina_id, quantidade, quantidade))
            return dict(cur.fetchone())
    except Exception:
        if disciplina_id in _estoque_db:
            _estoque_db[disciplina_id]["quantidade_total"] += quantidade
            _estoque_db[disciplina_id]["quantidade_disponivel"] += quantidade
            return _estoque_db[disciplina_id]
        item = {"id": new_id, "disciplina_id": disciplina_id, "quantidade_total": quantidade, "quantidade_disponivel": quantidade}
        _estoque_db[disciplina_id] = item
        return item


@router.get("/atribuidas", response_model=List[LicencaAtribuidaSchema], dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def list_licencas_atribuidas(polo_id: Optional[str] = None, escola_id: Optional[str] = None, aluno_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, disciplina_id, polo_id, escola_id, aluno_id, quantidade, atribuido_por, atribuido_em FROM licencas_atribuidas"
            conds, params = [], []
            if polo_id:
                conds.append("polo_id = %s")
                params.append(polo_id)
            if escola_id:
                conds.append("escola_id = %s")
                params.append(escola_id)
            if aluno_id:
                conds.append("aluno_id = %s")
                params.append(aluno_id)
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_licencas_db.values())


@router.post("/atribuir", response_model=LicencaAtribuidaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def atribuir_licenca(dados: LicencaAtribuidaSchema, current_user: UserResponse = Depends(get_current_user)):
    new_id = str(uuid.uuid4())
    l_dict = dados.model_dump()
    l_dict["id"] = new_id
    l_dict["atribuido_por"] = current_user.id
    l_dict["atribuido_em"] = datetime.now(timezone.utc)
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO licencas_atribuidas (id, disciplina_id, polo_id, escola_id, aluno_id, quantidade, atribuido_por, atribuido_em, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now(), now())
            """
            cur.execute(sql, (new_id, dados.disciplina_id, dados.polo_id, dados.escola_id, dados.aluno_id, dados.quantidade, current_user.id))
    except Exception:
        _licencas_db[new_id] = l_dict
    return l_dict
