"""Schemas Pydantic para o módulo administrativo do NEXUS 2.0."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Perfis & Permissões ----------

class PerfilItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    descricao: Optional[str] = None


class PermissaoItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chave: str
    descricao: Optional[str] = None


# ---------- Gestão de Usuários ----------

class UsuarioCreateRequest(BaseModel):
    nome: str = Field(min_length=1, description="Nome do usuário")
    sobrenome: Optional[str] = ""
    email: EmailStr
    cpf: Optional[str] = None
    senha: str = Field(min_length=6, description="Senha inicial com no mínimo 6 caracteres")
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    status: str = Field(default="ativo", pattern="^(ativo|inativo|bloqueado)$")
    permissoes: List[str] = Field(
        default_factory=list,
        description="Lista de chaves de permissões granulares (ex: p_cadastro, p_edicao, p_vendas, etc.)",
    )


class UsuarioUpdateRequest(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo|bloqueado)$")
    permissoes: Optional[List[str]] = None


class UsuarioPermissoesUpdateRequest(BaseModel):
    permissoes: List[str] = Field(
        description="Lista completa de permissões granulares que o usuário passará a ter",
    )


class UsuarioSenhaResetRequest(BaseModel):
    nova_senha: str = Field(min_length=6, description="Nova senha com no mínimo 6 caracteres")


class UsuarioAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    sobrenome: Optional[str] = ""
    email: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    foto_url: Optional[str] = None
    status: str = "ativo"
    perfil_id: Optional[str] = None
    perfil_nome: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    permissoes: List[str] = Field(default_factory=list)
    ultimo_login_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class UsuarioListResponse(BaseModel):
    total: int
    items: List[UsuarioAdminResponse]
    limit: int
    offset: int


# ---------- Logs de Auditoria ----------

class LogAuditoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: Optional[str] = None
    usuario_nome: Optional[str] = None
    usuario_email: Optional[str] = None
    acao: str
    entidade: Optional[str] = None
    entidade_id: Optional[str] = None
    dados_antes: Optional[Dict[str, Any]] = None
    dados_depois: Optional[Dict[str, Any]] = None
    ip: Optional[str] = None
    criado_em: Optional[datetime] = None


class LogAuditoriaListResponse(BaseModel):
    total: int
    items: List[LogAuditoriaResponse]
    limit: int
    offset: int


# ---------- Configurações Gerais ----------

class ConfiguracaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    chave: str
    valor: Any
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ConfiguracaoSetRequest(BaseModel):
    chave: str
    valor: Any


class ConfiguracaoBulkUpdateRequest(BaseModel):
    configuracoes: Dict[str, Any]


# ---------- ETL / Execuções ----------

class EtlErroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execucao_id: Optional[int] = None
    tabela_origem: Optional[str] = None
    id_origem: Optional[str] = None
    erro: Optional[str] = None
    linha_raw: Optional[Any] = None
    criado_em: Optional[datetime] = None


class EtlSyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    modo: str
    iniciado_em: datetime
    finalizado_em: Optional[datetime] = None
    total_lido: int = 0
    total_inserido: int = 0
    total_atualizado: int = 0
    total_erro: int = 0
    status: str = "rodando"
    duracao_segundos: Optional[float] = None
    total_erros_detalhados: Optional[int] = 0


class EtlSyncRunListResponse(BaseModel):
    total: int
    items: List[EtlSyncRunResponse]
    taxa_sucesso_geral: Optional[float] = None


class MessageResponse(BaseModel):
    message: str
