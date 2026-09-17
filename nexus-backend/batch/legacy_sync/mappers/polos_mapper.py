"""Carga de polos a partir dos usuarios legados com ``role_id = 3``.

Cada linha selecionada representa uma linha de origem da carga. O coordenador
legado (``role_id = 2`` com o mesmo CPF) e vinculado em um passo posterior,
depois que o mapper de usuarios tiver criado os UUIDs de destino.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

USERS_POLO_COLS = [
    "id", "role_id", "polo", "nome_polo", "first_name", "last_name", "email", "cpf",
    "cep", "logradouro", "numero", "bairro", "cidade", "uf", "complemento",
    "telefone", "status",
]


class PoloMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_POLO_COLS
    target_table: ClassVar[str] = "polos"
    order_by: ClassVar[str | None] = "id"

    def initial_where(self, last_run=None) -> str | None:
        return "role_id = 3"

    def current_legacy_id(self, row: dict) -> int:
        return int(row["id"])

    def map(self, row: dict) -> dict | None:
        return {
            "nome": self.str_clean(row.get("nome_polo")) or f"Polo {row['id']}",
            "responsavel_nome": self.str_clean(row.get("first_name"), 255),
            "responsavel_cpf": self.str_clean(row.get("cpf"), 20),
            "responsavel_email": self.str_clean(row.get("email"), 255),
            "cep": self.str_clean(row.get("cep"), 16),
            "logradouro": self.str_clean(row.get("logradouro"), 255),
            "numero": self.str_clean(row.get("numero"), 32),
            "bairro": self.str_clean(row.get("bairro"), 255),
            "cidade": self.str_clean(row.get("cidade"), 255),
            "uf": self.str_clean(row.get("uf"), 2),
            "complemento": self.str_clean(row.get("complemento"), 255),
            "status": "ativo",
        }