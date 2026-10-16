"""Schemas Pydantic v2 do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfessorCreateRequest(BaseModel):
    """Cadastro de docente — exige vínculo com um usuário (coluna NOT NULL)."""

    usuario_id: str = Field(min_length=1, description="ID do usuário vinculado ao docente")
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    materias: List[str] = Field(default_factory=list, description="Disciplinas/docências do professor")
    data_inicio: Optional[date] = None
    quantidade_aulas: int = 0
    horas_totais: int = 0
    valor_hora_aula: Optional[float] = None
    pix: Optional[str] = None
    conteudo_programatico: Optional[str] = None


class ProfessorUpdateRequest(BaseModel):
    """Atualização parcial do cadastro de docente."""

    usuario_id: Optional[str] = None
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    materias: Optional[List[str]] = None
    data_inicio: Optional[date] = None
    quantidade_aulas: Optional[int] = None
    horas_totais: Optional[int] = None
    valor_hora_aula: Optional[float] = None
    pix: Optional[str] = None
    conteudo_programatico: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(ativo|inativo)$")


class ProfessorResponse(BaseModel):
    """Docente com nomes resolvidos de Polo e Escola (JOIN nas tabelas)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_id: Optional[str] = None
    nome: Optional[str] = None
    email: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    materias: List[str] = Field(default_factory=list)
    data_inicio: Optional[date] = None
    quantidade_aulas: int = 0
    horas_totais: int = 0
    valor_hora_aula: Optional[float] = None
    pix: Optional[str] = None
    conteudo_programatico: Optional[str] = None
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ProfessorListResponse(BaseModel):
    total: int
    items: List[ProfessorResponse]
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str
