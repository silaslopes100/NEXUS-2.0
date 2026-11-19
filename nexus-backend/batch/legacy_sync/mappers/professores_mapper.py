"""Professores. Fonte legado: `users` com perfil professor/instrutor.

Chave PIX e valor de hora-aula nao existem no legado (viraram campos novos);
ficam NULL para preenchimento no novo sistema. `data_inicio_aulas` usa
`users.date_added` como referencia.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .perfis_mapper import perfil_nome
from .usuarios_mapper import USERS_COLUMNS, carregar_usuarios_migrados


class ProfessorMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_COLUMNS + ["payment_keys"]
    target_table: ClassVar[str] = "professores"
    order_by: ClassVar[str | None] = "id"

    def iter_source(self, source, last_run=None):
        # Apenas quem ficou com perfil PROFESSOR em usuarios (fonte unica);
        # sem acesso ao destino (testes), usa a classificacao por role/flags.
        self._usuarios = carregar_usuarios_migrados(self.registry)
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            if self._usuarios is not None:
                nome = (self._usuarios.get(int(row["id"])) or {}).get("perfil")
            else:
                nome = perfil_nome(self.registry, row)
            if nome == "professor":
                yield row

    def _lotacao(self, row: dict) -> tuple[str | None, str | None]:
        """(polo_id, escola_id): os mesmos gravados no usuario (inclui o
        fallback polo-da-escola e o vinculo por CPF)."""
        u = (getattr(self, "_usuarios", None) or {}).get(self.as_int(row.get("id")))
        if u is not None:
            return u["polo_id"], u["escola_id"]
        if not self.registry:
            return None, None
        return (
            self.registry.resolve("polos", "users", row.get("polo")),
            self.registry.resolve("escolas", "users", row.get("escola")),
        )

    def map(self, row: dict) -> dict | None:
        usuario_id = self.registry.resolve("usuarios", "users", row.get("id")) if self.registry else None
        if not usuario_id:
            self.warn(f"professor sem usuario migrado: id={row.get('id')}")
            return None
        polo_id, escola_id = self._lotacao(row)
        return {
            "usuario_id": usuario_id,
            "polo_id": polo_id,
            "escola_id": escola_id,
            "chave_pix": self.str_clean(row.get("payment_keys"), 255) if "payment_keys" in row else None,
            "valor_hora_aula": None,
            "data_inicio_aulas": self.parse_ts(row.get("date_added")),
        }