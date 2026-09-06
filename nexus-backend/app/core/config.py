"""Configurações da aplicação NEXUS 2.0."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env do nexus-backend ou do diretório atual
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=False)
load_dotenv(Path.cwd() / ".env", override=False)


class Settings:
    # --- Segurança e JWT ---
    SECRET_KEY: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "nexus-2.0-secret-key-change-in-production-2026"))
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "60"))

    # --- Bloqueio de Login por Tentativas ---
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_ATTEMPTS_WINDOW_MINUTES: int = int(os.getenv("LOGIN_ATTEMPTS_WINDOW_MINUTES", "15"))

    # --- Banco de dados ---
    PG_DSN: str = os.getenv("PG_DSN", os.getenv("DATABASE_URL", ""))

    # --- E-mail / SMTP ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@nexus2.com.br")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "NEXUS 2.0")

    # --- Ambiente ---
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
