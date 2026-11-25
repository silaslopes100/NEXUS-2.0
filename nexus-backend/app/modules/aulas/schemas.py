"""Schemas do módulo `aulas` (aula ministrada: ata + materiais + chamada)."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.carga_horaria.schemas import AulaPrevistaResponse, TipoAula


class AulaCreateRequest(BaseModel):
    professor_disciplina_id: str = Field(min_length=1)
    data_aula: date
    numero_aula: int = Field(default=1, ge=1)
    conteudo_ministrado: Optional[str] = None
    observacoes: Optional[str] = None
    visivel_aluno: bool = True
    # RN03: aula prevista do cronograma ou aula não prevista com tipo e justificativa.
    tipo: TipoAula = "prevista"
    aula_prevista_id: Optional[str] = None
    horas: Optional[float] = Field(default=None, gt=0, le=200)
    justificativa: Optional[str] = Field(default=None, max_length=2000)


class AulaUpdateRequest(BaseModel):
    data_aula: Optional[date] = None
    numero_aula: Optional[int] = Field(default=None, ge=1)
    conteudo_ministrado: Optional[str] = None
    observacoes: Optional[str] = None
    visivel_aluno: Optional[bool] = None
    horas: Optional[float] = Field(default=None, gt=0, le=200)
    justificativa: Optional[str] = Field(default=None, max_length=2000)


class AulaTipoUpdateRequest(BaseModel):
    """RN03.5: troca do tipo depois do registro, só por perfil de coordenação (com auditoria)."""
    tipo: TipoAula
    aula_prevista_id: Optional[str] = None
    justificativa: Optional[str] = Field(default=None, max_length=2000)


class AulasPendentesResponse(BaseModel):
    cronograma_gerado: bool
    turma_data_inicio: Optional[date] = None
    turma_data_fim: Optional[date] = None
    tipos_permitidos: List[TipoAula]
    pendentes: List[AulaPrevistaResponse] = Field(default_factory=list)
    # Todas as aulas previstas da disciplina (referência para Reforço/Complemento/Revisão).
    previstas: List[AulaPrevistaResponse] = Field(default_factory=list)


class AulaResumo(BaseModel):
    id: str
    professor_disciplina_id: str
    disciplina_id: str
    disciplina_nome: Optional[str] = None
    curso_nome: Optional[str] = None
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None
    professor_id: str
    professor_nome: Optional[str] = None
    data_aula: date
    numero_aula: int
    conteudo_ministrado: Optional[str] = None
    observacoes: Optional[str] = None
    visivel_aluno: bool = True
    tipo: str = "prevista"
    aula_prevista_id: Optional[str] = None
    aula_prevista_numero: Optional[int] = None
    horas: Optional[float] = None
    justificativa: Optional[str] = None
    total_materiais: int = 0
    presentes: int = 0
    total_chamada: int = 0
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class MaterialAula(BaseModel):
    id: str
    descricao: Optional[str] = None
    arquivo_url: Optional[str] = None
    arquivo_nome: Optional[str] = None
    arquivo_mime_type: Optional[str] = None
    arquivo_tamanho_bytes: Optional[int] = None
    tem_arquivo: bool = False


class AlunoChamadaAula(BaseModel):
    aluno_id: str
    nome: str
    numero_matricula: Optional[str] = None
    presente: Optional[bool] = None


class AulaDetalhe(AulaResumo):
    materiais: List[MaterialAula] = Field(default_factory=list)
    chamada: List[AlunoChamadaAula] = Field(default_factory=list)


class AulaListResponse(BaseModel):
    total: int
    items: List[AulaResumo]
    limit: int
    offset: int


class OpcaoFiltro(BaseModel):
    id: str
    nome: str


class FiltrosAuditoriaResponse(BaseModel):
    disciplinas: List[OpcaoFiltro]
    polos: List[OpcaoFiltro]
    professores: List[OpcaoFiltro]


class DisciplinaAulasResumo(BaseModel):
    disciplina_id: str
    total_aulas: int
    ultima_aula: Optional[date] = None


class DisciplinaAtividade(BaseModel):
    id: str
    nome: str
    total_aulas: int


class PoloSemRegistro(BaseModel):
    id: str
    nome: str
    ultima_aula: Optional[date] = None


class AtividadeDocenteResponse(BaseModel):
    dias: int
    dias_sem_registro: int
    data_inicio: date
    aulas_registradas: int
    disciplinas_com_aula: int
    polos_com_aula: int
    top_disciplinas: List[DisciplinaAtividade]
    polos_sem_registro: List[PoloSemRegistro]


class MessageResponse(BaseModel):
    message: str
