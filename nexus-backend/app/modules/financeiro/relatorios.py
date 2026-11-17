"""Relatórios exportáveis do módulo 2.4 (Fase 4): vendas, boletos/pagamentos, pedidos e etiqueta.

Reaproveita os mesmos serviços/filtros das telas, então o arquivo bate com o que o usuário vê.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException, Response, status

from app.modules.auth.schemas import UserResponse
from app.modules.financeiro import exportacao as exp
from app.modules.financeiro.etiqueta import gerar_etiqueta
from app.modules.financeiro.operacao_service import OperacaoService
from app.modules.financeiro.repository import FinanceiroRepositoryInterface
from app.modules.financeiro.schemas import FiltrosPeriodo
from app.modules.financeiro.service import escopo_do_usuario

Formato = Literal["pdf", "xlsx"]
CHAVE_REMETENTE = "remetente_etiqueta"
CAMPOS_REMETENTE_OBRIGATORIOS = ("nome", "logradouro", "cidade", "uf", "cep")
STATUS_ETIQUETA = ("pago_aguardando_envio", "enviado", "entregue")
TIPO_LABEL = {"livro": "Livro", "licenca": "Licença"}
STATUS_LABEL = {
    "aguardando_pagamento": "Aguardando pagamento",
    "pago_aguardando_envio": "Pago - aguardando envio",
    "enviado": "Enviado",
    "entregue": "Entregue",
    "concluido": "Concluído",
    "cancelado": "Cancelado",
}


def _rotulo_status(valor: Optional[str]) -> str:
    return STATUS_LABEL.get(valor or "", valor or "-")


class RelatoriosService:
    def __init__(self, repo: FinanceiroRepositoryInterface, operacao: Optional[OperacaoService] = None) -> None:
        self.repo = repo
        self.operacao = operacao or OperacaoService(repo)

    # ------------------------------------------------------------------
    def _todos(self, filtros: FiltrosPeriodo) -> FiltrosPeriodo:
        """Sem paginação: pede uma linha a mais que o teto para detectar excesso."""
        return filtros.model_copy(update={"limit": exp.MAX_LINHAS_EXPORT + 1, "offset": 0})

    def _nomes(self, filtros: FiltrosPeriodo, linhas: List[Dict[str, Any]]) -> Dict[str, str]:
        nomes: Dict[str, str] = {}
        if filtros.polo_id:
            nomes["polo"] = next((l.get("polo_nome") for l in linhas if l.get("polo_nome")), "") or ""
        if filtros.escola_id:
            nomes["escola"] = next((l.get("escola_nome") for l in linhas if l.get("escola_nome")), "") or ""
        return nomes

    # ------------------------------------------------------------------
    # Pedidos / histórico
    # ------------------------------------------------------------------

    def pedidos(self, filtros: FiltrosPeriodo, formato: Formato, user: UserResponse) -> Response:
        total, linhas = self.repo.list_pedidos(self._todos(filtros), escopo_do_usuario(user))
        exp.garantir_limite(total)
        envios = self.repo.ultimos_envios([p["id"] for p in linhas])
        colunas: List[exp.Coluna] = [
            ("Número", 30, "L", "texto"), ("Criado em", 20, "C", "data"), ("Polo", 34, "L", "texto"),
            ("Escola", 28, "L", "texto"), ("Tipo", 14, "L", "texto"), ("Itens", 12, "C", "int"),
            ("Status", 30, "L", "texto"), ("Total", 22, "R", "moeda"), ("Pago em", 20, "C", "data"),
            ("Enviado em", 20, "C", "data"), ("Transportadora", 24, "L", "texto"), ("Rastreio", 24, "L", "texto"),
        ]
        dados = []
        for p in linhas:
            envio = envios.get(p["id"]) or {}
            dados.append([
                p.get("numero"), p.get("criado_em"), p.get("polo_nome"), p.get("escola_nome"),
                TIPO_LABEL.get(p.get("tipo"), p.get("tipo")), sum(int(i.get("quantidade") or 0) for i in p.get("itens") or []),
                _rotulo_status(p.get("status")), p.get("valor_total"), p.get("pago_em"), p.get("enviado_em"),
                envio.get("transportadora"), envio.get("codigo_rastreio"),
            ])
        totais = ["Total", None, None, None, None, sum(d[5] for d in dados), None,
                  sum(float(d[7] or 0) for d in dados), None, None, None, None]
        filtros_txt = exp.descrever_filtros(filtros, self._nomes(filtros, linhas))
        if formato == "xlsx":
            itens_col: List[exp.Coluna] = [("Pedido", 0, "L", "texto"), ("Item", 0, "L", "texto"),
                                           ("Quantidade", 0, "C", "int"), ("Unitário", 0, "R", "moeda"),
                                           ("Total", 0, "R", "moeda")]
            itens = [[p.get("numero"), i.get("descricao"), i.get("quantidade"), i.get("valor_unitario"), i.get("valor_total")]
                     for p in linhas for i in p.get("itens") or []]
            conteudo = exp.planilha_xlsx([("Pedidos", colunas, dados), ("Itens", itens_col, itens)], filtros_txt)
        else:
            pdf = exp.RelatorioPDF("Histórico de pedidos", filtros_txt, paisagem=True)
            pdf.add_page()
            pdf.tabela(colunas, dados, totais)
            conteudo = pdf.bytes()
        return exp.resposta_arquivo(conteudo, "pedidos", formato)

    # ------------------------------------------------------------------
    # Boletos / pagamentos
    # ------------------------------------------------------------------

    def pagamentos(self, filtros: FiltrosPeriodo, formato: Formato, user: UserResponse) -> Response:
        total, linhas = self.repo.list_pagamentos(self._todos(filtros), escopo_do_usuario(user))
        exp.garantir_limite(total)
        colunas: List[exp.Coluna] = [
            ("Criado em", 20, "C", "data"), ("Polo", 40, "L", "texto"), ("Pedido", 30, "L", "texto"),
            ("Meio", 16, "L", "texto"), ("Gateway", 26, "L", "texto"), ("Vencimento", 20, "C", "data"),
            ("Status", 20, "L", "texto"), ("Valor", 24, "R", "moeda"), ("Pago em", 20, "C", "data"),
            ("Valor líquido", 24, "R", "moeda"),
        ]
        dados = [[
            pg.get("criado_em"), pg.get("polo_nome"), pg.get("pedido_numero"), pg.get("billing_type"),
            "Simulador" if pg.get("gateway") == "fake" else f"{pg.get('gateway') or '-'} ({pg.get('ambiente') or '-'})",
            pg.get("vencimento_em"), pg.get("status"), pg.get("valor"), pg.get("pago_em"), pg.get("valor_liquido"),
        ] for pg in linhas]
        por_status: Dict[str, Tuple[int, float]] = {}
        for pg in linhas:
            qtd, soma = por_status.get(pg.get("status") or "-", (0, 0.0))
            por_status[pg.get("status") or "-"] = (qtd + 1, soma + float(pg.get("valor") or 0))
        resumo_col: List[exp.Coluna] = [("Status", 60, "L", "texto"), ("Cobranças", 40, "C", "int"), ("Valor", 60, "R", "moeda")]
        resumo = [[s, q, v] for s, (q, v) in sorted(por_status.items())]
        filtros_txt = exp.descrever_filtros(filtros, self._nomes(filtros, linhas))
        if formato == "xlsx":
            conteudo = exp.planilha_xlsx([("Cobranças", colunas, dados), ("Por status", resumo_col, resumo)], filtros_txt)
        else:
            pdf = exp.RelatorioPDF("Boletos & Pagamentos", filtros_txt, paisagem=True)
            pdf.add_page()
            pdf.secao("Resumo por status")
            pdf.tabela(resumo_col, resumo, ["Total", sum(r[1] for r in resumo), sum(r[2] for r in resumo)])
            pdf.secao("Cobranças")
            pdf.tabela(colunas, dados, ["Total", None, None, None, None, None, None,
                                        sum(float(d[7] or 0) for d in dados), None, None])
            conteudo = pdf.bytes()
        return exp.resposta_arquivo(conteudo, "boletos-pagamentos", formato)

    # ------------------------------------------------------------------
    # Vendas
    # ------------------------------------------------------------------

    def vendas(self, filtros: FiltrosPeriodo, formato: Formato, user: UserResponse) -> Response:
        kpis = self.operacao.kpis_vendas(filtros, user)
        serie = self.operacao.serie_vendas(filtros, user)
        pagos_total, pagos = self.repo.list_pedidos(self._todos(filtros), escopo_do_usuario(user))
        exp.garantir_limite(pagos_total)
        pagos = [p for p in pagos if p.get("pago_em") and p.get("status") != "cancelado"]

        resumo = [
            ("Receita paga", exp.brl(kpis.receita_paga)), ("Pedidos pagos", str(kpis.pedidos_pagos)),
            ("A receber", exp.brl(kpis.a_receber)), ("Vencido", exp.brl(kpis.vencido)),
            ("Ticket médio", exp.brl(kpis.ticket_medio)), ("Pedidos (exceto cancelados)", str(kpis.pedidos)),
            ("Receita licenças", exp.brl(kpis.receita_licencas)), ("Receita livros", exp.brl(kpis.receita_livros)),
            ("Licenças vendidas", str(kpis.licencas_vendidas)), ("Livros vendidos", str(kpis.livros_vendidos)),
        ]
        mensal_col: List[exp.Coluna] = [("Mês", 40, "L", "texto"), ("Pedidos", 30, "C", "int"),
                                        ("Pagos", 30, "C", "int"), ("Receita", 50, "R", "moeda")]
        mensal = [[s.mes, s.pedidos, s.pedidos_pagos, s.receita] for s in serie]
        polos_col: List[exp.Coluna] = [("Polo", 90, "L", "texto"), ("Pedidos pagos", 40, "C", "int"),
                                       ("Receita", 60, "R", "moeda")]
        polos = [[p.polo_nome or "-", p.pedidos_pagos, p.receita] for p in kpis.top_polos]
        status_col: List[exp.Coluna] = [("Status", 90, "L", "texto"), ("Pedidos", 40, "C", "int"), ("Valor", 60, "R", "moeda")]
        por_status = [[_rotulo_status(s.status), s.pedidos, s.valor] for s in kpis.por_status]
        pagos_col: List[exp.Coluna] = [("Número", 30, "L", "texto"), ("Polo", 50, "L", "texto"), ("Tipo", 20, "L", "texto"),
                                       ("Pago em", 25, "C", "data"), ("Total", 30, "R", "moeda")]
        pagos_linhas = [[p.get("numero"), p.get("polo_nome"), TIPO_LABEL.get(p.get("tipo"), p.get("tipo")),
                         p.get("pago_em"), p.get("valor_total")] for p in pagos]
        filtros_txt = exp.descrever_filtros(filtros, self._nomes(filtros, pagos))

        if formato == "xlsx":
            resumo_col: List[exp.Coluna] = [("Indicador", 0, "L", "texto"), ("Valor", 0, "L", "texto")]
            conteudo = exp.planilha_xlsx([
                ("Resumo", resumo_col, [list(r) for r in resumo]), ("Mensal", mensal_col, mensal),
                ("Top Polos", polos_col, polos), ("Por status", status_col, por_status),
                ("Pedidos pagos", pagos_col, pagos_linhas),
            ], filtros_txt)
        else:
            pdf = exp.RelatorioPDF("Relatório de vendas", filtros_txt)
            pdf.add_page()
            pdf.secao("Indicadores")
            pdf.pares(resumo)
            pdf.secao("Receita por mês (mês de criação do pedido)")
            pdf.tabela(mensal_col, mensal, ["Total", sum(m[1] for m in mensal), sum(m[2] for m in mensal),
                                            sum(float(m[3]) for m in mensal)])
            pdf.secao("Top Polos (receita paga)")
            pdf.tabela(polos_col, polos)
            pdf.secao("Pedidos por status")
            pdf.tabela(status_col, por_status)
            conteudo = pdf.bytes()
        return exp.resposta_arquivo(conteudo, "vendas", formato)

    # ------------------------------------------------------------------
    # Etiqueta 10×15
    # ------------------------------------------------------------------

    def remetente(self) -> Dict[str, Any]:
        valor = self.repo.get_configuracao(CHAVE_REMETENTE)
        if isinstance(valor, dict) and isinstance(valor.get("valor"), dict):
            valor = valor["valor"]
        faltando = [c for c in CAMPOS_REMETENTE_OBRIGATORIOS if not (valor or {}).get(c)] if isinstance(valor, dict) else list(CAMPOS_REMETENTE_OBRIGATORIOS)
        if faltando:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Configure o remetente das etiquetas em Configurações (faltando: {', '.join(faltando)}).",
            )
        return valor

    def etiqueta(self, pedido_id: str, user: UserResponse) -> Response:
        pedido_resp = self.operacao.pedidos.get_pedido(pedido_id, user)  # valida escopo
        if pedido_resp.tipo != "livro" or pedido_resp.status not in STATUS_ETIQUETA:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Etiqueta só para pedidos de livro pagos (aguardando envio, enviados ou entregues)")
        remetente = self.remetente()
        pedido = self.repo.get_pedido(pedido_resp.id)
        envio = self.repo.ultimos_envios([pedido["id"]]).get(pedido["id"])  # None = pré-envio (volume 1)
        conteudo = gerar_etiqueta(pedido, remetente, envio, self.operacao.peso_sugerido(pedido_resp))
        if envio and envio.get("id"):
            self.repo.marcar_etiqueta_gerada(envio["id"])
        return Response(
            content=conteudo,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{exp.nome_arquivo(f"etiqueta-{pedido["numero"]}", "pdf")}"'},
        )
