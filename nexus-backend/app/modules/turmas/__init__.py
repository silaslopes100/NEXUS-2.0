"""Módulo de Turmas e Calendários Oficiais do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/turmas", tags=["Turmas & Calendários"])


class TurmaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    curso_id: Optional[str] = None
    polo_id: Optional[str] = None
    nome: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    calendario_oficial_id: Optional[str] = None


class CalendarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    curso_id: Optional[str] = None
    disciplina_id: Optional[str] = None
    data_liberacao: Optional[date] = None
    data_encerramento: Optional[date] = None


_turmas_db: Dict[str, Dict[str, Any]] = {}
_calendarios_db: Dict[str, Dict[str, Any]] = {}
_turma_alunos_db: List[Dict[str, Any]] = []


@router.get("", response_model=List[TurmaSchema])
async def list_turmas(polo_id: Optional[str] = None, curso_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, curso_id, polo_id, nome, data_inicio, data_fim, calendario_oficial_id FROM turmas"
            conds = []
            params = []
            if polo_id:
                conds.append("polo_id = %s")
                params.append(polo_id)
            if curso_id:
                conds.append("curso_id = %s")
                params.append(curso_id)
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        turmas = list(_turmas_db.values())
        if polo_id:
            turmas = [t for t in turmas if t.get("polo_id") == polo_id]
        return turmas


@router.post("", response_model=TurmaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def create_turma(dados: TurmaSchema):
    new_id = str(uuid.uuid4())
    t_dict = dados.model_dump()
    t_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO turmas (id, curso_id, polo_id, nome, data_inicio, data_fim, calendario_oficial_id, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.curso_id, dados.polo_id, dados.nome, dados.data_inicio, dados.data_fim, dados.calendario_oficial_id))
    except Exception:
        _turmas_db[new_id] = t_dict
    return t_dict


@router.post("/{turma_id}/matricular-aluno", dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def matricular_aluno_turma(turma_id: str, aluno_id: str):
    new_id = str(uuid.uuid4())
    try:
        with get_db_cursor() as cur:
            cur.execute("INSERT INTO turma_alunos (id, turma_id, aluno_id, data_matricula, status, criado_em, atualizado_em) VALUES (%s, %s, %s, now(), 'ativo', now(), now()) ON CONFLICT DO NOTHING", (new_id, turma_id, aluno_id))
    except Exception:
        _turma_alunos_db.append({"turma_id": turma_id, "aluno_id": aluno_id})
    return {"message": "Aluno matriculado na turma com sucesso"}


@router.get("/calendarios", response_model=List[CalendarioSchema])
async def list_calendarios(curso_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, curso_id, disciplina_id, data_liberacao, data_encerramento FROM calendarios_oficiais"
            if curso_id:
                sql += " WHERE curso_id = %s"
                cur.execute(sql, (curso_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_calendarios_db.values())


@router.post("/calendarios", response_model=CalendarioSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_calendario(dados: CalendarioSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO calendarios_oficiais (id, curso_id, disciplina_id, data_liberacao, data_encerramento, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.curso_id, dados.disciplina_id, dados.data_liberacao, dados.data_encerramento))
    except Exception:
        _calendarios_db[new_id] = c_dict
    return c_dict
