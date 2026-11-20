"""Schemas do módulo de Comunicação: Feed de Notícias e Avisos (pop-ups)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Perfis canônicos do NEXUS (ver app.modules.auth.roles).
Perfil = Literal["admin", "polo", "escola", "professor", "aluno", "financeiro", "logistica"]
PERFIS: tuple = ("admin", "polo", "escola", "professor", "aluno", "financeiro", "logistica")
# Equipe Etademp: publica no feed. Aluno só curte, comenta e responde via chat.
PERFIS_PUBLICAR: tuple = ("admin", "polo", "escola", "professor", "financeiro", "logistica")

MAX_MIDIAS = 10
MAX_LINKS = 3

StatusComentario = Literal["pendente", "aprovado", "rejeitado"]
TipoMidia = Literal["imagem", "video", "arquivo"]
StatusAviso = Literal["agendado", "ativo", "expirado", "inativo"]


# ---------------------------------------------------------------------------
# Comuns
# ---------------------------------------------------------------------------

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


class ArquivoIn(BaseModel):
    """Arquivo já enviado ao armazenamento (resultado de enviarArquivoDireto)."""
    url: str = Field(max_length=1000)
    pathname: str = Field(max_length=200)
    nome: str = Field(max_length=255)
    mime: str = Field(max_length=127)
    tamanho: int = Field(gt=0)


class AutorOut(BaseModel):
    id: str
    nome: str
    perfil: Optional[str] = None
    foto_url: Optional[str] = None


class MidiaOut(BaseModel):
    id: Optional[str] = None
    tipo: str
    url: str
    pathname: Optional[str] = None
    nome: Optional[str] = None
    mime: Optional[str] = None
    tamanho: Optional[int] = None
    embed_tipo: Optional[str] = None
    embed_id: Optional[str] = None


class LinkPreviewIn(BaseModel):
    url: str = Field(min_length=3, max_length=2000)


class LinkPreviewOut(BaseModel):
    url: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    imagem_url: Optional[str] = None
    site_nome: Optional[str] = None
    embed_tipo: Optional[Literal["youtube", "vimeo"]] = None
    embed_id: Optional[str] = None


def _utc(valor: datetime) -> datetime:
    return valor.replace(tzinfo=timezone.utc) if valor.tzinfo is None else valor


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

class PostIn(BaseModel):
    conteudo_html: str = Field(default="", max_length=60000)
    midias: List[ArquivoIn] = Field(default_factory=list, max_length=MAX_MIDIAS)
    links: List[LinkPreviewIn] = Field(default_factory=list, max_length=MAX_LINKS)
    publico_perfis: Optional[List[Perfil]] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    permite_comentarios: bool = True

    @field_validator("publico_perfis")
    @classmethod
    def _perfis(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        v = list(dict.fromkeys(v or []))
        return v or None  # lista vazia = todos

    @field_validator("polo_id", "escola_id")
    @classmethod
    def _vazio(cls, v: Optional[str]) -> Optional[str]:
        return v or None


class ComentarioOut(BaseModel):
    id: str
    post_id: str
    parent_id: Optional[str] = None
    autor: AutorOut
    texto: str
    criado_em: datetime
    # Só preenchido para quem modera o post (o autor do comentário não vê a moderação).
    status: Optional[StatusComentario] = None
    pode_excluir: bool = False
    pode_moderar: bool = False


class PostOut(BaseModel):
    id: str
    autor: AutorOut
    conteudo_html: str
    midias: List[MidiaOut] = Field(default_factory=list)
    links: List[LinkPreviewOut] = Field(default_factory=list)
    publico_perfis: Optional[List[str]] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    fixado: bool = False
    permite_comentarios: bool = True
    total_curtidas: int = 0
    total_comentarios: int = 0
    curtido_por_mim: bool = False
    editado: bool = False
    criado_em: datetime
    atualizado_em: Optional[datetime] = None
    pode_editar: bool = False
    pode_moderar: bool = False
    pendentes: int = 0
    comentarios_recentes: List[ComentarioOut] = Field(default_factory=list)


class FeedPage(BaseModel):
    itens: List[PostOut]
    proximo_cursor: Optional[str] = None


class CurtidaOut(BaseModel):
    curtido: bool
    total_curtidas: int


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[str] = None

    @field_validator("texto")
    @classmethod
    def _texto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Escreva um comentário.")
        return v


class ComentariosPage(BaseModel):
    itens: List[ComentarioOut]
    proximo_cursor: Optional[str] = None


class RejeitarIn(BaseModel):
    motivo: Optional[str] = Field(default=None, max_length=500)


class LoteModeracaoIn(BaseModel):
    ids: List[str] = Field(min_length=1, max_length=100)
    acao: Literal["aprovar", "rejeitar"]
    motivo: Optional[str] = Field(default=None, max_length=500)


class ModeracaoItemOut(BaseModel):
    id: str
    post_id: str
    post_trecho: str
    post_autor_nome: Optional[str] = None
    parent_id: Optional[str] = None
    autor: AutorOut
    texto: str
    status: StatusComentario
    criado_em: datetime
    moderado_em: Optional[datetime] = None
    moderado_por_nome: Optional[str] = None
    motivo_rejeicao: Optional[str] = None


class ModeracaoPage(BaseModel):
    total: int
    itens: List[ModeracaoItemOut]


class ResumoOut(BaseModel):
    pendentes: int


class ResponderChatIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class ResponderChatOut(BaseModel):
    conversa_id: str


# ---------------------------------------------------------------------------
# Avisos (pop-ups)
# ---------------------------------------------------------------------------

class AvisoMidiaIn(BaseModel):
    tipo: Literal["arquivo_enviado", "video_link"]
    arquivo: Optional[ArquivoIn] = None
    url: Optional[str] = Field(default=None, max_length=2000)  # video_link

    @model_validator(mode="after")
    def _coerente(self) -> "AvisoMidiaIn":
        if self.tipo == "arquivo_enviado" and self.arquivo is None:
            raise ValueError("Arquivo da mídia não informado.")
        if self.tipo == "video_link" and not (self.url or "").strip():
            raise ValueError("Informe o link do vídeo.")
        return self


class AvisoIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    conteudo_html: str = Field(default="", max_length=100000)
    publico_tipo: Literal["todos", "perfis", "usuarios"] = "todos"
    perfis: List[Perfil] = Field(default_factory=list)
    usuarios: List[str] = Field(default_factory=list, max_length=2000)
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    inicio_em: datetime
    fim_em: datetime
    frequencia: Literal["uma_vez", "ate_confirmar", "toda_sessao"] = "uma_vez"
    exige_confirmacao: bool = False
    prioridade: int = Field(default=0, ge=0, le=100)
    ativo: bool = True
    cor_destaque: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    largura: Literal["pequena", "media", "grande"] = "media"
    midias: List[AvisoMidiaIn] = Field(default_factory=list, max_length=MAX_MIDIAS)

    @field_validator("polo_id", "escola_id", "cor_destaque", mode="before")
    @classmethod
    def _vazio(cls, v):  # noqa: ANN001
        return v or None

    @model_validator(mode="after")
    def _regras(self) -> "AvisoIn":
        self.titulo = self.titulo.strip()
        self.inicio_em, self.fim_em = _utc(self.inicio_em), _utc(self.fim_em)
        if self.fim_em <= self.inicio_em:
            raise ValueError("A data de fim deve ser posterior à de início.")
        if self.publico_tipo == "perfis" and not self.perfis:
            raise ValueError("Escolha ao menos um perfil.")
        if self.publico_tipo == "usuarios" and not self.usuarios:
            raise ValueError("Escolha ao menos um usuário.")
        if self.frequencia == "ate_confirmar":
            self.exige_confirmacao = True
        self.perfis = list(dict.fromkeys(self.perfis)) if self.publico_tipo == "perfis" else []
        self.usuarios = list(dict.fromkeys(self.usuarios)) if self.publico_tipo == "usuarios" else []
        return self


class AvisoOut(BaseModel):
    id: str
    titulo: str
    conteudo_html: str
    publico_tipo: str
    perfis: List[str] = Field(default_factory=list)
    usuarios: List[AutorOut] = Field(default_factory=list)
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    inicio_em: datetime
    fim_em: datetime
    frequencia: str
    exige_confirmacao: bool
    prioridade: int
    ativo: bool
    cor_destaque: Optional[str] = None
    largura: str
    midias: List[MidiaOut] = Field(default_factory=list)
    status: StatusAviso
    criado_por_nome: Optional[str] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    total_visualizacoes: int = 0
    total_confirmacoes: int = 0


class AvisosPage(BaseModel):
    total: int
    itens: List[AvisoOut]


class AvisoPopupOut(BaseModel):
    id: str
    titulo: str
    conteudo_html: str
    midias: List[MidiaOut] = Field(default_factory=list)
    frequencia: str
    exige_confirmacao: bool
    cor_destaque: Optional[str] = None
    largura: str


class VisualizacaoOut(BaseModel):
    usuario: AutorOut
    primeira_vez_em: datetime
    ultima_vez_em: datetime
    vezes: int
    confirmado_em: Optional[datetime] = None


class EstatisticasOut(BaseModel):
    publico_estimado: int
    visualizacoes: int
    confirmacoes: int
    total: int
    itens: List[VisualizacaoOut]


class UsuarioBuscaOut(AutorOut):
    email: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
