"""Controle de acesso do AVA: exclusivo do aluno EAD.

Aluno de Polo/Escola (``alunos.modalidade='polo'``) e usuários de Polo/Escola que também são
alunos (``tambem_aluno``) não acessam o AVA.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse

MENSAGEM_SEM_ACESSO = "A Sala de Aula Virtual é exclusiva para alunos EAD."


def aluno_ead_do_usuario(usuario_id: str) -> Dict[str, Any] | None:
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id, modalidade, status FROM alunos WHERE usuario_id = %s AND modalidade = 'ead' LIMIT 1",
            (usuario_id,),
        )
        row = cur.fetchone()
    return {"id": str(row["id"]), "modalidade": row["modalidade"], "status": row["status"]} if row else None


async def require_aluno_ead(user: UserResponse = Depends(get_current_user)) -> Dict[str, Any]:
    """Devolve ``{"user", "aluno"}``; 403 para quem não é aluno EAD ativo."""
    if perfil_do_usuario(user) != "aluno":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=MENSAGEM_SEM_ACESSO)
    aluno = aluno_ead_do_usuario(str(user.id))
    if not aluno:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=MENSAGEM_SEM_ACESSO)
    if aluno["status"] == "desistente":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Sua matrícula precisa ser regularizada para acessar a Sala de Aula Virtual.")
    return {"user": user, "aluno": aluno}


async def require_ava_leitura(user: UserResponse = Depends(get_current_user)) -> Dict[str, Any]:
    """Aluno EAD, ou admin em pré-visualização (``previa=True``: sem travas e sem gravar progresso)."""
    if perfil_do_usuario(user) == "admin":
        return {"user": user, "aluno": None, "previa": True}
    return await require_aluno_ead(user)
