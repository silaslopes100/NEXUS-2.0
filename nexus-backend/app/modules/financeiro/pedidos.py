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


# "kit" = Disciplina (1 livro físico + 1 licença por unidade). É o produto vendido a partir da
# migração 021; "livro" e "licenca" ficam para o histórico.
TIPOS_COM_ENVIO: FrozenSet[str] = frozenset({"livro", "kit"})        # passam pela logística
TIPOS_COM_LICENCA: FrozenSet[str] = frozenset({"licenca", "kit"})    # creditam licenças ao pagar

# Status que não fazem sentido para cada tipo de pedido.
STATUS_INVALIDOS_POR_TIPO: Dict[str, FrozenSet[str]] = {
    "livro": frozenset({"concluido"}),  # livro termina em 'entregue'
    "kit": frozenset({"concluido"}),    # kit também termina na entrega do livro
    "licenca": frozenset({"pago_aguardando_envio", "enviado", "entregue"}),  # sem logística
}


def tem_envio(tipo: str) -> bool:
    return tipo in TIPOS_COM_ENVIO


def credita_licenca(tipo: str) -> bool:
    return tipo in TIPOS_COM_LICENCA


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

    Livro físico (e kit) segue para a fila da logística; licença avulsa é entregue na hora.
    """
    return "pago_aguardando_envio" if tem_envio(tipo) else "concluido"


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
