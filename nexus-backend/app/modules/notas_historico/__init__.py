"""Módulo de Notas, Avaliações e Histórico Unificado do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
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


@router.get(
    "/notas",
    response_model=List[NotaSchema],
    dependencies=[Depends(require_role(["admin", "professor", "polo", "escola", "aluno"]))],
)
async def list_notas(
    aluno_id: Optional[str] = None,
    disciplina_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
):
    eh_professor = usuario_eh_professor(current_user)
    if not settings.PG_DSN:
        notas = list(_notas_db.values())
        if aluno_id:
            notas = [nota for nota in notas if str(nota.get("aluno_id")) == str(aluno_id)]
        if disciplina_id:
            notas = [
                nota for nota in notas
                if str(nota.get("disciplina_id")) == str(disciplina_id)
            ]
        if eh_professor:
            vinculos = listar_vinculos_academicos_docente(current_user)
            if not vinculos:
                return []
            atribuicoes = {
                (str(vinculo["disciplina_id"]), str(vinculo["turma_id"]))
                for vinculo in vinculos
                if vinculo.get("disciplina_id") and vinculo.get("turma_id")
            }
            notas = [
                nota
                for nota in notas
                if (
                    str(nota.get("disciplina_id")),
                    str(nota.get("turma_id")),
                ) in atribuicoes
                and aluno_vinculado_a_turma(
                    str(nota.get("aluno_id")),
                    str(nota.get("turma_id")),
                )
            ]
        return notas

    conds, params = [], []
    if aluno_id:
        conds.append("nota.aluno_id = %s")
        params.append(aluno_id)
    if disciplina_id:
        conds.append("nota.disciplina_id = %s")
        params.append(disciplina_id)
    if eh_professor:
        conds.append(
            """
            EXISTS (
                SELECT 1
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                JOIN turma_alunos matricula
                  ON matricula.turma_id = vinculo.turma_id
                 AND matricula.aluno_id = nota.aluno_id
                WHERE professor.usuario_id = %s
                  AND vinculo.disciplina_id = nota.disciplina_id
                  AND vinculo.turma_id = nota.turma_id
                  AND vinculo.ativo = true
            )
            """
        )
        params.append(str(current_user.id))
    sql = (
        "SELECT nota.id, nota.aluno_id, nota.disciplina_id, nota.turma_id, nota.origem, "
        "nota.valor, nota.lancado_por, nota.lancado_em FROM notas nota"
    )
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


@router.post("/notas", response_model=NotaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "professor"]))])
async def lancar_nota(dados: NotaSchema, current_user: UserResponse = Depends(get_current_user)):
    exigir_vinculo_turma_docente(
        current_user,
        aluno_id=dados.aluno_id,
        disciplina_id=dados.disciplina_id,
        turma_id=dados.turma_id,
    )
    new_id = str(uuid.uuid4())
    n_dict = dados.model_dump()
    n_dict["id"] = new_id
    n_dict["lancado_por"] = current_user.id
    n_dict["lancado_em"] = datetime.now(timezone.utc)
    if not settings.PG_DSN:
        _notas_db[new_id] = n_dict
        return n_dict
    with get_db_cursor() as cur:
        sql = """
            INSERT INTO notas (id, aluno_id, disciplina_id, turma_id, origem, valor, lancado_por, lancado_em, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now(), now())
        """
        cur.execute(
            sql,
            (
                new_id,
                dados.aluno_id,
                dados.disciplina_id,
                dados.turma_id,
                dados.origem,
                dados.valor,
                current_user.id,
            ),
        )
    return n_dict


@router.get(
    "/historico/{aluno_id}",
    response_model=List[HistoricoUnificadoSchema],
    dependencies=[Depends(require_role(["admin", "polo", "escola", "professor", "aluno"]))],
)
async def get_historico_aluno(
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    eh_professor = usuario_eh_professor(current_user)
    if not settings.PG_DSN:
        historico = [
            item for item in _historico_db.values()
            if str(item.get("aluno_id")) == str(aluno_id)
        ]
        if eh_professor:
            vinculos = listar_vinculos_academicos_docente(current_user)
            atribuicoes = {
                (str(vinculo["disciplina_id"]), str(vinculo["turma_id"]))
                for vinculo in vinculos
                if vinculo.get("disciplina_id") and vinculo.get("turma_id")
            }
            if not atribuicoes:
                return []
            historico = [
                item
                for item in historico
                if any(
                    disciplina_id == str(item.get("disciplina_id"))
                    and aluno_vinculado_a_turma(aluno_id, turma_id)
                    for disciplina_id, turma_id in atribuicoes
                )
            ]
        return historico

    sql = (
        "SELECT historico.id, historico.aluno_id, historico.disciplina_id, "
        "historico.nota_final, historico.status, historico.eh_extra_grade "
        "FROM historico_unificado historico WHERE historico.aluno_id = %s"
    )
    params: List[Any] = [aluno_id]
    if eh_professor:
        sql += """
            AND EXISTS (
                SELECT 1
                FROM professor_disciplinas vinculo
                JOIN professores professor ON professor.id = vinculo.professor_id
                JOIN turma_alunos matricula
                  ON matricula.turma_id = vinculo.turma_id
                 AND matricula.aluno_id = historico.aluno_id
                WHERE professor.usuario_id = %s
                  AND vinculo.disciplina_id = historico.disciplina_id
                  AND vinculo.ativo = true
            )
        """
        params.append(str(current_user.id))
    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]
