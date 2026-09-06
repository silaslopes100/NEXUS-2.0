"""Módulo de Notas, Avaliações e Histórico Unificado do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/notas-historico", tags=["Notas & Histórico Unificado"])


class NotaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    disciplina_id: Optional[str] = None
    turma_id: Optional[str] = None
    origem: str = "ava"
    valor: float
    lancado_por: Optional[str] = None
    lancado_em: Optional[datetime] = None


class HistoricoUnificadoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    disciplina_id: Optional[str] = None
    nota_final: Optional[float] = None
    status: str = "cursando"
    eh_extra_grade: bool = False


_notas_db: Dict[str, Dict[str, Any]] = {}
_historico_db: Dict[str, Dict[str, Any]] = {}


@router.get("/notas", response_model=List[NotaSchema], dependencies=[Depends(require_role(["admin", "professor", "polo", "escola", "aluno"]))])
async def list_notas(aluno_id: Optional[str] = None, disciplina_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, aluno_id, disciplina_id, turma_id, origem, valor, lancado_por, lancado_em FROM notas"
            conds, params = [], []
            if aluno_id:
                conds.append("aluno_id = %s")
                params.append(aluno_id)
            if disciplina_id:
                conds.append("disciplina_id = %s")
                params.append(disciplina_id)
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        notas = list(_notas_db.values())
        if aluno_id:
            notas = [n for n in notas if n.get("aluno_id") == aluno_id]
        if disciplina_id:
            notas = [n for n in notas if n.get("disciplina_id") == disciplina_id]
        return notas


@router.post("/notas", response_model=NotaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def lancar_nota(dados: NotaSchema, current_user: UserResponse = Depends(get_current_user)):
    new_id = str(uuid.uuid4())
    n_dict = dados.model_dump()
    n_dict["id"] = new_id
    n_dict["lancado_por"] = current_user.id
    n_dict["lancado_em"] = datetime.now(timezone.utc)
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO notas (id, aluno_id, disciplina_id, turma_id, origem, valor, lancado_por, lancado_em, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now(), now())
            """
            cur.execute(sql, (new_id, dados.aluno_id, dados.disciplina_id, dados.turma_id, dados.origem, dados.valor, current_user.id))
    except Exception:
        _notas_db[new_id] = n_dict
    return n_dict


@router.get("/historico/{aluno_id}", response_model=List[HistoricoUnificadoSchema], dependencies=[Depends(require_role(["admin", "polo", "escola", "professor", "aluno"]))])
async def get_historico_aluno(aluno_id: str):
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, aluno_id, disciplina_id, nota_final, status, eh_extra_grade FROM historico_unificado WHERE aluno_id = %s", (aluno_id,))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return [h for h in _historico_db.values() if h.get("aluno_id") == aluno_id]
