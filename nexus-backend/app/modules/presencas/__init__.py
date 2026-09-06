"""Módulo de Presenças e Diário de Frequência do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/presencas", tags=["Presenças & Frequência"])


class PresencaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    aluno_id: str
    professor_disciplina_id: Optional[str] = None
    numero_aula: Optional[int] = 1
    data_aula: Optional[date] = None
    presente: bool = False


_presencas_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[PresencaSchema], dependencies=[Depends(require_role(["admin", "professor", "polo", "escola", "aluno"]))])
async def list_presencas(aluno_id: Optional[str] = None, professor_disciplina_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, aluno_id, professor_disciplina_id, numero_aula, data_aula, presente FROM presencas"
            conds, params = [], []
            if aluno_id:
                conds.append("aluno_id = %s")
                params.append(aluno_id)
            if professor_disciplina_id:
                conds.append("professor_disciplina_id = %s")
                params.append(professor_disciplina_id)
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            cur.execute(sql, tuple(params))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        pres = list(_presencas_db.values())
        if aluno_id:
            pres = [p for p in pres if p.get("aluno_id") == aluno_id]
        if professor_disciplina_id:
            pres = [p for p in pres if p.get("professor_disciplina_id") == professor_disciplina_id]
        return pres


@router.post("/lancar", response_model=PresencaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def lancar_presenca(dados: PresencaSchema):
    new_id = str(uuid.uuid4())
    p_dict = dados.model_dump()
    p_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = "INSERT INTO presencas (id, aluno_id, professor_disciplina_id, numero_aula, data_aula, presente, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, now(), now())"
            cur.execute(sql, (new_id, dados.aluno_id, dados.professor_disciplina_id, dados.numero_aula, dados.data_aula, dados.presente))
    except Exception:
        _presencas_db[new_id] = p_dict
    return p_dict
