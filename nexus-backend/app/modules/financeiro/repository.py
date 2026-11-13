"""Persistência de produtos, pedidos (tabela única) e pagamentos.

Tabelas: produtos, pedidos, pedidos_itens, pedidos_status_historico, envios,
pagamentos (migrations 016/017).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

from fastapi import HTTPException, status
from psycopg2.errors import UniqueViolation
from psycopg2.extras import Json

from app.core.database import get_db_cursor
from app.modules.financeiro.schemas import FiltrosPeriodo


@dataclass(frozen=True)
class Escopo:
    """Restrição de visibilidade (None = sem restrição)."""

    polo_id: Optional[str] = None
    escola_id: Optional[str] = None


ESCOPO_GLOBAL = Escopo()

COLUNAS_PRODUTO = (
    "tipo", "sku", "nome", "descricao", "disciplina_id", "preco", "peso_g",
    "altura_cm", "largura_cm", "comprimento_cm", "ativo",
)
COLUNAS_PEDIDO = (
    "tipo", "polo_id", "escola_id", "solicitante_id", "status", "valor_bruto",
    "desconto", "valor_total", "cupom_id", "fornecedor",
    "entrega_nome", "entrega_cep", "entrega_logradouro", "entrega_numero",
    "entrega_complemento", "entrega_bairro", "entrega_cidade", "entrega_uf",
    "entrega_telefone", "observacao", "pago_em", "cancelado_em",
    "motivo_cancelamento", "enviado_em", "entregue_em",
)
# Campos que alterar_status_pedido pode atualizar junto com o status.
CAMPOS_STATUS_EXTRA = frozenset(
    {"pago_em", "cancelado_em", "motivo_cancelamento", "enviado_em", "entregue_em"}
)
CAMPOS_GATEWAY_CONFIG = ("credenciais_cripto", "webhook_token_cripto", "ativo", "padrao", "atualizado_por")
GATEWAYS_REAIS = ("asaas", "pagbank", "mercadopago")
COLUNAS_PAGAMENTO = (
    "pedido_id", "polo_id", "escola_id", "aluno_id", "gateway", "ambiente",
    "gateway_customer_id", "gateway_payment_id", "asaas_customer_id",
    "asaas_payment_id", "billing_type", "valor", "valor_liquido", "status",
    "parcelas", "boleto_url", "invoice_url", "linha_digitavel", "nosso_numero",
    "pix_copia_cola", "pix_qrcode_base64", "vencimento_em", "pago_em",
    "cancelado_em", "descricao",
)


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normaliza tipos do driver: UUID -> str, Decimal -> float."""
    if row is None:
        return None
    out: Dict[str, Any] = {}
    for k, v in dict(row).items():
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


def _filtrar_colunas(dados: Dict[str, Any], permitidas: Iterable[str]) -> Dict[str, Any]:
    permitidas = set(permitidas)
    return {k: v for k, v in dados.items() if k in permitidas}


def where_periodo(
    filtros: FiltrosPeriodo,
    escopo: Escopo,
    *,
    alias: str,
    coluna_data: str,
    coluna_status: Optional[str] = None,
    coluna_tipo: Optional[str] = None,
    coluna_pedido: Optional[str] = None,
) -> Tuple[List[str], List[Any]]:
    """Monta condições SQL + parâmetros para os filtros de período/unidade.

    `alias` é o alias da tabela que tem polo_id/escola_id; `coluna_data` já
    deve vir qualificada (ex.: "p.criado_em" ou "COALESCE(p.pago_em, p.criado_em)").
    Reutilizado por listas, relatórios e exportações.
    """
    conds: List[str] = []
    params: List[Any] = []
    if filtros.data_inicio:
        conds.append(f"{coluna_data} >= %s")
        params.append(filtros.data_inicio)
    if filtros.data_fim:
        conds.append(f"{coluna_data} < (%s::date + 1)")
        params.append(filtros.data_fim)
    if filtros.ano:
        conds.append(f"EXTRACT(YEAR FROM {coluna_data}) = %s")
        params.append(filtros.ano)
    if filtros.mes:
        conds.append(f"EXTRACT(MONTH FROM {coluna_data}) = %s")
        params.append(filtros.mes)
    if filtros.semestre:
        conds.append(
            f"EXTRACT(MONTH FROM {coluna_data}) BETWEEN %s AND %s"
        )
        params.extend([1, 6] if filtros.semestre == 1 else [7, 12])
    polo_id = escopo.polo_id or filtros.polo_id
    if escopo.polo_id and filtros.polo_id and filtros.polo_id != escopo.polo_id:
        conds.append("FALSE")  # pediu um polo fora do próprio escopo
    if polo_id:
        conds.append(f"{alias}.polo_id = %s")
        params.append(polo_id)
    escola_id = escopo.escola_id or filtros.escola_id
    if escopo.escola_id and filtros.escola_id and filtros.escola_id != escopo.escola_id:
        conds.append("FALSE")
    if escola_id:
        conds.append(f"{alias}.escola_id = %s")
        params.append(escola_id)
    if filtros.status and coluna_status:
        conds.append(f"{coluna_status} = %s")
        params.append(filtros.status)
    if filtros.tipo and coluna_tipo:
        conds.append(f"{coluna_tipo} = %s")
        params.append(filtros.tipo)
    if filtros.pedido_id and coluna_pedido:
        conds.append(f"{coluna_pedido} = %s")
        params.append(filtros.pedido_id)
    return conds, params


