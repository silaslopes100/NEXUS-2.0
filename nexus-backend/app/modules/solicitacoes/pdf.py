"""PDF da Nota de Prestação de Contas (Polo → Escola)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict

from app.modules.financeiro.exportacao import RelatorioPDF, latin1


def _moeda(v: Any) -> str:
    return f"R$ {float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data(v: Any) -> str:
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, str) and len(v) >= 10:
        return f"{v[8:10]}/{v[5:7]}/{v[:4]}"
    return "-"


def _endereco(u: Dict[str, Any]) -> str:
    partes = [", ".join(p for p in (u.get("logradouro"), u.get("numero")) if p), u.get("complemento"), u.get("bairro"),
              " / ".join(p for p in (u.get("cidade"), u.get("uf")) if p),
              f"CEP {u['cep']}" if u.get("cep") else None]
    return " - ".join(p for p in partes if p) or "-"


def gerar_nota_prestacao(s: Dict[str, Any], nota: Dict[str, Any], polo: Dict[str, Any], escola: Dict[str, Any]) -> bytes:
    pdf = RelatorioPDF("Nota de Prestação de Contas", f"Nota {nota.get('numero', '-')} - Solicitação {s.get('numero', '-')}")
    pdf.add_page()

    pdf.secao("Polo (credor)")
    pdf.pares([("Polo", polo.get("razao_social") or polo.get("nome") or "-"),
               ("Documento", polo.get("documento_fiscal") or "-")])
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, latin1(f"Endereço: {_endereco(polo)}"), new_x="LMARGIN", new_y="NEXT")
    if polo.get("email_financeiro") or polo.get("telefone_financeiro"):
        pdf.multi_cell(0, 5, latin1(f"Financeiro: {polo.get('email_financeiro') or ''} {polo.get('telefone_financeiro') or ''}"),
                       new_x="LMARGIN", new_y="NEXT")

    pdf.secao("Escola (devedora)")
    pdf.pares([("Escola", escola.get("nome") or "-"), ("Solicitação", s.get("numero") or "-")])
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, latin1(f"Endereço: {_endereco(escola)}"), new_x="LMARGIN", new_y="NEXT")

    pdf.secao("Itens entregues (licença + livro por disciplina)")
    linhas, total = [], 0.0
    for i in s.get("itens", []):
        qtd = int(i.get("quantidade_atendida") or 0)
        if not qtd:
            continue
        subtotal = qtd * float(i.get("valor_unitario") or 0)
        total += subtotal
        linhas.append([i.get("disciplina_nome") or "-", i.get("quantidade"), qtd, i.get("valor_unitario"), subtotal])
    pdf.tabela(
        [("Disciplina", 80, "L", "texto"), ("Pedido", 18, "R", "int"), ("Entregue", 20, "R", "int"),
         ("Valor unit.", 30, "R", "moeda"), ("Subtotal", 32, "R", "moeda")],
        linhas, totais=["Total", None, None, None, total],
    )

    pdf.secao("Pagamento")
    pdf.pares([("Valor total", _moeda(nota.get("valor_total", total))), ("Vencimento", _data(nota.get("vencimento"))),
               ("Emissão", _data(nota.get("criado_em"))),
               ("Situação", "Repasse recebido" if nota.get("status") == "repasse_recebido" else "Aguardando repasse")])
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 6, latin1("Repasse o valor total ao Polo até o vencimento. Após o recebimento, o Polo confirma "
                                "o repasse no NEXUS e esta Nota fica quitada."), new_x="LMARGIN", new_y="NEXT")
    if s.get("observacao"):
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, latin1(f"Observação da Escola: {s['observacao']}"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(14)
    meia = pdf.largura_util / 2
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(meia - 6, 5, latin1("_" * 40), align="C")
    pdf.cell(meia, 5, latin1("_" * 40), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(meia - 6, 5, latin1("Polo"), align="C")
    pdf.cell(meia, 5, latin1("Escola"), align="C", new_x="LMARGIN", new_y="NEXT")
    return pdf.bytes()
