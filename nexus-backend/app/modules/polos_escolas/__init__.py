"""Módulo de Polos e Escolas do NEXUS 2.0."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import hash_password
from app.modules.auth.dependencies import get_current_user, get_scoped_user, require_role
from app.modules.auth.repository import get_auth_repository
from app.modules.auth.schemas import UserResponse

router = APIRouter(tags=["Polos & Escolas"])


class EnderecoSchema(BaseModel):
    logradouro: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    cep: str


class PoloCreate(BaseModel):
    nome: str = Field(..., min_length=2)
    responsavel_nome: str | None = None
    responsavel_cpf: str | None = Field(default=None, min_length=11, max_length=14)
    responsavel_email: EmailStr | None = None
    endereco_completo: EnderecoSchema | None = None
    cidade: str | None = None
    uf: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    cep: str | None = None


class PoloResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    responsavel_nome: str | None = None
    responsavel_cpf: str | None = None
    responsavel_email: EmailStr | None = None
    endereco_completo: EnderecoSchema
    status: str = "ativo"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EscolaCreate(BaseModel):
    nome: str = Field(..., min_length=2)
    responsavel_nome: str | None = None
    responsavel_cpf: str | None = Field(default=None, min_length=11, max_length=14)
    responsavel_email: EmailStr | None = None
    endereco_completo: EnderecoSchema | None = None
    polo_id: str | None = None
    cidade: str | None = None
    uf: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    cep: str | None = None


class EscolaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    polo_id: str
    nome: str
    responsavel_nome: str | None = None
    responsavel_cpf: str | None = None
    responsavel_email: EmailStr | None = None
    endereco_completo: EnderecoSchema
    status: str = "ativo"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CoordenadorCreate(BaseModel):
    nome: str
    cpf: str = Field(..., min_length=11, max_length=14)
    email: EmailStr
    senha: str = Field(..., min_length=8)


class CoordenadorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    email: EmailStr
    perfil: str
    polo_id: str
    status: str = "ativo"
    created_at: datetime | None = None


_polos_db: Dict[str, Dict[str, Any]] = {}
_escolas_db: Dict[str, Dict[str, Any]] = {}
_alunos_db: Dict[str, Dict[str, Any]] = {}
_professores_db: Dict[str, Dict[str, Any]] = {}
_licencas_estoque_db: Dict[str, Dict[str, int]] = {"polo": {}, "escola": {}}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_polo_response(polo: Dict[str, Any]) -> PoloResponse:
    endereco = polo.get("endereco_completo") or {
        "logradouro": polo.get("logradouro") or "",
        "numero": polo.get("numero") or "",
        "bairro": polo.get("bairro") or "",
        "cidade": polo.get("cidade") or "",
        "estado": polo.get("estado") or "",
        "cep": polo.get("cep") or "",
    }
    email = polo.get("responsavel_email") or None
    return PoloResponse(
        id=str(polo["id"]),
        nome=polo["nome"],
        responsavel_nome=polo.get("responsavel_nome") or "",
        responsavel_cpf=polo.get("responsavel_cpf") or "",
        responsavel_email=email,
        endereco_completo=EnderecoSchema(**endereco),
        status=polo.get("status", "ativo"),
        created_at=polo.get("created_at"),
        updated_at=polo.get("updated_at"),
    )


def _build_endereco(payload: EnderecoSchema | None, fallback: Dict[str, str | None] | None = None) -> EnderecoSchema:
    source = (payload.model_dump() if payload else {})
    if fallback:
        source = {**fallback, **source}
    return EnderecoSchema(
        logradouro=str(source.get("logradouro") or ""),
        numero=str(source.get("numero") or ""),
        bairro=str(source.get("bairro") or ""),
        cidade=str(source.get("cidade") or ""),
        estado=str(source.get("estado") or ""),
        cep=str(source.get("cep") or ""),
    )


def _as_escola_response(escola: Dict[str, Any]) -> EscolaResponse:
    endereco = escola.get("endereco_completo") or {
        "logradouro": escola.get("logradouro") or "",
        "numero": escola.get("numero") or "",
        "bairro": escola.get("bairro") or "",
        "cidade": escola.get("cidade") or "",
        "estado": escola.get("estado") or "",
        "cep": escola.get("cep") or "",
    }
    email = escola.get("responsavel_email") or None
    return EscolaResponse(
        id=str(escola["id"]),
        polo_id=str(escola["polo_id"]),
        nome=escola["nome"],
        responsavel_nome=escola.get("responsavel_nome") or "",
        responsavel_cpf=escola.get("responsavel_cpf") or "",
        responsavel_email=email,
        endereco_completo=EnderecoSchema(**endereco),
        status=escola.get("status", "ativo"),
        created_at=escola.get("created_at"),
        updated_at=escola.get("updated_at"),
    )


def _check_forbidden_scope(current_user: UserResponse, polo_id: Optional[str] = None, escola_id: Optional[str] = None) -> None:
    perfil = (current_user.perfil.nome if current_user.perfil else "").lower()
    if perfil == "admin":
        return
    if perfil == "polo":
        if polo_id and str(current_user.polo_id) != str(polo_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a este polo.")
        return
    if perfil == "escola":
        if escola_id and str(current_user.escola_id) != str(escola_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta escola.")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado.")


def _duplicate_contact_exists(model: str, cpf: str, email: str) -> bool:
    if model == "polo":
        for polo in _polos_db.values():
            if str(polo.get("responsavel_cpf", "")).lower() == cpf.lower() or str(polo.get("responsavel_email", "")).lower() == email.lower():
                return True
    else:
        for escola in _escolas_db.values():
            if str(escola.get("responsavel_cpf", "")).lower() == cpf.lower() or str(escola.get("responsavel_email", "")).lower() == email.lower():
                return True
    return False


@router.get("/polos", response_model=List[PoloResponse], dependencies=[Depends(require_role(["admin", "polo"]))])
async def list_polos(
    current_user: UserResponse = Depends(get_current_user),
):
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em FROM polos WHERE status != 'inativo'"
            params = []
            if current_user.perfil and current_user.perfil.nome.lower() == "polo" and current_user.polo_id:
                sql += " AND id = %s"
                params.append(str(current_user.polo_id))
            sql += " ORDER BY nome ASC"
            cur.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
            return [_as_polo_response(p) for p in rows]
    except Exception:
        polos = list(_polos_db.values())
        if current_user.perfil and current_user.perfil.nome.lower() == "polo" and current_user.polo_id:
            polos = [p for p in polos if str(p.get("id")) == str(current_user.polo_id)]
        return [_as_polo_response(p) for p in polos if p.get("status") != "inativo"]


@router.post("/polos", response_model=PoloResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_polo(payload: PoloCreate, current_user: UserResponse = Depends(get_current_user)):
    del current_user
    cpf = (payload.responsavel_cpf or "").strip()
    email = str(payload.responsavel_email or "").lower()
    if cpf or email:
        if _duplicate_contact_exists("polo", cpf, email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CPF ou e-mail do responsável já cadastrado.")

    endereco = _build_endereco(payload.endereco_completo, {
        "cidade": payload.cidade,
        "estado": payload.uf,
        "logradouro": payload.logradouro,
        "numero": payload.numero,
        "bairro": payload.bairro,
        "cep": payload.cep,
    })

    polo_id = str(uuid4())
    now = _now()
    polo = {
        "id": polo_id,
        "nome": payload.nome,
        "responsavel_nome": payload.responsavel_nome or "",
        "responsavel_cpf": cpf,
        "responsavel_email": email,
        "endereco_completo": endereco.model_dump(),
        "logradouro": endereco.logradouro,
        "numero": endereco.numero,
        "bairro": endereco.bairro,
        "cidade": endereco.cidade,
        "estado": endereco.estado,
        "cep": endereco.cep,
        "status": "ativo",
        "created_at": now,
        "updated_at": now,
    }

    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO polos (id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            """
            cur.execute(sql, (
                polo_id,
                payload.nome,
                payload.responsavel_nome or "",
                cpf or None,
                email or None,
                endereco.logradouro,
                endereco.numero,
                endereco.bairro,
                endereco.cidade,
                endereco.estado,
                endereco.cep,
                "ativo",
            ))
    except Exception:
        pass

    _polos_db[polo_id] = polo
    return _as_polo_response(polo)


