"""Cupons. Fonte legado: `coupons`.

`discount_percentage` e VARCHAR no legado; convertido para NUMERIC com
tolerancia a virgula. `created_at`/`expiry_date` sao unix timestamps.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

COUPONS_COLUMNS = ["id", "code", "discount_percentage", "created_at", "expiry_date"]


class CupomMapper(BaseMapper):
    source_table: ClassVar[str] = "coupons"
    source_columns: ClassVar[list[str]] = COUPONS_COLUMNS
    target_table: ClassVar[str] = "cupons"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        codigo = self.str_clean(row.get("code"), 64)
        if not codigo:
            return None
        return {
            "codigo": codigo,
            "percentual_desconto": self.as_float(row.get("discount_percentage")),
            "valido_de": self.parse_date(row.get("created_at")),
            "valido_ate": self.parse_date(row.get("expiry_date")),
        }