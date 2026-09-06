"""Módulo de Autenticação do NEXUS 2.0."""
from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_active_user,
    get_current_user,
    require_permissao,
    require_role,
)
from app.modules.auth.repository import (
    AuthRepositoryInterface,
    InMemoryAuthRepository,
    PostgresAuthRepository,
    get_auth_repository,
    set_auth_repository,
)
from app.modules.auth.router import router
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    PerfilResponse,
    PermissaoResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    UserResponse,
)
from app.modules.auth.service import AuthService

__all__ = [
    "router",
    "AuthService",
    "AuthRepositoryInterface",
    "PostgresAuthRepository",
    "InMemoryAuthRepository",
    "get_auth_repository",
    "set_auth_repository",
    "get_auth_service",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_permissao",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "LogoutRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "MessageResponse",
    "UserResponse",
    "PerfilResponse",
    "PermissaoResponse",
]
