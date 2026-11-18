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
COLUNAS_REGRA = (
    "nome", "aplica_tipo_pedido", "aplica_polo_id", "meios_permitidos", "gateway_preferido",
    "dias_vencimento", "multa_pct", "juros_mes_pct", "desconto_antecipado_pct", "valor_minimo",
    "prioridade", "ativo",
)
COLUNAS_ENVIO = ("transportadora", "codigo_rastreio", "volumes", "peso_total_g", "observacao", "etiqueta_gerada_em")
# Campos do pedido editáveis pela logística/financeiro (Fase 3C).
CAMPOS_PEDIDO_EDITAVEIS = frozenset({
    "entrega_nome", "entrega_cep", "entrega_logradouro", "entrega_numero", "entrega_complemento",
    "entrega_bairro", "entrega_cidade", "entrega_uf", "entrega_telefone", "observacao",
    "valor_bruto", "desconto", "valor_total",
})


def regra_generica(regra: Dict[str, Any]) -> bool:
    """Regra sem filtros (fallback do checkout)."""
    return (not regra.get("aplica_tipo_pedido") and not regra.get("aplica_polo_id")
            and float(regra.get("valor_minimo") or 0) == 0)
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
    coluna_gateway: Optional[str] = None,
    coluna_meio: Optional[str] = None,
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
        if filtros.tipo == "com_envio":  # livro + kit (logística)
            conds.append(f"{coluna_tipo} IN ('livro', 'kit')")
        else:
            conds.append(f"{coluna_tipo} = %s")
            params.append(filtros.tipo)
    if filtros.pedido_id and coluna_pedido:
        conds.append(f"{coluna_pedido} = %s")
        params.append(filtros.pedido_id)
    if filtros.gateway and coluna_gateway:
        conds.append(f"{coluna_gateway} = %s")
        params.append(filtros.gateway)
    if filtros.meio and coluna_meio:
        conds.append(f"{coluna_meio} = %s")
        params.append(filtros.meio)
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
    def get_regra_pagamento(self, tipo: str, polo_id: Optional[str], valor: Optional[float] = None) -> Optional[Dict[str, Any]]: ...
    # regras de pagamento (Fase 3B)
    def list_regras(self) -> List[Dict[str, Any]]: ...
    def get_regra(self, regra_id: str) -> Optional[Dict[str, Any]]: ...
    def create_regra(self, dados: Dict[str, Any]) -> Dict[str, Any]: ...
    def update_regra(self, regra_id: str, campos: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    # logística (Fase 3C)
    def registrar_envio(self, pedido_id: str, dados: Dict[str, Any], usuario_id: Optional[str]) -> str: ...
    def update_pedido(self, pedido_id: str, campos: Dict[str, Any], itens: Optional[List[Dict[str, Any]]],
                      usuario_id: Optional[str], observacao: str) -> None: ...
    # catálogo por Curso (kits)
    def catalogo_cursos(self) -> List[Dict[str, Any]]: ...
    def catalogo_curso(self, curso_id: str, polo_id: Optional[str]) -> Optional[Dict[str, Any]]: ...
    # exportação e etiqueta (Fase 4)
    def ultimos_envios(self, pedido_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]: ...
    def get_configuracao(self, chave: str) -> Any: ...
    def marcar_etiqueta_gerada(self, envio_id: str) -> None: ...
    # vendas (Fase 3D)
    def kpis_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Dict[str, Any]: ...
    def serie_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> List[Dict[str, Any]]: ...
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
    def list_webhooks(self, gateway: Optional[str], status: Optional[str], limit: int, offset: int,
                      payment_id: Optional[str] = None) -> Tuple[int, List[Dict[str, Any]]]: ...
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
            coluna_gateway="pg.gateway", coluna_meio="pg.billing_type",
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

    def get_regra_pagamento(self, tipo: str, polo_id: Optional[str], valor: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Regra mais específica (Polo > tipo) e, no empate, a de menor prioridade."""
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT * FROM regras_pagamento
                 WHERE ativo
                   AND (aplica_tipo_pedido IS NULL OR aplica_tipo_pedido = %s)
                   AND (aplica_polo_id IS NULL OR aplica_polo_id::text = %s)
                   AND (%s::numeric IS NULL OR valor_minimo <= %s::numeric)
                 ORDER BY (aplica_polo_id IS NULL), (aplica_tipo_pedido IS NULL), prioridade, valor_minimo DESC
                 LIMIT 1
                """,
                (tipo, str(polo_id or ""), valor, valor),
            )
            return _limpar(cur.fetchone())

    # ---------------- regras de pagamento ----------------

    _SELECT_REGRA = """
        SELECT r.*, po.nome AS polo_nome
          FROM regras_pagamento r LEFT JOIN polos po ON po.id = r.aplica_polo_id
    """

    def list_regras(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(self._SELECT_REGRA + " ORDER BY r.ativo DESC, r.prioridade, r.nome")
            return [_limpar(r) for r in cur.fetchall()]

    def get_regra(self, regra_id: str) -> Optional[Dict[str, Any]]:
        try:
            uuid.UUID(str(regra_id))
        except ValueError:
            return None
        with get_db_cursor() as cur:
            cur.execute(self._SELECT_REGRA + " WHERE r.id = %s", (str(regra_id),))
            return _limpar(cur.fetchone())

    def create_regra(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        campos = _filtrar_colunas(dados, COLUNAS_REGRA)
        cols = ", ".join(campos)
        marks = ", ".join(["%s"] * len(campos))
        with get_db_cursor() as cur:
            cur.execute(f"INSERT INTO regras_pagamento ({cols}) VALUES ({marks}) RETURNING id", tuple(campos.values()))
            regra_id = str(cur.fetchone()["id"])
        return self.get_regra(regra_id)

    def update_regra(self, regra_id: str, campos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        campos = _filtrar_colunas(campos, COLUNAS_REGRA)
        if campos:
            sets = ", ".join(f"{k} = %s" for k in campos)
            with get_db_cursor() as cur:
                cur.execute(
                    f"UPDATE regras_pagamento SET {sets}, atualizado_em = now() WHERE id = %s",
                    (*campos.values(), str(regra_id)),
                )
        return self.get_regra(regra_id)

    # ---------------- logística ----------------

    def registrar_envio(self, pedido_id: str, dados: Dict[str, Any], usuario_id: Optional[str]) -> str:
        campos = _filtrar_colunas(dados, COLUNAS_ENVIO)
        cols = "".join(f", {k}" for k in campos)
        marks = "".join(", %s" for _ in campos)
        with get_db_cursor() as cur:
            cur.execute(
                f"INSERT INTO envios (pedido_id, enviado_por, enviado_em{cols}) "
                f"VALUES (%s, %s, now(){marks}) RETURNING id",
                (str(pedido_id), usuario_id, *campos.values()),
            )
            return str(cur.fetchone()["id"])

    def update_pedido(self, pedido_id: str, campos: Dict[str, Any], itens: Optional[List[Dict[str, Any]]],
                      usuario_id: Optional[str], observacao: str) -> None:
        campos = _filtrar_colunas(campos, CAMPOS_PEDIDO_EDITAVEIS)
        with get_db_cursor() as cur:
            if campos:
                sets = ", ".join(f"{k} = %s" for k in campos)
                cur.execute(
                    f"UPDATE pedidos SET {sets}, atualizado_em = now() WHERE id = %s",
                    (*campos.values(), str(pedido_id)),
                )
            if itens is not None:
                cur.execute("DELETE FROM pedidos_itens WHERE pedido_id = %s", (str(pedido_id),))
                for item in itens:
                    cur.execute(
                        """
                        INSERT INTO pedidos_itens (pedido_id, produto_id, disciplina_id, descricao,
                                                   quantidade, valor_unitario, valor_total)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (str(pedido_id), item.get("produto_id"), item.get("disciplina_id"), item.get("descricao"),
                         item["quantidade"], item["valor_unitario"], item["valor_total"]),
                    )
            cur.execute(
                """
                INSERT INTO pedidos_status_historico (pedido_id, status_de, status_para, usuario_id, origem, observacao)
                SELECT id, status, status, %s, 'usuario', %s FROM pedidos WHERE id = %s
                """,
                (usuario_id, observacao, str(pedido_id)),
            )

    # ---------------- catálogo por Curso ----------------

    def catalogo_cursos(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.nome, c.modalidade,
                       COUNT(d.id) AS disciplinas,
                       COUNT(p.id) AS disciplinas_a_venda,
                       COALESCE(SUM(p.preco), 0) AS preco_curso,
                       MIN(p.preco) AS preco_min, MAX(p.preco) AS preco_max
                  FROM cursos c
                  JOIN disciplinas d ON d.curso_id = c.id AND d.ativo
                  LEFT JOIN produtos p ON p.disciplina_id = d.id AND p.tipo = 'kit' AND p.ativo
                 WHERE COALESCE(c.status, 'ativo') = 'ativo'
                 GROUP BY c.id, c.nome, c.modalidade
                 ORDER BY c.nome
                """
            )
            return [_limpar(r) for r in cur.fetchall()]

    def catalogo_curso(self, curso_id: str, polo_id: Optional[str]) -> Optional[Dict[str, Any]]:
        try:
            uuid.UUID(str(curso_id))
        except ValueError:
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, modalidade FROM cursos WHERE id = %s", (str(curso_id),))
            curso = _limpar(cur.fetchone())
            if not curso:
                return None
            cur.execute(
                """
                SELECT d.id AS disciplina_id, d.nome, d.semestre, d.ordem, p.id AS produto_id, p.preco,
                       (p.id IS NOT NULL) AS a_venda,
                       COALESCE(le.quantidade_disponivel, 0) AS saldo_polo
                  FROM disciplinas d
                  LEFT JOIN produtos p ON p.disciplina_id = d.id AND p.tipo = 'kit' AND p.ativo
                  LEFT JOIN licencas_estoque le
                         ON le.materia_id = d.id AND le.escola_id IS NULL AND le.polo_id::text = %s
                 WHERE d.curso_id = %s AND d.ativo
                 ORDER BY d.semestre NULLS LAST, d.ordem, d.nome
                """,
                (str(polo_id or ""), str(curso_id)),
            )
            curso["disciplinas"] = [_limpar(r) for r in cur.fetchall()]
            return curso

    # ---------------- exportação e etiqueta ----------------

    def ultimos_envios(self, pedido_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        if not pedido_ids:
            return {}
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (pedido_id) * FROM envios
                 WHERE pedido_id::text = ANY(%s)
                 ORDER BY pedido_id, criado_em DESC
                """,
                (list({str(i) for i in pedido_ids}),),
            )
            return {r["pedido_id"]: r for r in (_limpar(x) for x in cur.fetchall())}

    def get_configuracao(self, chave: str) -> Any:
        with get_db_cursor() as cur:
            cur.execute("SELECT valor FROM configuracoes WHERE chave = %s", (chave,))
            row = cur.fetchone()
            return row["valor"] if row else None

    def marcar_etiqueta_gerada(self, envio_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE envios SET etiqueta_gerada_em = now(), atualizado_em = now() WHERE id = %s",
                (str(envio_id),),
            )

    # ---------------- vendas ----------------

    def _where_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Tuple[str, List[Any]]:
        conds, params = where_periodo(filtros, escopo, alias="p", coluna_data="p.criado_em", coluna_tipo="p.tipo")
        return _where(conds), params

    def kpis_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Dict[str, Any]:
        where, params = self._where_vendas(filtros, escopo)
        pago = "p.pago_em IS NOT NULL AND p.status <> 'cancelado'"
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) FILTER (WHERE p.status <> 'cancelado') AS pedidos,
                       COUNT(*) FILTER (WHERE {pago}) AS pedidos_pagos,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE {pago}), 0) AS receita_paga,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE p.status = 'aguardando_pagamento'), 0) AS a_receber,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE {pago} AND p.tipo = 'licenca'), 0) AS receita_licencas,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE {pago} AND p.tipo = 'livro'), 0) AS receita_livros,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE {pago} AND p.tipo = 'kit'), 0) AS receita_kits
                  FROM pedidos p {where}
                """,
                tuple(params),
            )
            kpis = _limpar(cur.fetchone()) or {}
            cur.execute(
                f"""
                SELECT p.tipo, COALESCE(SUM(pi.quantidade), 0) AS quantidade
                  FROM pedidos p JOIN pedidos_itens pi ON pi.pedido_id = p.id
                  {where}{' AND ' if where else ' WHERE '}{pago}
                 GROUP BY p.tipo
                """,
                tuple(params),
            )
            quantidades = {r["tipo"]: int(r["quantidade"]) for r in cur.fetchall()}
            cur.execute(
                f"""
                SELECT COALESCE(SUM(pg.valor), 0) AS vencido
                  FROM pagamentos pg JOIN pedidos p ON p.id = pg.pedido_id
                  {where}{' AND ' if where else ' WHERE '}pg.status = 'vencido' AND p.status = 'aguardando_pagamento'
                """,
                tuple(params),
            )
            vencido = float(cur.fetchone()["vencido"] or 0)
            cur.execute(
                f"SELECT p.status, COUNT(*) AS pedidos, COALESCE(SUM(p.valor_total), 0) AS valor "
                f"FROM pedidos p {where} GROUP BY p.status ORDER BY p.status",
                tuple(params),
            )
            por_status = [_limpar(r) for r in cur.fetchall()]
            cur.execute(
                f"""
                SELECT p.polo_id, po.nome AS polo_nome,
                       COUNT(*) FILTER (WHERE {pago}) AS pedidos_pagos,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE {pago}), 0) AS receita
                  FROM pedidos p LEFT JOIN polos po ON po.id = p.polo_id
                  {where}
                 GROUP BY p.polo_id, po.nome
                HAVING COUNT(*) FILTER (WHERE {pago}) > 0
                 ORDER BY receita DESC LIMIT 10
                """,
                tuple(params),
            )
            top = [_limpar(r) for r in cur.fetchall()]
        kits = quantidades.get("kit", 0)  # cada kit = 1 livro + 1 licença
        return {**kpis, "vencido": vencido, "licencas_vendidas": quantidades.get("licenca", 0) + kits,
                "livros_vendidos": quantidades.get("livro", 0) + kits, "por_status": por_status, "top_polos": top}

    def serie_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> List[Dict[str, Any]]:
        where, params = self._where_vendas(filtros, escopo)
        pago = "p.pago_em IS NOT NULL AND p.status <> 'cancelado'"
        with get_db_cursor() as cur:
            cur.execute(
                f"""
                SELECT to_char(date_trunc('month', p.criado_em), 'YYYY-MM') AS mes,
                       COUNT(*) FILTER (WHERE p.status <> 'cancelado') AS pedidos,
                       COUNT(*) FILTER (WHERE {pago}) AS pedidos_pagos,
                       COALESCE(SUM(p.valor_total) FILTER (WHERE {pago}), 0) AS receita
                  FROM pedidos p {where}
                 GROUP BY 1 ORDER BY 1
                """,
                tuple(params),
            )
            return [_limpar(r) for r in cur.fetchall()]

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
                ([*GATEWAYS_REAIS, "fake"], limite),
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

    def list_webhooks(self, gateway: Optional[str], status: Optional[str], limit: int, offset: int,
                      payment_id: Optional[str] = None) -> Tuple[int, List[Dict[str, Any]]]:
        conds, params = [], []
        if gateway:
            conds.append("gateway = %s")
            params.append(gateway)
        if payment_id:
            conds.append("gateway_payment_id = %s")
            params.append(payment_id)
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
    pagamento: bool = False,
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
    if filtros.tipo == "com_envio":
        if tipo not in ("livro", "kit"):
            return False
    elif filtros.tipo and tipo != filtros.tipo:
        return False
    if filtros.pedido_id and registro.get("pedido_id") != filtros.pedido_id:
        return False
    if pagamento:
        if filtros.gateway and registro.get("gateway") != filtros.gateway:
            return False
        if filtros.meio and registro.get("billing_type") != filtros.meio:
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
            if _casa_periodo(pg, filtros, escopo, campo_data="criado_em", tipo=tipo_do(pg), pagamento=True)
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

    def get_regra_pagamento(self, tipo: str, polo_id: Optional[str], valor: Optional[float] = None) -> Optional[Dict[str, Any]]:
        candidatas = [
            r for r in self.regras
            if r.get("ativo", True)
            and r.get("aplica_tipo_pedido") in (None, tipo)
            and r.get("aplica_polo_id") in (None, polo_id)
            and (valor is None or float(r.get("valor_minimo") or 0) <= valor)
        ]
        candidatas.sort(key=lambda r: (r.get("aplica_polo_id") is None, r.get("aplica_tipo_pedido") is None,
                                       r.get("prioridade", 100), -float(r.get("valor_minimo") or 0)))
        return dict(candidatas[0]) if candidatas else None

    # regras de pagamento
    def _regra_completa(self, r: Dict[str, Any]) -> Dict[str, Any]:
        out = {"multa_pct": 0, "juros_mes_pct": 0, "desconto_antecipado_pct": 0, "valor_minimo": 0,
               "prioridade": 100, "dias_vencimento": 3, "meios_permitidos": ["BOLETO", "PIX"], "ativo": True,
               "aplica_tipo_pedido": None, "aplica_polo_id": None, "gateway_preferido": None, **r}
        out.setdefault("id", str(uuid.uuid4()))
        out["polo_nome"] = (self.polos.get(out.get("aplica_polo_id") or "") or {}).get("nome")
        return out

    def list_regras(self) -> List[Dict[str, Any]]:
        regras = [self._regra_completa(r) for r in self.regras]
        return sorted(regras, key=lambda r: (not r["ativo"], r["prioridade"], r["nome"]))

    def get_regra(self, regra_id: str) -> Optional[Dict[str, Any]]:
        for r in self.regras:
            if r.get("id") == str(regra_id):
                return self._regra_completa(r)
        return None

    def create_regra(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        regra = {"id": str(uuid.uuid4()), **_filtrar_colunas(dados, COLUNAS_REGRA),
                 "criado_em": _agora(), "atualizado_em": _agora()}
        self.regras.append(regra)
        return self._regra_completa(regra)

    def update_regra(self, regra_id: str, campos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for r in self.regras:
            if r.get("id") == str(regra_id):
                r.update(_filtrar_colunas(campos, COLUNAS_REGRA))
                r["atualizado_em"] = _agora()
                return self._regra_completa(r)
        return None

    # logística
    def registrar_envio(self, pedido_id: str, dados: Dict[str, Any], usuario_id: Optional[str]) -> str:
        eid = str(uuid.uuid4())
        self.envios.append({"id": eid, "pedido_id": str(pedido_id), "volumes": 1,
                            **_filtrar_colunas(dados, COLUNAS_ENVIO),
                            "enviado_por": usuario_id, "enviado_em": _agora(), "criado_em": _agora()})
        return eid

    def update_pedido(self, pedido_id: str, campos: Dict[str, Any], itens: Optional[List[Dict[str, Any]]],
                      usuario_id: Optional[str], observacao: str) -> None:
        p = self.pedidos[str(pedido_id)]
        p.update(_filtrar_colunas(campos, CAMPOS_PEDIDO_EDITAVEIS))
        p["atualizado_em"] = _agora()
        if itens is not None:
            self.itens = [i for i in self.itens if i["pedido_id"] != str(pedido_id)]
            for item in itens:
                self.itens.append({"id": str(uuid.uuid4()), "pedido_id": str(pedido_id), **item})
        self.historico.append({
            "id": str(uuid.uuid4()), "pedido_id": str(pedido_id), "status_de": p["status"],
            "status_para": p["status"], "usuario_id": usuario_id, "origem": "usuario",
            "observacao": observacao, "criado_em": _agora(),
        })

    # catálogo por Curso (testes: self.cursos {id: {...}}, self.disciplinas {id: {...curso_id}})
    def _kits_ativos(self) -> Dict[str, Dict[str, Any]]:
        return {str(p["disciplina_id"]): p for p in self.produtos.values()
                if p.get("tipo") == "kit" and p.get("ativo") and p.get("disciplina_id")}

    def _disciplinas_ativas(self, curso_id: str) -> Dict[str, Dict[str, Any]]:
        return {d: disc for d, disc in getattr(self, "disciplinas", {}).items()
                if disc.get("curso_id") == curso_id and disc.get("ativo", True)}

    def catalogo_cursos(self) -> List[Dict[str, Any]]:
        kits = self._kits_ativos()
        saida = []
        for cid, curso in getattr(self, "cursos", {}).items():
            if (curso.get("status") or "ativo") != "ativo":
                continue
            ativas = self._disciplinas_ativas(cid)
            if not ativas:
                continue
            precos = [float(kits[d]["preco"]) for d in ativas if d in kits]
            saida.append({"id": cid, "nome": curso["nome"], "modalidade": curso.get("modalidade"),
                          "disciplinas": len(ativas), "disciplinas_a_venda": len(precos),
                          "preco_curso": round(sum(precos), 2),
                          "preco_min": min(precos) if precos else None, "preco_max": max(precos) if precos else None})
        return sorted(saida, key=lambda c: c["nome"])

    def catalogo_curso(self, curso_id: str, polo_id: Optional[str]) -> Optional[Dict[str, Any]]:
        curso = getattr(self, "cursos", {}).get(str(curso_id))
        if not curso:
            return None
        kits = self._kits_ativos()
        saldos = getattr(self, "saldos_polo", {})
        disciplinas = [
            {"disciplina_id": d, "nome": disc["nome"], "semestre": disc.get("semestre"), "ordem": disc.get("ordem", 0),
             "produto_id": kits[d]["id"] if d in kits else None,
             "preco": float(kits[d]["preco"]) if d in kits else None, "a_venda": d in kits,
             "saldo_polo": int(saldos.get((str(polo_id), d), 0))}
            for d, disc in self._disciplinas_ativas(str(curso_id)).items()
        ]
        disciplinas.sort(key=lambda x: (x["semestre"] or 99, x["ordem"], x["nome"]))
        return {"id": str(curso_id), "nome": curso["nome"], "modalidade": curso.get("modalidade"),
                "disciplinas": disciplinas}

    # exportação e etiqueta
    def ultimos_envios(self, pedido_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        ids = {str(i) for i in pedido_ids}
        out: Dict[str, Dict[str, Any]] = {}
        for e in sorted(self.envios, key=lambda x: x["criado_em"]):
            if e["pedido_id"] in ids:
                out[e["pedido_id"]] = dict(e)
        return out

    def get_configuracao(self, chave: str) -> Any:
        return getattr(self, "configuracoes", {}).get(chave)

    def marcar_etiqueta_gerada(self, envio_id: str) -> None:
        for e in self.envios:
            if e["id"] == str(envio_id):
                e["etiqueta_gerada_em"] = _agora()

    # vendas
    def _pedidos_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> List[Dict[str, Any]]:
        sem_status = filtros.model_copy(update={"status": None})
        return [p for p in self.pedidos.values()
                if _casa_periodo(p, sem_status, escopo, campo_data="criado_em", tipo=p["tipo"])]

    @staticmethod
    def _pago(p: Dict[str, Any]) -> bool:
        return bool(p.get("pago_em")) and p["status"] != "cancelado"

    def kpis_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> Dict[str, Any]:
        pedidos = self._pedidos_vendas(filtros, escopo)
        pagos = [p for p in pedidos if self._pago(p)]
        ids_pagos = {p["id"] for p in pagos}
        tipo_por_id = {p["id"]: p["tipo"] for p in pedidos}
        quantidades: Dict[str, int] = {}
        for i in self.itens:
            if i["pedido_id"] in ids_pagos:
                tipo = tipo_por_id[i["pedido_id"]]
                quantidades[tipo] = quantidades.get(tipo, 0) + int(i["quantidade"])
        aguardando = {p["id"] for p in pedidos if p["status"] == "aguardando_pagamento"}
        por_status: Dict[str, Dict[str, Any]] = {}
        for p in pedidos:
            s = por_status.setdefault(p["status"], {"status": p["status"], "pedidos": 0, "valor": 0.0})
            s["pedidos"] += 1
            s["valor"] += float(p["valor_total"] or 0)
        polos: Dict[Optional[str], Dict[str, Any]] = {}
        for p in pagos:
            item = polos.setdefault(p.get("polo_id"), {
                "polo_id": p.get("polo_id"),
                "polo_nome": (self.polos.get(p.get("polo_id") or "") or {}).get("nome"),
                "pedidos_pagos": 0, "receita": 0.0,
            })
            item["pedidos_pagos"] += 1
            item["receita"] += float(p["valor_total"] or 0)
        return {
            "pedidos": sum(1 for p in pedidos if p["status"] != "cancelado"),
            "pedidos_pagos": len(pagos),
            "receita_paga": sum(float(p["valor_total"] or 0) for p in pagos),
            "a_receber": sum(float(p["valor_total"] or 0) for p in pedidos if p["id"] in aguardando),
            "receita_licencas": sum(float(p["valor_total"] or 0) for p in pagos if p["tipo"] == "licenca"),
            "receita_livros": sum(float(p["valor_total"] or 0) for p in pagos if p["tipo"] == "livro"),
            "receita_kits": sum(float(p["valor_total"] or 0) for p in pagos if p["tipo"] == "kit"),
            "vencido": sum(float(pg["valor"] or 0) for pg in self.pagamentos.values()
                           if pg.get("status") == "vencido" and pg.get("pedido_id") in aguardando),
            "licencas_vendidas": quantidades.get("licenca", 0) + quantidades.get("kit", 0),
            "livros_vendidos": quantidades.get("livro", 0) + quantidades.get("kit", 0),
            "por_status": sorted(por_status.values(), key=lambda s: s["status"]),
            "top_polos": sorted(polos.values(), key=lambda x: x["receita"], reverse=True)[:10],
        }

    def serie_vendas(self, filtros: FiltrosPeriodo, escopo: Escopo) -> List[Dict[str, Any]]:
        meses: Dict[str, Dict[str, Any]] = {}
        for p in self._pedidos_vendas(filtros, escopo):
            mes = p["criado_em"].strftime("%Y-%m")
            m = meses.setdefault(mes, {"mes": mes, "pedidos": 0, "pedidos_pagos": 0, "receita": 0.0})
            if p["status"] != "cancelado":
                m["pedidos"] += 1
            if self._pago(p):
                m["pedidos_pagos"] += 1
                m["receita"] += float(p["valor_total"] or 0)
        return [meses[k] for k in sorted(meses)]

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

    def list_webhooks(self, gateway: Optional[str], status: Optional[str], limit: int, offset: int,
                      payment_id: Optional[str] = None) -> Tuple[int, List[Dict[str, Any]]]:
        itens = [dict(w) for w in self.webhooks.values()
                 if (not gateway or w["gateway"] == gateway) and (not status or w["status"] == status)
                 and (not payment_id or w.get("gateway_payment_id") == payment_id)]
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
