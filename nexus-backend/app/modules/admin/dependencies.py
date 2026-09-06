"""Dependências FastAPI para o módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from app.modules.admin.repository import AdminRepositoryInterface, get_admin_repository
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse


def get_admin_service(
    repo: AdminRepositoryInterface = Depends(get_admin_repository),
) -> AdminService:
    """Provedor injetável da camada de serviço de administração."""
    return AdminService(repo=repo)


async def require_admin_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Valida se o usuário autenticado possui o perfil 'admin'."""
    role = (current_user.perfil.nome if current_user.perfil else "").lower().strip()
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: apenas administradores com permissão de sistema podem acessar este recurso",
        )
    return current_user
