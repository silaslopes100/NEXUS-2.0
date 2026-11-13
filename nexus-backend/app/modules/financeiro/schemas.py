"""Schemas do módulo Financeiro & Logística (2.4)."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

TipoPedido = Literal["livro", "licenca"]
StatusPedido = Literal[
    "aguardando_pagamento",
    "pago_aguardando_envio",
    "enviado",
    "entregue",
    "concluido",
    "cancelado",
]
StatusPagamento = Literal["pendente", "pago", "vencido", "cancelado", "estornado", "falhou"]
MeioPagamento = Literal["BOLETO", "PIX", "CREDIT_CARD"]
OrigemStatus = Literal["usuario", "webhook", "cron", "migracao"]


# ---------------------------------------------------------------------------
# Filtros comuns (listas, relatórios e exportações)
# ---------------------------------------------------------------------------

class FiltrosPeriodo(BaseModel):
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    mes: Optional[int] = Field(default=None, ge=1, le=12)
    semestre: Optional[int] = Field(default=None, ge=1, le=2)
    ano: Optional[int] = Field(default=None, ge=2000, le=2100)
    polo_id: Optional[str] = None
    escola_id: Optional[str] = None
    modalidade: Optional[Literal["ead"]] = None
    status: Optional[str] = None
    tipo: Optional[TipoPedido] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _intervalo_valido(self) -> "FiltrosPeriodo":
        if self.data_inicio and self.data_fim and self.data_inicio > self.data_fim:
            raise ValueError("data_inicio não pode ser posterior a data_fim")
        return self


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------

class ProdutoBase(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    descricao: Optional[str] = None
    disciplina_id: Optional[str] = None
    preco: float = Field(ge=0)
    peso_g: Optional[int] = Field(default=None, ge=0)
    altura_cm: Optional[float] = Field(default=None, ge=0)
    largura_cm: Optional[float] = Field(default=None, ge=0)
    comprimento_cm: Optional[float] = Field(default=None, ge=0)
    ativo: bool = True


class ProdutoCreate(ProdutoBase):
    tipo: TipoPedido
    sku: str = Field(min_length=2, max_length=64)


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=255)
    descricao: Optional[str] = None
    disciplina_id: Optional[str] = None
    preco: Optional[float] = Field(default=None, ge=0)
    peso_g: Optional[int] = Field(default=None, ge=0)
    altura_cm: Optional[float] = Field(default=None, ge=0)
    largura_cm: Optional[float] = Field(default=None, ge=0)
    comprimento_cm: Optional[float] = Field(default=None, ge=0)
    ativo: Optional[bool] = None


class ProdutoResponse(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tipo: TipoPedido
    sku: str
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ProdutoListResponse(BaseModel):
    total: int
    items: List[ProdutoResponse]


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------

class EnderecoEntrega(BaseModel):
    nome: Optional[str] = Field(default=None, max_length=255)
    cep: Optional[str] = Field(default=None, max_length=16)
    logradouro: Optional[str] = Field(default=None, max_length=255)
    numero: Optional[str] = Field(default=None, max_length=32)
    complemento: Optional[str] = Field(default=None, max_length=255)
    bairro: Optional[str] = Field(default=None, max_length=255)
    cidade: Optional[str] = Field(default=None, max_length=255)
    uf: Optional[str] = Field(default=None, max_length=2)
    telefone: Optional[str] = Field(default=None, max_length=32)


class PedidoItemIn(BaseModel):
    produto_id: str
    quantidade: int = Field(ge=1, le=100000)


class PedidoCreate(BaseModel):
    tipo: TipoPedido
    polo_id: Optional[str] = None  # Polo: assume o do usuário
    escola_id: Optional[str] = None
    itens: List[PedidoItemIn] = Field(min_length=1)
    endereco: Optional[EnderecoEntrega] = None  # padrão: endereço do Polo
    observacao: Optional[str] = Field(default=None, max_length=2000)


class PedidoStatusUpdate(BaseModel):
    """Mudança manual de status (baixa de pagamento offline, conclusão ou cancelamento)."""

    status: Literal["pago_aguardando_envio", "concluido", "cancelado"]
    observacao: Optional[str] = Field(default=None, max_length=2000)
    motivo_cancelamento: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _motivo_obrigatorio(self) -> "PedidoStatusUpdate":
        if self.status == "cancelado" and not (self.motivo_cancelamento or "").strip():
            raise ValueError("Informe o motivo do cancelamento")
        return self


class PedidoItemResponse(BaseModel):
    id: str
    produto_id: Optional[str] = None
    disciplina_id: Optional[str] = None
    descricao: Optional[str] = None
    quantidade: int
    valor_unitario: float
    valor_total: float


class PedidoHistoricoResponse(BaseModel):
    id: str
    status_de: Optional[str] = None
    status_para: str
    usuario_id: Optional[str] = None
    origem: str
    observacao: Optional[str] = None
    criado_em: Optional[datetime] = None


class EnvioResponse(BaseModel):
    id: str
    transportadora: Optional[str] = None
    codigo_rastreio: Optional[str] = None
    volumes: int = 1
    peso_total_g: Optional[int] = None
    etiqueta_gerada_em: Optional[datetime] = None
    enviado_por: Optional[str] = None
    enviado_em: Optional[datetime] = None
    observacao: Optional[str] = None


class PedidoResponse(BaseModel):
    id: str
    numero: str
    tipo: TipoPedido
    status: StatusPedido
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    escola_nome: Optional[str] = None
    solicitante_id: Optional[str] = None
    valor_bruto: float = 0
    desconto: float = 0
    valor_total: float = 0
    fornecedor: Optional[str] = None
    endereco: EnderecoEntrega = Field(default_factory=EnderecoEntrega)
    observacao: Optional[str] = None
    pago_em: Optional[datetime] = None
    cancelado_em: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None
    enviado_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    itens: List[PedidoItemResponse] = Field(default_factory=list)
    historico: List[PedidoHistoricoResponse] = Field(default_factory=list)
    envios: List[EnvioResponse] = Field(default_factory=list)


class PedidoListResponse(BaseModel):
    total: int
    items: List[PedidoResponse]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Pagamentos
# ---------------------------------------------------------------------------

class PagamentoResponse(BaseModel):
    id: str
    pedido_id: Optional[str] = None
    pedido_numero: Optional[str] = None
    polo_id: Optional[str] = None
    polo_nome: Optional[str] = None
    escola_id: Optional[str] = None
    aluno_id: Optional[str] = None
    gateway: Optional[str] = None
    ambiente: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    billing_type: Optional[str] = None
    valor: Optional[float] = None
    valor_liquido: Optional[float] = None
    status: Optional[str] = None
    parcelas: Optional[int] = None
    boleto_url: Optional[str] = None
    invoice_url: Optional[str] = None
    linha_digitavel: Optional[str] = None
    pix_copia_cola: Optional[str] = None
    vencimento_em: Optional[date] = None
    pago_em: Optional[datetime] = None
    cancelado_em: Optional[datetime] = None
    descricao: Optional[str] = None
    criado_em: Optional[datetime] = None


class PagamentoListResponse(BaseModel):
    total: int
    items: List[PagamentoResponse]
    limit: int
    offset: int
