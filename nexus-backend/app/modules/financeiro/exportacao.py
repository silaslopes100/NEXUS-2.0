"""Exportação dos relatórios do módulo 2.4 em PDF (fpdf2) e XLSX (openpyxl) — Fase 4.

PDF usa fontes core (Helvetica/latin-1): sem TTF embutida, leve para o ambiente serverless.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, Response, status
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.modules.financeiro.schemas import FiltrosPeriodo

# Teto de linhas por arquivo: a resposta de função na Vercel é limitada (~4,5 MB).
MAX_LINHAS_EXPORT = 5000

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
          "Setembro", "Outubro", "Novembro", "Dezembro"]

# (rótulo, largura em mm no PDF, alinhamento, formato: "texto" | "moeda" | "data" | "datahora" | "int")
Coluna = Tuple[str, float, str, str]


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------

def latin1(texto: object) -> str:
    """Fontes core do fpdf2 só aceitam latin-1 (acentos pt-BR estão incluídos)."""
    return (str(texto).replace("—", "-").replace("–", "-").replace("·", "-")
            .replace("×", "x").encode("latin-1", "replace").decode("latin-1"))


def truncar(pdf: FPDF, texto: str, largura: float) -> str:
    limite = largura - 2
    if pdf.get_string_width(texto) <= limite:
        return texto
    while texto and pdf.get_string_width(texto + "...") > limite:
        texto = texto[:-1]
    return texto + "..."


def brl(valor: Any) -> str:
    numero = float(valor or 0)
    inteiro, centavos = f"{numero:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _como_data(valor: Any) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        try:
            return datetime.fromisoformat(valor.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _como_datahora(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, str) and valor:
        try:
            return datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def formatar(valor: Any, formato: str) -> str:
    if valor is None or valor == "":
        return "-"
    if formato == "moeda":
        return brl(valor)
    if formato == "data":
        d = _como_data(valor)
        return d.strftime("%d/%m/%Y") if d else str(valor)
    if formato == "datahora":
        d = _como_datahora(valor)
        return d.strftime("%d/%m/%Y %H:%M") if d else str(valor)
    return str(valor)


def descrever_filtros(filtros: FiltrosPeriodo, nomes: Optional[Dict[str, str]] = None) -> str:
    """Texto curto dos filtros aplicados (cabeçalho do PDF e aba Filtros do XLSX)."""
    nomes = nomes or {}
    partes: List[str] = []
    if filtros.data_inicio or filtros.data_fim:
        ini = filtros.data_inicio.strftime("%d/%m/%Y") if filtros.data_inicio else "início"
        fim = filtros.data_fim.strftime("%d/%m/%Y") if filtros.data_fim else "hoje"
        partes.append(f"Período: {ini} a {fim}")
    if filtros.mes:
        partes.append(f"Mês: {_MESES[filtros.mes]}")
    if filtros.semestre:
        partes.append(f"{filtros.semestre}º semestre")
    if filtros.ano:
        partes.append(f"Ano: {filtros.ano}")
    if filtros.polo_id:
        partes.append(f"Polo: {nomes.get('polo') or filtros.polo_id}")
    if filtros.escola_id:
        partes.append(f"Escola: {nomes.get('escola') or filtros.escola_id}")
    for campo, rotulo in (("tipo", "Tipo"), ("status", "Status"), ("gateway", "Gateway"), ("meio", "Meio")):
        valor = getattr(filtros, campo)
        if valor:
            partes.append(f"{rotulo}: {valor}")
    return " | ".join(partes) or "Sem filtros (todos os registros)"


def nome_arquivo(base: str, formato: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9_-]", "_", base).strip("_") or "relatorio"
    return f"{seguro}-{datetime.now().strftime('%Y%m%d-%H%M')}.{formato}"


def resposta_arquivo(conteudo: bytes, base: str, formato: str) -> Response:
    return Response(
        content=conteudo,
        media_type=MEDIA_TYPES[formato],
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo(base, formato)}"'},
    )


def garantir_limite(total: int) -> None:
    if total > MAX_LINHAS_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A exportação tem {total} registros (máximo {MAX_LINHAS_EXPORT}). Refine os filtros.",
        )


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

class RelatorioPDF(FPDF):
    """A4 com cabeçalho (título, filtros, emissão) e rodapé com paginação."""

    def __init__(self, titulo: str, filtros_txt: str, paisagem: bool = False) -> None:
        super().__init__(orientation="L" if paisagem else "P", format="A4")
        self.titulo = titulo
        self.filtros_txt = filtros_txt
        self.emitido = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=14)
        self.alias_nb_pages()

    def header(self) -> None:
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 7, latin1(f"NEXUS 2.0 - {self.titulo}"), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(90, 90, 90)
        self.multi_cell(0, 4, latin1(f"Filtros: {self.filtros_txt}"), new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, latin1(f"Emitido em {self.emitido}"), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-10)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, latin1(f"Página {self.page_no()}/{{nb}}"), align="R")
        self.set_text_color(0, 0, 0)

    @property
    def largura_util(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def secao(self, texto: str) -> None:
        if self.get_y() > self.page_break_trigger - 20:
            self.add_page()
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, latin1(texto), new_x="LMARGIN", new_y="NEXT")

    def pares(self, itens: Sequence[Tuple[str, str]]) -> None:
        """Bloco de indicadores em duas colunas (rótulo: valor)."""
        metade = self.largura_util / 2
        for i in range(0, len(itens), 2):
            for rotulo, valor in itens[i:i + 2]:
                self.set_font("Helvetica", "", 9)
                self.cell(metade * 0.55, 6, latin1(rotulo))
                self.set_font("Helvetica", "B", 9)
                self.cell(metade * 0.45, 6, latin1(valor))
            self.ln()

    def tabela(self, colunas: Sequence[Coluna], linhas: Sequence[Sequence[Any]],
               totais: Optional[Sequence[Any]] = None) -> None:
        escala = self.largura_util / sum(c[1] for c in colunas)
        larguras = [c[1] * escala for c in colunas]

        def cabecalho() -> None:
            self.set_font("Helvetica", "B", 8)
            self.set_fill_color(226, 232, 240)
            for (rotulo, _, alinhamento, _), largura in zip(colunas, larguras):
                self.cell(largura, 6, truncar(self, latin1(rotulo), largura), border=1, align=alinhamento, fill=True)
            self.ln()
            self.set_font("Helvetica", "", 8)

        cabecalho()
        if not linhas:
            self.cell(sum(larguras), 6, latin1("Nenhum registro encontrado."), border=1)
            self.ln()
        for linha in linhas:
            if self.get_y() + 6 > self.page_break_trigger:
                self.add_page()
                cabecalho()
            for (_, _, alinhamento, formato), largura, valor in zip(colunas, larguras, linha):
                self.cell(largura, 6, truncar(self, latin1(formatar(valor, formato)), largura), border=1, align=alinhamento)
            self.ln()
        if totais:
            self.set_font("Helvetica", "B", 8)
            for (_, _, alinhamento, formato), largura, valor in zip(colunas, larguras, totais):
                texto = "" if valor is None else formatar(valor, formato)
                self.cell(largura, 6, truncar(self, latin1(texto), largura), border=1, align=alinhamento)
            self.ln()

    def bytes(self) -> bytes:
        return bytes(self.output())


# ---------------------------------------------------------------------------
# XLSX
# ---------------------------------------------------------------------------

_FORMATO_XLSX = {"moeda": 'R$ #,##0.00', "data": "DD/MM/YYYY", "datahora": "DD/MM/YYYY HH:MM", "int": "0"}


def _valor_xlsx(valor: Any, formato: str) -> Any:
    if valor is None or valor == "":
        return None
    if formato == "moeda":
        return float(valor)
    if formato == "int":
        return int(valor)
    if formato == "data":
        return _como_data(valor)
    if formato == "datahora":
        d = _como_datahora(valor)
        return d.replace(tzinfo=None) if d else None  # Excel não guarda fuso
    return str(valor)


def planilha_xlsx(abas: Sequence[Tuple[str, Sequence[Coluna], Sequence[Sequence[Any]]]], filtros_txt: str) -> bytes:
    """Uma aba por tabela + aba "Filtros". Cabeçalho congelado, formatos de moeda/data e larguras ajustadas."""
    wb = Workbook()
    wb.remove(wb.active)
    negrito = Font(bold=True)
    fundo = PatternFill("solid", fgColor="E2E8F0")
    for nome, colunas, linhas in abas:
        ws = wb.create_sheet(title=nome[:31])
        ws.append([c[0] for c in colunas])
        for celula in ws[1]:
            celula.font = negrito
            celula.fill = fundo
            celula.alignment = Alignment(vertical="center")
        for linha in linhas:
            ws.append([_valor_xlsx(v, c[3]) for c, v in zip(colunas, linha)])
        for idx, coluna in enumerate(colunas, start=1):
            letra = get_column_letter(idx)
            if coluna[3] in _FORMATO_XLSX:
                for (celula,) in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                    celula.number_format = _FORMATO_XLSX[coluna[3]]
            maior = max([len(str(coluna[0]))] + [len(formatar(l[idx - 1], coluna[3])) for l in linhas[:500]])
            ws.column_dimensions[letra].width = min(max(10, maior + 2), 60)
        ws.freeze_panes = "A2"
    info = wb.create_sheet(title="Filtros")
    info.append(["Filtros aplicados", filtros_txt])
    info.append(["Emitido em", datetime.now().strftime("%d/%m/%Y %H:%M")])
    info["A1"].font = negrito
    info["A2"].font = negrito
    info.column_dimensions["A"].width = 20
    info.column_dimensions["B"].width = 100
    saida = BytesIO()
    wb.save(saida)
    return saida.getvalue()
