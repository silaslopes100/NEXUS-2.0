"""Schemas da Central de Alunos."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

Observacao = Literal["formado", "churn", "transferido", "revalidado", "sem_movimentacao"]


class AlunoGestaoResponse(BaseModel):
    id: str
    usuario_id: str
    numero_matricula: Optional[str] = None
    nome: str
    email: Optional[str] = None
    modalidade: Optional[str] = None
    status: str
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    turmas: List[str] = []
    percentual_presenca: float = 0.0
    ultimo_acesso_em: Optional[datetime] = None
    disciplinas_em_curso: int = 0
    observacoes: List[Observacao] = []
    reingresso_polo_destino_id: Optional[str] = None
    reingresso_escola_destino_id: Optional[str] = None


class AlunoGestaoListResponse(BaseModel):
    total: int
    items: List[AlunoGestaoResponse]
    limit: int
    offset: int


class DisciplinaAcademicaResponse(BaseModel):
    id: str
    nome: str
    semestre: Optional[int] = None
    carga_horaria: Optional[int] = None
    nota: Optional[float] = None
    situacao: str
    em_curso: bool
    total_conteudos: int
    conteudos_concluidos: int
    progresso: Optional[int] = None


class CursoAcademicoResponse(BaseModel):
    id: str
    nome: str
    disciplinas: List[DisciplinaAcademicaResponse]


class AcademicoResponse(BaseModel):
    aluno_id: str
    aluno_nome: str
    numero_matricula: Optional[str] = None
    cursos: List[CursoAcademicoResponse]


class ReingressoRequest(BaseModel):
    modalidade: Literal["polo", "ead"]
    polo_destino_id: Optional[uuid.UUID] = None
    escola_destino_id: Optional[uuid.UUID] = None
    taxa_confirmada: bool = False


class ReingressoResponse(BaseModel):
    aluno_id: str
    numero_matricula: str
    licencas_debitadas: int


class MessageResponse(BaseModel):
    message: str


class ConteudoAprendizadoResponse(BaseModel):
    id: str
    titulo: Optional[str] = None
    tipo_midia: Optional[str] = None
    url_arquivo: Optional[str] = None
    arquivo_nome: Optional[str] = None
    arquivo_mime_type: Optional[str] = None
    arquivo_tamanho_bytes: Optional[int] = None
    tem_arquivo: bool = False
    concluido: bool


class DisciplinaAprendizadoResponse(BaseModel):
    id: str
    nome: str
    conteudos: List[ConteudoAprendizadoResponse]


class CursoAprendizadoResponse(BaseModel):
    id: str
    nome: str
    disciplinas: List[DisciplinaAprendizadoResponse]
