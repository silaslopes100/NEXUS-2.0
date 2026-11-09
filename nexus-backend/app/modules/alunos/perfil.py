"""Rotas self-service do perfil do aluno."""
from __future__ import annotations

import io
import json
import logging
import re
import uuid
import warnings
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from psycopg2.errors import UniqueViolation

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/alunos",
    tags=["Perfil do Aluno"],
    dependencies=[Depends(require_role(["aluno"]))],
)

PHOTO_DIRECTORY = Path(__file__).resolve().parents[3] / "uploads" / "profile_photos"
PHOTO_URL = "/alunos/meu-perfil/foto"
MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000
PHOTO_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
PHOTO_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_PHOTO_FILENAME = re.compile(r"^[a-f0-9]{32}\.(?:jpg|png|webp)$")

_PROFILE_FIELDS = """
    id, nome, sobrenome, email, telefone, celular, foto_url,
    cep, logradouro, numero, complemento, bairro, cidade, uf
"""


class EnderecoAluno(BaseModel):
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None


class PerfilAlunoResponse(BaseModel):
    id: str
    nome: str
    sobrenome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None
    foto_url: Optional[str] = None
    endereco: EnderecoAluno


class PerfilAlunoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    telefone: Optional[str] = Field(default=None, max_length=64)
    celular: Optional[str] = Field(default=None, max_length=64)
    cep: Optional[str] = Field(default=None, max_length=16)
    logradouro: Optional[str] = Field(default=None, max_length=255)
    numero: Optional[str] = Field(default=None, max_length=32)
    complemento: Optional[str] = Field(default=None, max_length=255)
    bairro: Optional[str] = Field(default=None, max_length=255)
    cidade: Optional[str] = Field(default=None, max_length=255)
    uf: Optional[str] = Field(default=None, max_length=2)


class FotoAlunoResponse(BaseModel):
    foto_url: str


def _stored_photo_path(filename: Optional[str]) -> Optional[Path]:
    if not filename or not _PHOTO_FILENAME.fullmatch(filename):
        return None
    return PHOTO_DIRECTORY / filename


def _prepare_photo(content: bytes, content_type: str) -> tuple[bytes, str]:
    expected_format = PHOTO_FORMATS.get(content_type.lower())
    if not expected_format:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato inválido. Envie uma imagem JPEG, PNG ou WebP.",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(io.BytesIO(content))
            if source.format != expected_format:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="O conteúdo da imagem não corresponde ao formato informado.",
                )
            if source.width * source.height > MAX_PHOTO_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="A imagem excede a resolução máxima permitida.",
                )
            source.verify()

        with Image.open(io.BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            if expected_format == "JPEG":
                image = image.convert("RGB")
            elif expected_format == "PNG" and image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                image = image.convert("RGBA")
            elif expected_format == "WEBP" and image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")

            output = io.BytesIO()
            image.save(output, format=expected_format, optimize=True)
            return output.getvalue(), PHOTO_EXTENSIONS[expected_format]
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="O arquivo enviado não é uma imagem válida.",
        ) from exc


def _write_photo(content: bytes, extension: str) -> str:
    filename = f"{uuid.uuid4().hex}.{extension}"
    PHOTO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = PHOTO_DIRECTORY / filename
    temporary = PHOTO_DIRECTORY / f".{filename}.tmp"
    try:
        temporary.write_bytes(content)
        temporary.replace(destination)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return filename


def _remove_photo(filename: Optional[str]) -> None:
    path = _stored_photo_path(filename)
    if not path:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Não foi possível remover foto antiga do aluno: %s", path.name)


def _profile_response(row: dict) -> PerfilAlunoResponse:
    photo_path = _stored_photo_path(row.get("foto_url"))
    return PerfilAlunoResponse(
        id=str(row["id"]),
        nome=row.get("nome") or "",
        sobrenome=row.get("sobrenome"),
        email=row["email"],
        telefone=row.get("telefone"),
        celular=row.get("celular"),
        foto_url=(
            f"{PHOTO_URL}?v={row['foto_url']}"
            if photo_path and photo_path.is_file()
            else None
        ),
        endereco=EnderecoAluno(
            cep=row.get("cep"),
            logradouro=row.get("logradouro"),
            numero=row.get("numero"),
            complemento=row.get("complemento"),
            bairro=row.get("bairro"),
            cidade=row.get("cidade"),
            uf=row.get("uf"),
        ),
    )


