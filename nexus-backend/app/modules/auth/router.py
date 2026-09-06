"""Rotas HTTP da API de Autenticação do NEXUS 2.0."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.modules.auth.dependencies import (
    get_auth_service,
    get_client_ip,
    get_current_user,
    security_bearer,
)
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Efetua login do usuário",
    description="Valida credenciais, efetua lazy rehash se legado, checa tentativas e retorna tokens de acesso e refresh.",
)
async def login(
    dados: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    client_ip = get_client_ip(request)
    return service.login(
        email=dados.email,
        senha=dados.senha,
        client_ip=client_ip,
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Rotaciona o refresh token e emite novo access token",
    description="Valida o refresh token atual, revoga-o e emite um novo par de tokens (uso único).",
)
async def refresh(
    dados: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> RefreshTokenResponse:
    client_ip = get_client_ip(request)
    return service.refresh(
        refresh_token_str=dados.refresh_token,
        client_ip=client_ip,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Encerra sessão e revoga refresh token",
    description="Revoga o refresh token informado no corpo ou a sessão ativa.",
)
async def logout(
    request: Request,
    dados: Optional[LogoutRequest] = None,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    refresh_token = dados.refresh_token if dados else None

    # Tenta extrair ID do usuário logado se token access estiver presente
    current_user_id = None
    if auth_header and auth_header.credentials:
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(auth_header.credentials)
            if payload and payload.get("sub"):
                current_user_id = str(payload["sub"])
        except Exception:
            pass

    resultado = service.logout(
        refresh_token_str=refresh_token,
        current_user_id=current_user_id,
        client_ip=client_ip,
    )
    return MessageResponse(message=resultado["message"])


@router.post(
    "/esqueci-senha",
    response_model=MessageResponse,
    summary="Solicita recuperação de senha",
    description="Gera token temporário e envia e-mail com instruções em português.",
)
async def forgot_password(
    dados: ForgotPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    resultado = service.forgot_password(email=dados.email, client_ip=client_ip)
    return MessageResponse(message=resultado["message"])


@router.post(
    "/redefinir-senha",
    response_model=MessageResponse,
    summary="Redefine a senha com token de validação",
    description="Valida o token de recuperação e define uma nova senha em Argon2id.",
)
async def reset_password(
    dados: ResetPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    resultado = service.reset_password(
        token=dados.token,
        nova_senha=dados.nova_senha,
        client_ip=client_ip,
    )
    return MessageResponse(message=resultado["message"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Dados do usuário logado",
    description="Retorna informações completas do usuário autenticado, seu perfil e lista de permissões.",
)
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return current_user
