"""Runner: aplica um mapper sobre o legado e grava no destino, com isolamento
de erro por linha (nunca derruba o batch por causa de um registro corrompido)
e commit em lotes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .etl_sync_log import RunLogger
from .mappers.base import BaseMapper
from .registry import IdRegistry
from .source_mysql import MySQLSource
from .target_postgres import PostgresTarget

logger = logging.getLogger(__name__)


class MapperRunner:
    def __init__(
        self,
        source: MySQLSource,
        target: PostgresTarget,
        registry: IdRegistry,
        run_log: RunLogger,
        batch_size: int = 500,
    ) -> None:
        self.source = source
        self.target = target
        self.registry = registry
        self.run_log = run_log
        self.batch_size = batch_size

    def run(self, mapper: BaseMapper, last_run=None) -> dict:
        """Executa o mapper e retorna {lido, inserido, atualizado, erro}."""
        logger.info(
            "Mapper %s -> %s", mapper.source_table or "-", mapper.target_table
        )
        contador = {"lido": 0, "inserido": 0, "atualizado": 0, "erro": 0}
        buffer: list = []
        cols: list[str] | None = None

        def flush() -> None:
            nonlocal cols
            if not buffer:
                return
            if mapper.has_tracking:
                # dedup defensivo: mesmo (source_table, legacy_id) no lote usa o ultimo
                uniq: dict[tuple, list] = {}
                for legacy_id, vals in buffer:
                    uniq[(mapper.source_table, legacy_id)] = vals
                itens = list(uniq.items())
                rows = [v for _, v in itens]
                keys = [k for k, _ in itens]
                outcomes = self.target.upsert_rows(mapper.target_table, cols, rows)
                for (_, legacy_id), (row_id, inseriu) in zip(keys, outcomes):
                    if inseriu and mapper.source_table:
                        self.registry.register(
                            mapper.target_table, mapper.source_table, legacy_id, row_id
                        )
                contador["inserido"] += sum(1 for _, ins in outcomes if ins)
                contador["atualizado"] += sum(1 for _, ins in outcomes if not ins)
            else:
                contador["inserido"] += self.target.upsert_rows_conflict(
                    mapper.target_table, cols, mapper.conflict_columns, buffer
                )
            self.target.commit()
            buffer.clear()

        for row in mapper.iter_source(self.source, last_run):
            contador["lido"] += 1
            try:
                mapped = mapper.map(row)
            except Exception as exc:  # noqa: BLE001 - isolamento por linha
                contador["erro"] += 1
                self.run_log.add_erro(
                    mapper.target_table,
                    mapper.current_legacy_id(row),
                    f"{type(exc).__name__}: {exc}",
                    dict(row),
                )
                continue
            if not mapped:
                continue
            legacy_id = mapper.current_legacy_id(row)
            if mapper.has_tracking:
                cols = list(mapped.keys()) + ["legacy_table", "legacy_id", "synced_at"]
                vals = list(mapped.values()) + [
                    mapper.source_table,
                    legacy_id,
                    datetime.now(timezone.utc),
                ]
                buffer.append((legacy_id, vals))
            else:
                cols = list(mapped.keys())
                vals = list(mapped.values())
                buffer.append(vals)
            if len(buffer) >= self.batch_size:
                flush()

        flush()
        self.run_log.add_lido(contador["lido"])
        self.run_log.add_result(contador["inserido"], contador["atualizado"])
        return contador