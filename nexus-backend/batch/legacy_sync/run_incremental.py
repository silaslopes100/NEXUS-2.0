"""Atualizacao diaria. Usa a coluna `last_modified` (quando existir e confiavel)
para so ler o que mudou desde a ultima execucao bem-sucedida; tabelas sem essa
coluna rodam em modo de re-upsert completo (idempotente, nunca duplica).
"""
from __future__ import annotations

import logging

from .mappers.perfis_mapper import preload_role_map
from .run_full_load import rodar_pos_passos, selecionar_mappers

logger = logging.getLogger(__name__)


def run_incremental(source, target, registry, run_log, runner, last_run, only: str | None = None) -> None:
    mappers = selecionar_mappers(only)

    preload_role_map(source, registry)

    for cls in mappers:
        mapper = cls(registry=registry)
        if mapper.incremental_column and last_run is not None:
            logger.info(
                "%s -> %s (incremental desde %s)",
                mapper.source_table, mapper.target_table, last_run,
            )
        else:
            logger.info(
                "%s -> %s (sem coluna de data; re-upsert completo idempotente)",
                mapper.source_table, mapper.target_table,
            )
        runner.run(mapper, last_run=last_run if mapper.incremental_column else None)

    rodar_pos_passos(source, target, mappers)
