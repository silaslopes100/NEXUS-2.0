"""Schemas Pydantic do Chat Interno."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class UsuarioResumo(BaseModel):
    id: str
    nome: str
    perfil: Optional[str] = None
    foto_url: Optional[str] = None


class ContatoOut(UsuarioResumo):
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None


class MembroOut(UsuarioResumo):
    papel: str
    ultima_leitura_em: Optional[datetime] = None


class ConversaOut(BaseModel):
    id: str
    tipo: Literal["individual", "grupo"]
    titulo: str
    turma_id: Optional[str] = None
    status: Literal["ativa", "encerrada"]
    papel: Optional[str] = None
    nao_lidas: int = 0
    total_membros: int = 0
    outro: Optional[UsuarioResumo] = None
    ultima_mensagem_em: Optional[datetime] = None
    ultima_mensagem: Optional[str] = None
    ultima_remetente_id: Optional[str] = None
    criado_em: Optional[datetime] = None


class ConversaDetalheOut(ConversaOut):
    membros: List[MembroOut] = Field(default_factory=list)
    pode_encerrar: bool = False
    pode_gerenciar_membros: bool = False


class MensagemOut(BaseModel):
    id: str
    conversa_id: str
    remetente_id: Optional[str] = None
    remetente_nome: Optional[str] = None
    tipo: Literal["texto", "anexo", "sistema"]
    texto: Optional[str] = None
    anexo_url: Optional[str] = None
    anexo_nome: Optional[str] = None
    anexo_mime: Optional[str] = None
    anexo_tamanho: Optional[int] = None
    # Referência a outro recurso (ex.: resposta a um post do feed: ref_tipo='feed_post').
    ref_tipo: Optional[str] = None
    ref_id: Optional[str] = None
    criado_em: datetime


class TurmaChatOut(BaseModel):
    id: str
    nome: str
    curso_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    polo_nome: Optional[str] = None
    conversa_id: Optional[str] = None


class ResumoOut(BaseModel):
    nao_lidas: int


class IniciarIndividualIn(BaseModel):
    usuario_id: str


class CriarGrupoIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    membros: List[str] = Field(min_length=1, max_length=300)


class AlterarMembrosIn(BaseModel):
    adicionar: List[str] = Field(default_factory=list, max_length=300)
    remover: List[str] = Field(default_factory=list, max_length=300)


class AnexoIn(BaseModel):
    url: str = Field(max_length=1000)
    pathname: str = Field(max_length=200)
    nome: str = Field(max_length=255)
    mime: str = Field(max_length=127)
    tamanho: int = Field(gt=0)


class EnviarMensagemIn(BaseModel):
    texto: Optional[str] = Field(default=None, max_length=5000)
    anexo: Optional[AnexoIn] = None

    @model_validator(mode="after")
    def _algum_conteudo(self) -> "EnviarMensagemIn":
        if not (self.texto and self.texto.strip()) and self.anexo is None:
            raise ValueError("Escreva uma mensagem ou anexe um arquivo.")
        return self


class UploadIn(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    mime: str = Field(min_length=1, max_length=127)
    tamanho: int = Field(gt=0)


class UploadOut(BaseModel):
    modo: Literal["blob", "local"]
    pathname: str
    content_type: str
    token: Optional[str] = None
    upload_url: Optional[str] = None


class ConversaAdminOut(BaseModel):
    id: str
    tipo: str
    titulo: str
    status: str
    turma_id: Optional[str] = None
    membros: List[UsuarioResumo] = Field(default_factory=list)
    total_mensagens: int = 0
    ultima_mensagem_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None


class ConversasAdminPage(BaseModel):
    total: int
    itens: List[ConversaAdminOut]


class RotacaoOut(BaseModel):
    movidas_para_historico: int
    removidas_do_historico: int
    anexos_removidos: int
    detalhes: Optional[Any] = None
