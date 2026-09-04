"""Licencas. Fonte legado: `licences`.

- licences -> licencas_atribuidas (atribuicao por Polo).
- O "Estoque Geral" (estoque_licencas) nao tem equivalente 1:1 no legado
  (que so registra atribuicoes) e sera iniciado vazio, controlado pelo novo
  modulo de Vendas. Documentar para a equipe conferir saldos.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

LICENCES_COLUMNS = [
    "id", "polo_id", "course_id", "pacote_id", "date_added", "total_licences",
    "valor", "polo_transferiu",
]


class LicencaMapper(BaseMapper):
    source_table: ClassVar[str] = "licences"
    source_columns: ClassVar[list[str]] = LICENCES_COLUMNS
    target_table: ClassVar[str] = "licencas_atribuidas"
    order_by: ClassVar[str | None] = "id"
    incremental_column: ClassVar[str | None] = "date_added"

    def map(self, row: dict) -> dict | None:
        polo_id = (
            self.registry.resolve("polos", "users", row.get("polo_id")) if self.registry else None
        )
        return {
            "disciplina_id": None,  # legado vincula licenca a course/pacote, nao a disciplina
            "polo_id": polo_id,
            "escola_id": None,
            "aluno_id": None,
            "quantidade": self.as_int(row.get("total_licences")) or 0,
            "atribuido_por": None,
            "atribuido_em": self.parse_ts(row.get("date_added")),
        }