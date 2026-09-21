"""Geração de PDFs para o módulo administrativo (fpdf2)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF


class AdminPDF(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def _header(self, titulo: str) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, titulo, ln=True)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, f"Gerado em {datetime.now(timezone.utc).isoformat()}", ln=True)
        self.ln(5)

    def _tabela(self, headers: List[str], rows: List[List[Any]], col_widths: Optional[List[float]] = None) -> None:
        if col_widths is None:
            total = 190
            col_widths = [total / len(headers)] * len(headers)
        self.set_font("Helvetica", "B", 8)
        for h, w in zip(headers, col_widths):
            self.cell(w, 6, str(h), border=1)
        self.ln()
        self.set_font("Helvetica", "", 8)
        for row in rows:
            for cell, w in zip(row, col_widths):
                text = str(cell) if cell is not None else ""
                self.cell(w, 5, text[:50], border=1)
            self.ln()


def gerar_ranking_polos(
    itens: List[Dict[str, Any]],
    titulo: str = "Ranking de Polos por Licenças/Livros",
) -> bytes:
    pdf = AdminPDF()
    pdf.add_page()
    pdf._header(titulo)
    headers = ["Polo", "Licenças", "Livros", "Total Adquirido"]
    rows = [[i.get("polo_nome", "-"), str(i.get("total_licencas", 0)), str(i.get("total_livros", 0)), str(i.get("total_adquirido", 0))] for i in itens]
    pdf._tabela(headers, rows, col_widths=[80, 35, 35, 40])
    return pdf.output(dest="S").encode("latin-1") if isinstance(pdf.output(dest="S"), str) else pdf.output(dest="S")


def gerar_relatorio_vendas(
    vendas: List[Dict[str, Any]],
    titulo: str = "Relatório de Vendas",
) -> bytes:
    pdf = AdminPDF()
    pdf.add_page()
    pdf._header(titulo)
    headers = ["Venda ID", "Polo", "Escola", "Modalidade", "Valor", "Status", "Data"]
    rows = [[str(v.get("id", "-") or "-"), str(v.get("polo_nome") or "-"), str(v.get("escola_nome") or "-"), str(v.get("modalidade") or "-"), f"{float(v.get('valor', 0)):.2f}", str(v.get("status") or "-"), str(v.get("criado_em") or "-")] for v in vendas]
    pdf._tabela(headers, rows, col_widths=[25, 30, 30, 25, 25, 20, 35])
    return pdf.output()


def gerar_historico_aluno(
    aluno_id: str,
    notas: List[Dict[str, Any]],
    historico: List[Dict[str, Any]],
    titulo: str = "Histórico do Aluno",
) -> bytes:
    pdf = AdminPDF()
    pdf.add_page()
    pdf._header(f"{titulo} - {aluno_id}")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Notas das Avaliações", ln=True)
    pdf.ln(2)
    if notas:
        pdf._tabela(["Matéria", "Nota", "Tipo", "Semestre", "Ano"], [[n.get("materia_nome") or "-", str(n.get("nota") or "-"), str(n.get("tipo") or "-"), str(n.get("semestre") or "-"), str(n.get("ano") or "-")] for n in notas], col_widths=[60, 25, 30, 30, 25])
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Histórico Completo", ln=True)
    pdf.ln(2)
    if historico:
        pdf._tabela(["Descrição", "Tipo", "Semestre", "Ano", "Data"], [[h.get("descricao") or "-", str(h.get("tipo") or "-"), str(h.get("semestre") or "-"), str(h.get("ano") or "-"), str(h.get("criado_em") or "-")] for h in historico], col_widths=[60, 25, 25, 20, 40])
    return pdf.output()


def gerar_conversa_chat(
    conversa: Dict[str, Any],
    mensagens: List[Dict[str, Any]],
    titulo: str = "Conversa Particular",
) -> bytes:
    pdf = AdminPDF()
    pdf.add_page()
    pdf._header(f"{titulo} - {conversa.get('id', '-')}")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Participantes", ln=True)
    pdf.ln(2)
    participantes = conversa.get("participantes") or []
    if participantes:
        for p in participantes:
            nome = p.get("nome") if isinstance(p, dict) else str(p)
            perfil = p.get("perfil") if isinstance(p, dict) else "?"
            pdf.cell(0, 5, f"- {nome} ({perfil})", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Mensagens", ln=True)
    pdf.ln(2)
    if mensagens:
        pdf._tabela(["Remetente", "Conteúdo", "Data"], [[m.get("remetente_nome") or "-", str(m.get("conteudo") or "-")[:80], str(m.get("criado_em") or "-")] for m in mensagens], col_widths=[40, 110, 40])
    return pdf.output()
