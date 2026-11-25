"""Contratos do AVA (gestor de conteúdo)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.modules.comunicacao.schemas import ArquivoIn, UploadIn, UploadOut  # noqa: F401 — reexportados

TipoAula = Literal["conteudo", "avaliacao"]
TipoItem = Literal["video_embed", "arquivo", "imagem", "link", "texto"]
Provedor = Literal["youtube", "vimeo", "panda", "iframe"]


# ---------------------------------------------------------------------------
# Disciplinas / configuração
# ---------------------------------------------------------------------------

class DisciplinaAvaOut(BaseModel):
    id: str
    nome: str
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    semestre: Optional[int] = None
    ordem: Optional[int] = None
    ativo: bool = True
    capa_url: Optional[str] = None
    publicado: bool = False
    sequencial: bool = False
    total_capitulos: int = 0
    total_aulas: int = 0
    atualizado_em: Optional[datetime] = None


class ConfigIn(BaseModel):
    capa_url: Optional[str] = Field(default=None, max_length=1000)
    descricao_ava: Optional[str] = Field(default=None, max_length=5000)
    sequencial: bool = False
    publicado: bool = False


class ConfigOut(ConfigIn):
    disciplina_id: str


# ---------------------------------------------------------------------------
# Estrutura
# ---------------------------------------------------------------------------

class ItemIn(BaseModel):
    tipo: TipoItem
    titulo: Optional[str] = Field(default=None, max_length=255)
    url: Optional[str] = Field(default=None, max_length=2000)
    conteudo_html: Optional[str] = Field(default=None, max_length=200_000)
    arquivo: Optional[ArquivoIn] = None
    permite_download: bool = True


class ItemOut(BaseModel):
    id: str
    aula_id: str
    tipo: TipoItem
    titulo: Optional[str] = None
    url: Optional[str] = None
    provedor: Optional[Provedor] = None
    embed_id: Optional[str] = None
    conteudo_html: Optional[str] = None
    arquivo_nome: Optional[str] = None
    arquivo_mime: Optional[str] = None
    arquivo_tamanho: Optional[int] = None
    permite_download: bool = True
    ordem: int = 0


class AulaIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=20_000)
    tipo: TipoAula = "conteudo"
    avaliacao_id: Optional[str] = None
    duracao_min: Optional[int] = Field(default=None, ge=0, le=10_000)
    publicado: bool = True
    obrigatoria: bool = True
    liberar_apos_dias: Optional[int] = Field(default=None, ge=0, le=3650)
    capa_url: Optional[str] = Field(default=None, max_length=1000)


class AulaCreateIn(AulaIn):
    capitulo_id: str


class AulaOut(BaseModel):
    id: str
    capitulo_id: str
    titulo: str
    descricao: Optional[str] = None
    tipo: TipoAula
    avaliacao_id: Optional[str] = None
    avaliacao_titulo: Optional[str] = None
    avaliacao_disciplina_nome: Optional[str] = None
    duracao_min: Optional[int] = None
    ordem: int = 0
    publicado: bool = True
    obrigatoria: bool = True
    liberar_apos_dias: Optional[int] = None
    capa_url: Optional[str] = None
    itens: List[ItemOut] = Field(default_factory=list)


class CapituloIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=5000)
    publicado: bool = True


class CapituloOut(BaseModel):
    id: str
    titulo: str
    descricao: Optional[str] = None
    ordem: int = 0
    publicado: bool = True
    aulas: List[AulaOut] = Field(default_factory=list)


class EstruturaOut(BaseModel):
    disciplina: DisciplinaAvaOut
    config: ConfigOut
    capitulos: List[CapituloOut] = Field(default_factory=list)


class OrdemCapitulo(BaseModel):
    id: str
    ordem: int = Field(ge=0)


class OrdemAula(BaseModel):
    id: str
    ordem: int = Field(ge=0)
    capitulo_id: str


class ReordenarIn(BaseModel):
    capitulos: List[OrdemCapitulo] = Field(default_factory=list, max_length=500)
    aulas: List[OrdemAula] = Field(default_factory=list, max_length=2000)
    itens: List[OrdemCapitulo] = Field(default_factory=list, max_length=500)


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------

class AvaliacaoOpcaoOut(BaseModel):
    avaliacao_id: str
    titulo: str
    disciplina_id: str
    disciplina_nome: str
    ativo: bool = True
    total_questoes: int = 0


class EmbedIn(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


class EmbedOut(BaseModel):
    url: str
    provedor: Provedor
    embed_id: Optional[str] = None
    embed_url: str
    thumbnail_url: Optional[str] = None
