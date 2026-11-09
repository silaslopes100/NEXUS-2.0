"""Rotas self-service do perfil do aluno."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from psycopg2.errors import UniqueViolation

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(
    prefix="/alunos",
    tags=["Perfil do Aluno"],
    dependencies=[Depends(require_role(["aluno"]))],
)

_PROFILE_FIELDS = """
    id, nome, sobrenome, email, telefone, celular,
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


def _profile_response(row: dict) -> PerfilAlunoResponse:
    return PerfilAlunoResponse(
        id=str(row["id"]),
        nome=row.get("nome") or "",
        sobrenome=row.get("sobrenome"),
        email=row["email"],
        telefone=row.get("telefone"),
        celular=row.get("celular"),
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
    if values["email"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
                          cep, logradouro, numero, complemento, bairro, cidade, uf
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
