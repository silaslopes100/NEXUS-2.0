"""Configuracao central do ETL. Le `.env` na raiz do nexus-backend ou no cwd."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Precedencia: .env na raiz do nexus-backend (parente daqui) -> .env no cwd
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # nexus-backend/
load_dotenv(_PROJECT_ROOT / ".env", override=False)
load_dotenv(Path.cwd() / ".env", override=False)


class Config:
    """Credenciais e parametros do batch. Nunca hardcode valores reais aqui."""

    # --- MySQL legado (somente leitura) ---
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "mysql247.umbler.com")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "41890"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "adp_etadem")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "teo-eadetademp")

    # --- PostgreSQL destino (NeonDB) ---
    PG_DSN: str = os.getenv("PG_DSN", "")

    # --- Comportamento ---
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "2000"))
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Sao_Paulo")
    ONLY_MAPPER: str | None = os.getenv("ETL_ONLY_MAPPER") or None

    # Sem credencial de destino informada, o batch para com mensagem clara.
    def require_pg(self) -> str:
        if not self.PG_DSN:
            raise SystemExit(
                "PG_DSN nao configurado. Preencha .env (veja .env.example) "
                "com a connection string do NeonDB."
            )
        return self.PG_DSN

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


config = Config()