"""Base dos mappers: contrato + utilitarios de normalizacao de tipos do legado.

O legado e desorganizado: datas como int (unix) ou texto livre, numeros como
varchar, e NULLs em campos que deveriam ter valor. Todas as funcoes abaixo sao
tolerantes e NAO derrubam o batch: retornam None em vez de levantar, e o erro
por linha fica registrado em etl_erros pelo runner.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, ClassVar

logger = logging.getLogger(__name__)

INCREMENTAL_MARGIN = timedelta(hours=6)


class BaseMapper:
    source_table: ClassVar[str | None] = None          # tabela MySQL de origem
    source_columns: ClassVar[list[str]] = []           # colunas lidas do legado
    target_table: ClassVar[str] = ""                   # tabela de destino
    order_by: ClassVar[str | None] = None              # ordenacao estavel da leitura
    incremental_column: ClassVar[str | None] = None    # coluna 'last_modified' p/ diff
    has_tracking: ClassVar[bool] = True                # False p/ tabelas sem legacy_*
    conflict_columns: ClassVar[list[str]] = []         # cols de conflito p/ sem tracking
    upsert_conflict_columns: ClassVar[tuple[str, ...]] = ("legacy_table", "legacy_id")
    legacy_table: ClassVar[str | None] = None          # valor para coluna legacy_table (default: source_table)
    # colunas gravadas so no INSERT: o re-upsert nao sobrescreve o que o NEXUS mantem
    insert_only_columns: ClassVar[tuple[str, ...]] = ()
    # expressao SQL custom no DO UPDATE ({table} = linha atual; EXCLUDED = legado)
    update_expressions: ClassVar[dict[str, str]] = {}

    def __init__(self, registry=None) -> None:
        from ..registry import IdRegistry

        self.registry: IdRegistry = registry
        self.seen_emails: dict[str, int | None] = {}
        self.warnings: list[str] = []

    # --- utilitarios ---

    @staticmethod
    def as_int(value: Any) -> int | None:
        if value in (None, "", "0"):
            return 0 if value == "0" else None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def as_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def as_bool(value: Any) -> bool:
        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(value)

    @staticmethod
    def parse_ts(value: Any) -> datetime | None:
        """Aceita int (unix), datetime, date e strings nos formatos mais comuns."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value))
            except (ValueError, OSError):
                return None
        s = str(value).strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def parse_date(value: Any):
        ts = BaseMapper.parse_ts(value)
        return ts.date() if ts else None

    @staticmethod
    def str_clean(value: Any, max_len: int | None = None) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        if s in ("", "NULL", "null", "None", "0", "0000-00-00", "0000-00-00 00:00:00"):
            return None
        if max_len:
            s = s[:max_len]
        return s

    @staticmethod
    def only_digits(value: Any) -> str | None:
        """So os digitos (CPF/CNPJ com ou sem mascara -> forma canonica)."""
        if value is None:
            return None
        digits = re.sub(r"\D", "", str(value))
        return digits or None

    # --- contrato ---

    def map(self, row: dict) -> dict | None:
        """Transforma a linha do legado em dict de colunas do destino (ou None = ignorar).

        Nao incluir as colunas de rastreamento (legacy_table/legacy_id/synced_at):
        o runner as preenche automaticamente.
        """
        raise NotImplementedError

    def iter_source(self, source, last_run=None):
        """Iteracao padrao: stream da tabela de origem (com filtro incremental)."""
        where = None
        params: tuple = ()
        if last_run is not None and self.incremental_column:
            where, params = self.incremental_filter(last_run)
        extra = self.initial_where(last_run)
        if extra:
            where = f"({where}) AND ({extra})" if where else extra
        yield from source.stream(
            self.source_table, self.source_columns, where=where,
            params=params, order=self.order_by, offset=self.initial_offset(last_run),
        )

    def incremental_filter(self, last_run: Any) -> tuple[str, tuple]:
        """WHERE incremental tolerante ao tipo da coluna no legado.

        O legado guarda datas ora como unix int, ora como DATETIME/varchar. Um
        `int > '2026-01-01 ...'` no MySQL vira `int > 2026` e deixa passar
        tudo, por isso a comparacao e feita com o parametro do tipo certo.
        Aplica uma margem de seguranca (fuso do legado / relogios): reler um
        pouco a mais e inofensivo, pois o upsert e idempotente.
        """
        col = self.incremental_column
        ref = last_run
        if isinstance(ref, datetime):
            ref = ref - INCREMENTAL_MARGIN
            unix = int(ref.timestamp())
            text = ref.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        else:
            unix, text = ref, ref
        where = (
            f"(({col} REGEXP '^[0-9]+$' AND {col} > %s) "
            f"OR ({col} NOT REGEXP '^[0-9]+$' AND {col} > %s))"
        )
        return where, (unix, text)

    def current_legacy_id(self, row: dict):
        """id legado que vira a chave (legacy_table, legacy_id) do destino."""
        return row.get("id")

    def initial_where(self, last_run: Any = None) -> str | None:
        """Clausula WHERE fixa combinada a incremental (ex.: retomar carga). None = sem filtro."""
        return None

    def initial_offset(self, last_run: Any = None) -> int:
        """Quantidade de linhas a pular no inicio da leitura (OFFSET). 0 = sem skip."""
        return 0


    # --- helpers de estado ---

    def _dedup_email(self, email: str | None, current_lid: int | None = None) -> str | None:
        """e-mail unico no destino; duplicados do legado ficam NULL p/ auditoria."""
        if not email:
            return None
        key = email.lower().strip()
        if key in self.seen_emails:
            existing_lid = self.seen_emails[key]
            if current_lid is not None and existing_lid is not None and existing_lid == current_lid:
                return email
            self.warnings.append(f"email duplicado ignorado: {email}")
            return None
        self.seen_emails[key] = current_lid
        return email

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)