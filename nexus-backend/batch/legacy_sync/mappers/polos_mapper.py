"""Polos. Fonte legado: tabela `users` (os polos vivem dentro do user, como
`polo` + `nome_polo` + endereco). Extrai UM polo por valor distinto de
`users.polo`, usando o representante de menor id como fonte dos dados.

O legacy_id do polo e o proprio valor de `users.polo` (nao o id do usuario).
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

USERS_POLO_COLS = [
    "id", "polo", "nome_polo", "first_name", "last_name", "email", "cpf",
    "cep", "logradouro", "numero", "bairro", "cidade", "uf", "complemento",
    "telefone", "status",
]


class PoloMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_POLO_COLS
    target_table: ClassVar[str] = "polos"
    order_by: ClassVar[str | None] = "id"

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._processados: set[int] = set()

    def iter_source(self, source, last_run=None):
        """Dedup: um polo por valor distinto de users.polo."""
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            polo_id = BaseMapper.as_int(row.get("polo"))
            if polo_id is None or polo_id == 0:
                continue
            if polo_id in self._processados:
                continue
            self._processados.add(polo_id)
            yield row

    def current_legacy_id(self, row: dict) -> int:
        return int(row["polo"])

    def map(self, row: dict) -> dict | None:
        responsavel = " ".join(
            p for p in (self.str_clean(row.get("first_name")), self.str_clean(row.get("last_name"))) if p
        )
        return {
            "nome": self.str_clean(row.get("nome_polo")) or f"Polo {row['polo']}",
            "responsavel_nome": responsavel or None,
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