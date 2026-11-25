"""Contratos dos Treinamentos."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.modules.ava.schemas import CapituloOut

Categoria = Literal["treinamento", "workshop", "capacitacao"]
PerfilAlvo = Literal["polo", "escola", "professor"]

ROTULO_CATEGORIA = {"treinamento": "Treinamento", "workshop": "Workshop", "capacitacao": "Capacitação"}


class UnidadeOut(BaseModel):
    id: str
    nome: str
    polo_id: Optional[str] = None


class UnidadesOut(BaseModel):
    polos: List[UnidadeOut] = Field(default_factory=list)
    escolas: List[UnidadeOut] = Field(default_factory=list)


class TreinamentoIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=20_000)
    capa_url: Optional[str] = Field(default=None, max_length=1000)
    categoria: Categoria = "treinamento"
    carga_horaria: Optional[int] = Field(default=None, ge=0, le=10_000)
    perfis_alvo: List[PerfilAlvo] = Field(min_length=1)
    polo_ids: List[str] = Field(default_factory=list, max_length=500)
    escola_ids: List[str] = Field(default_factory=list, max_length=2000)
    certificado_ativo: bool = True
    sequencial: bool = False
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    publicado: bool = False

    @model_validator(mode="after")
    def _periodo(self) -> "TreinamentoIn":
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValueError("A data de término precisa ser depois do início.")
        return self


class TreinamentoOut(BaseModel):
    id: str
    titulo: str
    descricao: Optional[str] = None
    capa_url: Optional[str] = None
    categoria: Categoria
    carga_horaria: Optional[int] = None
    perfis_alvo: List[PerfilAlvo] = Field(default_factory=list)
    polos: List[UnidadeOut] = Field(default_factory=list)
    escolas: List[UnidadeOut] = Field(default_factory=list)
    certificado_ativo: bool = True
    sequencial: bool = False
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    publicado: bool = False
    total_capitulos: int = 0
    total_aulas: int = 0
    total_participantes: int = 0
    total_concluintes: int = 0
    atualizado_em: Optional[datetime] = None


class TreinamentosPage(BaseModel):
    items: List[TreinamentoOut]
    total: int


class EstruturaTreinamentoOut(BaseModel):
    treinamento: TreinamentoOut
    capitulos: List[CapituloOut] = Field(default_factory=list)


class ParticipanteOut(BaseModel):
    usuario_id: str
    nome: str
    perfil: Optional[str] = None
    unidade: Optional[str] = None
    aulas_concluidas: int = 0
    total_aulas: int = 0
    progresso_pct: int = 0
    ultimo_acesso_em: Optional[datetime] = None
    concluido_em: Optional[datetime] = None
    codigo_validacao: Optional[str] = None


class TreinamentoCatalogoOut(BaseModel):
    id: str
    titulo: str
    descricao: Optional[str] = None
    capa_url: Optional[str] = None
    categoria: Categoria
    carga_horaria: Optional[int] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    certificado_ativo: bool = True
    total_aulas: int = 0
    aulas_concluidas: int = 0
    progresso_pct: int = 0
    duracao_min: int = 0
    concluido_em: Optional[datetime] = None
    ultimo_acesso_em: Optional[datetime] = None
    disponivel: bool = True


class CertificadoValidacaoOut(BaseModel):
    valido: bool
    codigo: str
    nome: Optional[str] = None
    treinamento: Optional[str] = None
    categoria: Optional[str] = None
    carga_horaria: Optional[int] = None
    concluido_em: Optional[datetime] = None
