"""Anexos do chat (arquivos, fotos, vídeos e áudios).

Produção: o navegador envia o arquivo direto ao Vercel Blob (store PÚBLICO dedicado ao chat)
com um *client token* de curta duração emitido aqui. O caminho tem 128 bits aleatórios e a URL só
é entregue aos membros da conversa. A API nunca trafega o arquivo, então não há limite de 4,5 MB.

Desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN): upload e leitura via disco local.
A mecânica é a de :mod:`app.core.blob_upload`; aqui fica só a configuração do chat.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence

from fastapi import UploadFile

from app.core.blob_upload import MB, AnexoValidado, EscopoUpload, usa_blob  # noqa: F401 — API pública

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

ESCOPO = EscopoUpload(prefixo="chat", categorias=CATEGORIAS, rota_local="/chat/anexos/local",
                      rotulo="chat", nome_item="Anexo")
LOCAL_DIR: Path = ESCOPO.local_dir
LOCAL_URL_PREFIX = ESCOPO.local_url_prefix


def categoria_do_mime(mime: str) -> Optional[str]:
    return ESCOPO.categoria_do_mime(mime)


def emitir_upload(nome: str, mime: str, tamanho: int) -> Dict[str, object]:
    return ESCOPO.emitir_upload(nome, mime, tamanho)


def validar_anexo(*, url: str, pathname: str, nome: str, mime: str, tamanho: int) -> AnexoValidado:
    return ESCOPO.validar_anexo(url=url, pathname=pathname, nome=nome, mime=mime, tamanho=tamanho)


async def salvar_local(pathname: str, arquivo: UploadFile) -> Dict[str, str]:
    return await ESCOPO.salvar_local(pathname, arquivo)


def caminho_local(arquivo: str) -> Path:
    return ESCOPO.caminho_local(arquivo)


async def excluir_anexos(refs: Sequence[str]) -> None:
    await ESCOPO.excluir(refs)