@router.get("/meu-perfil", response_model=PerfilAlunoResponse)
async def get_meu_perfil(
    current_user: UserResponse = Depends(get_current_user),
) -> PerfilAlunoResponse:
    with get_db_cursor() as cur:
        cur.execute(
            f"SELECT {_PROFILE_FIELDS} FROM usuarios WHERE id = %s",
            (current_user.id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil do aluno não encontrado",
        )
    return _profile_response(dict(row))


@router.get("/meu-perfil/foto")
async def get_meu_perfil_foto(
    current_user: UserResponse = Depends(get_current_user),
) -> FileResponse:
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT foto_url FROM usuarios WHERE id = %s",
            (current_user.id,),
        )
        row = cur.fetchone()

    photo_path = _stored_photo_path(row.get("foto_url") if row else None)
    if not photo_path or not photo_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foto de perfil não encontrada",
        )

    media_type = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }[photo_path.suffix]
    return FileResponse(
        photo_path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/meu-perfil/foto", response_model=FotoAlunoResponse)
async def upload_meu_perfil_foto(
    request: Request,
    foto: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
) -> FotoAlunoResponse:
    content = await foto.read(MAX_PHOTO_BYTES + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione uma imagem para enviar.",
        )
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="A imagem deve ter no máximo 5 MB.",
        )

    processed_content, extension = _prepare_photo(content, foto.content_type or "")
    new_filename = _write_photo(processed_content, extension)
    previous_filename: Optional[str] = None
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT foto_url FROM usuarios WHERE id = %s FOR UPDATE",
                (current_user.id,),
            )
            previous = cur.fetchone()
            if not previous:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Perfil do aluno não encontrado",
                )
            previous_filename = previous.get("foto_url")

            cur.execute(
                """
                UPDATE usuarios SET foto_url = %s, atualizado_em = now()
                WHERE id = %s
                """,
                (new_filename, current_user.id),
            )
            cur.execute(
                """
                INSERT INTO logs_auditoria (
                    usuario_id, acao, entidade, entidade_id, dados_depois,
                    ip, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    current_user.id,
                    "perfil_foto_atualizada",
                    "usuarios",
                    current_user.id,
                    json.dumps({"foto_url": PHOTO_URL}),
                    get_client_ip(request),
                ),
            )
    except Exception:
        _remove_photo(new_filename)
        raise

    if previous_filename != new_filename:
        _remove_photo(previous_filename)
    return FotoAlunoResponse(foto_url=f"{PHOTO_URL}?v={new_filename}")


@router.put("/meu-perfil", response_model=PerfilAlunoResponse)
async def update_meu_perfil(
    dados: PerfilAlunoUpdate,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
) -> PerfilAlunoResponse:
    values = dados.model_dump()
    values["email"] = str(dados.email).strip().lower()
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = value.strip() or None
    for field, expected_length, label in (
        ("telefone", 11, "O telefone"),
        ("celular", 11, "O celular"),
        ("cep", 8, "O CEP"),
    ):
        value = values[field]
        if value is None:
            continue
        digits = re.sub(r"\D", "", value)
        if len(digits) != expected_length:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{label} deve conter {expected_length} dígitos",
            )
        values[field] = digits
    if values["email"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="O e-mail é obrigatório",
        )
    if values["uf"]:
        values["uf"] = values["uf"].upper()

    try:
        with get_db_cursor() as cur:
            cur.execute(
                f"SELECT {_PROFILE_FIELDS} FROM usuarios WHERE id = %s",
                (current_user.id,),
            )
            previous = cur.fetchone()
            if not previous:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Perfil do aluno não encontrado",
                )

            cur.execute(
                """
                SELECT id FROM usuarios
                WHERE lower(email) = lower(%s) AND id <> %s
                LIMIT 1
                """,
                (values["email"], current_user.id),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este e-mail já está em uso",
                )

            cur.execute(
                """
                UPDATE usuarios
                SET email = %s, telefone = %s, celular = %s, cep = %s,
                    logradouro = %s, numero = %s, complemento = %s,
                    bairro = %s, cidade = %s, uf = %s, atualizado_em = now()
                WHERE id = %s
                RETURNING id, nome, sobrenome, email, telefone, celular,
                          foto_url, cep, logradouro, numero, complemento,
                          bairro, cidade, uf
                """,
                (
                    values["email"],
                    values["telefone"],
                    values["celular"],
                    values["cep"],
                    values["logradouro"],
                    values["numero"],
                    values["complemento"],
                    values["bairro"],
                    values["cidade"],
                    values["uf"],
                    current_user.id,
                ),
            )
            updated = cur.fetchone()
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Perfil do aluno não encontrado",
                )

            cur.execute(
                """
                INSERT INTO logs_auditoria (
                    usuario_id, acao, entidade, entidade_id, dados_antes,
                    dados_depois, ip, criado_em, atualizado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    current_user.id,
                    "perfil_atualizado",
                    "usuarios",
                    current_user.id,
                    json.dumps({
                        key: previous.get(key)
                        for key in values
                    }, default=str),
                    json.dumps({
                        key: updated.get(key)
                        for key in values
                    }, default=str),
                    get_client_ip(request),
                ),
            )
    except UniqueViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está em uso",
        ) from exc

    return _profile_response(dict(updated))
