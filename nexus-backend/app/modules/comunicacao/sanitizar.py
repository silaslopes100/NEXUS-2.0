"""Sanitização do HTML vindo do editor rico (allowlist, só biblioteca padrão).

Tudo que não está na allowlist é descartado: tags desconhecidas perdem a tag (o texto fica),
e o conteúdo de ``script``/``style``/``iframe``… é removido por inteiro. Atributos de evento,
``javascript:`` e CSS fora da lista nunca passam.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Dict, FrozenSet, List, Optional, Tuple

_TAGS_POST = frozenset({"p", "br", "strong", "b", "em", "i", "u", "s", "a", "ul", "ol", "li", "blockquote",
                        "h2", "h3", "span", "mark"})
_TAGS_AVISO = _TAGS_POST | frozenset({"h1", "h4", "hr"})

_VAZIAS = frozenset({"br", "hr"})
# Conteúdo removido junto com a tag.
_DESCARTAR_CONTEUDO = frozenset({"script", "style", "iframe", "object", "embed", "noscript", "template",
                                 "svg", "math", "head", "title", "textarea", "select", "button", "form"})
# Tags de bloco que aceitam alinhamento.
_BLOCOS = frozenset({"p", "h1", "h2", "h3", "h4", "li", "blockquote"})

_COR = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-z]{3,20}|rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*(0|1|0?\.\d+)\s*)?\))$")
_TAMANHO = re.compile(r"^(\d{1,2}(\.\d)?)(px|pt|rem|em)$")
_ALINHAMENTOS = frozenset({"left", "right", "center", "justify"})
_URL_OK = re.compile(r"^(https?://|mailto:|/)", re.I)


def _estilo(valor: str, tag: str) -> str:
    """Mantém só color, background-color (realce), font-size e text-align com valores seguros."""
    saida: List[str] = []
    for decl in (valor or "").split(";"):
        if ":" not in decl:
            continue
        prop, val = (p.strip().lower() for p in decl.split(":", 1))
        if prop in {"color", "background-color"} and _COR.fullmatch(val):
            saida.append(f"{prop}: {val}")
        elif prop == "font-size":
            m = _TAMANHO.fullmatch(val)
            if m and 8 <= float(m.group(1)) * (16 if m.group(3) in {"rem", "em"} else 1) <= 72:
                saida.append(f"font-size: {val}")
        elif prop == "text-align" and val in _ALINHAMENTOS and tag in _BLOCOS:
            saida.append(f"text-align: {val}")
    return "; ".join(saida)


def _href(valor: str) -> Optional[str]:
    url = (valor or "").strip()
    # Remove caracteres de controle/espaços que navegadores ignoram (ex.: "java\tscript:").
    compacto = re.sub(r"[\x00-\x20]", "", url)
    if not _URL_OK.match(compacto) or compacto.startswith("//"):
        return None
    return url[:2000]


class _Sanitizador(HTMLParser):
    def __init__(self, permitidas: FrozenSet[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.permitidas = permitidas
        self.saida: List[str] = []
        self.abertas: List[str] = []
        self.descartando = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in _DESCARTAR_CONTEUDO:
            if tag not in _VAZIAS:
                self.descartando += 1
            return
        if self.descartando or tag not in self.permitidas:
            return
        atributos: Dict[str, str] = {}
        for nome, valor in attrs:
            nome = (nome or "").lower()
            if nome == "style":
                estilo = _estilo(valor or "", tag)
                if estilo:
                    atributos["style"] = estilo
            elif nome == "href" and tag == "a":
                href = _href(valor or "")
                if href:
                    atributos["href"] = href
        if tag == "a":
            if "href" not in atributos:
                return  # link sem destino válido: fica só o texto
            atributos["target"] = "_blank"
            atributos["rel"] = "noopener noreferrer nofollow"
        attrs_txt = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in atributos.items())
        if tag in _VAZIAS:
            self.saida.append(f"<{tag}{attrs_txt}>")
            return
        self.saida.append(f"<{tag}{attrs_txt}>")
        self.abertas.append(tag)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() in _VAZIAS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _DESCARTAR_CONTEUDO:
            if self.descartando:
                self.descartando -= 1
            return
        if self.descartando or tag in _VAZIAS or tag not in self.abertas:
            return
        # Fecha também as que ficaram abertas dentro (HTML malformado).
        while self.abertas:
            aberta = self.abertas.pop()
            self.saida.append(f"</{aberta}>")
            if aberta == tag:
                break

    def handle_data(self, data: str) -> None:
        if not self.descartando:
            self.saida.append(html.escape(data, quote=False))

    def resultado(self) -> str:
        while self.abertas:
            self.saida.append(f"</{self.abertas.pop()}>")
        return "".join(self.saida)


def sanitizar_html(conteudo: Optional[str], *, variante: str = "post") -> str:
    """HTML seguro para gravar e renderizar. ``variante``: 'post' (feed) ou 'aviso' (pop-up)."""
    if not conteudo:
        return ""
    parser = _Sanitizador(_TAGS_AVISO if variante == "aviso" else _TAGS_POST)
    parser.feed(conteudo)
    parser.close()
    limpo = parser.resultado().strip()
    # Editor vazio costuma mandar "<p></p>".
    return "" if not texto_do_html(limpo) else limpo


class _Texto(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: List[str] = []

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "blockquote"}:
            self.partes.append("\n")

    def handle_data(self, data):  # noqa: ANN001
        self.partes.append(data)


def texto_do_html(conteudo: Optional[str]) -> str:
    """Texto puro (para busca, prévia e notificações)."""
    if not conteudo:
        return ""
    p = _Texto()
    p.feed(conteudo)
    p.close()
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", "".join(p.partes))).strip()
