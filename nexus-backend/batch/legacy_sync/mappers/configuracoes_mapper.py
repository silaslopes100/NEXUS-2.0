"""Configuracoes do sistema. Fontes legado: `settings`, `frontend_settings` e
`customize` (todas chave/valor) -> `configuracoes` (valor JSONB).

A chave e prefixada com a origem para nao colidir entre tabelas.
"""
from __future__ import annotations

import json
from typing import ClassVar

from .base import BaseMapper

CHAVE_COLS = ["id", "key", "value"]


class ConfigMapper(BaseMapper):
    source_table: ClassVar[str] = "settings"
    source_columns: ClassVar[list[str]] = CHAVE_COLS
    target_table: ClassVar[str] = "configuracoes"
    order_by: ClassVar[str | None] = "id"
    prefixo: ClassVar[str] = "settings"

    def map(self, row: dict) -> dict | None:
        chave = self.str_clean(row.get("key"), 240)
        if not chave:
            return None
        valor = row.get("value")
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except (json.JSONDecodeError, TypeError):
                valor = valor
        return {
            "chave": f"{self.prefixo}.{chave}",
            "valor": valor if valor is not None else "",
        }


class FrontendSettingsMapper(ConfigMapper):
    source_table: ClassVar[str] = "frontend_settings"
    prefixo: ClassVar[str] = "frontend"


class CustomizeMapper(ConfigMapper):
    source_table: ClassVar[str] = "customize"
    prefixo: ClassVar[str] = "customize"