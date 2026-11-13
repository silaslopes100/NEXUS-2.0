"""Criptografia simétrica de segredos (credenciais de gateways de pagamento).

Usa Fernet (AES-128-CBC + HMAC-SHA256) com a chave `PAYMENT_SECRETS_KEY`.
A chave só é exigida no uso, para não impedir o boot da API sem ela.
"""
from __future__ import annotations

from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet(key: Optional[str] = None) -> Fernet:
    chave = key if key is not None else settings.PAYMENT_SECRETS_KEY
    if not chave:
        raise RuntimeError("PAYMENT_SECRETS_KEY não configurada")
    try:
        return Fernet(chave.encode() if isinstance(chave, str) else chave)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PAYMENT_SECRETS_KEY inválida (esperada chave Fernet base64)") from exc


def encrypt_secret(texto: str, key: Optional[str] = None) -> str:
    """Criptografa `texto` e devolve o token Fernet (str)."""
    return _fernet(key).encrypt(texto.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str, key: Optional[str] = None) -> str:
    """Descriptografa um token gerado por `encrypt_secret`."""
    try:
        return _fernet(key).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Não foi possível descriptografar o segredo (chave diferente?)") from exc


def mask_secret(texto: Optional[str], visiveis: int = 4) -> str:
    """Mascara um segredo para exibição: '••••abcd'."""
    if not texto:
        return ""
    return "••••" + texto[-visiveis:] if len(texto) > visiveis else "••••"
