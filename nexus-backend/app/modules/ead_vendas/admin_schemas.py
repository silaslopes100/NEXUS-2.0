"""Contratos da Gestão de Matrículas EAD (admin)."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.modules.ead_vendas.schemas import PedidoAlunoOut, TurmaLojaOut

TipoMatricula = Literal["regular", "bolsista"]
MotivoLiberacao = Literal["bolsa", "pagamento_externo", "problema_pagamento", "cortesia", "outro"]


class ResumoEadOut(BaseModel):
    matriculas_ativas: int = 0
    bolsistas: int = 0
    canceladas: int = 0
    novas_site: int = 0
    novas_manuais: int = 0
    compras_pagas: int = 0
    compras_pendentes: int = 0
    liberacoes_manuais: int = 0
    receita: float = 0
    vendas_com_livro: int = 0


class TurmaEadOpcao(BaseModel):
    id: str
    nome: str
    codigo: Optional[str] = None
    curso_id: str
    curso_nome: str
    aberta: bool = True


class MatriculaEadItem(BaseModel):
    id: str
    aluno_id: str
    nome: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    numero_matricula: Optional[str] = None
    curso_id: Optional[str] = None
    curso_nome: Optional[str] = None
    turma_id: Optional[str] = None
    turma_nome: Optional[str] = None
    tipo: str = "regular"
    origem: str = "legado"
    status: str = "ativa"
    data_matricula: Optional[datetime] = None
    observacao: Optional[str] = None
    disciplinas_pagas: int = 0
    disciplinas_liberadas: int = 0
    disciplinas_pendentes: int = 0
    ultimo_movimento: Optional[datetime] = None
    aluno_desistente: bool = False


class MatriculasEadPage(BaseModel):
    total: int
    items: List[MatriculaEadItem]


class CompraEadAdmin(BaseModel):
    id: str
    disciplina_id: Optional[str] = None
    disciplina_nome: Optional[str] = None
    turma_nome: Optional[str] = None
    origem: str = "legado"
    status_pagamento: Optional[str] = None
    valor_pago: Optional[float] = None
    com_livro: bool = False
    liberada_em: Optional[datetime] = None
    motivo: Optional[str] = None
    motivo_texto: Optional[str] = None
    liberada_por_nome: Optional[str] = None
    pedido_id: Optional[str] = None
    pedido_numero: Optional[str] = None
    criado_em: Optional[datetime] = None
    cancelada_em: Optional[datetime] = None
    pode_revogar: bool = False


class MovimentacaoEad(BaseModel):
    evento: str
    data: Optional[datetime] = None
    aluno_id: Optional[str] = None
    aluno_nome: Optional[str] = None
    numero_matricula: Optional[str] = None
    turma_nome: Optional[str] = None
    disciplina_nome: Optional[str] = None
    valor: Optional[float] = None
    detalhe: Optional[str] = None
    pedido_id: Optional[str] = None
    autor_nome: Optional[str] = None


class MovimentacoesPage(BaseModel):
    total: int
    items: List[MovimentacaoEad]


class FichaEadOut(BaseModel):
    aluno_id: str
    usuario_id: str
    nome: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    celular: Optional[str] = None
    numero_matricula: Optional[str] = None
    status_aluno: Optional[str] = None
    matriculas: List[MatriculaEadItem] = Field(default_factory=list)
    turmas: List[TurmaLojaOut] = Field(default_factory=list)
    compras: List[CompraEadAdmin] = Field(default_factory=list)
    pedidos: List[PedidoAlunoOut] = Field(default_factory=list)
    movimentacoes: List[MovimentacaoEad] = Field(default_factory=list)


class AlunoEadBusca(BaseModel):
    aluno_id: str
    nome: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    numero_matricula: Optional[str] = None


class NovoAlunoIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    sobrenome: str = Field(min_length=1, max_length=160)
    email: EmailStr
    cpf: str = Field(min_length=11, max_length=18)
    celular: Optional[str] = Field(default=None, max_length=20)
    data_nascimento: date


class MatriculaManualIn(BaseModel):
    aluno_id: Optional[str] = None
    novo_aluno: Optional[NovoAlunoIn] = None
    turma_id: str
    tipo: TipoMatricula = "regular"
    observacao: Optional[str] = Field(default=None, max_length=2000)
    ignorar_vagas: bool = False

    @model_validator(mode="after")
    def _um_aluno(self) -> "MatriculaManualIn":
        if bool(self.aluno_id) == bool(self.novo_aluno):
            raise ValueError("Informe um aluno existente ou os dados de um aluno novo.")
        return self


class MatriculaPatchIn(BaseModel):
    tipo: Optional[TipoMatricula] = None
    turma_id: Optional[str] = None  # transferência para outra Turma EAD do mesmo curso
    observacao: Optional[str] = Field(default=None, max_length=2000)


class MotivoIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


class LiberacaoIn(BaseModel):
    motivo: MotivoLiberacao
    texto: Optional[str] = Field(default=None, max_length=500)
    turma_id: Optional[str] = None


class MatriculaCriadaOut(BaseModel):
    matricula_id: str
    aluno_id: str
    convite_enviado: Optional[bool] = None
