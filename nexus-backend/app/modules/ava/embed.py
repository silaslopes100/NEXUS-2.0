"""Resolução de links de vídeo para embed (YouTube, Vimeo, Panda Video ou iframe https genérico)."""
from __future__ import annotations

import re
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException, status

from app.modules.comunicacao.link_preview import detectar_embed, normalizar_url

_PANDA_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_PANDA_HOSTS = (".pandavideo.com.br", ".pandavideo.com")


def _panda(url: str) -> Optional[Dict[str, str]]:
    alvo = urlparse(url)
    host = (alvo.hostname or "").lower()
    if not host.endswith(_PANDA_HOSTS):
        return None
    vid = (parse_qs(alvo.query).get("v") or [""])[0]
    if not _PANDA_ID.fullmatch(vid):
        return None
    # O player do Panda é servido pelo mesmo host do link (player-vz-<conta>.tv.pandavideo.com.br).
    base = host if host.startswith("player") else None
    embed = f"https://{base}/embed/?v={vid}" if base else url
    return {"provedor": "panda", "embed_id": vid, "embed_url": embed}


def resolver_embed(url: str) -> Dict[str, Optional[str]]:
    """Devolve ``{url, provedor, embed_id, embed_url, thumbnail_url}``; 422 para links inaceitáveis."""
    url = normalizar_url(url)
    achado = detectar_embed(url)
    if achado and achado["embed_tipo"] == "youtube":
        vid = achado["embed_id"]
        return {"url": url, "provedor": "youtube", "embed_id": vid,
                "embed_url": f"https://www.youtube-nocookie.com/embed/{vid}",
                "thumbnail_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}
    if achado and achado["embed_tipo"] == "vimeo":
        vid = achado["embed_id"]
        return {"url": url, "provedor": "vimeo", "embed_id": vid,
                "embed_url": f"https://player.vimeo.com/video/{vid}", "thumbnail_url": None}
    panda = _panda(url)
    if panda:
        return {"url": url, **panda, "thumbnail_url": None}
    if urlparse(url).scheme != "https":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Use um link https do YouTube, Vimeo, Panda Video ou de um player incorporável.")
    return {"url": url, "provedor": "iframe", "embed_id": None, "embed_url": url, "thumbnail_url": None}