def _where(conds: Sequence[str]) -> str:
    return ("WHERE " + " AND ".join(conds)) if conds else ""


def _conflito_status(pedido_id: str, de: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Pedido {pedido_id} não está mais em '{de}' (alterado por outra operação)",
    )


class FinanceiroRepositoryInterface(Protocol):
    # produtos
    def list_produtos(self, tipo: Optional[str] = None, ativo: Optional[bool] = None) -> List[Dict[str, Any]]: ...
    def get_produto(self, produto_id: str) -> Optional[Dict[str, Any]]: ...
    def get_produtos_por_ids(self, ids: Sequence[str]) -> Dict[str, Dict[str, Any]]: ...
    def create_produto(self, dados: Dict[str, Any]) -> Dict[str, Any]: ...
    def update_produto(self, produto_id: str, campos: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    # pedidos
    def create_pedido(self, dados: Dict[str, Any], itens: List[Dict[str, Any]], usuario_id: Optional[str]) -> str: ...
    def get_pedido(self, pedido_id: str) -> Optional[Dict[str, Any]]: ...
    def list_pedidos(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[int, List[Dict[str, Any]]]: ...
    def alterar_status_pedido(
        self,
        pedido_id: str,
        de: str,
        para: str,
        usuario_id: Optional[str],
        origem: str,
        observacao: Optional[str] = None,
        campos: Optional[Dict[str, Any]] = None,
    ) -> None: ...
    # pagamentos
    def create_pagamento(self, dados: Dict[str, Any]) -> str: ...
    def get_pagamento(self, pagamento_id: str) -> Optional[Dict[str, Any]]: ...
    def get_pagamento_por_gateway_id(self, gateway: str, payment_id: str) -> Optional[Dict[str, Any]]: ...
    def list_pagamentos(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[int, List[Dict[str, Any]]]: ...
    def update_pagamento(self, pagamento_id: str, campos: Dict[str, Any]) -> None: ...
    # apoio
    def get_endereco_polo(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def get_dados_cobranca_polo(self, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def get_regra_pagamento(self, tipo: str, polo_id: Optional[str]) -> Optional[Dict[str, Any]]: ...
    # gateways
    def get_gateway_config(self, gateway: str, ambiente: str) -> Optional[Dict[str, Any]]: ...
    def list_gateway_configs(self) -> List[Dict[str, Any]]: ...
    def salvar_gateway_config(self, gateway: str, ambiente: str, campos: Dict[str, Any]) -> Dict[str, Any]: ...
    def marcar_teste_gateway(self, gateway: str, ambiente: str, ok: bool) -> None: ...
    def get_cliente_gateway(self, gateway: str, ambiente: str, polo_id: str) -> Optional[Dict[str, Any]]: ...
    def salvar_cliente_gateway(self, gateway: str, ambiente: str, polo_id: str, customer_id: str, documento: str) -> None: ...
    def get_pagamento_pendente_do_pedido(self, pedido_id: str) -> Optional[Dict[str, Any]]: ...
    def list_pagamentos_para_reconciliar(self, limite: int = 50) -> List[Dict[str, Any]]: ...
    # webhooks
    def registrar_webhook(self, gateway: str, ambiente: str, evento_id: str, tipo_evento: Optional[str],
                          payment_id: Optional[str], payload: Any) -> Optional[str]: ...
    def finalizar_webhook(self, webhook_id: str, status: str, erro: Optional[str] = None) -> None: ...
    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]: ...
    def list_webhooks(self, gateway: Optional[str], status: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]: ...
    def list_webhooks_com_erro(self, max_tentativas: int = 5, limite: int = 50) -> List[Dict[str, Any]]: ...


# =============================================================================
# PostgreSQL
# =============================================================================

_SELECT_PEDIDO = """
    SELECT p.*, po.nome AS polo_nome, e.nome AS escola_nome
      FROM pedidos p
      LEFT JOIN polos po ON po.id = p.polo_id
      LEFT JOIN escolas e ON e.id = p.escola_id
"""

_SELECT_PAGAMENTO = """
    SELECT pg.*, p.numero AS pedido_numero, po.nome AS polo_nome
      FROM pagamentos pg
      LEFT JOIN pedidos p ON p.id = pg.pedido_id
      LEFT JOIN polos po ON po.id = pg.polo_id
"""


class PostgresFinanceiroRepository:
    # ---------------- produtos ----------------

    def list_produtos(self, tipo: Optional[str] = None, ativo: Optional[bool] = None) -> List[Dict[str, Any]]:
        conds, params = [], []
        if tipo:
            conds.append("tipo = %s")
            params.append(tipo)
        if ativo is not None:
            conds.append("ativo = %s")
            params.append(ativo)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT * FROM produtos {_where(conds)} ORDER BY tipo, nome", tuple(params))
            return [_limpar(r) for r in cur.fetchall()]

    def get_produto(self, produto_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM produtos WHERE id = %s", (str(produto_id),))
            return _limpar(cur.fetchone())

    def get_produtos_por_ids(self, ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        if not ids:
            return {}
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM produtos WHERE id::text = ANY(%s)", (list({str(i) for i in ids}),))
            return {r["id"]: r for r in (_limpar(x) for x in cur.fetchall())}

    def create_produto(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        campos = _filtrar_colunas(dados, COLUNAS_PRODUTO)
        cols = ", ".join(campos)
        marks = ", ".join(["%s"] * len(campos))
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    f"INSERT INTO produtos ({cols}) VALUES ({marks}) RETURNING *",
                    tuple(campos.values()),
                )
                return _limpar(cur.fetchone())
        except UniqueViolation as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU já cadastrado") from exc

    def update_produto(self, produto_id: str, campos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        campos = _filtrar_colunas(campos, set(COLUNAS_PRODUTO) - {"tipo", "sku"})
        if not campos:
            return self.get_produto(produto_id)
        sets = ", ".join(f"{k} = %s" for k in campos)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE produtos SET {sets}, atualizado_em = now() WHERE id = %s RETURNING *",
                (*campos.values(), str(produto_id)),
            )
            return _limpar(cur.fetchone())

    # ---------------- pedidos ----------------

    def create_pedido(self, dados: Dict[str, Any], itens: List[Dict[str, Any]], usuario_id: Optional[str]) -> str:
        campos = _filtrar_colunas(dados, COLUNAS_PEDIDO)
        cols = ", ".join(campos)
        marks = ", ".join(["%s"] * len(campos))
        with get_db_cursor() as cur:
            cur.execute(
                f"INSERT INTO pedidos ({cols}) VALUES ({marks}) RETURNING id",
                tuple(campos.values()),
            )
            pedido_id = str(cur.fetchone()["id"])
            for item in itens:
                cur.execute(
                    """
                    INSERT INTO pedidos_itens (pedido_id, produto_id, disciplina_id, descricao,
                                               quantidade, valor_unitario, valor_total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        pedido_id, item.get("produto_id"), item.get("disciplina_id"),
                        item.get("descricao"), item["quantidade"], item["valor_unitario"],
                        item["valor_total"],
                    ),
                )
            cur.execute(
                """
                INSERT INTO pedidos_status_historico (pedido_id, status_de, status_para, usuario_id, origem, observacao)
                VALUES (%s, NULL, %s, %s, 'usuario', 'Pedido criado')
                """,
                (pedido_id, campos.get("status", "aguardando_pagamento"), usuario_id),
            )
        return pedido_id

    def _carregar_itens(self, cur, pedido_ids: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
        if not pedido_ids:
            return {}
        cur.execute(
            "SELECT * FROM pedidos_itens WHERE pedido_id::text = ANY(%s) ORDER BY criado_em, id",
            (list(pedido_ids),),
        )
        out: Dict[str, List[Dict[str, Any]]] = {}
        for r in cur.fetchall():
            item = _limpar(r)
            out.setdefault(item["pedido_id"], []).append(item)
        return out

    def get_pedido(self, pedido_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(_SELECT_PEDIDO + " WHERE p.id = %s", (str(pedido_id),))
            pedido = _limpar(cur.fetchone())
            if not pedido:
                return None
            pedido["itens"] = self._carregar_itens(cur, [pedido["id"]]).get(pedido["id"], [])
            cur.execute(
                "SELECT * FROM pedidos_status_historico WHERE pedido_id = %s ORDER BY criado_em, id",
                (pedido["id"],),
            )
            pedido["historico"] = [_limpar(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT * FROM envios WHERE pedido_id = %s ORDER BY criado_em DESC",
                (pedido["id"],),
            )
            pedido["envios"] = [_limpar(r) for r in cur.fetchall()]
            return pedido

    def list_pedidos(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[int, List[Dict[str, Any]]]:
        conds, params = where_periodo(
            filtros, escopo, alias="p", coluna_data="p.criado_em",
            coluna_status="p.status", coluna_tipo="p.tipo",
        )
        where = _where(conds)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM pedidos p {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"{_SELECT_PEDIDO} {where} ORDER BY p.criado_em DESC, p.id LIMIT %s OFFSET %s",
                tuple(params + [filtros.limit, filtros.offset]),
            )
            pedidos = [_limpar(r) for r in cur.fetchall()]
            itens = self._carregar_itens(cur, [p["id"] for p in pedidos])
            for p in pedidos:
                p["itens"] = itens.get(p["id"], [])
            return total, pedidos

    def alterar_status_pedido(
        self,
        pedido_id: str,
        de: str,
        para: str,
        usuario_id: Optional[str],
        origem: str,
        observacao: Optional[str] = None,
        campos: Optional[Dict[str, Any]] = None,
    ) -> None:
        extras = _filtrar_colunas(campos or {}, CAMPOS_STATUS_EXTRA)
        sets = "".join(f", {k} = %s" for k in extras)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE pedidos SET status = %s{sets}, atualizado_em = now() "
                "WHERE id = %s AND status = %s",
                (para, *extras.values(), str(pedido_id), de),
            )
            if cur.rowcount == 0:
                raise _conflito_status(pedido_id, de)
            cur.execute(
                """
                INSERT INTO pedidos_status_historico (pedido_id, status_de, status_para, usuario_id, origem, observacao)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (str(pedido_id), de, para, usuario_id, origem, observacao),
            )

    # ---------------- pagamentos ----------------

    def create_pagamento(self, dados: Dict[str, Any]) -> str:
        campos = _filtrar_colunas(dados, COLUNAS_PAGAMENTO)
        cols = ", ".join(campos)
        marks = ", ".join(["%s"] * len(campos))
        with get_db_cursor() as cur:
            cur.execute(
                f"INSERT INTO pagamentos ({cols}) VALUES ({marks}) RETURNING id",
                tuple(campos.values()),
            )
            return str(cur.fetchone()["id"])

    def get_pagamento(self, pagamento_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(_SELECT_PAGAMENTO + " WHERE pg.id = %s", (str(pagamento_id),))
            return _limpar(cur.fetchone())

    def get_pagamento_por_gateway_id(self, gateway: str, payment_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                _SELECT_PAGAMENTO + " WHERE pg.gateway = %s AND pg.gateway_payment_id = %s LIMIT 1",
                (gateway, payment_id),
            )
            return _limpar(cur.fetchone())

    def list_pagamentos(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[int, List[Dict[str, Any]]]:
        conds, params = where_periodo(
            filtros, escopo, alias="pg", coluna_data="pg.criado_em",
            coluna_status="pg.status", coluna_tipo="p.tipo", coluna_pedido="pg.pedido_id",
        )
        where = _where(conds)
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS total FROM pagamentos pg LEFT JOIN pedidos p ON p.id = pg.pedido_id {where}",
                tuple(params),
            )
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"{_SELECT_PAGAMENTO} {where} ORDER BY pg.criado_em DESC, pg.id LIMIT %s OFFSET %s",
                tuple(params + [filtros.limit, filtros.offset]),
            )
            return total, [_limpar(r) for r in cur.fetchall()]

    def update_pagamento(self, pagamento_id: str, campos: Dict[str, Any]) -> None:
        campos = _filtrar_colunas(campos, COLUNAS_PAGAMENTO)
        if not campos:
            return
        sets = ", ".join(f"{k} = %s" for k in campos)
        with get_db_cursor() as cur:
            cur.execute(
                f"UPDATE pagamentos SET {sets}, atualizado_em = now() WHERE id = %s",
                (*campos.values(), str(pagamento_id)),
            )

    # ---------------- apoio ----------------

    def get_endereco_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT nome, cep, logradouro, numero, complemento, bairro, cidade, uf FROM polos WHERE id = %s",
                (str(polo_id),),
            )
            return _limpar(cur.fetchone())

    def get_dados_cobranca_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, nome, cep, logradouro, numero, complemento, bairro, cidade, uf,
                       documento_fiscal, razao_social, email_financeiro, telefone_financeiro
                  FROM polos WHERE id = %s
                """,
                (str(polo_id),),
            )
            return _limpar(cur.fetchone())

    def get_regra_pagamento(self, tipo: str, polo_id: Optional[str]) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM regras_pagamento
                 WHERE ativo
                   AND (aplica_tipo_pedido IS NULL OR aplica_tipo_pedido = %s)
                   AND (aplica_polo_id IS NULL OR aplica_polo_id::text = %s)
                 ORDER BY (aplica_polo_id IS NULL), (aplica_tipo_pedido IS NULL), prioridade
                 LIMIT 1
                """,
                (tipo, str(polo_id or "")),
            )
            return _limpar(cur.fetchone())

    # ---------------- gateways ----------------

    def get_gateway_config(self, gateway: str, ambiente: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM gateways_config WHERE gateway = %s AND ambiente = %s", (gateway, ambiente))
            return _limpar(cur.fetchone())

    def list_gateway_configs(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM gateways_config ORDER BY gateway, ambiente")
            return [_limpar(r) for r in cur.fetchall()]

    def salvar_gateway_config(self, gateway: str, ambiente: str, campos: Dict[str, Any]) -> Dict[str, Any]:
        campos = _filtrar_colunas(campos, CAMPOS_GATEWAY_CONFIG)
        with get_db_cursor() as cur:
            if campos.get("padrao"):
                cur.execute(
                    "UPDATE gateways_config SET padrao = false, atualizado_em = now() "
                    "WHERE ambiente = %s AND gateway <> %s AND padrao",
                    (ambiente, gateway),
                )
            cols = ["gateway", "ambiente", *campos.keys()]
            sets = ", ".join(f"{k} = EXCLUDED.{k}" for k in campos) or "gateway = EXCLUDED.gateway"
            cur.execute(
                f"""
                INSERT INTO gateways_config ({", ".join(cols)}) VALUES ({", ".join(["%s"] * len(cols))})
                ON CONFLICT (gateway, ambiente) DO UPDATE SET {sets}, atualizado_em = now()
                RETURNING *
                """,
                (gateway, ambiente, *campos.values()),
            )
            return _limpar(cur.fetchone())

    def marcar_teste_gateway(self, gateway: str, ambiente: str, ok: bool) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE gateways_config SET ultimo_teste_em = now(), ultimo_teste_ok = %s WHERE gateway = %s AND ambiente = %s",
                (ok, gateway, ambiente),
            )

    def get_cliente_gateway(self, gateway: str, ambiente: str, polo_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM gateway_clientes WHERE gateway = %s AND ambiente = %s AND polo_id = %s",
                (gateway, ambiente, str(polo_id)),
            )
            return _limpar(cur.fetchone())

    def salvar_cliente_gateway(self, gateway: str, ambiente: str, polo_id: str, customer_id: str, documento: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO gateway_clientes (gateway, ambiente, polo_id, customer_id, documento_fiscal)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (gateway, ambiente, polo_id) DO UPDATE
                   SET customer_id = EXCLUDED.customer_id, documento_fiscal = EXCLUDED.documento_fiscal,
                       atualizado_em = now()
                """,
                (gateway, ambiente, str(polo_id), customer_id, documento),
            )

    def get_pagamento_pendente_do_pedido(self, pedido_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                _SELECT_PAGAMENTO + " WHERE pg.pedido_id = %s AND pg.status = 'pendente' "
                "ORDER BY pg.criado_em DESC LIMIT 1",
                (str(pedido_id),),
            )
            return _limpar(cur.fetchone())

    def list_pagamentos_para_reconciliar(self, limite: int = 50) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                _SELECT_PAGAMENTO
                + """
                 WHERE pg.status IN ('pendente', 'vencido')
                   AND pg.gateway = ANY(%s) AND pg.ambiente IS NOT NULL
                   AND pg.gateway_payment_id IS NOT NULL
                   AND pg.criado_em < now() - interval '30 minutes'
                 ORDER BY pg.atualizado_em NULLS FIRST, pg.criado_em
                 LIMIT %s
                """,
                (list(GATEWAYS_REAIS), limite),
            )
            return [_limpar(r) for r in cur.fetchall()]

    # ---------------- webhooks ----------------

    def registrar_webhook(self, gateway: str, ambiente: str, evento_id: str, tipo_evento: Optional[str],
                          payment_id: Optional[str], payload: Any) -> Optional[str]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO webhook_eventos (gateway, ambiente, evento_id, tipo_evento, gateway_payment_id, payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (gateway, evento_id) DO NOTHING
                RETURNING id
                """,
                (gateway, ambiente, evento_id[:128], (tipo_evento or "")[:64] or None,
                 (payment_id or "")[:128] or None, Json(payload)),
            )
            row = cur.fetchone()
            return str(row["id"]) if row else None

    def finalizar_webhook(self, webhook_id: str, status: str, erro: Optional[str] = None) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """
                UPDATE webhook_eventos
                   SET status = %s, erro = %s, tentativas = tentativas + 1, processado_em = now()
                 WHERE id = %s
                """,
                (status, (erro or None) and erro[:2000], str(webhook_id)),
            )

    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM webhook_eventos WHERE id = %s", (str(webhook_id),))
            return _limpar(cur.fetchone())

    def list_webhooks(self, gateway: Optional[str], status: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        conds, params = [], []
        if gateway:
            conds.append("gateway = %s")
            params.append(gateway)
        if status:
            conds.append("status = %s")
            params.append(status)
        where = _where(conds)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM webhook_eventos {where}", tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute(
                f"SELECT * FROM webhook_eventos {where} ORDER BY recebido_em DESC LIMIT %s OFFSET %s",
                tuple(params + [limit, offset]),
            )
            return total, [_limpar(r) for r in cur.fetchall()]

    def list_webhooks_com_erro(self, max_tentativas: int = 5, limite: int = 50) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM webhook_eventos WHERE status = 'erro' AND tentativas < %s "
                "ORDER BY recebido_em LIMIT %s",
                (max_tentativas, limite),
            )
            return [_limpar(r) for r in cur.fetchall()]


# =============================================================================
# InMemory (testes)
# =============================================================================

def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _data_de(valor: Any) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return None


def _casa_periodo(
    registro: Dict[str, Any],
    filtros: FiltrosPeriodo,
    escopo: Escopo,
    *,
    campo_data: str,
    campo_status: Optional[str] = "status",
    tipo: Optional[str] = None,
) -> bool:
    """Equivalente em Python de `where_periodo`."""
    d = _data_de(registro.get(campo_data))
    if filtros.data_inicio and (d is None or d < filtros.data_inicio):
        return False
    if filtros.data_fim and (d is None or d > filtros.data_fim):
        return False
    if filtros.ano and (d is None or d.year != filtros.ano):
        return False
    if filtros.mes and (d is None or d.month != filtros.mes):
        return False
    if filtros.semestre and (d is None or (1 if d.month <= 6 else 2) != filtros.semestre):
        return False
    if escopo.polo_id and filtros.polo_id and filtros.polo_id != escopo.polo_id:
        return False
    polo_id = escopo.polo_id or filtros.polo_id
    if polo_id and registro.get("polo_id") != polo_id:
        return False
    if escopo.escola_id and filtros.escola_id and filtros.escola_id != escopo.escola_id:
        return False
    escola_id = escopo.escola_id or filtros.escola_id
    if escola_id and registro.get("escola_id") != escola_id:
        return False
    if filtros.status and campo_status and registro.get(campo_status) != filtros.status:
        return False
    if filtros.tipo and tipo != filtros.tipo:
        return False
    if filtros.pedido_id and registro.get("pedido_id") != filtros.pedido_id:
        return False
    return True


class InMemoryFinanceiroRepository:
    def __init__(self) -> None:
        self.produtos: Dict[str, Dict[str, Any]] = {}
        self.pedidos: Dict[str, Dict[str, Any]] = {}
        self.itens: List[Dict[str, Any]] = []
        self.historico: List[Dict[str, Any]] = []
        self.envios: List[Dict[str, Any]] = []
        self.pagamentos: Dict[str, Dict[str, Any]] = {}
        self.polos: Dict[str, Dict[str, Any]] = {}
        self.regras: List[Dict[str, Any]] = []
        self.gateway_configs: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.gateway_clientes: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self.webhooks: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    # produtos
    def list_produtos(self, tipo: Optional[str] = None, ativo: Optional[bool] = None) -> List[Dict[str, Any]]:
        out = [
            dict(p) for p in self.produtos.values()
            if (tipo is None or p["tipo"] == tipo) and (ativo is None or p["ativo"] == ativo)
        ]
        return sorted(out, key=lambda p: (p["tipo"], p["nome"]))

    def get_produto(self, produto_id: str) -> Optional[Dict[str, Any]]:
        p = self.produtos.get(str(produto_id))
        return dict(p) if p else None

    def get_produtos_por_ids(self, ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        return {str(i): dict(self.produtos[str(i)]) for i in ids if str(i) in self.produtos}

    def create_produto(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        if any(p["sku"] == dados["sku"] for p in self.produtos.values()):
            raise HTTPException(status_code=409, detail="SKU já cadastrado")
        pid = str(uuid.uuid4())
        agora = _agora()
        self.produtos[pid] = {
            "id": pid, **_filtrar_colunas(dados, COLUNAS_PRODUTO),
            "criado_em": agora, "atualizado_em": agora,
        }
        self.produtos[pid].setdefault("ativo", True)
        return dict(self.produtos[pid])

    def update_produto(self, produto_id: str, campos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        p = self.produtos.get(str(produto_id))
        if not p:
            return None
        p.update(_filtrar_colunas(campos, set(COLUNAS_PRODUTO) - {"tipo", "sku"}))
        p["atualizado_em"] = _agora()
        return dict(p)

    # pedidos
    def create_pedido(self, dados: Dict[str, Any], itens: List[Dict[str, Any]], usuario_id: Optional[str]) -> str:
        pid = str(uuid.uuid4())
        self._seq += 1
        agora = _agora()
        pedido = {c: None for c in COLUNAS_PEDIDO}
        pedido.update(_filtrar_colunas(dados, COLUNAS_PEDIDO))
        pedido.update(
            id=pid,
            numero=f"PED-{agora.year}-{self._seq:06d}",
            criado_em=agora,
            atualizado_em=agora,
        )
        pedido["status"] = pedido.get("status") or "aguardando_pagamento"
        self.pedidos[pid] = pedido
        for item in itens:
            self.itens.append({"id": str(uuid.uuid4()), "pedido_id": pid, **item})
        self.historico.append({
            "id": str(uuid.uuid4()), "pedido_id": pid, "status_de": None,
            "status_para": pedido["status"], "usuario_id": usuario_id,
            "origem": "usuario", "observacao": "Pedido criado", "criado_em": agora,
        })
        return pid

    def _montar(self, pedido: Dict[str, Any], completo: bool) -> Dict[str, Any]:
        p = dict(pedido)
        p["polo_nome"] = (self.polos.get(p.get("polo_id") or "") or {}).get("nome")
        p["escola_nome"] = None
        p["itens"] = [dict(i) for i in self.itens if i["pedido_id"] == p["id"]]
        if completo:
            p["historico"] = [dict(h) for h in self.historico if h["pedido_id"] == p["id"]]
            p["envios"] = [dict(e) for e in self.envios if e["pedido_id"] == p["id"]]
        return p

    def get_pedido(self, pedido_id: str) -> Optional[Dict[str, Any]]:
        p = self.pedidos.get(str(pedido_id))
        return self._montar(p, completo=True) if p else None

    def list_pedidos(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[int, List[Dict[str, Any]]]:
        filtrados = [
            p for p in self.pedidos.values()
            if _casa_periodo(p, filtros, escopo, campo_data="criado_em", tipo=p["tipo"])
        ]
        filtrados.sort(key=lambda p: p["criado_em"], reverse=True)
        pagina = filtrados[filtros.offset: filtros.offset + filtros.limit]
        return len(filtrados), [self._montar(p, completo=False) for p in pagina]

    def alterar_status_pedido(
        self,
        pedido_id: str,
        de: str,
        para: str,
        usuario_id: Optional[str],
        origem: str,
        observacao: Optional[str] = None,
        campos: Optional[Dict[str, Any]] = None,
    ) -> None:
        p = self.pedidos.get(str(pedido_id))
        if not p or p["status"] != de:
            raise _conflito_status(pedido_id, de)
        p.update(_filtrar_colunas(campos or {}, CAMPOS_STATUS_EXTRA))
        p["status"] = para
        p["atualizado_em"] = _agora()
        self.historico.append({
            "id": str(uuid.uuid4()), "pedido_id": str(pedido_id), "status_de": de,
            "status_para": para, "usuario_id": usuario_id, "origem": origem,
            "observacao": observacao, "criado_em": _agora(),
        })

    # pagamentos
    def _montar_pagamento(self, pg: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(pg)
        pedido = self.pedidos.get(pg.get("pedido_id") or "")
        out["pedido_numero"] = pedido["numero"] if pedido else None
        out["polo_nome"] = (self.polos.get(pg.get("polo_id") or "") or {}).get("nome")
        return out

    def create_pagamento(self, dados: Dict[str, Any]) -> str:
        pid = str(uuid.uuid4())
        registro = {c: None for c in COLUNAS_PAGAMENTO}
        registro.update(_filtrar_colunas(dados, COLUNAS_PAGAMENTO))
        registro.update(id=pid, criado_em=_agora(), atualizado_em=_agora())
        self.pagamentos[pid] = registro
        return pid

    def get_pagamento(self, pagamento_id: str) -> Optional[Dict[str, Any]]:
        pg = self.pagamentos.get(str(pagamento_id))
        return self._montar_pagamento(pg) if pg else None

    def get_pagamento_por_gateway_id(self, gateway: str, payment_id: str) -> Optional[Dict[str, Any]]:
        for pg in self.pagamentos.values():
            if pg.get("gateway") == gateway and pg.get("gateway_payment_id") == payment_id:
                return self._montar_pagamento(pg)
        return None

    def list_pagamentos(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[int, List[Dict[str, Any]]]:
        def tipo_do(pg: Dict[str, Any]) -> Optional[str]:
            pedido = self.pedidos.get(pg.get("pedido_id") or "")
            return pedido["tipo"] if pedido else None

        filtrados = [
            pg for pg in self.pagamentos.values()
            if _casa_periodo(pg, filtros, escopo, campo_data="criado_em", tipo=tipo_do(pg))
        ]
        filtrados.sort(key=lambda pg: pg["criado_em"], reverse=True)
        pagina = filtrados[filtros.offset: filtros.offset + filtros.limit]
        return len(filtrados), [self._montar_pagamento(pg) for pg in pagina]

    def update_pagamento(self, pagamento_id: str, campos: Dict[str, Any]) -> None:
        pg = self.pagamentos.get(str(pagamento_id))
        if pg:
            pg.update(_filtrar_colunas(campos, COLUNAS_PAGAMENTO))
            pg["atualizado_em"] = _agora()

    # apoio
    def get_endereco_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        p = self.polos.get(str(polo_id))
        return dict(p) if p else None

    def get_dados_cobranca_polo(self, polo_id: str) -> Optional[Dict[str, Any]]:
        p = self.polos.get(str(polo_id))
        return {"id": str(polo_id), **p} if p else None

    def get_regra_pagamento(self, tipo: str, polo_id: Optional[str]) -> Optional[Dict[str, Any]]:
        candidatas = [
            r for r in self.regras
            if r.get("ativo", True)
            and r.get("aplica_tipo_pedido") in (None, tipo)
            and r.get("aplica_polo_id") in (None, polo_id)
        ]
        candidatas.sort(key=lambda r: (r.get("aplica_polo_id") is None, r.get("aplica_tipo_pedido") is None,
                                       r.get("prioridade", 100)))
        return dict(candidatas[0]) if candidatas else None

    # gateways
    def get_gateway_config(self, gateway: str, ambiente: str) -> Optional[Dict[str, Any]]:
        c = self.gateway_configs.get((gateway, ambiente))
        return dict(c) if c else None

    def list_gateway_configs(self) -> List[Dict[str, Any]]:
        return [dict(c) for _, c in sorted(self.gateway_configs.items())]

    def salvar_gateway_config(self, gateway: str, ambiente: str, campos: Dict[str, Any]) -> Dict[str, Any]:
        campos = _filtrar_colunas(campos, CAMPOS_GATEWAY_CONFIG)
        if campos.get("padrao"):
            for (g, a), c in self.gateway_configs.items():
                if a == ambiente and g != gateway:
                    c["padrao"] = False
        atual = self.gateway_configs.setdefault((gateway, ambiente), {
            "id": str(uuid.uuid4()), "gateway": gateway, "ambiente": ambiente, "credenciais_cripto": None,
            "webhook_token_cripto": None, "ativo": False, "padrao": False,
            "ultimo_teste_em": None, "ultimo_teste_ok": None, "criado_em": _agora(),
        })
        atual.update(campos)
        atual["atualizado_em"] = _agora()
        return dict(atual)

    def marcar_teste_gateway(self, gateway: str, ambiente: str, ok: bool) -> None:
        c = self.gateway_configs.get((gateway, ambiente))
        if c:
            c.update(ultimo_teste_em=_agora(), ultimo_teste_ok=ok)

    def get_cliente_gateway(self, gateway: str, ambiente: str, polo_id: str) -> Optional[Dict[str, Any]]:
        c = self.gateway_clientes.get((gateway, ambiente, str(polo_id)))
        return dict(c) if c else None

    def salvar_cliente_gateway(self, gateway: str, ambiente: str, polo_id: str, customer_id: str, documento: str) -> None:
        self.gateway_clientes[(gateway, ambiente, str(polo_id))] = {
            "customer_id": customer_id, "documento_fiscal": documento,
        }

    def get_pagamento_pendente_do_pedido(self, pedido_id: str) -> Optional[Dict[str, Any]]:
        pendentes = [pg for pg in self.pagamentos.values()
                     if pg.get("pedido_id") == str(pedido_id) and pg.get("status") == "pendente"]
        pendentes.sort(key=lambda pg: pg["criado_em"], reverse=True)
        return self._montar_pagamento(pendentes[0]) if pendentes else None

    def list_pagamentos_para_reconciliar(self, limite: int = 50) -> List[Dict[str, Any]]:
        limite_data = _agora() - timedelta(minutes=30)
        out = [
            self._montar_pagamento(pg) for pg in self.pagamentos.values()
            if pg.get("status") in ("pendente", "vencido") and pg.get("gateway_payment_id")
            and pg.get("ambiente") and pg.get("gateway") in (*GATEWAYS_REAIS, "fake")
            and pg["criado_em"] < limite_data
        ]
        return out[:limite]

    # webhooks
    def registrar_webhook(self, gateway: str, ambiente: str, evento_id: str, tipo_evento: Optional[str],
                          payment_id: Optional[str], payload: Any) -> Optional[str]:
        if any(w["gateway"] == gateway and w["evento_id"] == evento_id for w in self.webhooks.values()):
            return None
        wid = str(uuid.uuid4())
        self.webhooks[wid] = {
            "id": wid, "gateway": gateway, "ambiente": ambiente, "evento_id": evento_id,
            "tipo_evento": tipo_evento, "gateway_payment_id": payment_id, "payload": payload,
            "status": "recebido", "tentativas": 0, "erro": None, "recebido_em": _agora(), "processado_em": None,
        }
        return wid

    def finalizar_webhook(self, webhook_id: str, status: str, erro: Optional[str] = None) -> None:
        w = self.webhooks[str(webhook_id)]
        w.update(status=status, erro=erro, processado_em=_agora())
        w["tentativas"] += 1

    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        w = self.webhooks.get(str(webhook_id))
        return dict(w) if w else None

    def list_webhooks(self, gateway: Optional[str], status: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        itens = [dict(w) for w in self.webhooks.values()
                 if (not gateway or w["gateway"] == gateway) and (not status or w["status"] == status)]
        itens.sort(key=lambda w: w["recebido_em"], reverse=True)
        return len(itens), itens[offset: offset + limit]

    def list_webhooks_com_erro(self, max_tentativas: int = 5, limite: int = 50) -> List[Dict[str, Any]]:
        return [dict(w) for w in self.webhooks.values()
                if w["status"] == "erro" and w["tentativas"] < max_tentativas][:limite]


_repo_instance: Optional[FinanceiroRepositoryInterface] = None


def get_financeiro_repository() -> FinanceiroRepositoryInterface:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = PostgresFinanceiroRepository()
    return _repo_instance


def set_financeiro_repository(repo: Optional[FinanceiroRepositoryInterface]) -> None:
    global _repo_instance
    _repo_instance = repo
