"""Módulo Administrativo Geral do NEXUS 2.0."""
from app.modules.admin.dependencies import get_admin_service, require_admin_user
from app.modules.admin.repository import (
    AdminRepositoryInterface,
    InMemoryAdminRepository,
    PostgresAdminRepository,
    get_admin_repository,
    set_admin_repository,
)
from app.modules.admin.router import router
from app.modules.admin.schemas import (
    ConfiguracaoBulkUpdateRequest,
    ConfiguracaoResponse,
    ConfiguracaoSetRequest,
    EtlErroResponse,
    EtlSyncRunListResponse,
    EtlSyncRunResponse,
    LogAuditoriaListResponse,
    LogAuditoriaResponse,
    PerfilItemResponse,
    PermissaoItemResponse,
    UsuarioAdminResponse,
    UsuarioCreateRequest,
    UsuarioListResponse,
    UsuarioPermissoesUpdateRequest,
    UsuarioSenhaResetRequest,
    UsuarioUpdateRequest,
)
from app.modules.admin.service import AdminService

__all__ = [
    "router",
    "AdminService",
    "AdminRepositoryInterface",
    "PostgresAdminRepository",
    "InMemoryAdminRepository",
    "get_admin_repository",
    "set_admin_repository",
    "get_admin_service",
    "require_admin_user",
    "UsuarioCreateRequest",
    "UsuarioUpdateRequest",
    "UsuarioPermissoesUpdateRequest",
    "UsuarioSenhaResetRequest",
    "UsuarioAdminResponse",
    "UsuarioListResponse",
    "PerfilItemResponse",
    "PermissaoItemResponse",
    "LogAuditoriaResponse",
    "LogAuditoriaListResponse",
    "ConfiguracaoResponse",
    "ConfiguracaoSetRequest",
    "ConfiguracaoBulkUpdateRequest",
    "EtlSyncRunResponse",
    "EtlSyncRunListResponse",
    "EtlErroResponse",
]
