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
    escola_id: Optional[str] = None
    polo_id: Optional[str] = None
    quantidade_total: int = 0
    quantidade_disponivel: int = 0


class DistribuicaoEstoqueRequest(BaseModel):
    disciplina_id: str
    escola_id: str
    quantidade: int


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
_estoque_por_escola_db: Dict[str, Dict[str, Any]] = {}
_licencas_db: Dict[str, Dict[str, Any]] = {}


def _get_estoque_global(disciplina_id: str) -> Dict[str, Any]:
    if disciplina_id not in _estoque_db:
        _estoque_db[disciplina_id] = {
            "id": str(uuid.uuid4()),
            "disciplina_id": disciplina_id,
            "escola_id": None,
            "polo_id": None,
            "quantidade_total": 0,
            "quantidade_disponivel": 0,
        }
    return _estoque_db[disciplina_id]


def _get_estoque_escola(disciplina_id: str, escola_id: str) -> Dict[str, Any]:
    key = f"{disciplina_id}:{escola_id}"
    if key not in _estoque_por_escola_db:
        _estoque_por_escola_db[key] = {
            "id": str(uuid.uuid4()),
            "disciplina_id": disciplina_id,
            "escola_id": escola_id,
            "polo_id": None,
            "quantidade_total": 0,
            "quantidade_disponivel": 0,
        }
    return _estoque_por_escola_db[key]


@router.get("/estoque", response_model=List[EstoqueLicencaSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_estoque(disciplina_id: Optional[str] = None, escola_id: Optional[str] = None):
    if escola_id:
        items = [item for item in _estoque_por_escola_db.values() if item.get("escola_id") == escola_id]
        if disciplina_id:
            items = [item for item in items if item.get("disciplina_id") == disciplina_id]
        return items

    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, disciplina_id, quantidade_total, quantidade_disponivel FROM estoque_licencas"
            conds, params = [], []
            if disciplina_id:
                conds.append("disciplina_id = %s")
                params.append(disciplina_id)
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            cur.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
            return [{**row, "escola_id": None, "polo_id": None} for row in rows]
    except Exception:
        items = list(_estoque_db.values())
        if disciplina_id:
            items = [item for item in items if item.get("disciplina_id") == disciplina_id]
        return items


@router.post("/estoque/adicionar", response_model=EstoqueLicencaSchema, dependencies=[Depends(require_role(["admin"]))])
async def adicionar_estoque(disciplina_id: str, quantidade: int):
    if quantidade <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade deve ser maior que zero.")

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
        item = _get_estoque_global(disciplina_id)
        item["quantidade_total"] += quantidade
        item["quantidade_disponivel"] += quantidade
        return item


@router.post("/estoque/distribuir", response_model=EstoqueLicencaSchema, dependencies=[Depends(require_role(["admin"]))])
async def distribuir_estoque(dados: DistribuicaoEstoqueRequest):
    if dados.quantidade <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade deve ser maior que zero.")

    item = _get_estoque_global(dados.disciplina_id)
    if item["quantidade_disponivel"] < dados.quantidade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estoque global insuficiente para esta distribuição.")

    item["quantidade_disponivel"] -= dados.quantidade

    escola_item = _get_estoque_escola(dados.disciplina_id, dados.escola_id)
    escola_item["quantidade_total"] += dados.quantidade
    escola_item["quantidade_disponivel"] += dados.quantidade
    return escola_item


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
    if dados.quantidade <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantidade deve ser maior que zero.")

    if dados.escola_id:
        escola_item = _get_estoque_escola(dados.disciplina_id or "", dados.escola_id)
        if escola_item["quantidade_disponivel"] < dados.quantidade:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estoque da escola insuficiente para esta atribuição.")
        escola_item["quantidade_disponivel"] -= dados.quantidade
        if escola_item["quantidade_disponivel"] <= 0:
            escola_item["quantidade_disponivel"] = 0
    else:
        item = _get_estoque_global(dados.disciplina_id or "")
        if item["quantidade_disponivel"] < dados.quantidade:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estoque insuficiente para esta atribuição.")
        item["quantidade_disponivel"] -= dados.quantidade

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
