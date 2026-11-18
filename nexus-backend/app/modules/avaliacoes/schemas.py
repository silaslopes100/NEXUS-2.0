"""Schemas das Avaliações (questionários por Disciplina)."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class AlternativaIn(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)
    correta: bool = False


class QuestaoIn(BaseModel):
    enunciado: str = Field(min_length=3, max_length=5000)
    peso: float = Field(default=1, gt=0, le=100)
    alternativas: List[AlternativaIn] = Field(min_length=2, max_length=6)


class AvaliacaoSalvar(BaseModel):
    """Salva a avaliação inteira da disciplina (substitui as questões)."""

    titulo: str = Field(min_length=3, max_length=255)
    instrucoes: Optional[str] = Field(default=None, max_length=5000)
    tempo_limite_min: Optional[int] = Field(default=None, ge=1, le=600)
    tentativas_max: int = Field(default=2, ge=1, le=20)
    nota_minima: float = Field(default=6.0, ge=0, le=10)
    embaralhar: bool = False
    ativo: bool = False
    questoes: List[QuestaoIn] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def _validar(self) -> "AvaliacaoSalvar":
        for n, q in enumerate(self.questoes, start=1):
            corretas = sum(1 for a in q.alternativas if a.correta)
            if corretas != 1:
                raise ValueError(f"A questão {n} precisa ter exatamente uma alternativa correta")
        if self.ativo and not self.questoes:
            raise ValueError("Cadastre ao menos uma questão antes de ativar a avaliação")
        return self


class AlternativaOut(BaseModel):
    id: str
    texto: str
    correta: Optional[bool] = None  # só para quem edita (admin/professor)


class QuestaoOut(BaseModel):
    id: str
    enunciado: str
    peso: float
    ordem: int = 0
    alternativas: List[AlternativaOut]


class AvaliacaoOut(BaseModel):
    id: str
    disciplina_id: str
    disciplina_nome: Optional[str] = None
    titulo: str
    instrucoes: Optional[str] = None
    tempo_limite_min: Optional[int] = None
    tentativas_max: int
    nota_minima: float
    embaralhar: bool
    ativo: bool
    origem: str = "manual"
    questoes: List[QuestaoOut] = Field(default_factory=list)
    atualizado_em: Optional[datetime] = None


class AvaliacaoResumo(BaseModel):
    id: str
    disciplina_id: str
    titulo: str
    ativo: bool
    origem: str = "manual"
    total_questoes: int = 0


# --- Aluno -----------------------------------------------------------------

class AvaliacaoAluno(BaseModel):
    """Situação do aluno em uma disciplina com licença (tela Minhas Disciplinas)."""

    disciplina_id: str
    disciplina_nome: Optional[str] = None
    curso_id: Optional[str] = None
    avaliacao_id: Optional[str] = None
    titulo: Optional[str] = None
    tempo_limite_min: Optional[int] = None
    tentativas_max: int = 0
    tentativas_usadas: int = 0
    tentativas_restantes: int = 0
    melhor_nota: Optional[float] = None
    nota_minima: float = 6.0
    situacao: str  # disponivel | em_andamento | aprovado | reprovado | sem_tentativas | sem_avaliacao | ava
    tentativa_aberta_id: Optional[str] = None
    pode_realizar: bool = False


class TentativaOut(BaseModel):
    tentativa_id: str
    avaliacao_id: str
    titulo: str
    instrucoes: Optional[str] = None
    disciplina_nome: Optional[str] = None
    expira_em: Optional[datetime] = None
    questoes: List[QuestaoOut]  # sem gabarito
    respostas: Dict[str, str] = Field(default_factory=dict)  # questao_id -> alternativa_id


class RespostasIn(BaseModel):
    respostas: Dict[str, str] = Field(default_factory=dict)


class ResultadoOut(BaseModel):
    tentativa_id: str
    nota: float
    aprovado: bool
    nota_minima: float
    acertos: int
    total_questoes: int
    tentativas_restantes: int
    melhor_nota: Optional[float] = None
