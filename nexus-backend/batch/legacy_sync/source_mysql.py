"""Conexao de LEITURA ao MySQL legado (PyMySQL). Somente SELECT."""
from __future__ import annotations

import logging
from typing import Iterable, Sequence

import pymysql
from pymysql.cursors import DictCursor, SSCursor

from .config import config

logger = logging.getLogger(__name__)


class MySQLSource:
    """Leitura somente-read do legado. Toda consulta e um SELECT."""

    def __init__(self) -> None:
        self._conn: pymysql.Connection | None = None

    @property
    def conn(self) -> pymysql.Connection:
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=config.MYSQL_HOST,
                port=config.MYSQL_PORT,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                database=config.MYSQL_DB,
                charset="utf8mb4",
                cursorclass=DictCursor,
                read_timeout=60,
                write_timeout=60,
            )
            # Garantia extra: qualquer escrita acidental falha.
            self._conn.autocommit(False)
        return self._conn

    def close(self) -> None:
        if self._conn is not None and self._conn.open:
            self._conn.close()

    def __enter__(self) -> "MySQLSource":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def count(self, table: str, where: str | None = None, params: Sequence = ()) -> int:
        sql = f"SELECT COUNT(*) AS n FROM `{table}`"
        if where:
            sql += f" WHERE {where}"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return int(row["n"]) if row else 0

    def actual_columns(self, table: str) -> set[str]:
        """Colunas existentes hoje no MySQL para uma tabela (INFORMATION_SCHEMA)."""
        sql = """
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (config.MYSQL_DB, table))
            return {r["COLUMN_NAME"].lower() for r in cur.fetchall()}

    def stream(
        self,
        table: str,
        columns: Sequence[str],
        where: str | None = None,
        params: Sequence = (),
        order: str | None = None,
        batch_size: int | None = None,
    ) -> Iterable[dict]:
        """Itera por lotes usando cursor server-side (nao carrega tudo em memoria)."""
        size = batch_size or config.BATCH_SIZE
        cols = ", ".join(f"`{c}`" for c in columns)
        sql = f"SELECT {cols} FROM `{table}`"
        if where:
            sql += f" WHERE {where}"
        if order:
            sql += f" ORDER BY {order}"
        cursor = self.conn.cursor(SSCursor)
        try:
            cursor.execute(sql, params)
            while True:
                rows = cursor.fetchmany(size)
                if not rows:
                    break
                for row in rows:
                    yield row
        finally:
            cursor.close()

    def preflight(self, expected: dict[str, Sequence[str]]) -> dict[str, dict]:
        """Compara as colunas esperadas (dicionario de dados) com o MySQL real.

        Retorna { tabela: { "faltando": [...], "extras": [...], "ok": bool } }.
        Usado como dry-run para validar premissas de mapeamento.
        """
        report: dict[str, dict] = {}
        for table, cols in expected.items():
            actual = self.actual_columns(table)
            missing = sorted(set(c.lower() for c in cols) - actual)
            extras = sorted(actual - set(c.lower() for c in cols))
            report[table] = {
                "faltando": missing,
                "extras": extras,
                "ok": not missing,
            }
        return report