"""Bookkeeping do ETL: etl_sync_runs (execucoes) e etl_erros (linhas com falha)."""
from __future__ import annotations

import json
from typing import Any

from .target_postgres import PostgresTarget


class RunLogger:
    """Registra uma execucao e os erros isolados por linha."""

    def __init__(self, target: PostgresTarget, modo: str) -> None:
        self.target = target
        self.modo = modo
        self.run_id: int | None = None
        self.total_lido = 0
        self.total_inserido = 0
        self.total_atualizado = 0
        self.total_erro = 0

    def start(self) -> None:
        with self.target.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO etl_sync_runs (modo, status) VALUES (%s, 'rodando') "
                "RETURNING id",
                (self.modo,),
            )
            self.run_id = cur.fetchone()[0]
        self.target.commit()

    def add_lido(self, n: int = 1) -> None:
        self.total_lido += n

    def add_result(self, inseridos: int, atualizados: int) -> None:
        self.total_inserido += inseridos
        self.total_atualizado += atualizados

    def add_erro(self, tabela: str, id_origem: Any, erro: str, linha_raw: dict) -> None:
        self.total_erro += 1
        if self.run_id is None:
            return
        raw = json.dumps(linha_raw, ensure_ascii=False, default=str)
        self.target.execute(
            "INSERT INTO etl_erros (execucao_id, tabela_origem, id_origem, erro, linha_raw) "
            "VALUES (%s, %s, %s, %s, %s::jsonb)",
            (self.run_id, tabela, str(id_origem), erro[:4000], raw),
        )

    def finish(self, status: str) -> None:
        self.target.execute(
            "UPDATE etl_sync_runs SET finalizado_em = now(), status = %s, "
            "total_lido = %s, total_inserido = %s, total_atualizado = %s, total_erro = %s "
            "WHERE id = %s",
            (
                status,
                self.total_lido,
                self.total_inserido,
                self.total_atualizado,
                self.total_erro,
                self.run_id,
            ),
        )
        self.target.commit()

    def last_successful_run(self) -> Any:
        """Maior finalizado_em de uma execucao bem-sucedida (base do incremental)."""
        sql = (
            "SELECT MAX(finalizado_em) FROM etl_sync_runs "
            "WHERE status = 'ok' AND modo = 'full'"
        )
        with self.target.conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]