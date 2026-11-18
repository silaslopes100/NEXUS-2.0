"""Anexos do chat (arquivos, fotos, vídeos e áudios).

Produção: o navegador envia o arquivo direto ao Vercel Blob (store PÚBLICO dedicado ao chat)
com um *client token* de curta duração emitido aqui. O caminho tem 128 bits aleatórios e a URL só
é entregue aos membros da conversa. A API nunca trafega o arquivo, então não há limite de 4,5 MB.

Desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN): upload e leitura via disco local.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)

MB = 1024 * 1024

# categoria -> (limite em bytes, {mime: extensão})
CATEGORIAS: Dict[str, tuple] = {
    "imagem": (10 * MB, {
        "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif",
    }),
    "audio": (20 * MB, {
        "audio/webm": "webm", "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a",
        "audio/x-m4a": "m4a", "audio/aac": "aac", "audio/wav": "wav", "audio/x-wav": "wav",
    }),
    "video": (50 * MB, {
        "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov",
    }),
    "documento": (20 * MB, {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "text/plain": "txt",
        "application/zip": "zip",
    }),
}

_PATHNAME = re.compile(r"^chat/[a-f0-9]{32}\.[a-z0-9]{2,5}$")
LOCAL_DIR = Path(__file__).resolve().parents[3] / "uploads" / "chat"
LOCAL_URL_PREFIX = "/chat/anexos/local/"
_TOKEN_VALIDADE_S = 5 * 60


@dataclass(frozen=True)
class AnexoValidado:
    url: str
    storage_key: str
    nome: str
    mime: str
    tamanho: int


def _normalizar_mime(mime: Optional[str]) -> str:
    return (mime or "").split(";", 1)[0].strip().lower()


def categoria_do_mime(mime: str) -> Optional[str]:
    for nome, (_, tipos) in CATEGORIAS.items():
        if mime in tipos:
            return nome
    return None


def _validar_tipo_tamanho(mime: str, tamanho: int) -> tuple:
    categoria = categoria_do_mime(mime)
    if not categoria:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="Tipo de arquivo não permitido no chat.")
    limite, tipos = CATEGORIAS[categoria]
    if tamanho <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")
    if tamanho > limite:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"Arquivo muito grande: o limite para {categoria} é {limite // MB} MB.")
    return limite, tipos[mime]


def _nome_seguro(nome: Optional[str]) -> str:
    base = (nome or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return (base or "arquivo")[:255]


def usa_blob() -> bool:
    return bool(settings.CHAT_BLOB_READ_WRITE_TOKEN)


def _store_id() -> str:
    partes = settings.CHAT_BLOB_READ_WRITE_TOKEN.split("_")
    if len(partes) < 5 or not partes[3]:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Armazenamento do chat mal configurado.")
    return partes[3]


def _gerar_client_token(pathname: str, mime: str, limite: int) -> str:
    """Equivalente a `generateClientTokenFromReadWriteToken` do @vercel/blob."""
    rw = settings.CHAT_BLOB_READ_WRITE_TOKEN
    payload = base64.b64encode(json.dumps({
        "pathname": pathname,
        "allowedContentTypes": [mime],
        "maximumSizeInBytes": limite,
        "addRandomSuffix": False,
        "validUntil": int((time.time() + _TOKEN_VALIDADE_S) * 1000),
    }, separators=(",", ":")).encode()).decode()
    assinatura = hmac.new(rw.encode(), payload.encode(), hashlib.sha256).hexdigest()
    corpo = base64.b64encode(f"{assinatura}.{payload}".encode()).decode()
    return f"vercel_blob_client_{_store_id()}_{corpo}"


def emitir_upload(nome: str, mime: str, tamanho: int) -> Dict[str, object]:
    """Valida o arquivo pretendido e devolve como enviá-lo."""
    mime = _normalizar_mime(mime)
    limite, extensao = _validar_tipo_tamanho(mime, tamanho)
    pathname = f"chat/{uuid.uuid4().hex}.{extensao}"
    if usa_blob():
        return {"modo": "blob", "pathname": pathname, "token": _gerar_client_token(pathname, mime, limite),
                "content_type": mime}
    return {"modo": "local", "pathname": pathname, "upload_url": f"/chat/anexos/local?pathname={pathname}",
            "content_type": mime}


def validar_anexo(*, url: str, pathname: str, nome: str, mime: str, tamanho: int) -> AnexoValidado:
    """Confere que o anexo informado pelo cliente pertence ao store do chat."""
    mime = _normalizar_mime(mime)
    _, extensao = _validar_tipo_tamanho(mime, int(tamanho or 0))
    if not _PATHNAME.fullmatch(pathname or "") or not pathname.endswith(f".{extensao}"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Anexo inválido.")
    if usa_blob():
        alvo = urlparse(url or "")
        host_esperado = f"{_store_id().lower()}.public.blob.vercel-storage.com"
        if alvo.scheme != "https" or (alvo.hostname or "").lower() != host_esperado or alvo.path != f"/{pathname}":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Anexo inválido.")
        url_final = f"https://{host_esperado}/{pathname}"
    else:
        arquivo = LOCAL_DIR / pathname.split("/", 1)[1]
        if not arquivo.is_file():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Anexo não encontrado. Envie o arquivo novamente.")
        url_final = f"{LOCAL_URL_PREFIX}{arquivo.name}"
    return AnexoValidado(url=url_final, storage_key=pathname, nome=_nome_seguro(nome), mime=mime,
                         tamanho=int(tamanho))


async def salvar_local(pathname: str, arquivo: UploadFile) -> Dict[str, str]:
    """Upload em desenvolvimento (sem Blob)."""
    if usa_blob():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Não encontrado")
    if not _PATHNAME.fullmatch(pathname or ""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Caminho inválido.")
    mime = _normalizar_mime(arquivo.content_type)
    limite = CATEGORIAS.get(categoria_do_mime(mime) or "", (0, {}))[0]
    conteudo = await arquivo.read(limite + 1)
    _, extensao = _validar_tipo_tamanho(mime, len(conteudo))
    if not pathname.endswith(f".{extensao}"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Tipo de arquivo diferente do informado.")
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    destino = LOCAL_DIR / pathname.split("/", 1)[1]
    destino.write_bytes(conteudo)
    return {"url": f"{LOCAL_URL_PREFIX}{destino.name}", "pathname": pathname}


def caminho_local(arquivo: str) -> Path:
    if usa_blob() or not re.fullmatch(r"[a-f0-9]{32}\.[a-z0-9]{2,5}", arquivo or ""):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Não encontrado")
    caminho = LOCAL_DIR / arquivo
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Não encontrado")
    return caminho


async def excluir_anexos(refs: Sequence[str]) -> None:
    """Remove anexos do store (URLs do Blob ou caminhos locais). Falhas só são registradas."""
    refs = [r for r in refs if r]
    if not refs:
        return
    if usa_blob():
        try:
            from vercel import blob
            from vercel.api import session
            from vercel.blob import BlobCredentials, BlobServiceOptions

            credenciais = BlobCredentials(settings.CHAT_BLOB_READ_WRITE_TOKEN, _store_id())
            opcoes = BlobServiceOptions(credentials_factory=lambda: credenciais)
            async with session(service_options=[opcoes]):
                for i in range(0, len(refs), 1000):
                    await blob.delete_blob(list(refs[i:i + 1000]))
        except Exception:  # noqa: BLE001 — limpeza é acessória
            logger.exception("Falha ao excluir %d anexo(s) do chat no Blob", len(refs))
        return
    for ref in refs:
        nome = ref.rsplit("/", 1)[-1]
        if re.fullmatch(r"[a-f0-9]{32}\.[a-z0-9]{2,5}", nome):
            try:
                (LOCAL_DIR / nome).unlink(missing_ok=True)
            except OSError:
                logger.exception("Falha ao excluir anexo local do chat %s", nome)
