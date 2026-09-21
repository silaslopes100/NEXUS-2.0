"""Dependências FastAPI para o módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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


def get_actor_context(
    current_user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """Converte o usuário autenticado no contexto do ator (RN-02 multi-tenancy)."""
    perfil = (current_user.perfil.nome if current_user.perfil else "").lower().strip()
    polo_id = getattr(current_user, "polo_id", None)
    escola_id = getattr(current_user, "escola_id", None)
    return {
        "user_id": current_user.id,
        "perfil": perfil,
        "global_view": perfil in ("admin", "secretario_geral"),
        "polo_id": polo_id if polo_id else None,
        "escola_id": escola_id if escola_id else None,
    }


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


async def require_permission(
    perm_key: str,
    allow_roles: Optional[List[str]] = None,
) -> UserResponse:
    """Valida acesso baseado em permissão granular ou perfil (RN-02).

    Admin e secretário_geral têm acesso total.
    Outros perfis são validados contra allow_roles.
    """
    async def _dep(
        current_user: UserResponse = Depends(get_current_user),
        repo: AdminRepositoryInterface = Depends(get_admin_repository),
    ) -> UserResponse:
        role = (current_user.perfil.nome if current_user.perfil else "").lower().strip()
        if role in (allow_roles or []) or role == "admin" or role == "secretario_geral":
            return current_user
        try:
            permissoes = repo.list_usuario_permissoes(user_id=current_user.id) if hasattr(repo, "list_usuario_permissoes") else []
            if any(p.get("permissao_id") == perm_key or p.get("chave") == perm_key or p.get("permissao_id") == f"perm-{perm_key}" for p in (permissoes or [])):
                return current_user
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: permissão '{perm_key}' necessária",
        )

    return await _dep()
