"""Regras puras dos pedidos (sem I/O): máquina de status e cálculo de totais."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, FrozenSet, Iterable, Tuple

from fastapi import HTTPException, status

# Transições permitidas. Estados finais não têm saída.
TRANSICOES: Dict[str, FrozenSet[str]] = {
    "aguardando_pagamento": frozenset({"pago_aguardando_envio", "concluido", "cancelado"}),
    "pago_aguardando_envio": frozenset({"enviado", "cancelado"}),
    "enviado": frozenset({"entregue"}),
    "entregue": frozenset(),
    "concluido": frozenset(),
    "cancelado": frozenset(),
}

# Timestamp preenchido ao entrar em cada status.
TIMESTAMP_DO_STATUS: Dict[str, str] = {
    "pago_aguardando_envio": "pago_em",
    "concluido": "pago_em",
    "enviado": "enviado_em",
    "entregue": "entregue_em",
    "cancelado": "cancelado_em",
}

CENTAVOS = Decimal("0.01")


def transicao_permitida(de: str, para: str) -> bool:
    return para in TRANSICOES.get(de, frozenset())


def validar_transicao(de: str, para: str) -> None:
    """Levanta 409 se a transição `de -> para` não for permitida."""
    if not transicao_permitida(de, para):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transição de status inválida: '{de}' → '{para}'",
        )


# Status que não fazem sentido para cada tipo de pedido.
STATUS_INVALIDOS_POR_TIPO: Dict[str, FrozenSet[str]] = {
    "livro": frozenset({"concluido"}),  # livro termina em 'entregue'
    "licenca": frozenset({"pago_aguardando_envio", "enviado", "entregue"}),  # sem logística
}


def validar_transicao_para_tipo(tipo: str, de: str, para: str) -> None:
    """Valida a transição e se o destino é coerente com o tipo do pedido (409 se não)."""
    validar_transicao(de, para)
    if para in STATUS_INVALIDOS_POR_TIPO.get(tipo, frozenset()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Status '{para}' não se aplica a pedidos do tipo '{tipo}'",
        )


def status_pos_pagamento(tipo: str) -> str:
    """Status do pedido quando o pagamento é confirmado.

    Livro físico segue para a fila da logística; licença é entregue na hora.
    """
    return "pago_aguardando_envio" if tipo == "livro" else "concluido"


def _dec(valor) -> Decimal:
    return Decimal(str(valor or 0))


def arredondar(valor) -> Decimal:
    return _dec(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_totais(
    itens: Iterable[Tuple[object, int]], desconto: object = 0
) -> Tuple[Decimal, Decimal, Decimal]:
    """Recebe pares (valor_unitario, quantidade) e o desconto absoluto.

    Retorna (bruto, desconto_aplicado, total). O desconto nunca deixa o total negativo.
    """
    bruto = sum((arredondar(preco) * int(qtd) for preco, qtd in itens), Decimal("0"))
    bruto = arredondar(bruto)
    desc = min(max(arredondar(desconto), Decimal("0")), bruto)
    return bruto, desc, arredondar(bruto - desc)
