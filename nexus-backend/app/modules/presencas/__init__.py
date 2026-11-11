"""Módulo de Presenças e Diário de Frequência do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.professores.access import (
    aluno_vinculado_a_turma,
    exigir_vinculo_turma_docente,
    listar_vinculos_academicos_docente,
    usuario_eh_professor,
)

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


@router.get(
    "",
    response_model=List[PresencaSchema],
    dependencies=[Depends(require_role(["admin", "professor", "polo", "escola", "aluno"]))],
)
async def list_presencas(
    aluno_id: Optional[str] = None,
    professor_disciplina_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    eh_professor = usuario_eh_professor(current_user)
    vinculos_docente = listar_vinculos_academicos_docente(current_user)
    ids_vinculos = {str(vinculo["id"]) for vinculo in vinculos_docente}
    if eh_professor and not ids_vinculos:
        return []

    if not settings.PG_DSN:
        presencas = list(_presencas_db.values())
        if aluno_id:
            presencas = [item for item in presencas if str(item.get("aluno_id")) == str(aluno_id)]
        if professor_disciplina_id:
            presencas = [
                item for item in presencas
                if str(item.get("professor_disciplina_id")) == str(professor_disciplina_id)
            ]
        if eh_professor:
            turma_por_vinculo = {
                str(vinculo["id"]): str(vinculo["turma_id"])
                for vinculo in vinculos_docente
                if vinculo.get("turma_id")
            }
            presencas = [
                item
                for item in presencas
                if str(item.get("professor_disciplina_id")) in ids_vinculos
                and str(item.get("professor_disciplina_id")) in turma_por_vinculo
                and aluno_vinculado_a_turma(
                    str(item.get("aluno_id")),
                    turma_por_vinculo[str(item["professor_disciplina_id"])],
                )
            ]
        return presencas

    conds, params = [], []
    if aluno_id:
        conds.append("presenca.aluno_id = %s")
        params.append(aluno_id)
    if professor_disciplina_id:
        conds.append("presenca.professor_disciplina_id = %s")
        params.append(professor_disciplina_id)
    if eh_professor:
        conds.append("presenca.professor_disciplina_id = ANY(%s::uuid[])")
        params.append(list(ids_vinculos))
        conds.append(
            """
            EXISTS (
                SELECT 1
                FROM professor_disciplinas vinculo
                JOIN turma_alunos matricula ON matricula.turma_id = vinculo.turma_id
                WHERE vinculo.id = presenca.professor_disciplina_id
                  AND vinculo.ativo = true
                  AND matricula.aluno_id = presenca.aluno_id
            )
            """
        )
    sql = (
        "SELECT presenca.id, presenca.aluno_id, presenca.professor_disciplina_id, "
        "presenca.numero_aula, presenca.data_aula, presenca.presente FROM presencas presenca"
    )
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


@router.post("/lancar", response_model=PresencaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def lancar_presenca(
    dados: PresencaSchema,
    current_user: UserResponse = Depends(get_current_user),
):
    exigir_vinculo_turma_docente(
        current_user,
        aluno_id=dados.aluno_id,
        professor_disciplina_id=dados.professor_disciplina_id,
    )
    new_id = str(uuid.uuid4())
    p_dict = dados.model_dump()
    p_dict["id"] = new_id
    if not settings.PG_DSN:
        _presencas_db[new_id] = p_dict
        return p_dict
    with get_db_cursor() as cur:
        sql = "INSERT INTO presencas (id, aluno_id, professor_disciplina_id, numero_aula, data_aula, presente, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, %s, %s, now(), now())"
        cur.execute(
            sql,
            (
                new_id,
                dados.aluno_id,
                dados.professor_disciplina_id,
                dados.numero_aula,
                dados.data_aula,
                dados.presente,
            ),
        )
    return p_dict
