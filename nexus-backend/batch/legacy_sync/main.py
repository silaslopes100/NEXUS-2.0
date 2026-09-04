"""CLI do batch: `python -m batch.legacy_sync.main --mode=full|incremental`

Opcoes:
  --mode full|incremental   modo de execucao
  --only NomeDoMapper       roda apenas um mapper (ex: --only=UsuarioMapper)
  --create-schema           cria/valida o schema do destino antes de rodar
  --dry-run                 nao toca o destino: so valida conexoes, preflight
                            de colunas e contagens
  --no-report               nao gera relatorio_baseline.md no modo full
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import run_incremental, run_full_load
from .config import config
from .etl_sync_log import RunLogger
from .registry import IdRegistry
from .runner import MapperRunner
from .run_full_load import FULL_LOAD_ORDER
from .source_mysql import MySQLSource
from .target_postgres import PostgresTarget

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("legacy_sync")


def _preflight(source: MySQLSource) -> None:
    """Compara colunas esperadas (dicionario de dados) com o MySQL real."""
    esperado: dict[str, list[str]] = {}
    for cls in FULL_LOAD_ORDER:
        if cls.source_table:
            esperado.setdefault(cls.source_table, []).extend(cls.source_columns)
    logger.info("Executando preflight de colunas (%s tabelas)...", len(esperado))
    report = source.preflight(esperado)
    problemas = 0
    for tabela, info in sorted(report.items()):
        if info["ok"]:
            logger.info("  ok      %s", tabela)
        else:
            problemas += 1
            logger.warning("  FALTA   %s: colunas ausentes no MySQL -> %s", tabela, info["faltando"])
    if problemas:
        logger.warning("Preflight com %s tabela(s) divergente(s). Revise os mappers.", problemas)
    else:
        logger.info("Preflight OK: todas as colunas esperadas existem no legado.")


def _main() -> None:
    parser = argparse.ArgumentParser(description="ETL NEXUS 2.0 (legado MySQL -> NeonDB)")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    parser.add_argument("--only", default=None, help="Nome do mapper (ex: UsuarioMapper)")
    parser.add_argument("--create-schema", action="store_true", help="cria/valida o schema")
    parser.add_argument("--dry-run", action="store_true", help="so valida conexoes e colunas")
    parser.add_argument("--no-report", action="store_true", help="nao gera relatorio no full")
    args = parser.parse_args()

    with MySQLSource() as source:
        logger.info(
            "Conectado ao legado %s@%s:%s/%s",
            config.MYSQL_USER, config.MYSQL_HOST, config.MYSQL_PORT, config.MYSQL_DB,
        )
        _preflight(source)

        if args.dry_run:
            logger.info("Dry-run: destino intacto. Encerrando.")
            return

        dsn = config.require_pg()
        target = PostgresTarget(dsn)
        try:
            if args.create_schema or args.mode == "full":
                target.ensure_schema()

            registry = IdRegistry(target)
            run_log = RunLogger(target, args.mode)
            run_log.start()
            runner = MapperRunner(source, target, registry, run_log)

            try:
                if args.mode == "full":
                    run_full_load.run_full_load(
                        source, target, registry, run_log, runner, only=args.only
                    )
                    if not args.no_report:
                        run_full_load.generate_baseline_report(
                            source, target, Path(__file__).resolve().parents[1] / "relatorios"
                        )
                else:
                    last_run = run_log.last_successful_run()
                    run_incremental.run_incremental(
                        source, target, registry, run_log, runner, last_run, only=args.only
                    )
            except Exception:
                run_log.finish("falhou")
                logger.exception("Execucao falhou; marcada como falhou em etl_sync_runs.")
                raise
            run_log.finish("ok")
            logger.info(
                "Execucao concluida: %d lidos, %d inseridos, %d atualizados, %d erros.",
                run_log.total_lido, run_log.total_inserido,
                run_log.total_atualizado, run_log.total_erro,
            )
        finally:
            target.close()


if __name__ == "__main__":
    sys.exit(_main())