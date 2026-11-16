"""Validação de documentos brasileiros (CPF e CNPJ)."""
from __future__ import annotations

import re
from typing import Optional


def normalizar_documento(valor: Optional[str]) -> str:
    """Remove máscara: mantém só dígitos."""
    return re.sub(r"\D", "", valor or "")


def _cpf_valido(d: str) -> bool:
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(d[tamanho]):
            return False
    return True


def _cnpj_valido(d: str) -> bool:
    if len(d) != 14 or d == d[0] * 14:
        return False
    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_2 = [6] + pesos_1
    for pesos, pos in ((pesos_1, 12), (pesos_2, 13)):
        soma = sum(int(d[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(d[pos]):
            return False
    return True


def documento_valido(valor: Optional[str]) -> bool:
    """True para CPF (11 dígitos) ou CNPJ (14 dígitos) com dígitos verificadores corretos."""
    d = normalizar_documento(valor)
    return _cpf_valido(d) if len(d) == 11 else _cnpj_valido(d) if len(d) == 14 else False
