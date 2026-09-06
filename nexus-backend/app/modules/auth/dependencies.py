"""Dependências FastAPI para autenticação, perfis e permissões granulares."""
from __future__ import annotations

from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.modules.auth.repository import AuthRepositoryInterface, get_auth_repository
from app.modules.auth.schemas import PerfilResponse, UserResponse
from app.modules.auth.service import AuthService

security_bearer = HTTPBearer(auto_error=False)


def get_auth_service(
    repo: AuthRepositoryInterface = Depends(get_auth_repository),
) -> AuthService:
    """Provedor injetável da camada de serviço de autenticação."""
    return AuthService(repo=repo)


def get_client_ip(request: Request) -> Optional[str]:
    """Obtém o IP do cliente a partir dos headers (X-Forwarded-For) ou da conexão direta."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Extrai e valida o token JWT do header de autorização, retornando o usuário logado."""
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não informado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.credentials
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(payload["sub"])
    user = service.repo.get_user_by_id(user_id)
    if not user or user.get("status") != "ativo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo ou não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    permissoes = service.repo.get_usuario_permissoes(user_id)
    return service._build_user_response(user, permissoes)


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Garante que o usuário autenticado está ativo."""
    if current_user.status != "ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo ou bloqueado",
        )
    return current_user


def require_role(allowed_roles: List[str]) -> Callable:
    """Gera dependência FastAPI para controle de acesso baseado em papéis (RBAC).

    Exemplo:
        @router.get("/polos", dependencies=[Depends(require_role(["admin", "polo"]))])
    """
    normalized_allowed = [r.lower().strip() for r in allowed_roles]

    async def role_checker(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        user_role = current_user.perfil.nome.lower().strip() if current_user.perfil else ""
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: perfil '{user_role}' não possui autorização para este recurso",
            )
        return current_user

    return role_checker


def require_permissao(chave: str) -> Callable:
    """Gera dependência FastAPI para permissões granulares (ex: 'vendas', 'financeiro', 'academico').

    O perfil 'admin' possui acesso total irrestrito.
    Para outros perfis, valida se a chave (ou sua variante 'p_<chave>') está associada ao usuário.
    """
    target_key = chave.lower().strip()
    target_p_key = f"p_{target_key}" if not target_key.startswith("p_") else target_key

    async def permissao_checker(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        # Administrador possui bypass de permissão granular
        if current_user.perfil and current_user.perfil.nome.lower() == "admin":
            return current_user

        user_perms = {p.lower().strip() for p in current_user.permissoes}
        has_permission = (
            target_key in user_perms
            or target_p_key in user_perms
            or (target_key.startswith("p_") and target_key[2:] in user_perms)
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: usuário não possui a permissão '{chave}'",
            )
        return current_user

    return permissao_checker
