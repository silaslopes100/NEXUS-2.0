"""Certificado de conclusão de treinamento (PDF gerado sob demanda, fpdf2)."""
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


def gerar_certificado(*, nome: str, treinamento: str, categoria: str, carga_horaria: Any, concluido_em: Any,
                      codigo: str, url_validacao: str) -> bytes:
    pdf = FPDF(orientation="L", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(30, 20, 30)
    pdf.add_page()
    largura = pdf.w - 60

    # Moldura dupla (azul + dourado)
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, pdf.w, 16, style="F")
    pdf.rect(0, pdf.h - 16, pdf.w, 16, style="F")
    pdf.set_draw_color(255, 184, 0)
    pdf.set_line_width(1.2)
    pdf.rect(10, 22, pdf.w - 20, pdf.h - 44)
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(0.3)
    pdf.rect(13, 25, pdf.w - 26, pdf.h - 50)

    pdf.set_y(36)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(largura, 6, latin1("ETADEMP - NEXUS 2.0"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 34)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(largura, 14, latin1("CERTIFICADO"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(largura, 7, latin1(f"de conclusão de {categoria.lower()}"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(largura, 7, latin1("Certificamos que"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(30, 58, 138)
    pdf.multi_cell(largura, 11, latin1(nome), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    carga = f", com carga horária de {carga_horaria} hora(s)" if carga_horaria else ""
    artigo = "a" if categoria.lower().startswith("capacita") else "o"
    texto = (f"concluiu {artigo} {categoria.lower()} \"{treinamento}\"{carga}, "
             f"em {_data_extenso(concluido_em)}, na plataforma NEXUS 2.0.")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(largura, 8, latin1(texto), align="C", new_x="LMARGIN", new_y="NEXT")

    # Assinatura
    y = pdf.h - 62
    meio = pdf.w / 2
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    pdf.line(meio - 50, y, meio + 50, y)
    pdf.set_xy(30, y + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(largura, 5, latin1("Coordenação Pedagógica"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(largura, 5, latin1("ETADEMP"), align="C", new_x="LMARGIN", new_y="NEXT")

    # Validação
    pdf.set_y(pdf.h - 38)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(largura, 4, latin1(f"Código de validação: {codigo}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(largura, 4, latin1(f"Confira a autenticidade em {url_validacao}"), align="C", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
