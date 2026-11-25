"""Schemas Pydantic para o módulo de autenticação."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PerfilResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    nome: str
    descricao: Optional[str] = None


class PermissaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chave: str
    id: Optional[str] = None
    descricao: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    sobrenome: Optional[str] = ""
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    foto_url: Optional[str] = None
    status: str = "ativo"
    perfil: Optional[PerfilResponse] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    permissoes: List[str] = Field(default_factory=list)
    ultimo_login_em: Optional[datetime] = None
    # Usuário de perfil Polo ou Escola que também possui cadastro de aluno.
    tambem_aluno: bool = False
    # Aluno em Churn: precisa regularizar a situação antes de nova matrícula.
    aluno_desistente: bool = False
    # Aluno com modalidade EAD: único perfil com acesso ao AVA (Sala de Aula Virtual).
    aluno_ead: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutos em segundos
    usuario: UserResponse
    perfil: Optional[PerfilResponse] = None
    permissoes: List[str] = Field(default_factory=list)
    # Login por licença: para onde levar o aluno (disciplina da licença e avaliação ativa).
    destino: Optional[dict] = None
    via: Optional[str] = None  # "licenca" quando a sessão foi aberta pelo número da licença


class LoginLicencaRequest(BaseModel):
    numero: str = Field(min_length=6, max_length=32)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutos


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=6, description="Nova senha com no mínimo 6 caracteres")


class MessageResponse(BaseModel):
    message: str
