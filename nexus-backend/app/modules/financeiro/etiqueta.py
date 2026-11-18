"""Etiqueta de envio 10×15 cm gerada pelo próprio Nexus (Fase 4).

Página por volume (destinatário em destaque, remetente, código de barras do pedido)
+ página final de declaração de conteúdo simplificada.

O fpdf2 instalado (2.8.x) não tem Code128; o código de barras é desenhado aqui
(Code128 conjunto B: letras, dígitos e hífen do número "PED-AAAA-NNNNNN").
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from app.modules.financeiro.exportacao import brl, latin1, truncar

# Larguras (barra, espaço, barra, ...) de cada símbolo Code128, índices 0..105; 106 = STOP.
CODE128_PADROES: List[str] = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
]
START_B = 104
STOP = 106


def code128b_simbolos(texto: str) -> List[int]:
    """START B + dados + dígito verificador (módulo 103) + STOP."""
    if not texto or any(not 32 <= ord(c) <= 126 for c in texto):
        raise ValueError("Code128 B aceita apenas ASCII imprimível")
    dados = [ord(c) - 32 for c in texto]
    soma = START_B + sum(valor * peso for peso, valor in enumerate(dados, start=1))
    return [START_B, *dados, soma % 103, STOP]


def desenhar_code128(pdf: FPDF, texto: str, x: float, y: float, largura: float, altura: float) -> None:
    """Desenha o Code128 B ocupando `largura` mm (zona de silêncio de 10 módulos de cada lado)."""
    simbolos = code128b_simbolos(texto)
    modulos = sum(sum(int(d) for d in CODE128_PADROES[s]) for s in simbolos) + 20
    passo = largura / modulos
    cursor = x + 10 * passo
    pdf.set_fill_color(0, 0, 0)
    for simbolo in simbolos:
        for i, digito in enumerate(CODE128_PADROES[simbolo]):
            w = int(digito) * passo
            if i % 2 == 0:  # posições pares = barras
                pdf.rect(cursor, y, w, altura, style="F")
            cursor += w


def _linhas_endereco(e: Dict[str, Any]) -> List[str]:
    linha1 = ", ".join(p for p in [e.get("logradouro"), e.get("numero")] if p)
    if e.get("complemento"):
        linha1 += f" - {e['complemento']}"
    cidade = "/".join(p for p in [e.get("cidade"), e.get("uf")] if p)
    linha2 = " - ".join(p for p in [e.get("bairro"), cidade] if p)
    return [l for l in (linha1, linha2) if l]


def _cep(valor: Optional[str]) -> str:
    digitos = "".join(c for c in str(valor or "") if c.isdigit())
    return f"{digitos[:5]}-{digitos[5:]}" if len(digitos) == 8 else (valor or "-")


def gerar_etiqueta(pedido: Dict[str, Any], remetente: Dict[str, Any], envio: Optional[Dict[str, Any]],
                   peso_sugerido: Optional[int] = None, destinatario: Optional[Dict[str, Any]] = None) -> bytes:
    """PDF 100×150 mm: uma página por volume + declaração de conteúdo.

    `destinatario` é o endereço cadastrado no Polo (regra do negócio); sem ele, usa o snapshot do pedido.
    """
    envio = envio or {}
    volumes = max(int(envio.get("volumes") or 1), 1)
    peso = envio.get("peso_total_g") or peso_sugerido
    destino = destinatario or {k[len("entrega_"):]: v for k, v in pedido.items() if k.startswith("entrega_")}
    numero = str(pedido.get("numero") or pedido.get("id"))

    pdf = FPDF(unit="mm", format=(100, 150))
    pdf.set_margins(5, 5, 5)
    pdf.set_auto_page_break(auto=False)
    largura = 90

    for volume in range(1, volumes + 1):
        pdf.add_page()
        # Faixa superior
        pdf.set_fill_color(15, 23, 42)
        pdf.rect(5, 5, largura, 9, style="F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_xy(7, 6.5)
        pdf.cell(40, 6, "NEXUS 2.0")
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(46, 6, latin1(f"Pedido {numero}"), align="R")
        pdf.set_text_color(0, 0, 0)

        # Destinatário
        pdf.set_xy(5, 17)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(largura, 4, latin1("DESTINATÁRIO"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(largura, 7, truncar(pdf, latin1(destino.get("nome") or pedido.get("polo_nome") or "-"), largura),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for linha in _linhas_endereco(destino):
            pdf.multi_cell(largura, 5, latin1(linha), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(largura, 9, latin1(f"CEP {_cep(destino.get('cep'))}"), new_x="LMARGIN", new_y="NEXT")
        if destino.get("telefone"):
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(largura, 5, latin1(f"Tel.: {destino['telefone']}"), new_x="LMARGIN", new_y="NEXT")

        # Código de barras do pedido
        y_barras = 82
        desenhar_code128(pdf, numero, 5, y_barras, largura, 16)
        pdf.set_xy(5, y_barras + 17)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(largura, 4, latin1(numero), align="C")

        # Envio
        pdf.set_xy(5, 104)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(largura / 2, 5, latin1(f"Volume {volume}/{volumes}"))
        pdf.cell(largura / 2, 5, latin1(f"Peso: {peso} g" if peso else "Peso: -"), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        transporte = envio.get("transportadora") or "Transportadora a definir"
        rastreio = f" - rastreio {envio['codigo_rastreio']}" if envio.get("codigo_rastreio") else ""
        pdf.cell(largura, 5, truncar(pdf, latin1(f"{transporte}{rastreio}"), largura), new_x="LMARGIN", new_y="NEXT")

        # Remetente
        pdf.line(5, 117, 95, 117)
        pdf.set_xy(5, 119)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(largura, 4, "REMETENTE", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(largura, 4.5, truncar(pdf, latin1(remetente.get("nome") or "-"), largura), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        for linha in _linhas_endereco(remetente):
            pdf.cell(largura, 4, truncar(pdf, latin1(linha), largura), new_x="LMARGIN", new_y="NEXT")
        extras = [f"CEP {_cep(remetente.get('cep'))}"]
        if remetente.get("telefone"):
            extras.append(f"Tel. {remetente['telefone']}")
        if remetente.get("documento"):
            extras.append(f"CPF/CNPJ {remetente['documento']}")
        pdf.cell(largura, 4, truncar(pdf, latin1(" - ".join(extras)), largura))

    # Declaração de conteúdo simplificada
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(largura, 7, latin1("DECLARAÇÃO DE CONTEÚDO"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(largura, 5, latin1(f"Pedido {numero} - {datetime.now().strftime('%d/%m/%Y')}"), align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(72, 6, "Item", border=1, fill=True)
    pdf.cell(18, 6, "Qtd.", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    itens = pedido.get("itens") or []
    for item in itens:
        if pdf.get_y() > 115:  # cabe ~14 itens; o total abaixo continua considerando todos
            pdf.cell(largura, 6, latin1("... (demais itens no pedido)"), border=1, new_x="LMARGIN", new_y="NEXT")
            break
        pdf.cell(72, 6, truncar(pdf, latin1(item.get("descricao") or "Item"), 72), border=1)
        pdf.cell(18, 6, str(int(item.get("quantidade") or 0)), border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    total_itens = sum(int(i.get("quantidade") or 0) for i in itens)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(72, 6, latin1(f"Total ({brl(pedido.get('valor_total'))})"), border=1)
    pdf.cell(18, 6, str(total_itens), border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(5, 125)
    pdf.set_font("Helvetica", "", 7)
    pdf.multi_cell(largura, 3.5, latin1("Declaro que o conteúdo desta remessa corresponde aos itens acima."),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.line(15, pdf.get_y(), 85, pdf.get_y())
    pdf.ln(1)
    pdf.cell(largura, 4, latin1(f"Assinatura - {remetente.get('nome') or 'Remetente'}"), align="C")
    return bytes(pdf.output())
