"""Códigos legíveis gerados pelo sistema (número da licença do aluno)."""
from __future__ import annotations

import re
import secrets
from typing import Optional

# Sem caracteres ambíguos (0/O, 1/I/L): fácil de ditar e digitar por alunos leigos.
ALFABETO_LICENCA = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_RE_LICENCA = re.compile(r"^NX([2-9A-HJKMNP-Z]{4})([2-9A-HJKMNP-Z]{4})$")


def gerar_numero_licenca() -> str:
    """NX-XXXX-XXXX com 8 caracteres aleatórios fortes (~8,5×10^11 combinações)."""
    corpo = "".join(secrets.choice(ALFABETO_LICENCA) for _ in range(8))
    return f"NX-{corpo[:4]}-{corpo[4:]}"


def normalizar_numero_licenca(texto: Optional[str]) -> Optional[str]:
    """Aceita minúsculas, espaços e sem hífens ("nx 7k4p 92qd"); devolve None se inválido."""
    bruto = re.sub(r"[^0-9A-Za-z]", "", texto or "").upper()
    if not bruto.startswith("NX"):
        bruto = "NX" + bruto
    m = _RE_LICENCA.match(bruto)
    return f"NX-{m.group(1)}-{m.group(2)}" if m else None


def mascarar_numero_licenca(numero: Optional[str]) -> str:
    """Para logs: NX-7K4P-****."""
    return f"{numero[:8]}****" if numero and len(numero) >= 8 else "****"
