"""Gerenciamento de conexões com o banco de dados PostgreSQL."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: ThreadedConnectionPool | None = None


def get_connection_pool() -> ThreadedConnectionPool | None:
    """Retorna o pool de conexões do PostgreSQL se PG_DSN estiver configurado."""
    global _pool
    if _pool is None and settings.PG_DSN:
        try:
            _pool = ThreadedConnectionPool(minconn=1, maxconn=10, dsn=settings.PG_DSN)
        except Exception as exc:
            logger.warning("Não foi possível inicializar pool de conexões com PostgreSQL: %s", exc)
    return _pool


@contextmanager
def get_db_cursor() -> Generator[Any, None, None]:
    """Context manager que obtém um cursor do PostgreSQL com retorno em dicionário."""
    pool = get_connection_pool()
    if pool is None:
        raise RuntimeError("Pool de conexões não inicializado. Verifique PG_DSN.")

    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_connection_pool() -> None:
    """Encerra o pool de conexões."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
