"""Geração de PDFs (boletos, históricos, relatórios) do módulo `polos_escolas` usando fpdf2."""
from __future__ import annotations

from typing import Any, Dict

from fpdf import FPDF

from app.modules.polos_escolas.schemas import RelatorioDrilldownResponse


def _novo_pdf(titulo: str) -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, titulo, ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)
    return pdf


def gerar_boleto_pdf(boleto: Dict[str, Any]) -> bytes:
    """Gera a 2ª via do boleto em PDF."""
    pdf = _novo_pdf("NEXUS 2.0 — 2ª Via de Boleto")
    pdf.cell(0, 8, f"Boleto: {boleto.get('id')}", ln=True)
    pdf.cell(0, 8, f"Polo: {boleto.get('polo_id')}", ln=True)
    pdf.cell(0, 8, f"Valor: R$ {boleto.get('valor')}", ln=True)
    pdf.cell(0, 8, f"Vencimento: {boleto.get('data_vencimento')}", ln=True)
    pdf.cell(0, 8, f"Status: {boleto.get('status')}", ln=True)
    return bytes(pdf.output())


def gerar_historico_aluno_pdf(aluno: Dict[str, Any], notas: list[Dict[str, Any]]) -> bytes:
    """Gera o histórico escolar do aluno em PDF."""
    pdf = _novo_pdf("NEXUS 2.0 — Histórico do Aluno")
    pdf.cell(0, 8, f"Aluno: {aluno.get('nome', '')} {aluno.get('sobrenome', '')}", ln=True)
    pdf.cell(0, 8, f"CPF: {aluno.get('cpf', '')}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 8, "Matéria", border=1)
    pdf.cell(40, 8, "Nota", border=1, ln=True)
    pdf.set_font("Helvetica", "", 11)
    for nota in notas:
        pdf.cell(60, 8, str(nota.get("materia_id", "")), border=1)
        pdf.cell(40, 8, str(nota.get("valor", "")), border=1, ln=True)
    return bytes(pdf.output())


def gerar_relatorio_drilldown_pdf(relatorio: RelatorioDrilldownResponse) -> bytes:
    """Gera o relatório dinâmico hierárquico (Nível/Campo/Descrição/Fórmula) em PDF."""
    pdf = _novo_pdf("NEXUS 2.0 — Relatório Hierárquico de Licenças")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(25, 8, "Nível", border=1)
    pdf.cell(55, 8, "Campo", border=1)
    pdf.cell(75, 8, "Descrição", border=1)
    pdf.cell(30, 8, "Fórmula", border=1, ln=True)
    pdf.set_font("Helvetica", "", 9)
    for linha in relatorio.linhas:
        pdf.cell(25, 7, linha.nivel, border=1)
        pdf.cell(55, 7, linha.campo[:35], border=1)
        pdf.cell(75, 7, linha.descricao[:48], border=1)
        pdf.cell(30, 7, linha.formula[:18], border=1, ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, f"Total vendidas por escola: {relatorio.totais.total_vendidas_por_escola}", ln=True)
    pdf.cell(0, 8, f"Total não vendidas por escola: {relatorio.totais.total_nao_vendidas_por_escola}", ln=True)
    pdf.cell(0, 8, f"Total não vendidas por polo: {relatorio.totais.total_nao_vendidas_por_polo}", ln=True)
    return bytes(pdf.output())
