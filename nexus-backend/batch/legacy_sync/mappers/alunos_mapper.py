"""Alunos. Fonte legado: `users` com perfil aluno (role/aluno ou sem flags).

- numero_matricula: usa `users.codigo` quando existe; senao gera
  `legacy-<id>` deterministico (nao colide entre execucoes).
- modalidade: 'polo' se tem polo/escola vinculados, senao 'ead'.
- data_nascimento: `users.nascimento` (varchar livre, parse tolerante).
- status: 'desistente' quando `users.revalidacao` indica revalidacao pendente
  (heuristica); detalhes de churn (>1 ano parado) sao job diario do batch.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .perfis_mapper import perfil_nome
from .usuarios_mapper import USERS_COLUMNS


class AlunoMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_COLUMNS + ["codigo", "payment_keys"]
    target_table: ClassVar[str] = "alunos"
    order_by: ClassVar[str | None] = "id"

    def iter_source(self, source, last_run=None):
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            # Apenas usuarios classificados como ALUNO (mesma logica do
            # usuarios_mapper: role mapeada -> heuristica por flags).
            if perfil_nome(self.registry, row) == "aluno":
                yield row

    def map(self, row: dict) -> dict | None:
        usuario_id = self.registry.resolve("usuarios", "users", row.get("id")) if self.registry else None
        if not usuario_id:
            self.warn(f"aluno sem usuario migrado: id={row.get('id')}")
            return None

        polo_id = self.registry.resolve("polos", "users", row.get("polo")) if self.registry else None
        escola_id = self.registry.resolve("escolas", "users", row.get("escola")) if self.registry else None
        modalidade = "polo" if (polo_id or escola_id) else "ead"

        matricula = self.str_clean(row.get("codigo"), 32) or f"legacy-{row['id']}"
        nascimento = self.parse_date(row.get("nascimento"))

        revalidacao = self.str_clean(row.get("revalidacao"))
        status = "desistente" if revalidacao else "ativo"

        return {
            "usuario_id": usuario_id,
            "polo_id": polo_id,
            "escola_id": escola_id,
            "modalidade": modalidade,
            "numero_matricula": matricula,
            "data_nascimento": nascimento,
            "status": status,
            "ultima_movimentacao_em": self.parse_ts(row.get("last_modified")),
        }