"""Exportação de conversa do chat em PDF (Admin)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.modules.chat.schemas import ConversaDetalheOut
from app.modules.financeiro.exportacao import RelatorioPDF, latin1


def _quando(v: Any) -> str:
    if isinstance(v, datetime):
        return v.astimezone().strftime("%d/%m/%Y %H:%M")
    return str(v or "-")


def gerar_pdf_conversa(conversa: ConversaDetalheOut, mensagens: List[Dict[str, Any]]) -> bytes:
    tipo = "Grupo" if conversa.tipo == "grupo" else "Individual"
    pdf = RelatorioPDF("Exportação de Conversa", f"{tipo}: {conversa.titulo} - {len(mensagens)} mensagem(ns)")
    pdf.add_page()

    pdf.secao("Participantes")
    pdf.set_font("Helvetica", "", 9)
    for m in conversa.membros:
        pdf.multi_cell(0, 5, latin1(f"- {m.nome} ({m.perfil or '-'}){' - moderador' if m.papel == 'moderador' else ''}"),
                       new_x="LMARGIN", new_y="NEXT")
    pdf.pares([("Situação", "Encerrada" if conversa.status == "encerrada" else "Ativa"),
               ("Criada em", _quando(conversa.criado_em))])

    pdf.secao("Mensagens")
    if not mensagens:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, latin1("Nenhuma mensagem no período de retenção (48h ativas + 90 dias de histórico)."),
                 new_x="LMARGIN", new_y="NEXT")
    for msg in mensagens:
        if pdf.get_y() > pdf.page_break_trigger - 15:
            pdf.add_page()
        if msg.get("tipo") == "sistema":
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(110, 110, 110)
            pdf.multi_cell(0, 5, latin1(f"[{_quando(msg.get('criado_em'))}] {msg.get('texto') or ''}"),
                           new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            continue
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, latin1(f"{msg.get('remetente_nome') or 'Usuário removido'} - {_quando(msg.get('criado_em'))}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        if msg.get("texto"):
            pdf.multi_cell(0, 5, latin1(msg["texto"]), new_x="LMARGIN", new_y="NEXT")
        if msg.get("anexo_nome"):
            pdf.set_text_color(40, 80, 160)
            pdf.multi_cell(0, 5, latin1(f"Anexo: {msg['anexo_nome']} ({msg.get('anexo_mime') or '-'}) "
                                        f"{msg.get('anexo_url') or ''}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(1)
    return pdf.bytes()
