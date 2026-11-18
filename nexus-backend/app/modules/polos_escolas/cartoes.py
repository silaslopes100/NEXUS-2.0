"""Cartões de acesso do aluno (número da licença) em PDF A4, 8 por página, para recortar e entregar."""
from __future__ import annotations

from typing import Any, Dict, List

from fpdf import FPDF

from app.modules.financeiro.exportacao import latin1, truncar

_LARGURA, _ALTURA = 92.0, 64.0
_MARGEM_X, _MARGEM_Y, _ESPACO = 10.0, 12.0, 6.0


def gerar_cartoes_acesso(cartoes: List[Dict[str, Any]]) -> bytes:
    """Cada cartão: nome do aluno, disciplina, número da licença em destaque e 3 passos simples."""
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    por_pagina = 8
    for i, cartao in enumerate(cartoes):
        if i % por_pagina == 0:
            pdf.add_page()
        pos = i % por_pagina
        x = _MARGEM_X + (pos % 2) * (_LARGURA + _ESPACO)
        y = _MARGEM_Y + (pos // 2) * (_ALTURA + _ESPACO)
        pdf.set_draw_color(150, 150, 150)
        pdf.set_line_width(0.2)
        pdf.dashed_line(x - 2, y - 2, x + _LARGURA + 2, y - 2, 1.5, 1.5)
        pdf.rect(x, y, _LARGURA, _ALTURA)

        pdf.set_fill_color(15, 23, 42)
        pdf.rect(x, y, _LARGURA, 9, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_xy(x + 3, y + 1.5)
        pdf.cell(_LARGURA - 6, 6, latin1("NEXUS 2.0 - Cartão de acesso à avaliação"))
        pdf.set_text_color(0, 0, 0)

        pdf.set_xy(x + 3, y + 11)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(_LARGURA - 6, 5, truncar(pdf, latin1(cartao["aluno_nome"]), _LARGURA - 6), new_x="LEFT", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(_LARGURA - 6, 4, truncar(pdf, latin1(f"Disciplina: {cartao['disciplina_nome']}"), _LARGURA - 6),
                 new_x="LEFT", new_y="NEXT")

        pdf.set_xy(x + 3, y + 23)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(_LARGURA - 6, 4, latin1("SEU NÚMERO DE ACESSO"), align="C", new_x="LEFT", new_y="NEXT")
        pdf.set_font("Courier", "B", 20)
        pdf.cell(_LARGURA - 6, 10, latin1(cartao["numero_licenca"]), align="C", new_x="LEFT", new_y="NEXT")

        pdf.set_xy(x + 4, y + 40)
        pdf.set_font("Helvetica", "", 7.5)
        passos = [
            "1. Abra o site do Nexus.",
            '2. Toque em "Entrar com número da licença".',
            "3. Digite o número acima e faça a sua avaliação.",
        ]
        for passo in passos:
            pdf.cell(_LARGURA - 8, 4.2, latin1(passo), new_x="LEFT", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(_LARGURA - 8, 4, latin1("Guarde este cartão. Não compartilhe o número com outras pessoas."))
        pdf.set_text_color(0, 0, 0)
    return bytes(pdf.output())
