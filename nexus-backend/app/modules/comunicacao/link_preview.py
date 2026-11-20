"""Prévia de links externos (miniatura estilo LinkedIn).

YouTube e Vimeo viram embed (id + miniatura) sem nenhuma requisição. Os demais links são lidos
no servidor (Open Graph / <title> / meta description) com proteção contra SSRF: só http(s),
portas 80/443, DNS resolvido e bloqueado para IPs privados, loopback, link-local etc. — checado
de novo a cada redirect. Lê no máximo 512 KB de HTML.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from html.parser import HTMLParser
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

_MAX_BYTES = 512 * 1024
_MAX_REDIRECTS = 3
_TIMEOUT = httpx.Timeout(5.0, connect=3.0)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NexusLinkPreview/1.0)",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.6",
}

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_VIMEO_ID = re.compile(r"^\d{6,12}$")


def normalizar_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe um link.")
    if "://" not in url:
        url = f"https://{url}"
    alvo = urlparse(url)
    if alvo.scheme not in {"http", "https"} or not alvo.hostname or len(url) > 2000:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Link inválido.")
    return url


def detectar_embed(url: str) -> Optional[Dict[str, str]]:
    """{'embed_tipo': 'youtube'|'vimeo', 'embed_id': ...} quando o link é de vídeo."""
    alvo = urlparse(url)
    host = (alvo.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        vid = alvo.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "youtube-nocookie.com", "music.youtube.com"}:
        if alvo.path == "/watch":
            vid = (parse_qs(alvo.query).get("v") or [""])[0]
        else:
            partes = [p for p in alvo.path.split("/") if p]
            vid = partes[1] if len(partes) >= 2 and partes[0] in {"embed", "shorts", "live", "v"} else ""
    elif host in {"vimeo.com", "player.vimeo.com"}:
        partes = [p for p in alvo.path.split("/") if p]
        vid = next((p for p in partes if _VIMEO_ID.fullmatch(p)), "")
        return {"embed_tipo": "vimeo", "embed_id": vid} if vid else None
    else:
        return None
    return {"embed_tipo": "youtube", "embed_id": vid} if _YOUTUBE_ID.fullmatch(vid or "") else None


def _dominio(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


async def _exigir_destino_publico(url: str) -> None:
    alvo = urlparse(url)
    if alvo.scheme not in {"http", "https"} or not alvo.hostname:
        raise ValueError("esquema não permitido")
    porta = alvo.port or (443 if alvo.scheme == "https" else 80)
    if porta not in {80, 443}:
        raise ValueError("porta não permitida")
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(alvo.hostname, porta, type=socket.SOCK_STREAM)
    if not infos:
        raise ValueError("host não resolvido")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise ValueError("destino interno bloqueado")


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: Dict[str, str] = {}
        self.titulo: str = ""
        self._no_title = False
        self.icone: Optional[str] = None

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        a = {k.lower(): (v or "") for k, v in attrs if k}
        if tag == "meta":
            chave = (a.get("property") or a.get("name") or "").lower().strip()
            if chave and a.get("content") and chave not in self.meta:
                self.meta[chave] = a["content"].strip()
        elif tag == "title":
            self._no_title = True
        elif tag == "link" and "icon" in (a.get("rel") or "").lower() and a.get("href") and not self.icone:
            self.icone = a["href"]

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag == "title":
            self._no_title = False

    def handle_data(self, data):  # noqa: ANN001
        if self._no_title and len(self.titulo) < 500:
            self.titulo += data


def _imagem_segura(base: str, valor: Optional[str]) -> Optional[str]:
    if not valor:
        return None
    url = urljoin(base, valor.strip())
    return url if urlparse(url).scheme in {"http", "https"} and len(url) <= 2000 else None


async def _baixar_html(url: str) -> tuple:
    atual = url
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=False) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            await _exigir_destino_publico(atual)
            async with client.stream("GET", atual) as resp:
                if resp.status_code in {301, 302, 303, 307, 308} and resp.headers.get("location"):
                    atual = urljoin(atual, resp.headers["location"])
                    continue
                if resp.status_code >= 400:
                    raise ValueError(f"HTTP {resp.status_code}")
                tipo = resp.headers.get("content-type", "").lower()
                if "html" not in tipo:
                    raise ValueError("não é HTML")
                corpo = bytearray()
                async for parte in resp.aiter_bytes():
                    corpo.extend(parte)
                    if len(corpo) >= _MAX_BYTES:
                        break
                return atual, bytes(corpo[:_MAX_BYTES]).decode(resp.encoding or "utf-8", errors="replace")
    raise ValueError("redirects demais")


def _limitar(texto: Optional[str], n: int) -> Optional[str]:
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return (texto[: n - 1] + "…" if len(texto) > n else texto) or None


async def buscar_preview(url: str) -> Dict[str, Any]:
    """Dados da prévia. Nunca lança por falha de rede: devolve a prévia mínima (só o domínio)."""
    url = normalizar_url(url)
    base: Dict[str, Any] = {"url": url, "titulo": None, "descricao": None, "imagem_url": None,
                            "site_nome": _dominio(url), "embed_tipo": None, "embed_id": None}
    embed = detectar_embed(url)
    if embed:
        base.update(embed)
        if embed["embed_tipo"] == "youtube":
            base["imagem_url"] = f"https://img.youtube.com/vi/{embed['embed_id']}/hqdefault.jpg"
            base["site_nome"] = "YouTube"
        else:
            base["site_nome"] = "Vimeo"
    try:
        final, conteudo = await _baixar_html(url)
    except Exception as exc:  # noqa: BLE001 — prévia é acessória
        logger.info("Prévia indisponível para %s: %s", url, exc)
        return base
    p = _MetaParser()
    try:
        p.feed(conteudo)
        p.close()
    except Exception:  # noqa: BLE001 — HTML malformado
        pass
    m = p.meta
    base["titulo"] = _limitar(m.get("og:title") or m.get("twitter:title") or p.titulo, 300)
    base["descricao"] = _limitar(m.get("og:description") or m.get("twitter:description") or m.get("description"), 500)
    base["imagem_url"] = base["imagem_url"] or _imagem_segura(final, m.get("og:image") or m.get("og:image:url")
                                                              or m.get("twitter:image"))
    base["site_nome"] = _limitar(m.get("og:site_name"), 120) or base["site_nome"]
    return base
