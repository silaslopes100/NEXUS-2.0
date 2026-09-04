"""Professores. Fonte legado: `users` com perfil professor/instrutor.

Chave PIX e valor de hora-aula nao existem no legado (viraram campos novos);
ficam NULL para preenchimento no novo sistema. `data_inicio_aulas` usa
`users.date_added` como referencia.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .perfis_mapper import perfil_nome
from .usuarios_mapper import USERS_COLUMNS


class ProfessorMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_COLUMNS + ["payment_keys"]
    target_table: ClassVar[str] = "professores"
    order_by: ClassVar[str | None] = "id"

    def iter_source(self, source, last_run=None):
        # Apenas usuarios classificados como PROFESSOR (role mapeada ou
        # heuristica por flags). is_vendedor (polo) nao entra aqui.
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            if perfil_nome(self.registry, row) == "professor":
                yield row

    def map(self, row: dict) -> dict | None:
        usuario_id = self.registry.resolve("usuarios", "users", row.get("id")) if self.registry else None
        if not usuario_id:
            self.warn(f"professor sem usuario migrado: id={row.get('id')}")
            return None
        return {
            "usuario_id": usuario_id,
            "polo_id": self.registry.resolve("polos", "users", row.get("polo")) if self.registry else None,
            "escola_id": self.registry.resolve("escolas", "users", row.get("escola")) if self.registry else None,
            "chave_pix": self.str_clean(row.get("payment_keys"), 255) if "payment_keys" in row else None,
            "valor_hora_aula": None,
            "data_inicio_aulas": self.parse_ts(row.get("date_added")),
        }