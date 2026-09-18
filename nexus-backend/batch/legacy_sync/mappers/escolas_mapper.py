"""Escolas. Fonte legado: tabela `users` (campos `escola`, `nome_escola`,
`polo`). Extrai UMA escola por valor distinto de `users.escola`.

A escola nao pode existir sem vinculo a um Polo; quando o `users.polo` nao
existe ou o polo ainda nao foi migrado, a escola fica com polo_id NULL e e
contada como pendente de revisao.

NOTA: Este mapper NAO e mais usado no fluxo principal (FULL_LOAD_ORDER).
A carga de escolas agora e feita via SQL direto em run_full_load.py
(POST_STEP load_escolas_from_legacy), que faz JOIN entre MySQL users
e PostgreSQL polos. Mantido apenas para historico e testes.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper


class EscolaMapper(BaseMapper):
    target_table: ClassVar[str] = "escolas"
    order_by: ClassVar[str | None] = "id"

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._processados: set[int] = set()

    def iter_source(self, source, last_run=None):
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            escola_id = BaseMapper.as_int(row.get("escola"))
            if escola_id is None or escola_id == 0:
                continue
            if escola_id in self._processados:
                continue
            self._processados.add(escola_id)
            yield row

    def current_legacy_id(self, row: dict) -> int:
        return int(row["escola"])

    def map(self, row: dict) -> dict | None:
        responsavel = " ".join(
            p for p in (self.str_clean(row.get("first_name")), self.str_clean(row.get("last_name"))) if p
        )
        return {
            "polo_id": self.registry.resolve("polos", "users", row.get("polo")) if self.registry else None,
            "nome": self.str_clean(row.get("nome_escola")) or f"Escola {row['escola']}",
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