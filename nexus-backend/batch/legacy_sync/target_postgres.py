"""Escrita no PostgreSQL destino (NeonDB): schema + upserts idempotentes."""
from __future__ import annotations

import logging
from typing import Sequence

import psycopg2
from psycopg2.extras import execute_values

from . import schema

logger = logging.getLogger(__name__)

TRACKING_COLS = ("legacy_table", "legacy_id", "synced_at")


class PostgresTarget:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: psycopg2.extensions.connection | None = None

    @property
    def conn(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self._dsn)
        return self._conn

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()

    def execute(self, sql: str, params: Sequence = ()) -> None:
        with self.conn.cursor() as cur:
            cur.execute(sql, params)

    def executemany(self, sql: str, rows: Sequence[Sequence]) -> None:
        with self.conn.cursor() as cur:
            cur.executemany(sql, rows)

    def commit(self) -> None:
        self.conn.commit()

    def ensure_schema(self) -> None:
        """Cria todas as tabelas do destino (idempotente) na ordem de dependencia."""
        logger.info("Criando/validando schema do destino (%s tabelas)...", len(schema.DDL))
        with self.conn.cursor() as cur:
            for stmt in schema.DDL:
                cur.execute(stmt)
        self.commit()

    def upsert_rows(
        self,
        table: str,
        columns: Sequence[str],
        rows: Sequence[Sequence],
    ) -> list[tuple[str, bool]]:
        """Insere/atualiza em lote.

        Base do upsert: UNIQUE (legacy_table, legacy_id). Retorna, na MESMA
        ordem das linhas de entrada, (id, inseriu) para o registry registrar
        os novos ids antes dos mappers filhos resolverem as FKs.
        """
        if not rows:
            return []
        non_tracking = [c for c in columns if c not in TRACKING_COLS]
        updates = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in non_tracking if c != "id"
        )
        if updates:
            updates += ", atualizado_em = now(), synced_at = EXCLUDED.synced_at"
        cols = ", ".join(columns)
        placeholders = "({})".format(", ".join(["%s"] * len(columns)))
        sql = (
            f"INSERT INTO {table} ({cols}) VALUES %s "
            f"ON CONFLICT (legacy_table, legacy_id) DO UPDATE SET {updates} "
            f"RETURNING id, (xmax = 0) AS inserted"
        )
        outcome: list[tuple[str, bool]] = []
        with self.conn.cursor() as cur:
            for chunk in _chunks(rows, 500):
                for row_id, inserted in execute_values(
                    cur, sql, chunk, fetch=True, page_size=500
                ):
                    outcome.append((str(row_id), bool(inserted)))
        return outcome

    def upsert_rows_conflict(
        self,
        table: str,
        columns: Sequence[str],
        conflict_columns: Sequence[str],
        rows: Sequence[Sequence],
    ) -> int:
        """Insere/ignora (ON CONFLICT DO NOTHING) para tabelas sem tracking legado."""
        if not rows:
            return 0
        cols = ", ".join(columns)
        conflict = ", ".join(conflict_columns)
        placeholders = "({})".format(", ".join(["%s"] * len(columns)))
        sql = (
            f"INSERT INTO {table} ({cols}) VALUES %s "
            f"ON CONFLICT ({conflict}) DO NOTHING"
        )
        inserted = 0
        with self.conn.cursor() as cur:
            for chunk in _chunks(rows, 500):
                for count in execute_values(
                    cur, sql, chunk, fetch=True, page_size=500
                ):
                    inserted += int(count == "1" or count is True)
        return inserted

    def select_legacy_ids(self, table: str) -> dict[int, str]:
        """legacy_id -> uuid para resolucao de FK dos mappers filhos."""
        sql = (
            f"SELECT legacy_id, id FROM {table} "
            f"WHERE legacy_id IS NOT NULL AND legacy_id <> 0"
        )
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return {int(r[0]): str(r[1]) for r in cur.fetchall()}


def _chunks(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]