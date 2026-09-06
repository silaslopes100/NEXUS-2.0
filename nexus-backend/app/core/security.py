"""Funções criptográficas, hashing de senhas e geração/validação de JWT."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import bcrypt
import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

# Argon2id hasher padrão
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Gera o hash da senha em Argon2id."""
    return _hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
    algorithm: str = "argon2id",
) -> Tuple[bool, bool]:
    """Verifica a senha contra o hash armazenado.

    Suporta:
    1. 'argon2id': Argon2id nativo do NEXUS 2.0.
    2. 'legacy_bcrypt': Hash do sistema legado via bcrypt ($2a$, $2b$, $2y$).

    Retorna:
        (valido: bool, precisa_rehash: bool)
    """
    if not hashed_password or not plain_password:
        return False, False

    # Identifica se é hash legado (por algoritmo ou formato do hash)
    is_legacy = algorithm == "legacy_bcrypt" or hashed_password.startswith(
        ("$2a$", "$2b$", "$2y$", "$2x$")
    )

    if is_legacy:
        try:
            pwd_bytes = plain_password.encode("utf-8")
            hash_bytes = hashed_password.encode("utf-8")
            if bcrypt.checkpw(pwd_bytes, hash_bytes):
                # Senha legado válida -> sinaliza necessidade de lazy rehash para Argon2id
                return True, True
            return False, False
        except Exception:
            return False, False

    # Validação padrão Argon2id
    try:
        if _hasher.verify(hashed_password, plain_password):
            needs_rehash = _hasher.check_needs_rehash(hashed_password)
            return True, needs_rehash
        return False, False
    except (VerifyMismatchError, InvalidHashError):
        return False, False
    except Exception:
        return False, False


def hash_token(token: str) -> str:
    """Gera hash SHA-256 do token para armazenamento seguro no banco."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(nbytes: int = 48) -> str:
    """Gera um token criptograficamente seguro em base64 URL-safe."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Cria um token de acesso JWT assinado."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "iat": now,
        "exp": expire,
        "tipo": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica e valida um token JWT. Retorna o payload se válido ou None."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("tipo") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None
