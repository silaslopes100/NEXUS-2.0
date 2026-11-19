"""Declaração de cumprimento de estágio (PDF gerado sob demanda, fpdf2)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fpdf import FPDF

from app.modules.financeiro.exportacao import latin1

_MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro"]


def _data_extenso(valor: Any) -> str:
    d = valor if isinstance(valor, datetime) else datetime.now()
    return f"{d.day} de {_MESES[d.month]} de {d.year}"


def gerar_comprovante(submissao: Dict[str, Any], etapa_titulo: str) -> bytes:
    aluno = submissao.get("aluno") or {}
    pdf = FPDF(orientation="P", format="A4")
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    largura = pdf.w - pdf.l_margin - pdf.r_margin

    # Moldura
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(0.8)
    pdf.rect(12, 12, pdf.w - 24, pdf.h - 24)
    pdf.set_line_width(0.2)
    pdf.rect(14, 14, pdf.w - 28, pdf.h - 28)

    pdf.set_y(32)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(largura, 6, latin1("ETADEMP - NEXUS 2.0"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(largura, 5, latin1("Central de Estágio"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(18)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 17)
    pdf.multi_cell(largura, 9, latin1("DECLARAÇÃO DE CUMPRIMENTO DE ESTÁGIO SUPERVISIONADO"), align="C",
                   new_x="LMARGIN", new_y="NEXT")

    pdf.ln(14)
    nome = aluno.get("nome") or "Aluno"
    identificacao = []
    if aluno.get("numero_matricula"):
        identificacao.append(f"matrícula {aluno['numero_matricula']}")
    if aluno.get("cpf"):
        identificacao.append(f"CPF {aluno['cpf']}")
    unidade = " / ".join(x for x in (aluno.get("polo_nome"), aluno.get("escola_nome")) if x)
    texto = (
        f"Declaramos, para os devidos fins, que {nome}"
        + (f", {', '.join(identificacao)}" if identificacao else "")
        + (f", vinculado(a) a {unidade}" if unidade else "")
        + f", cumpriu {submissao.get('horas') or 50} (cinquenta) horas de Estágio Supervisionado referentes "
        f"à disciplina {etapa_titulo}, tendo a documentação comprobatória (carta de apresentação, relatório "
        f"de estágio e registro fotográfico) sido analisada e APROVADA pela Coordenação de Estágio em "
        f"{_data_extenso(submissao.get('avaliado_em'))}."
    )
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(largura, 8, latin1(texto), align="J", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(28)
    pdf.set_draw_color(0, 0, 0)
    meio = pdf.w / 2
    pdf.line(meio - 45, pdf.get_y(), meio + 45, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(largura, 5, latin1("Coordenação de Estágio"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(largura, 5, latin1("ETADEMP"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.h - 42)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(90, 90, 90)
    codigo = submissao.get("codigo_comprovante") or "-"
    pdf.cell(largura, 4, latin1(f"Código de verificação: {codigo}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(largura, 4, latin1(f"Emitido em {datetime.now().strftime('%d/%m/%Y %H:%M')}"), align="C",
             new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
