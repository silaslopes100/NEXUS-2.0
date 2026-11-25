"""Contratos do AVA do aluno EAD (Sala de Aula Virtual)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.modules.ava.schemas import ItemOut, TipoAula

SituacaoDisciplina = Literal["liberada", "concluida", "em_breve", "bloqueada", "pagamento_pendente", "prazo_expirado"]
StatusAula = Literal["bloqueada", "disponivel", "em_andamento", "concluida"]
MotivoBloqueio = Literal["drip", "sequencial", "pre_requisito"]


class DisciplinaAlunoOut(BaseModel):
    id: str
    nome: str
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    semestre: Optional[int] = None
    capa_url: Optional[str] = None
    descricao: Optional[str] = None
    situacao: SituacaoDisciplina
    total_aulas: int = 0
    aulas_concluidas: int = 0
    progresso_pct: int = 0
    duracao_min: int = 0
    prazo_conclusao: Optional[datetime] = None
    ultimo_acesso_em: Optional[datetime] = None


class ContinuarOut(BaseModel):
    disciplina_id: str
    disciplina_nome: str
    capa_url: Optional[str] = None
    aula_id: str
    aula_titulo: str
    capitulo_titulo: str
    progresso_pct: int = 0
    ultimo_acesso_em: Optional[datetime] = None


class ResumoAlunoOut(BaseModel):
    aulas_concluidas: int = 0
    disciplinas_concluidas: int = 0
    disciplinas_liberadas: int = 0
    minutos_estudados: int = 0


class HomeOut(BaseModel):
    nome: str
    continuar: Optional[ContinuarOut] = None
    disciplinas: List[DisciplinaAlunoOut] = Field(default_factory=list)
    resumo: ResumoAlunoOut


class AulaResumoAlunoOut(BaseModel):
    id: str
    titulo: str
    tipo: TipoAula
    duracao_min: Optional[int] = None
    obrigatoria: bool = True
    status: StatusAula
    motivo_bloqueio: Optional[MotivoBloqueio] = None
    libera_em: Optional[datetime] = None
    tipos_itens: List[str] = Field(default_factory=list)


class CapituloAlunoOut(BaseModel):
    id: str
    titulo: str
    descricao: Optional[str] = None
    total_aulas: int = 0
    aulas_concluidas: int = 0
    aulas: List[AulaResumoAlunoOut] = Field(default_factory=list)


class DisciplinaPlayerOut(BaseModel):
    disciplina: DisciplinaAlunoOut
    sequencial: bool = False
    previa: bool = False
    proxima_aula_id: Optional[str] = None
    capitulos: List[CapituloAlunoOut] = Field(default_factory=list)


class AvaliacaoAulaOut(BaseModel):
    avaliacao_id: str
    titulo: str
    instrucoes: Optional[str] = None
    ativa: bool = True
    tempo_limite_min: Optional[int] = None
    total_questoes: int = 0
    tentativas_max: int = 0
    tentativas_usadas: int = 0
    tentativas_restantes: int = 0
    melhor_nota: Optional[float] = None
    nota_minima: float = 6.0
    aprovado: bool = False
    tentativa_aberta_id: Optional[str] = None
    pode_realizar: bool = False


class AnotacaoIn(BaseModel):
    texto: str = Field(min_length=1, max_length=5000)
    posicao_seg: Optional[int] = Field(default=None, ge=0)


class AnotacaoOut(BaseModel):
    id: str
    texto: str
    posicao_seg: Optional[int] = None
    criado_em: datetime
    atualizado_em: Optional[datetime] = None


class AulaAlunoOut(BaseModel):
    id: str
    disciplina_id: str
    capitulo_id: str
    capitulo_titulo: str
    titulo: str
    descricao: Optional[str] = None
    tipo: TipoAula
    duracao_min: Optional[int] = None
    status: StatusAula
    percentual: int = 0
    posicao_seg: Optional[int] = None
    itens: List[ItemOut] = Field(default_factory=list)
    avaliacao: Optional[AvaliacaoAulaOut] = None
    anotacoes: List[AnotacaoOut] = Field(default_factory=list)
    minha_nota: Optional[int] = None
    anterior_id: Optional[str] = None
    proxima_id: Optional[str] = None
    numero: int = 1
    total_aulas: int = 1


class ProgressoIn(BaseModel):
    percentual: int = Field(ge=0, le=100)
    posicao_seg: Optional[int] = Field(default=None, ge=0)


class ConclusaoOut(BaseModel):
    aula_id: str
    concluida: bool = True
    ja_estava_concluida: bool = False
    capitulo_concluido: bool = False
    disciplina_concluida: bool = False
    progresso_pct: int = 0
    proxima_aula_id: Optional[str] = None


class NotaAulaIn(BaseModel):
    nota: int = Field(ge=1, le=5)