@router.get("/polos/{polo_id}", response_model=PoloResponse, dependencies=[Depends(require_role(["admin", "polo"]))])
async def get_polo(polo_id: str, current_user: UserResponse = Depends(get_current_user)):
    _check_forbidden_scope(current_user, polo_id=polo_id)
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em FROM polos WHERE id = %s", (str(polo_id),))
            row = cur.fetchone()
            if row:
                return _as_polo_response(dict(row))
    except Exception:
        pass

    polo = _polos_db.get(polo_id)
    if not polo:
        raise HTTPException(status_code=404, detail="Polo não encontrado")
    return _as_polo_response(polo)


@router.put("/polos/{polo_id}", response_model=PoloResponse, dependencies=[Depends(require_role(["admin", "polo"]))])
async def update_polo(polo_id: str, payload: PoloCreate, current_user: UserResponse = Depends(get_current_user)):
    _check_forbidden_scope(current_user, polo_id=polo_id)
    endereco = _build_endereco(payload.endereco_completo, {
        "cidade": payload.cidade,
        "estado": payload.uf,
        "logradouro": payload.logradouro,
        "numero": payload.numero,
        "bairro": payload.bairro,
        "cep": payload.cep,
    })

    try:
        with get_db_cursor() as cur:
            sql = """
                UPDATE polos SET
                    nome = %s, responsavel_nome = %s, responsavel_cpf = %s, responsavel_email = %s,
                    logradouro = %s, numero = %s, bairro = %s, cidade = %s, uf = %s, cep = %s, atualizado_em = now()
                WHERE id = %s
            """
            cur.execute(sql, (
                payload.nome,
                payload.responsavel_nome,
                payload.responsavel_cpf,
                str(payload.responsavel_email).lower() if payload.responsavel_email else None,
                endereco.logradouro,
                endereco.numero,
                endereco.bairro,
                endereco.cidade,
                endereco.estado,
                endereco.cep,
                str(polo_id),
            ))
    except Exception:
        pass

    polo = _polos_db.get(polo_id)
    if polo:
        polo.update({
            "nome": payload.nome,
            "responsavel_nome": payload.responsavel_nome,
            "responsavel_cpf": payload.responsavel_cpf,
            "responsavel_email": str(payload.responsavel_email).lower() if payload.responsavel_email else None,
            "endereco_completo": endereco.model_dump(),
            "logradouro": endereco.logradouro,
            "numero": endereco.numero,
            "bairro": endereco.bairro,
            "cidade": endereco.cidade,
            "estado": endereco.estado,
            "cep": endereco.cep,
            "updated_at": _now(),
        })
        return _as_polo_response(polo)
    return _as_polo_response({
        "id": polo_id,
        "nome": payload.nome,
        "responsavel_nome": payload.responsavel_nome,
        "responsavel_cpf": payload.responsavel_cpf,
        "responsavel_email": str(payload.responsavel_email).lower() if payload.responsavel_email else None,
        "endereco_completo": endereco.model_dump(),
        "status": "ativo",
    })


