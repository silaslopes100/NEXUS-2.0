"""Módulo de Polos e Escolas do NEXUS 2.0."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/unidades", tags=["Polos & Escolas"])


class PoloSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    nome: str
    responsavel_nome: Optional[str] = None
    responsavel_cpf: Optional[str] = None
    responsavel_email: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    complemento: Optional[str] = None
    status: str = "ativo"


class EscolaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    polo_id: Optional[str] = None
    nome: str
    responsavel_nome: Optional[str] = None
    responsavel_cpf: Optional[str] = None
    responsavel_email: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    complemento: Optional[str] = None
    status: str = "ativo"


# In-memory storage for mock/testing
_polos_db: Dict[str, Dict[str, Any]] = {}
_escolas_db: Dict[str, Dict[str, Any]] = {}


@router.get("/polos", response_model=List[PoloSchema], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_polos(q: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, nome, responsavel_nome, responsavel_cpf, responsavel_email, cep, logradouro, numero, bairro, cidade, uf, status FROM polos"
            if q:
                sql += " WHERE lower(nome) LIKE %s"
                cur.execute(sql, (f"%{q.lower()}%",))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        polos = list(_polos_db.values())
        if q:
            polos = [p for p in polos if q.lower() in p["nome"].lower()]
        return polos


@router.post("/polos", response_model=PoloSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_polo(dados: PoloSchema):
    new_id = str(uuid.uuid4())
    polo_dict = dados.model_dump()
    polo_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO polos (id, nome, responsavel_nome, responsavel_cpf, responsavel_email, cep, logradouro, numero, bairro, cidade, uf, complemento, status, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                RETURNING id
            """
            cur.execute(sql, (new_id, dados.nome, dados.responsavel_nome, dados.responsavel_cpf, dados.responsavel_email, dados.cep, dados.logradouro, dados.numero, dados.bairro, dados.cidade, dados.uf, dados.complemento, dados.status))
    except Exception:
        _polos_db[new_id] = polo_dict
    return polo_dict


@router.get("/polos/{polo_id}", response_model=PoloSchema, dependencies=[Depends(require_role(["admin", "polo"]))])
async def get_polo(polo_id: str):
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM polos WHERE id = %s", (polo_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
    except Exception:
        if polo_id in _polos_db:
            return _polos_db[polo_id]
    raise HTTPException(status_code=404, detail="Polo não encontrado")


@router.get("/escolas", response_model=List[EscolaSchema], dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def list_escolas(polo_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, cep, logradouro, numero, bairro, cidade, uf, status FROM escolas"
            if polo_id:
                sql += " WHERE polo_id = %s"
                cur.execute(sql, (polo_id,))
            else:
                cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        escolas = list(_escolas_db.values())
        if polo_id:
            escolas = [e for e in escolas if e.get("polo_id") == polo_id]
        return escolas


@router.post("/escolas", response_model=EscolaSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def create_escola(dados: EscolaSchema):
    new_id = str(uuid.uuid4())
    escola_dict = dados.model_dump()
    escola_dict["id"] = new_id
    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO escolas (id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, cep, logradouro, numero, bairro, cidade, uf, complemento, status, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                RETURNING id
            """
            cur.execute(sql, (new_id, dados.polo_id, dados.nome, dados.responsavel_nome, dados.responsavel_cpf, dados.responsavel_email, dados.cep, dados.logradouro, dados.numero, dados.bairro, dados.cidade, dados.uf, dados.complemento, dados.status))
    except Exception:
        _escolas_db[new_id] = escola_dict
    return escola_dict
