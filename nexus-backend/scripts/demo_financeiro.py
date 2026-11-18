"""Dados de DEMONSTRAÇÃO do módulo Financeiro & Logística (Simulador, sandbox).

Cria pedidos, cobranças (gateway "fake"), envios e eventos simulados nos Polos reais,
para apresentar ao cliente. Tudo fica marcado e é removível:
  - produtos:   sku começa com "DEMO-"
  - pedidos:    observacao começa com "[DEMO]"
  - cobranças:  gateway_payment_id começa com "pay_fake_demo_"

Uso (na pasta nexus-backend):
  .venv\\Scripts\\python.exe scripts\\demo_financeiro.py --status
  .venv\\Scripts\\python.exe scripts\\demo_financeiro.py --criar
  .venv\\Scripts\\python.exe scripts\\demo_financeiro.py --limpar

Recusa rodar com PAYMENT_ENV=producao, e com ENVIRONMENT=production sem --permitir-producao.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg2.extras import Json  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db_cursor  # noqa: E402

MARCA = "[DEMO]"
PREFIXO_SKU = "DEMO-"
PREFIXO_PAGAMENTO = "pay_fake_demo_"
FUSO = timezone(timedelta(hours=-3))
LINHA_DIGITAVEL = "00190.00009 01234.567890 12345.678901 1 99990000010000"
PIX = "00020126580014br.gov.bcb.pix0136demo-nexus-simulado520400005303986"

LIVROS = [
    ("DEMO-LIV-MAT", "Matemática Vol. 1 (demonstração)", 89.90, 450),
    ("DEMO-LIV-POR", "Língua Portuguesa Vol. 1 (demonstração)", 79.90, 420),
    ("DEMO-LIV-CIE", "Ciências Vol. 1 (demonstração)", 74.50, 380),
]
LICENCA_PRECO = 39.90

# (situação, quantidade, meio, dias atrás da criação)
CENARIOS = [
    ("pago_aguardando_envio", 4, "BOLETO", [6, 4, 2, 1]),
    ("enviado", 3, "PIX", [12, 9, 7]),
    ("entregue", 3, "BOLETO", [150, 110, 75]),
    ("boleto_pendente", 3, "BOLETO", [3, 2, 1]),
    ("boleto_vencido", 2, "BOLETO", [20, 15]),
    ("pix_pendente", 1, "PIX", [0]),
    ("cancelado", 1, "BOLETO", [40]),
    ("licenca_pendente", 1, "PIX", [1]),
]
# Entregues/enviados antigos espalham a receita pelos meses (gráfico de Vendas).
ENTREGUES_EXTRA_DIAS = [45, 30]


@dataclass
class PedidoDemo:
    cenario: str
    tipo: str
    status: str
    meio: str
    criado_em: datetime
    status_pagamento: Optional[str]
    pago_em: Optional[datetime] = None
    vencimento: Optional[datetime] = None
    enviado_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    itens: List[Dict[str, Any]] = field(default_factory=list)


def _status(cenario: str) -> tuple[str, Optional[str], str]:
    """(status do pedido, status da cobrança, tipo)."""
    return {
        "pago_aguardando_envio": ("pago_aguardando_envio", "pago", "livro"),
        "enviado": ("enviado", "pago", "livro"),
        "entregue": ("entregue", "pago", "livro"),
        "boleto_pendente": ("aguardando_pagamento", "pendente", "livro"),
        "boleto_vencido": ("aguardando_pagamento", "vencido", "livro"),
        "pix_pendente": ("aguardando_pagamento", "pendente", "livro"),
        "cancelado": ("cancelado", "cancelado", "livro"),
        "licenca_pendente": ("aguardando_pagamento", "pendente", "licenca"),
    }[cenario]


def montar_plano(agora: datetime) -> List[PedidoDemo]:
    """Plano dos pedidos demo (função pura, testável). Datas sempre no passado."""
    plano: List[PedidoDemo] = []
    contador = 0
    cenarios = list(CENARIOS) + [("entregue", len(ENTREGUES_EXTRA_DIAS), "PIX", ENTREGUES_EXTRA_DIAS)]
    for cenario, qtd, meio, dias in cenarios:
        status_pedido, status_pg, tipo = _status(cenario)
        for i in range(qtd):
            criado = agora - timedelta(days=dias[i], hours=2 + i)
            p = PedidoDemo(cenario, tipo, status_pedido, meio, criado, status_pg)
            vence_dias = 3 if meio == "BOLETO" else 1
            p.vencimento = criado + timedelta(days=vence_dias)
            if cenario == "boleto_vencido":
                p.vencimento = agora - timedelta(days=3 + i)
            if status_pg == "pago":
                p.pago_em = criado + timedelta(hours=6)
            if status_pedido in ("enviado", "entregue"):
                p.enviado_em = criado + timedelta(days=1, hours=3)
            if status_pedido == "entregue":
                p.entregue_em = criado + timedelta(days=4)
            if tipo == "livro":
                a, b = LIVROS[contador % 3], LIVROS[(contador + 1) % 3]
                p.itens = [{"sku": a[0], "quantidade": 5 + (contador % 4) * 5},
                           {"sku": b[0], "quantidade": 3 + (contador % 3) * 2}]
            else:
                p.itens = [{"sku": "DEMO-LIC-1", "quantidade": 20}]
            contador += 1
            plano.append(p)
    return plano


def verificar_ambiente(permitir_producao: bool) -> None:
    if settings.PAYMENT_ENV == "producao":
        raise SystemExit("Recusado: PAYMENT_ENV=producao. Dados de demonstração só no sandbox.")
    if settings.ENVIRONMENT == "production" and not permitir_producao:
        raise SystemExit("Recusado: ENVIRONMENT=production. Use --permitir-producao apenas em banco de homologação.")
    if not settings.PG_DSN:
        raise SystemExit("PG_DSN não configurado.")
    host = urlparse(settings.PG_DSN).hostname or "?"
    print(f"Banco de destino: {host[:6]}…{host[-12:] if len(host) > 18 else ''} | PAYMENT_ENV={settings.PAYMENT_ENV}")


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

def _garantir_simulador(cur) -> None:
    cur.execute(
        """
        INSERT INTO gateways_config (gateway, ambiente, ativo) VALUES ('fake', 'sandbox', true)
        ON CONFLICT (gateway, ambiente) DO UPDATE SET ativo = true, atualizado_em = now()
        """
    )
    cur.execute("SELECT 1 FROM gateways_config WHERE ambiente = 'sandbox' AND padrao AND gateway <> 'fake'")
    if cur.fetchone() is None:
        cur.execute("UPDATE gateways_config SET padrao = true WHERE gateway = 'fake' AND ambiente = 'sandbox'")
        print("Simulador ativado e marcado como padrão no sandbox.")
    else:
        print("Simulador ativado (outro gateway continua como padrão no sandbox).")


def _produtos(cur) -> Dict[str, Dict[str, Any]]:
    cur.execute("SELECT id, nome FROM disciplinas ORDER BY nome LIMIT 2")
    disciplinas = cur.fetchall()
    especificacoes = [("livro", sku, nome, preco, peso, None) for sku, nome, preco, peso in LIVROS]
    for i, d in enumerate(disciplinas, start=1):
        especificacoes.append(("licenca", f"DEMO-LIC-{i}", f"Licença {d['nome']} (demonstração)", LICENCA_PRECO, None, d["id"]))
    produtos: Dict[str, Dict[str, Any]] = {}
    for tipo, sku, nome, preco, peso, disciplina in especificacoes:
        cur.execute(
            """
            INSERT INTO produtos (tipo, sku, nome, preco, peso_g, disciplina_id, ativo)
            VALUES (%s, %s, %s, %s, %s, %s, true)
            ON CONFLICT (sku) DO UPDATE SET nome = EXCLUDED.nome, preco = EXCLUDED.preco
            RETURNING id, sku, nome, preco, disciplina_id
            """,
            (tipo, sku, nome, preco, peso, disciplina),
        )
        row = cur.fetchone()
        produtos[row["sku"]] = dict(row)
    return produtos


def _polos(cur) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT p.id, p.nome, p.cep, p.logradouro, p.numero, p.complemento, p.bairro, p.cidade, p.uf,
               (SELECT e.id FROM escolas e WHERE e.polo_id = p.id ORDER BY e.nome LIMIT 1) AS escola_id
          FROM polos p ORDER BY p.nome LIMIT 20
        """
    )
    return [dict(r) for r in cur.fetchall()]


