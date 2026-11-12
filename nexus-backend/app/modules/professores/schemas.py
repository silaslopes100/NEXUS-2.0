"""Schemas Pydantic v2 do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LotacaoInput(BaseModel):
    """Polo (obrigatório, ou deduzido da escola) com escola opcional."""

    polo_id: Optional[str] = Field(default=None, max_length=64)
    escola_id: Optional[str] = Field(default=None, max_length=64)


class LotacaoItem(BaseModel):
    id: str
    polo_id: str
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None


class ProfessorCreateRequest(BaseModel):
    """Cadastro de docente — exige vínculo com um usuário (coluna NOT NULL)."""

    usuario_id: str = Field(min_length=1, description="ID do usuário vinculado ao docente")
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    lotacoes: Optional[List[LotacaoInput]] = Field(
        default=None,
        description="Polos/escolas em que o professor atua. Sem a lista, polo_id/escola_id viram a lotação.",
    )
    materias: List[str] = Field(default_factory=list, description="Disciplinas/docências do professor")
    disciplina_ids: List[UUID] = Field(default_factory=list, description="IDs das disciplinas vinculadas")
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
    lotacoes: Optional[List[LotacaoInput]] = None
    materias: Optional[List[str]] = None
    disciplina_ids: Optional[List[UUID]] = None
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
    lotacoes: List[LotacaoItem] = Field(default_factory=list)
    materias: List[str] = Field(default_factory=list)
    disciplina_ids: List[str] = Field(default_factory=list)
    data_inicio: Optional[date] = None
    quantidade_aulas: int = 0
    horas_totais: int = 0
    valor_hora_aula: Optional[float] = None
    pix: Optional[str] = None
    conteudo_programatico: Optional[str] = None
    status: str = "ativo"
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ProfessorDetalheDisciplina(BaseModel):
    id: str
    nome: str
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    carga_horaria: Optional[int] = None
    qtd_aulas_prevista: Optional[int] = None


class ProfessorDetalheAluno(BaseModel):
    id: str
    nome: Optional[str] = None
    numero_matricula: Optional[str] = None
    email: Optional[str] = None


class ProfessorDetalheTurma(BaseModel):
    id: str
    nome: str
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    alunos: List[ProfessorDetalheAluno] = Field(default_factory=list)


class ProfessorDetalheResponse(BaseModel):
    professor: ProfessorResponse
    disciplinas: List[ProfessorDetalheDisciplina]
    turmas: List[ProfessorDetalheTurma]


class ProfessorTurmaResumo(BaseModel):
    id: str
    nome: str
    professor_disciplina_id: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    polo_nome: Optional[str] = None
    escola_nome: Optional[str] = None


class ProfessorDisciplinaResumo(BaseModel):
    id: str
    nome: str
    curso_nome: Optional[str] = None
    semestre: Optional[int] = None
    carga_horaria: Optional[int] = None
    qtd_aulas_prevista: Optional[int] = None
    turmas: List[ProfessorTurmaResumo] = Field(default_factory=list)


class ProfessorDisciplinaListResponse(BaseModel):
    items: List[ProfessorDisciplinaResumo]


class ProfessorTurmaVinculoCreateRequest(BaseModel):
    professor_id: UUID
    disciplina_id: UUID


class ProfessorTurmaVinculoResumo(BaseModel):
    id: str
    professor_id: str
    professor_nome: str
    professor_email: Optional[str] = None
    disciplina_id: str
    disciplina_nome: str
    turma_id: str


class ProfessorTurmaVinculosResponse(BaseModel):
    items: List[ProfessorTurmaVinculoResumo]


class ProfessorConteudoItem(BaseModel):
    id: str
    disciplina_id: str
    titulo: Optional[str] = None
    tipo_midia: Optional[str] = None
    url_arquivo: Optional[str] = None
    ordem: int = 0
    arquivo_nome: Optional[str] = None
    arquivo_mime_type: Optional[str] = None
    arquivo_tamanho_bytes: Optional[int] = None
    tem_arquivo: bool = False


class ProfessorMaterialResumo(BaseModel):
    id: str
    professor_disciplina_id: str
    disciplina_id: str
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None
    arquivo_url: Optional[str] = None
    data_aula: Optional[date] = None
    descricao: Optional[str] = None
    expira_em: Optional[datetime] = None
    arquivo_nome: Optional[str] = None
    arquivo_mime_type: Optional[str] = None
    arquivo_tamanho_bytes: Optional[int] = None
    tem_arquivo: bool = False


class ProfessorDisciplinaConteudosResumo(BaseModel):
    id: str
    nome: str
    curso_nome: Optional[str] = None
    turmas: List[ProfessorTurmaResumo] = Field(default_factory=list)
    conteudos: List[ProfessorConteudoItem] = Field(default_factory=list)
    materiais: List[ProfessorMaterialResumo] = Field(default_factory=list)


class ProfessorConteudosResponse(BaseModel):
    items: List[ProfessorDisciplinaConteudosResumo]


class ProfessorDisponivel(BaseModel):
    """Dados mínimos para escolher um professor (sem remuneração nem PIX)."""

    id: str
    nome: Optional[str] = None
    email: Optional[str] = None
    lotacoes: List[LotacaoItem] = Field(default_factory=list)


class ProfessorDisponiveisResponse(BaseModel):
    items: List[ProfessorDisponivel]


class ProfessorListResponse(BaseModel):
    total: int
    items: List[ProfessorResponse]
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str
