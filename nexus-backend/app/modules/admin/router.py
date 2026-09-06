"""Rotas HTTP da API Administrativa do NEXUS 2.0."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.admin.dependencies import get_admin_service, require_admin_user
from app.modules.admin.schemas import (
    ConfiguracaoBulkUpdateRequest,
    ConfiguracaoResponse,
    ConfiguracaoSetRequest,
    EtlErroResponse,
    EtlSyncRunListResponse,
    LogAuditoriaListResponse,
    MessageResponse,
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
from app.modules.auth.dependencies import get_client_ip
from app.modules.auth.schemas import UserResponse

router = APIRouter(
    prefix="/admin",
    tags=["Administração Geral"],
    dependencies=[Depends(require_admin_user)],
)


# ==========================================
# 1. CRUD de Usuários Administrativos / Staff
# ==========================================

@router.get(
    "/usuarios",
    response_model=UsuarioListResponse,
    summary="Lista usuários do sistema com filtros e paginação",
)
async def list_usuarios(
    q: Optional[str] = Query(None, description="Busca por nome, sobrenome, e-mail ou CPF"),
    perfil_id: Optional[str] = Query(None, description="Filtra por ID do perfil"),
    perfil: Optional[str] = Query(None, description="Filtra por nome do perfil (admin, polo, escola, professor, aluno)"),
    status: Optional[str] = Query(None, description="Filtra por status (ativo, inativo, bloqueado)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioListResponse:
    return service.list_usuarios(
        query=q,
        perfil_id=perfil_id,
        perfil_nome=perfil,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioAdminResponse,
    summary="Obtém detalhes completos de um usuário e suas permissões",
)
async def get_usuario(
    usuario_id: str,
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    return service.get_usuario(usuario_id)


@router.post(
    "/usuarios",
    response_model=UsuarioAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário interno ou administrativo com perfil e permissões",
)
async def create_usuario(
    dados: UsuarioCreateRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    client_ip = get_client_ip(request)
    return service.create_usuario(
        dados=dados,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioAdminResponse,
    summary="Atualiza dados cadastrais, perfil, status ou permissões de um usuário",
)
async def update_usuario(
    usuario_id: str,
    dados: UsuarioUpdateRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    client_ip = get_client_ip(request)
    return service.update_usuario(
        user_id=usuario_id,
        dados=dados,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.put(
    "/usuarios/{usuario_id}/permissoes",
    response_model=UsuarioAdminResponse,
    summary="Atualiza a lista de permissões granulares de um usuário",
)
async def update_usuario_permissoes(
    usuario_id: str,
    dados: UsuarioPermissoesUpdateRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    client_ip = get_client_ip(request)
    return service.update_usuario_permissoes(
        user_id=usuario_id,
        dados=dados,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.post(
    "/usuarios/{usuario_id}/reset-senha",
    response_model=MessageResponse,
    summary="Redefine a senha de um usuário administrativamente com Argon2id",
)
async def reset_usuario_senha(
    usuario_id: str,
    dados: UsuarioSenhaResetRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    resultado = service.reset_usuario_senha(
        user_id=usuario_id,
        nova_senha=dados.nova_senha,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )
    return MessageResponse(message=resultado["message"])


@router.delete(
    "/usuarios/{usuario_id}",
    response_model=MessageResponse,
    summary="Exclui um usuário do sistema com registro em auditoria",
)
async def delete_usuario(
    usuario_id: str,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    resultado = service.delete_usuario(
        user_id=usuario_id,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )
    return MessageResponse(message=resultado["message"])


# ==========================================
# 2. Perfis & Permissões Granulares
# ==========================================

@router.get(
    "/perfis",
    response_model=List[PerfilItemResponse],
    summary="Lista todos os perfis de acesso cadastrados",
)
async def list_perfis(
    service: AdminService = Depends(get_admin_service),
) -> List[PerfilItemResponse]:
    return service.list_perfis()


@router.get(
    "/permissoes",
    response_model=List[PermissaoItemResponse],
    summary="Lista todas as chaves de permissões granulares disponíveis",
)
async def list_permissoes(
    service: AdminService = Depends(get_admin_service),
) -> List[PermissaoItemResponse]:
    return service.list_permissoes()


# ==========================================
# 3. Logs de Auditoria
# ==========================================

@router.get(
    "/logs-auditoria",
    response_model=LogAuditoriaListResponse,
    summary="Consulta os logs de auditoria do sistema com filtros avançados",
)
async def list_audit_logs(
    usuario_id: Optional[str] = Query(None, description="Filtra por ID do usuário executor"),
    entidade: Optional[str] = Query(None, description="Filtra por entidade (usuarios, configuracoes, etc.)"),
    acao: Optional[str] = Query(None, description="Filtra por tipo de ação (ex: login_sucesso, configuracao_atualizada)"),
    data_inicio: Optional[datetime] = Query(None, description="Data/hora inicial (ISO 8601)"),
    data_fim: Optional[datetime] = Query(None, description="Data/hora final (ISO 8601)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> LogAuditoriaListResponse:
    return service.list_audit_logs(
        usuario_id=usuario_id,
        entidade=entidade,
        acao=acao,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )


# ==========================================
# 4. Parâmetros & Configurações Gerais
# ==========================================

@router.get(
    "/configuracoes",
    response_model=List[ConfiguracaoResponse],
    summary="Lista todos os parâmetros e configurações gerais do sistema",
)
async def list_configuracoes(
    service: AdminService = Depends(get_admin_service),
) -> List[ConfiguracaoResponse]:
    return service.list_configuracoes()


@router.get(
    "/configuracoes/{chave}",
    response_model=ConfiguracaoResponse,
    summary="Obtém uma configuração específica pela chave",
)
async def get_configuracao(
    chave: str,
    service: AdminService = Depends(get_admin_service),
) -> ConfiguracaoResponse:
    return service.get_configuracao(chave)


@router.put(
    "/configuracoes/{chave}",
    response_model=ConfiguracaoResponse,
    summary="Cria ou atualiza uma configuração (chave/valor JSONB) com registro em auditoria",
)
async def set_configuracao_by_key(
    chave: str,
    payload: Dict[str, Any],
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConfiguracaoResponse:
    client_ip = get_client_ip(request)
    # Se o corpo for {"valor": ...}, extrai valor, caso contrário usa o payload inteiro
    valor = payload.get("valor", payload) if isinstance(payload, dict) and "valor" in payload else payload
    return service.set_configuracao(
        chave=chave,
        valor=valor,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.put(
    "/configuracoes",
    response_model=ConfiguracaoResponse,
    summary="Cria ou atualiza uma configuração via objeto ConfiguracaoSetRequest",
)
async def set_configuracao_body(
    dados: ConfiguracaoSetRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConfiguracaoResponse:
    client_ip = get_client_ip(request)
    return service.set_configuracao(
        chave=dados.chave,
        valor=dados.valor,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


# ==========================================
# 5. Execuções do Batch de Sincronização (ETL)
# ==========================================

@router.get(
    "/etl/execucoes",
    response_model=EtlSyncRunListResponse,
    summary="Lista as execuções do batch de sincronização diária (etl_sync_runs) com status e totais",
)
async def list_etl_execucoes(
    status: Optional[str] = Query(None, description="Filtra por status da execução (ex: sucesso, erro, rodando)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> EtlSyncRunListResponse:
    return service.list_etl_execucoes(
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/etl/execucoes/{execucao_id}/erros",
    response_model=List[EtlErroResponse],
    summary="Lista os erros detalhados de uma execução do ETL",
)
async def get_etl_execucao_erros(
    execucao_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> List[EtlErroResponse]:
    return service.get_etl_execucao_erros(
        execucao_id=execucao_id,
        limit=limit,
        offset=offset,
    )