def criar() -> None:
    agora = datetime.now(FUSO)
    with get_db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM pedidos WHERE observacao LIKE %s", (f"{MARCA}%",))
        if cur.fetchone()["n"]:
            raise SystemExit("Já existem dados DEMO. Rode --limpar antes de criar de novo.")
        polos = _polos(cur)
        if not polos:
            raise SystemExit("Nenhum Polo cadastrado: cadastre ao menos um Polo antes da demonstração.")
        _garantir_simulador(cur)
        produtos = _produtos(cur)
        plano = montar_plano(agora)
        if "DEMO-LIC-1" not in produtos:
            print("Aviso: sem disciplinas cadastradas, o pedido de licença DEMO foi omitido.")
            plano = [p for p in plano if p.tipo != "licenca"]

        for n, p in enumerate(plano, start=1):
            polo = polos[n % len(polos)]
            itens = [{**produtos[i["sku"]], "quantidade": i["quantidade"]} for i in p.itens]
            total = round(sum(float(i["preco"]) * i["quantidade"] for i in itens), 2)
            motivo = "Pedido duplicado pelo Polo (demonstração)" if p.status == "cancelado" else None
            cur.execute(
                """
                INSERT INTO pedidos (tipo, polo_id, escola_id, status, valor_bruto, desconto, valor_total,
                    entrega_nome, entrega_cep, entrega_logradouro, entrega_numero, entrega_complemento,
                    entrega_bairro, entrega_cidade, entrega_uf, observacao, pago_em, enviado_em, entregue_em,
                    cancelado_em, motivo_cancelamento, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, numero
                """,
                (p.tipo, polo["id"], polo["escola_id"] if p.tipo == "livro" else None, p.status, total, total,
                 polo["nome"], polo["cep"] or "01001000", polo["logradouro"] or "Rua de Demonstração",
                 polo["numero"] or "100", polo["complemento"], polo["bairro"] or "Centro",
                 polo["cidade"] or "São Paulo", (polo["uf"] or "SP")[:2],
                 f"{MARCA} Pedido simulado para demonstração", p.pago_em, p.enviado_em, p.entregue_em,
                 p.criado_em + timedelta(days=1) if p.status == "cancelado" else None, motivo,
                 p.criado_em, p.entregue_em or p.enviado_em or p.pago_em or p.criado_em),
            )
            pedido = cur.fetchone()
            for i in itens:
                cur.execute(
                    """
                    INSERT INTO pedidos_itens (pedido_id, produto_id, disciplina_id, descricao, quantidade,
                                               valor_unitario, valor_total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (pedido["id"], i["id"], i.get("disciplina_id"), i["nome"], i["quantidade"], i["preco"],
                     round(float(i["preco"]) * i["quantidade"], 2)),
                )
            _historico(cur, pedido["id"], p)
            pid = f"{PREFIXO_PAGAMENTO}{n:03d}"
            cur.execute(
                """
                INSERT INTO pagamentos (pedido_id, polo_id, escola_id, gateway, ambiente, gateway_customer_id,
                    gateway_payment_id, billing_type, valor, valor_liquido, status, parcelas, linha_digitavel,
                    pix_copia_cola, vencimento_em, pago_em, cancelado_em, descricao, criado_em, atualizado_em)
                VALUES (%s, %s, %s, 'fake', 'sandbox', 'cus_fake_demo', %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, now())
                """,
                (pedido["id"], polo["id"], polo["escola_id"] if p.tipo == "livro" else None, pid, p.meio, total,
                 round(total * 0.9801, 2) if p.status_pagamento == "pago" else None, p.status_pagamento,
                 LINHA_DIGITAVEL if p.meio == "BOLETO" else None, PIX if p.meio == "PIX" else None,
                 p.vencimento.date() if p.vencimento else None, p.pago_em,
                 p.criado_em + timedelta(days=1) if p.status_pagamento == "cancelado" else None,
                 f"Pedido {pedido['numero']}", p.criado_em + timedelta(minutes=2)),
            )
            if p.status_pagamento in ("pago", "vencido"):
                evento = "PAGO" if p.status_pagamento == "pago" else "VENCIDO"
                cur.execute(
                    """
                    INSERT INTO webhook_eventos (gateway, ambiente, evento_id, tipo_evento, gateway_payment_id,
                                                 payload, status, tentativas, recebido_em, processado_em)
                    VALUES ('fake', 'sandbox', %s, 'SIMULADO', %s, %s, 'processado', 1, %s, %s)
                    ON CONFLICT (gateway, evento_id) DO NOTHING
                    """,
                    (f"demo:{pid}:{evento}", pid,
                     Json({"id": f"demo:{pid}", "payment_id": pid, "status": p.status_pagamento, "demo": True}),
                     p.pago_em or p.vencimento, p.pago_em or p.vencimento),
                )
            if p.enviado_em:
                cur.execute(
                    """
                    INSERT INTO envios (pedido_id, transportadora, codigo_rastreio, volumes, peso_total_g,
                                        enviado_em, observacao, criado_em)
                    VALUES (%s, 'Correios', %s, %s, %s, %s, %s, %s)
                    """,
                    (pedido["id"], f"BRDEMO{n:06d}BR", 1 + n % 2, 3500 + n * 100, p.enviado_em, MARCA, p.enviado_em),
                )
        print(f"Criados {len(plano)} pedidos DEMO em {len(polos)} Polo(s).")


def _historico(cur, pedido_id: str, p: PedidoDemo) -> None:
    passos = [(None, "aguardando_pagamento", p.criado_em, "usuario", "Pedido criado")]
    if p.pago_em:
        destino = "pago_aguardando_envio" if p.tipo == "livro" else "concluido"
        passos.append(("aguardando_pagamento", destino, p.pago_em, "webhook", "Pagamento confirmado (demonstração)"))
    if p.enviado_em:
        passos.append(("pago_aguardando_envio", "enviado", p.enviado_em, "usuario", "Enviado por Correios (demonstração)"))
    if p.entregue_em:
        passos.append(("enviado", "entregue", p.entregue_em, "usuario", "Entrega confirmada"))
    if p.status == "cancelado":
        passos.append(("aguardando_pagamento", "cancelado", p.criado_em + timedelta(days=1), "usuario",
                       "Pedido duplicado pelo Polo (demonstração)"))
    for de, para, quando, origem, obs in passos:
        cur.execute(
            """
            INSERT INTO pedidos_status_historico (pedido_id, status_de, status_para, origem, observacao, criado_em)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (pedido_id, de, para, origem, obs, quando),
        )


