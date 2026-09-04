"""Pagamentos. Fontes legado: `pagamento`, `pagseguro_transaction` e
`offline_payment` -> mesma tabela `pagamentos` (legacy_table distingue a origem).

O legado ja vinha migrando para Asaas (colunas asaas_*), entao o gateway real
e preservado. Mapeamentos de status int -> string sao heuristicos e ajustaveis.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .matriculas_mapper import _first_int

# Status int usados pelo legado (pagseguro/asaas) -> status novo. Ajustavel.
STATUS_INT = {0: "pendente", 1: "pago", 2: "recusado", 3: "cancelado", 4: "aguardando"}

PAGAMENTO_COLUMNS = [
    "id", "user_id", "course_id", "valor", "vendedor", "vendedor_status",
    "professor", "professor_status", "tipo", "date", "pacote_id", "quantidade",
]

PAGSEGURO_COLUMNS = [
    "id", "id_user", "id_courses", "amount", "document", "status", "pacote_id",
    "payment_method", "gateway", "asaas_customer_id", "asaas_payment_id",
    "billing_type", "invoice_url", "code", "due_date", "paid_at",
]

OFFLINE_COLUMNS = [
    "id", "user_id", "amount", "course_id", "document_image", "timestamp", "status", "vendedor",
]


class PagamentoMapper(BaseMapper):
    """Tabela `pagamento` (pagamentos avulsos por curso)."""

    source_table: ClassVar[str] = "pagamento"
    source_columns: ClassVar[list[str]] = PAGAMENTO_COLUMNS
    target_table: ClassVar[str] = "pagamentos"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        vendedor_ok = bool(self.str_clean(row.get("vendedor_status")))
        professor_ok = bool(self.str_clean(row.get("professor_status")))
        return {
            "pedido_licenca_id": None,
            "compra_disciplina_ead_id": None,
            "gateway": "legado_pagamento",
            "asaas_customer_id": None,
            "asaas_payment_id": None,
            "billing_type": None,
            "valor": self.as_float(row.get("valor")),
            "status": "pago" if (vendedor_ok or professor_ok) else "pendente",
            "boleto_url": None,
            "vencimento_em": None,
            "pago_em": self.parse_ts(row.get("date")),
        }


class PagseguroMapper(BaseMapper):
    """Tabela `pagseguro_transaction` (gateway Asaas/PagSeguro)."""

    source_table: ClassVar[str] = "pagseguro_transaction"
    source_columns: ClassVar[list[str]] = PAGSEGURO_COLUMNS
    target_table: ClassVar[str] = "pagamentos"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        status_int = self.as_int(row.get("status"))
        return {
            "pedido_licenca_id": None,
            "compra_disciplina_ead_id": None,
            "gateway": self.str_clean(row.get("gateway"), 32) or "pagseguro",
            "asaas_customer_id": self.str_clean(row.get("asaas_customer_id"), 64),
            "asaas_payment_id": self.str_clean(row.get("asaas_payment_id"), 64),
            "billing_type": self.str_clean(row.get("billing_type"), 32),
            "valor": self.as_float(row.get("amount")),
            "status": STATUS_INT.get(status_int, "pendente"),
            "boleto_url": self.str_clean(row.get("invoice_url"), 500),
            "vencimento_em": self.parse_date(row.get("due_date")),
            "pago_em": self.parse_ts(row.get("paid_at")),
        }


class OfflinePaymentMapper(BaseMapper):
    """Tabela `offline_payment` (comprovante manual)."""

    source_table: ClassVar[str] = "offline_payment"
    source_columns: ClassVar[list[str]] = OFFLINE_COLUMNS
    target_table: ClassVar[str] = "pagamentos"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        status_int = self.as_int(row.get("status"))
        return {
            "pedido_licenca_id": None,
            "compra_disciplina_ead_id": None,
            "gateway": "legado_offline",
            "asaas_customer_id": None,
            "asaas_payment_id": None,
            "billing_type": None,
            "valor": self.as_float(row.get("amount")),
            "status": STATUS_INT.get(status_int, "pendente"),
            "boleto_url": self.str_clean(row.get("document_image"), 500),
            "vencimento_em": None,
            "pago_em": self.parse_ts(row.get("timestamp")),
        }