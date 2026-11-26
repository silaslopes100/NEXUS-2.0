"""Contratos da vitrine pública EAD e da loja de disciplinas do aluno."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# Estado da disciplina na loja do aluno.
# "bolsa" = bolsista com a disciplina liberada sem custo; "encerrada" = bolsista com o prazo vencido.
EstadoDisciplina = Literal["disponivel", "aguardando", "em_breve", "pendente", "comprada", "concluida", "recompra",
                           "bolsa", "encerrada"]


# ---------------------------------------------------------------------------
# Vitrine (pública)
# ---------------------------------------------------------------------------

class TurmaVitrineOut(BaseModel):
    id: str
    nome: str
    codigo: Optional[str] = None
    turno: Optional[str] = None
    curso_id: str
    curso_nome: str
    curso_descricao: Optional[str] = None
    nivel_academico: Optional[str] = None
    carga_horaria_total: Optional[int] = None
    semestres: Optional[int] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    vagas: Optional[int] = None
    vagas_restantes: Optional[int] = None  # None = sem limite
    total_disciplinas: int = 0
    valor_minimo: Optional[float] = None


class DisciplinaVitrineOut(BaseModel):
    id: str
    nome: str
    semestre: Optional[int] = None
    carga_horaria: int = 0
    valor_ead: float
    livro_disponivel: bool = False
    valor_livro_ead: float
    prazo_dias: Optional[int] = None
    libera_em_prevista: Optional[date] = None  # None = após concluir/vencer a anterior


class TurmaVitrineDetalheOut(TurmaVitrineOut):
    liberacao: str = "sequencial"  # sequencial | todas_no_inicio
    disciplinas: List[DisciplinaVitrineOut] = Field(default_factory=list)


class InscricaoIn(BaseModel):
    turma_id: str
    nome: str = Field(min_length=2, max_length=120)
    sobrenome: str = Field(min_length=1, max_length=160)
    email: EmailStr
    cpf: str = Field(min_length=11, max_length=18)
    celular: str = Field(min_length=10, max_length=20)
    data_nascimento: date
    senha: str = Field(min_length=8, max_length=128)
    aceite_termos: bool
    site: Optional[str] = Field(default=None, max_length=200)  # honeypot: humanos deixam vazio


# ---------------------------------------------------------------------------
# Loja (aluno EAD)
# ---------------------------------------------------------------------------

class EnderecoIn(BaseModel):
    cep: str = Field(min_length=8, max_length=10)
    logradouro: str = Field(min_length=2, max_length=255)
    numero: str = Field(min_length=1, max_length=32)
    complemento: Optional[str] = Field(default=None, max_length=255)
    bairro: Optional[str] = Field(default=None, max_length=255)
    cidade: str = Field(min_length=2, max_length=255)
    uf: str = Field(min_length=2, max_length=2)


class EnderecoOut(BaseModel):
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None


class DisciplinaLojaOut(BaseModel):
    id: str
    nome: str
    semestre: Optional[int] = None
    carga_horaria: int = 0
    capa_url: Optional[str] = None
    descricao: Optional[str] = None
    total_aulas: int = 0
    valor_ead: float
    livro_disponivel: bool = False
    valor_livro_ead: float
    estado: EstadoDisciplina
    libera_em: Optional[date] = None
    data_limite: Optional[date] = None
    prazo_dias: Optional[int] = None
    pedido_id: Optional[str] = None
    com_livro: bool = False


class TurmaLojaOut(BaseModel):
    id: str
    bolsista: bool = False
    nome: str
    codigo: Optional[str] = None
    curso_id: str
    curso_nome: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    disciplinas: List[DisciplinaLojaOut] = Field(default_factory=list)


class LojaOut(BaseModel):
    nome: str
    turmas: List[TurmaLojaOut] = Field(default_factory=list)
    outras_turmas: List[TurmaVitrineOut] = Field(default_factory=list)
    endereco: EnderecoOut = Field(default_factory=EnderecoOut)


class CheckoutIn(BaseModel):
    disciplina_id: str
    turma_id: Optional[str] = None
    com_livro: bool = False
    meio: Literal["PIX", "BOLETO"] = "PIX"
    endereco: Optional[EnderecoIn] = None


class PedidoAlunoOut(BaseModel):
    id: str
    numero: str
    tipo: str
    status: str
    valor_total: float
    criado_em: Optional[datetime] = None
    pago_em: Optional[datetime] = None
    enviado_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    disciplina_id: Optional[str] = None
    disciplina_nome: Optional[str] = None
    com_livro: bool = False
    pagamento_id: Optional[str] = None
    pagamento_status: Optional[str] = None
    billing_type: Optional[str] = None
    vencimento_em: Optional[date] = None
    pix_copia_cola: Optional[str] = None
    pix_qrcode_base64: Optional[str] = None
    boleto_url: Optional[str] = None
    invoice_url: Optional[str] = None
    linha_digitavel: Optional[str] = None
    transportadora: Optional[str] = None
    codigo_rastreio: Optional[str] = None
