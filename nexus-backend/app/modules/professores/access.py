"""Regras de autorização docente baseadas nos vínculos acadêmicos."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import get_db_cursor
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.professores.repository import get_professores_repository


def usuario_eh_professor(user: UserResponse) -> bool:
    return perfil_do_usuario(user) == "professor"


def exigir_vinculo_disciplina(user: UserResponse, disciplina_id: str) -> None:
    if not usuario_eh_professor(user):
        return
    if not get_professores_repository().professor_tem_disciplina(
        str(user.id), str(disciplina_id)
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Professor sem vínculo com esta disciplina",
        )


def listar_vinculos_academicos_docente(user: UserResponse) -> List[Dict[str, Any]]:
    if not usuario_eh_professor(user):
        return []
    return get_professores_repository().list_vinculos_academicos_por_usuario(str(user.id))


def exigir_vinculo_professor_disciplina(user: UserResponse, vinculo_id: str) -> None:
    if not usuario_eh_professor(user):
        return
    if not any(
        str(vinculo.get("id")) == str(vinculo_id)
        for vinculo in listar_vinculos_academicos_docente(user)
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Professor sem vínculo com esta turma",
        )


def exigir_vinculo_turma_docente(
    user: UserResponse,
    aluno_id: str,
    professor_disciplina_id: Optional[str] = None,
    disciplina_id: Optional[str] = None,
    turma_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not usuario_eh_professor(user):
        return None

    if not professor_disciplina_id and (not disciplina_id or not turma_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Disciplina e turma são obrigatórias para esta ação docente",
        )

    vinculos = get_professores_repository().list_vinculos_academicos_por_usuario(str(user.id))
    vinculo = next(
        (
            item
            for item in vinculos
            if item.get("turma_id")
            and (
                not professor_disciplina_id
                or str(item.get("id")) == str(professor_disciplina_id)
            )
            and (not disciplina_id or str(item.get("disciplina_id")) == str(disciplina_id))
            and (not turma_id or str(item.get("turma_id")) == str(turma_id))
        ),
        None,
    )
    if not vinculo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Professor sem vínculo com esta disciplina ou turma",
        )
    if not aluno_vinculado_a_turma(aluno_id, str(vinculo["turma_id"])):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Aluno não matriculado na turma vinculada ao professor",
        )
    return vinculo


def aluno_vinculado_a_turma(aluno_id: str, turma_id: str) -> bool:
    if not turma_id:
        return False
    if not settings.PG_DSN:
        from app.modules.turmas import _turma_alunos_db

        return any(
            str(vinculo.get("aluno_id")) == str(aluno_id)
            and str(vinculo.get("turma_id")) == str(turma_id)
            for vinculo in _turma_alunos_db
        )

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM turma_alunos
                WHERE aluno_id = %s AND turma_id = %s
            ) AS vinculado
            """,
            (str(aluno_id), str(turma_id)),
        )
        return bool(cur.fetchone()["vinculado"])
