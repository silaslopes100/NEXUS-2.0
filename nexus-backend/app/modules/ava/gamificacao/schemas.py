"""Contratos da gamificação."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ConquistaOut(BaseModel):
    codigo: str
    nome: str
    descricao: str
    icone: str
    cor: str
    xp_bonus: int = 0
    obtida_em: Optional[datetime] = None


class EventoXpOut(BaseModel):
    tipo: str
    rotulo: str
    xp: int
    descricao: Optional[str] = None
    criado_em: Optional[datetime] = None


class NivelOut(BaseModel):
    nivel: int
    nome: str
    xp_total: int
    xp_inicio: int
    xp_proximo: int
    progresso_pct: int


class RecompensaOut(BaseModel):
    """O que o aluno ganhou numa ação (para a celebração na tela)."""
    xp_ganho: int = 0
    eventos: List[EventoXpOut] = Field(default_factory=list)
    conquistas: List[ConquistaOut] = Field(default_factory=list)
    subiu_nivel: bool = False
    nivel: Optional[NivelOut] = None
    streak_atual: int = 0


class PerfilGamificacaoOut(BaseModel):
    nivel: NivelOut
    xp_semana: int = 0
    streak_atual: int = 0
    streak_recorde: int = 0
    estudou_hoje: bool = False
    ultimo_dia: Optional[date] = None
    ranking_visivel: bool = True
    conquistas: List[ConquistaOut] = Field(default_factory=list)
    historico: List[EventoXpOut] = Field(default_factory=list)


class RankingItemOut(BaseModel):
    posicao: int
    usuario_id: str
    nome: str
    foto_url: Optional[str] = None
    xp: int
    nivel: int
    eu: bool = False


class CursoRankingOut(BaseModel):
    id: str
    nome: str


class RankingOut(BaseModel):
    periodo: Literal["semana", "geral"]
    curso: Optional[CursoRankingOut] = None
    cursos: List[CursoRankingOut] = Field(default_factory=list)
    itens: List[RankingItemOut] = Field(default_factory=list)
    minha_posicao: Optional[RankingItemOut] = None
    total_participantes: int = 0
    ranking_visivel: bool = True


class PreferenciasIn(BaseModel):
    ranking_visivel: bool
