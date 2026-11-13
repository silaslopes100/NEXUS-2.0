"""Orders / logistica de livros fisicos. Fonte legado: `p_livros`.

- Cada linha de p_livros vira um pedido (tabela unica `pedidos`, tipo='livro')
  + 1 item (`pedidos_itens`). Migration 017 unificou pedidos_livros/pedidos_licenca.
- `status` int do legado nao tem dicionario; PEDIDO_STATUS e ajustavel.
- O Polo do pedido vem do polo do usuario logado no momento (usuario -> polo).
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

# 0 = pendente de envio (padrao). Ajuste conforme o dicionario real da operacao.
# Valores seguem ck_pedidos_status (migration 016).
PEDIDO_STATUS = {0: "pago_aguardando_envio", 1: "enviado", 2: "entregue"}

P_LIVROS_COLUMNS = [
    "id", "user_id", "pacote_id", "date_added", "status", "pagamento",
    "modalidade", "valor", "date_envio", "course_id", "quantidade",
]


class PedidoLivroMapper(BaseMapper):
    source_table: ClassVar[str] = "p_livros"
    source_columns: ClassVar[list[str]] = P_LIVROS_COLUMNS
    target_table: ClassVar[str] = "pedidos"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        polo_id = self.registry.usuario_polo(row.get("user_id")) if self.registry else None
        status_int = self.as_int(row.get("status"))
        status = PEDIDO_STATUS.get(status_int, "pago_aguardando_envio")
        valor = self.as_float(row.get("valor")) or 0.0
        return {
            "tipo": "livro",
            "polo_id": polo_id,
            "escola_id": None,
            "status": status,
            "valor_bruto": valor,
            "valor_total": valor,
            "criado_em": self.parse_ts(row.get("date_added")) or self.parse_ts(row.get("date_envio")),
            "enviado_em": self.parse_ts(row.get("date_envio")),
        }


class PedidoLivroItemMapper(BaseMapper):
    source_table: ClassVar[str] = "p_livros"
    source_columns: ClassVar[list[str]] = P_LIVROS_COLUMNS
    target_table: ClassVar[str] = "pedidos_itens"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        pedido_id = self.registry.resolve("pedidos", "p_livros", row.get("id")) if self.registry else None
        if not pedido_id:
            return None
        quantidade = max(self.as_int(row.get("quantidade")) or 1, 1)
        valor = self.as_float(row.get("valor")) or 0.0
        return {
            "pedido_id": pedido_id,
            "disciplina_id": None,
            "descricao": "Livro (legado)",
            "quantidade": quantidade,
            "valor_unitario": round(valor / quantidade, 2),
            "valor_total": valor,
        }