@router.delete("/polos/{polo_id}", response_model=PoloResponse, dependencies=[Depends(require_role(["admin"]))])
async def delete_polo(polo_id: str):
    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE polos SET status = 'inativo', atualizado_em = now() WHERE id = %s RETURNING id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em", (str(polo_id),))
            row = cur.fetchone()
            if row:
                return _as_polo_response(dict(row))
    except Exception:
        pass

    polo = _polos_db.get(polo_id)
    if not polo:
        raise HTTPException(status_code=404, detail="Polo não encontrado")
    polo["status"] = "inativo"
    polo["updated_at"] = _now()
    return _as_polo_response(polo)


@router.get("/polos/{polo_id}/escolas", response_model=List[EscolaResponse], dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def list_escolas_by_polo(polo_id: str, current_user: UserResponse = Depends(get_current_user)):
    _check_forbidden_scope(current_user, polo_id=polo_id)
    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em FROM escolas WHERE polo_id = %s AND status != 'inativo' ORDER BY nome ASC"
            cur.execute(sql, (str(polo_id),))
            rows = [dict(r) for r in cur.fetchall()]
            return [_as_escola_response(e) for e in rows]
    except Exception:
        escolas = [e for e in _escolas_db.values() if str(e.get("polo_id")) == str(polo_id) and e.get("status") != "inativo"]
        return [_as_escola_response(e) for e in escolas]


@router.get("/escolas", response_model=List[EscolaResponse], dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def list_escolas(polo_id: Optional[str] = None, current_user: UserResponse = Depends(get_current_user)):
    perfil = (current_user.perfil.nome if current_user.perfil else "").lower()
    if perfil == "polo" and current_user.polo_id:
        polo_id = current_user.polo_id

    try:
        with get_db_cursor() as cur:
            sql = "SELECT id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em FROM escolas WHERE status != 'inativo'"
            params = []
            if polo_id:
                sql += " AND polo_id = %s"
                params.append(str(polo_id))
            if perfil == "escola" and current_user.escola_id:
                sql += " AND id = %s"
                params.append(str(current_user.escola_id))
            sql += " ORDER BY nome ASC"
            cur.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
            return [_as_escola_response(e) for e in rows]
    except Exception:
        escolas = list(_escolas_db.values())
        if polo_id:
            escolas = [e for e in escolas if str(e.get("polo_id")) == str(polo_id)]
        if perfil == "escola" and current_user.escola_id:
            escolas = [e for e in escolas if str(e.get("id")) == str(current_user.escola_id)]
        return [_as_escola_response(e) for e in escolas if e.get("status") != "inativo"]


@router.post("/escolas", response_model=EscolaResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def create_escola_direct(payload: EscolaCreate, current_user: UserResponse = Depends(get_current_user)):
    polo_id = payload.polo_id
    if not polo_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="polo_id é obrigatório para cadastrar escola.")
    return await create_escola(polo_id, payload, current_user=current_user)


@router.post("/polos/{polo_id}/escolas", response_model=EscolaResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo"]))])
async def create_escola(polo_id: str, payload: EscolaCreate, current_user: UserResponse = Depends(get_current_user)):
    _check_forbidden_scope(current_user, polo_id=polo_id)
    cpf = (payload.responsavel_cpf or "").strip()
    email = str(payload.responsavel_email or "").lower()
    if cpf or email:
        if _duplicate_contact_exists("escola", cpf, email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CPF ou e-mail do responsável já cadastrado.")

    endereco = _build_endereco(payload.endereco_completo, {
        "cidade": payload.cidade,
        "estado": payload.uf,
        "logradouro": payload.logradouro,
        "numero": payload.numero,
        "bairro": payload.bairro,
        "cep": payload.cep,
    })

    escola_id = str(uuid4())
    now = _now()
    escola = {
        "id": escola_id,
        "polo_id": polo_id,
        "nome": payload.nome,
        "responsavel_nome": payload.responsavel_nome or "",
        "responsavel_cpf": cpf,
        "responsavel_email": email,
        "endereco_completo": endereco.model_dump(),
        "logradouro": endereco.logradouro,
        "numero": endereco.numero,
        "bairro": endereco.bairro,
        "cidade": endereco.cidade,
        "estado": endereco.estado,
        "cep": endereco.cep,
        "status": "ativo",
        "created_at": now,
        "updated_at": now,
    }

    try:
        with get_db_cursor() as cur:
            sql = """
                INSERT INTO escolas (id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            """
            cur.execute(sql, (
                escola_id,
                str(polo_id),
                payload.nome,
                payload.responsavel_nome or "",
                cpf or None,
                email or None,
                endereco.logradouro,
                endereco.numero,
                endereco.bairro,
                endereco.cidade,
                endereco.estado,
                endereco.cep,
                "ativo",
            ))
    except Exception:
        pass

    _escolas_db[escola_id] = escola
    return _as_escola_response(escola)


@router.get("/escolas/{escola_id}", response_model=EscolaResponse, dependencies=[Depends(require_role(["admin", "polo", "escola"]))])
async def get_escola(escola_id: str, current_user: UserResponse = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em FROM escolas WHERE id = %s", (str(escola_id),))
            row = cur.fetchone()
            if row:
                _check_forbidden_scope(current_user, polo_id=str(row.get("polo_id")), escola_id=escola_id)
                return _as_escola_response(dict(row))
    except Exception:
        pass

    escola = _escolas_db.get(escola_id)
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    _check_forbidden_scope(current_user, polo_id=escola.get("polo_id"), escola_id=escola_id)
    return _as_escola_response(escola)


@router.put("/escolas/{escola_id}", response_model=EscolaResponse, dependencies=[Depends(require_role(["admin", "polo"]))])
async def update_escola(escola_id: str, payload: EscolaCreate, current_user: UserResponse = Depends(get_current_user)):
    endereco = _build_endereco(payload.endereco_completo, {
        "cidade": payload.cidade,
        "estado": payload.uf,
        "logradouro": payload.logradouro,
        "numero": payload.numero,
        "bairro": payload.bairro,
        "cep": payload.cep,
    })

    try:
        with get_db_cursor() as cur:
            sql = """
                UPDATE escolas SET
                    nome = %s, responsavel_nome = %s, responsavel_cpf = %s, responsavel_email = %s,
                    logradouro = %s, numero = %s, bairro = %s, cidade = %s, uf = %s, cep = %s, atualizado_em = now()
                WHERE id = %s
            """
            cur.execute(sql, (
                payload.nome,
                payload.responsavel_nome,
                payload.responsavel_cpf,
                str(payload.responsavel_email).lower() if payload.responsavel_email else None,
                endereco.logradouro,
                endereco.numero,
                endereco.bairro,
                endereco.cidade,
                endereco.estado,
                endereco.cep,
                str(escola_id),
            ))
    except Exception:
        pass

    escola = _escolas_db.get(escola_id)
    if escola:
        escola.update({
            "nome": payload.nome,
            "responsavel_nome": payload.responsavel_nome,
            "responsavel_cpf": payload.responsavel_cpf,
            "responsavel_email": str(payload.responsavel_email).lower() if payload.responsavel_email else None,
            "endereco_completo": endereco.model_dump(),
            "logradouro": endereco.logradouro,
            "numero": endereco.numero,
            "bairro": endereco.bairro,
            "cidade": endereco.cidade,
            "estado": endereco.estado,
            "cep": endereco.cep,
            "updated_at": _now(),
        })
        return _as_escola_response(escola)

    return _as_escola_response({
        "id": escola_id,
        "polo_id": payload.polo_id or "",
        "nome": payload.nome,
        "responsavel_nome": payload.responsavel_nome,
        "responsavel_cpf": payload.responsavel_cpf,
        "responsavel_email": str(payload.responsavel_email).lower() if payload.responsavel_email else None,
        "endereco_completo": endereco.model_dump(),
        "status": "ativo",
    })


@router.delete("/escolas/{escola_id}", response_model=EscolaResponse, dependencies=[Depends(require_role(["admin", "polo"]))])
async def delete_escola(escola_id: str, current_user: UserResponse = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            cur.execute("UPDATE escolas SET status = 'inativo', atualizado_em = now() WHERE id = %s RETURNING id, polo_id, nome, responsavel_nome, responsavel_cpf, responsavel_email, logradouro, numero, bairro, cidade, uf, cep, status, criado_em, atualizado_em", (str(escola_id),))
            row = cur.fetchone()
            if row:
                return _as_escola_response(dict(row))
    except Exception:
        pass

    escola = _escolas_db.get(escola_id)
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    _check_forbidden_scope(current_user, polo_id=escola.get("polo_id"))
    escola["status"] = "inativo"
    escola["updated_at"] = _now()
    return _as_escola_response(escola)


@router.post("/polos/{polo_id}/coordenador", response_model=CoordenadorResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
async def create_coordenador(polo_id: str, payload: CoordenadorCreate):
    repo = get_auth_repository()
    usuarios = getattr(repo, "usuarios", {})
    cpf = payload.cpf.strip()
    email = str(payload.email).lower()
    if any(str(u.get("cpf", "")).strip().lower() == cpf.lower() or str(u.get("email", "")).strip().lower() == email.lower() for u in usuarios.values()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CPF ou e-mail já cadastrado no sistema.")

    user_id = str(uuid4())
    usuario = {
        "id": user_id,
        "nome": payload.nome,
        "sobrenome": "",
        "email": email,
        "cpf": cpf,
        "senha_hash": hash_password(payload.senha),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-polo",
        "polo_id": polo_id,
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    if hasattr(repo, "usuarios"):
        repo.usuarios[user_id] = usuario
    if hasattr(repo, "record_audit_log"):
        repo.record_audit_log(usuario_id=user_id, acao="coordenador_criado", entidade="usuarios", entidade_id=user_id, dados_depois={"perfil": "polo", "polo_id": polo_id})
    return CoordenadorResponse(
        id=user_id,
        nome=payload.nome,
        email=email,
        perfil="polo",
        polo_id=polo_id,
        status="ativo",
        created_at=usuario["created_at"],
    )


@router.get("/polos/{polo_id}/resumo")
async def resumo_polo(polo_id: str, current_user: UserResponse = Depends(get_current_user)):
    perfil = (current_user.perfil.nome if current_user.perfil else "").lower()
    if perfil == "polo" and str(current_user.polo_id) != str(polo_id):
        raise HTTPException(status_code=403, detail="Acesso negado a este polo.")
    if perfil not in {"admin", "polo"}:
        raise HTTPException(status_code=403, detail="Perfil não autorizado.")

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome FROM polos WHERE id = %s", (str(polo_id),))
            polo_row = cur.fetchone()
            nome_polo = polo_row["nome"] if polo_row else None

            cur.execute("SELECT count(*) as total FROM escolas WHERE polo_id = %s AND status != 'inativo'", (str(polo_id),))
            total_escolas_vinculadas = (cur.fetchone() or {}).get("total", 0)

            cur.execute("SELECT count(*) as total FROM alunos WHERE polo_id = %s AND status = 'ativo'", (str(polo_id),))
            total_alunos_ativos = (cur.fetchone() or {}).get("total", 0)

            cur.execute("SELECT count(*) as total FROM professores WHERE polo_id = %s", (str(polo_id),))
            total_professores = (cur.fetchone() or {}).get("total", 0)

            cur.execute("SELECT coalesce(sum(quantidade), 0) as total FROM licencas_atribuidas WHERE polo_id = %s", (str(polo_id),))
            licencas_no_polo = (cur.fetchone() or {}).get("total", 0)

            cur.execute("SELECT coalesce(sum(quantidade), 0) as total FROM licencas_atribuidas WHERE escola_id IN (SELECT id FROM escolas WHERE polo_id = %s)", (str(polo_id),))
            licencas_nas_escolas = (cur.fetchone() or {}).get("total", 0)

            materias_em_estoque = licencas_no_polo + licencas_nas_escolas

            return {
                "polo_id": str(polo_id),
                "nome_polo": nome_polo,
                "total_escolas_vinculadas": total_escolas_vinculadas,
                "total_alunos_ativos": total_alunos_ativos,
                "total_professores": total_professores,
                "materias_em_estoque": materias_em_estoque,
                "detalhamento": {
                    "licencas_no_polo": licencas_no_polo,
                    "licencas_nas_escolas": licencas_nas_escolas,
                },
            }
    except Exception:
        escolas = [e for e in _escolas_db.values() if str(e.get("polo_id")) == str(polo_id) and e.get("status") != "inativo"]
        total_escolas_vinculadas = len(escolas)
        total_alunos_ativos = sum(1 for a in _alunos_db.values() if str(a.get("polo_id")) == str(polo_id) and a.get("status") == "ativo")
        total_professores = sum(1 for p in _professores_db.values() if str(p.get("polo_id")) == str(polo_id) and p.get("status") != "inativo")
        licencas_no_polo = int(_licencas_estoque_db.get("polo", {}).get(str(polo_id), 0))
        licencas_nas_escolas = sum(int(_licencas_estoque_db.get("escola", {}).get(str(e["id"]), 0)) for e in escolas)
        materias_em_estoque = licencas_no_polo + licencas_nas_escolas

        return {
            "polo_id": str(polo_id),
            "nome_polo": (_polos_db.get(polo_id) or {}).get("nome"),
            "total_escolas_vinculadas": total_escolas_vinculadas,
            "total_alunos_ativos": total_alunos_ativos,
            "total_professores": total_professores,
            "materias_em_estoque": materias_em_estoque,
            "detalhamento": {
                "licencas_no_polo": licencas_no_polo,
                "licencas_nas_escolas": licencas_nas_escolas,
            },
        }


# Compatibility alias endpoints used in some legacy clients.
@router.get("/unidades/polos", response_model=List[PoloResponse])
async def legacy_list_polos(current_user: UserResponse = Depends(get_current_user)):
    return await list_polos(current_user=current_user)


@router.post("/unidades/polos", response_model=PoloResponse, status_code=status.HTTP_201_CREATED)
async def legacy_create_polo(
    payload: PoloCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    return await create_polo(payload, current_user=current_user)


@router.get("/unidades/escolas", response_model=List[EscolaResponse])
async def legacy_list_escolas(
    polo_id: str | None = None,
    current_user: UserResponse = Depends(get_current_user),
):
    if polo_id:
        return await list_escolas_by_polo(polo_id, current_user=current_user)
    return [_as_escola_response(e) for e in _escolas_db.values() if e.get("status") != "inativo"]


@router.post("/unidades/escolas", response_model=EscolaResponse, status_code=status.HTTP_201_CREATED)
async def legacy_create_escola(
    payload: EscolaCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    polo_id = payload.polo_id
    if not polo_id:
        raise HTTPException(status_code=400, detail="polo_id é obrigatório")
    return await create_escola(polo_id, payload, current_user=current_user)
