"""Private storage for academic attachments."""
from __future__ import annotations

import io
import logging
import re
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import quote

from fastapi import HTTPException, Response, UploadFile, status
from vercel import blob

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_ACADEMIC_FILE_BYTES = 4 * 1024 * 1024
ACADEMIC_FILES_DIRECTORY = Path(__file__).resolve().parents[2] / "uploads" / "academic_materials"
_STORAGE_KEY_PATTERN = re.compile(r"^academic_materials/[a-f0-9]{32}\.[a-z0-9]{2,5}$")
_ALLOWED_CONTENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
}
_OOXML_ENTRIES = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}
_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class StoredAcademicFile:
    storage_key: str
    filename: str
    content_type: str
    size_bytes: int


def _uses_blob_storage() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _storage_path(storage_key: str) -> Path:
    if not _STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo acadêmico não encontrado",
        )
    return ACADEMIC_FILES_DIRECTORY / storage_key.rsplit("/", 1)[1]


def _normalized_filename(filename: Optional[str], extension: str) -> str:
    base = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    if not base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um nome válido para o arquivo.",
        )
    stem = Path(base).stem.strip() or "arquivo"
    return f"{stem[: 255 - len(extension)]}{extension}"


def _validate_signature(extension: str, content: bytes) -> None:
    valid = True
    if extension == ".pdf":
        valid = content.startswith(b"%PDF-")
    elif extension in {".jpg", ".jpeg"}:
        valid = content.startswith(b"\xff\xd8\xff")
    elif extension == ".png":
        valid = content.startswith(_PNG_SIGNATURE)
    elif extension == ".webp":
        valid = len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    elif extension in {".doc", ".ppt", ".xls"}:
        valid = content.startswith(_OLE_SIGNATURE)
    elif extension in _OOXML_ENTRIES:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                valid = _OOXML_ENTRIES[extension] in archive.namelist()
        except (OSError, zipfile.BadZipFile):
            valid = False

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="O conteúdo enviado não corresponde ao formato informado.",
        )


async def store_academic_file(upload: UploadFile) -> StoredAcademicFile:
    filename = (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    extension = Path(filename).suffix.lower()
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if extension not in _ALLOWED_CONTENT_TYPES or content_type not in _ALLOWED_CONTENT_TYPES[extension]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato inválido. Envie PDF, documento, apresentação, planilha ou imagem compatível.",
        )

    content = await upload.read(MAX_ACADEMIC_FILE_BYTES + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione um arquivo para enviar.",
        )
    if len(content) > MAX_ACADEMIC_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="O arquivo deve ter no máximo 4 MiB.",
        )
    _validate_signature(extension, content)

    storage_key = f"academic_materials/{uuid.uuid4().hex}{extension}"
    if _uses_blob_storage():
        await blob.put_blob(
            storage_key,
            content,
            access="private",
            content_type=content_type,
        )
    else:
        ACADEMIC_FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)
        destination = _storage_path(storage_key)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(destination)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            logger.exception("Não foi possível armazenar arquivo acadêmico localmente")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível armazenar o arquivo enviado.",
            ) from exc

    return StoredAcademicFile(
        storage_key=storage_key,
        filename=_normalized_filename(upload.filename, extension),
        content_type=content_type,
        size_bytes=len(content),
    )


async def read_academic_file(storage_key: str) -> bytes:
    if _uses_blob_storage():
        try:
            result = await blob.get_blob(storage_key, access="private")
        except blob.BlobNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo acadêmico não encontrado",
            ) from None
        return result.body

    try:
        return _storage_path(storage_key).read_bytes()
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo acadêmico não encontrado",
        ) from None
    except OSError as exc:
        logger.exception("Não foi possível ler arquivo acadêmico local")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível ler o arquivo solicitado.",
        ) from exc


async def academic_file_response(file_metadata: Mapping[str, Any]) -> Response:
    storage_key = file_metadata.get("arquivo_storage_key")
    filename = file_metadata.get("arquivo_nome")
    if not storage_key or not filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo acadêmico não encontrado",
        )
    return Response(
        content=await read_academic_file(storage_key),
        media_type=file_metadata.get("arquivo_mime_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def delete_academic_file(storage_key: Optional[str]) -> None:
    if not storage_key:
        return
    if not _STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise ValueError("Chave interna de arquivo acadêmico inválida")

    if _uses_blob_storage():
        try:
            await blob.delete_blob(storage_key)
        except blob.BlobNotFoundError:
            return
        return

    _storage_path(storage_key).unlink(missing_ok=True)
