"""Geração do boletim escolar em PDF (fpdf2) para a Central de Alunos."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fpdf import FPDF

from app.modules.alunos_gestao.schemas import AcademicoResponse, CursoAcademicoResponse

_SITUACAO_LABEL = {
    "aprovado": "Aprovado",
    "reprovado": "Reprovado",
    "cursando": "Cursando",
}

# (título, largura em mm, alinhamento) — soma = 190 mm (A4 com margens de 10 mm).
_COLUNAS = [
    ("Disciplina", 86, "L"),
    ("Semestre", 22, "C"),
    ("Nota", 22, "C"),
    ("Situação", 34, "L"),
    ("Progresso", 26, "C"),
]


def _latin1(texto: object) -> str:
    """Fontes core do fpdf2 só aceitam latin-1; troca o que estiver fora disso."""
    return str(texto).replace("—", "-").replace("–", "-").encode("latin-1", "replace").decode("latin-1")


def _truncar(pdf: FPDF, texto: str, largura: float) -> str:
    limite = largura - 3
    if pdf.get_string_width(texto) <= limite:
        return texto
    while texto and pdf.get_string_width(texto + "...") > limite:
        texto = texto[:-1]
    return texto + "..."


def _cabecalho_tabela(pdf: FPDF) -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(226, 232, 240)
    for titulo, largura, alinhamento in _COLUNAS:
        pdf.cell(largura, 8, _latin1(titulo), border=1, align=alinhamento, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)


def _secao_curso(pdf: FPDF, curso: CursoAcademicoResponse) -> None:
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, _latin1(f"Curso: {curso.nome}"), new_x="LMARGIN", new_y="NEXT")
    _cabecalho_tabela(pdf)

    if not curso.disciplinas:
        pdf.cell(sum(c[1] for c in _COLUNAS), 7, "Nenhuma disciplina registrada.", border=1)
        pdf.ln()

    for disciplina in curso.disciplinas:
        if pdf.get_y() + 7 > pdf.page_break_trigger:
            pdf.add_page()
            _cabecalho_tabela(pdf)
        valores = [
            disciplina.nome,
            disciplina.semestre if disciplina.semestre is not None else "-",
            f"{disciplina.nota:.1f}" if disciplina.nota is not None else "-",
            _SITUACAO_LABEL.get(disciplina.situacao, disciplina.situacao),
            f"{disciplina.progresso}%" if disciplina.progresso is not None else "-",
        ]
        for (_, largura, alinhamento), valor in zip(_COLUNAS, valores):
            pdf.cell(largura, 7, _truncar(pdf, _latin1(valor), largura), border=1, align=alinhamento)
        pdf.ln()
    pdf.ln(6)


def gerar_boletim_pdf(academico: AcademicoResponse, curso_id: Optional[str] = None) -> bytes:
    """Gera o boletim do aluno; com `curso_id`, apenas daquele curso."""
    cursos: List[CursoAcademicoResponse] = [
        curso for curso in academico.cursos if curso_id is None or curso.id == curso_id
    ]

    pdf = FPDF(format="A4")
    pdf.set_margins(10, 12, 10)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "NEXUS 2.0 - Boletim Escolar", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, _latin1(f"Aluno: {academico.aluno_nome}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0,
        7,
        _latin1(f"Matrícula: {academico.numero_matricula or 'não informada'}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        7,
        _latin1(f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    if not cursos:
        pdf.cell(0, 8, "Nenhuma disciplina registrada para este aluno.", new_x="LMARGIN", new_y="NEXT")
    for curso in cursos:
        _secao_curso(pdf, curso)

    return bytes(pdf.output())