def limpar() -> None:
    with get_db_cursor() as cur:
        cur.execute("SELECT id, numero FROM pedidos WHERE observacao LIKE %s", (f"{MARCA}%",))
        pedidos = cur.fetchall()
        ids = [str(p["id"]) for p in pedidos]
        numeros = [p["numero"] for p in pedidos]
        # Reverte créditos de licença vindos de pagamentos simulados de pedidos DEMO.
        revertidas = 0
        if numeros:
            cur.execute(
                """
                SELECT id, polo_id, materia_id, quantidade FROM licencas_movimentacoes
                 WHERE tipo = 'compra_fornecedor' AND observacao = ANY(%s)
                """,
                ([f"Pedido {n} pago via gateway" for n in numeros],),
            )
            for mov in cur.fetchall():
                cur.execute(
                    """
                    UPDATE licencas_estoque
                       SET quantidade_disponivel = GREATEST(quantidade_disponivel - %s, 0), atualizado_em = now()
                     WHERE polo_id = %s AND escola_id IS NULL AND materia_id IS NOT DISTINCT FROM %s
                    """,
                    (mov["quantidade"], mov["polo_id"], mov["materia_id"]),
                )
                cur.execute("DELETE FROM licencas_movimentacoes WHERE id = %s", (mov["id"],))
                revertidas += 1
        # Eventos das cobranças DEMO e das geradas durante a apresentação (ex.: segunda via, simulações).
        cur.execute(
            """
            DELETE FROM webhook_eventos
             WHERE gateway = 'fake'
               AND (gateway_payment_id LIKE %s
                    OR gateway_payment_id IN (SELECT gateway_payment_id FROM pagamentos WHERE pedido_id::text = ANY(%s)))
            """,
            (f"{PREFIXO_PAGAMENTO}%", ids),
        )
        webhooks = cur.rowcount
        cur.execute("DELETE FROM pagamentos WHERE pedido_id::text = ANY(%s) OR gateway_payment_id LIKE %s",
                    (ids, f"{PREFIXO_PAGAMENTO}%"))
        pagamentos = cur.rowcount
        if ids:
            cur.execute("DELETE FROM pedidos WHERE id::text = ANY(%s)", (ids,))  # itens, histórico e envios em cascata
        cur.execute("DELETE FROM produtos WHERE sku LIKE %s AND id NOT IN "
                    "(SELECT produto_id FROM pedidos_itens WHERE produto_id IS NOT NULL)", (f"{PREFIXO_SKU}%",))
        produtos = cur.rowcount
    print(f"Removidos: {len(ids)} pedidos, {pagamentos} cobranças, {webhooks} eventos, {produtos} produtos; "
          f"{revertidas} crédito(s) de licença revertido(s).")


def status() -> None:
    with get_db_cursor() as cur:
        cur.execute("SELECT status, COUNT(*) AS n FROM pedidos WHERE observacao LIKE %s GROUP BY status ORDER BY status",
                    (f"{MARCA}%",))
        linhas = cur.fetchall()
        cur.execute("SELECT ativo, padrao FROM gateways_config WHERE gateway = 'fake' AND ambiente = 'sandbox'")
        sim = cur.fetchone()
    print("Pedidos DEMO:", ", ".join(f"{r['status']}={r['n']}" for r in linhas) or "nenhum")
    print("Simulador:", "não configurado" if not sim else f"ativo={sim['ativo']} padrão={sim['padrao']}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--criar", action="store_true")
    grupo.add_argument("--limpar", action="store_true")
    grupo.add_argument("--status", action="store_true")
    parser.add_argument("--permitir-producao", action="store_true")
    args = parser.parse_args(argv)
    verificar_ambiente(args.permitir_producao)
    if args.criar:
        criar()
    elif args.limpar:
        limpar()
    status()


if __name__ == "__main__":
    main()
