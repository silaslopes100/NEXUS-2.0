"""Módulo de Comunicação, Mensageria (Chat), Feed e Notificações do NEXUS 2.0."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/comunicacao", tags=["Comunicação, Chat & Feed"])


class ConversaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    tipo: str = "individual"
    criada_em: Optional[datetime] = None
    encerrada_em: Optional[datetime] = None


class MensagemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    conversa_id: str
    remetente_id: Optional[str] = None
    texto: str
    lida_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None


class FeedPostSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    autor_id: Optional[str] = None
    titulo: Optional[str] = None
    conteudo: str
    criado_em: Optional[datetime] = None


class LembreteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    usuario_destino_id: Optional[str] = None
    perfil_destino: Optional[str] = None
    titulo: Optional[str] = None
    mensagem: str
    exibir_de: Optional[date] = None
    exibir_ate: Optional[date] = None


_conversas_db: Dict[str, Dict[str, Any]] = {}
_mensagens_db: Dict[str, Dict[str, Any]] = {}
_feed_db: Dict[str, Dict[str, Any]] = {}
_lembretes_db: Dict[str, Dict[str, Any]] = {}


@router.get("/conversas", response_model=List[ConversaSchema])
async def list_conversas():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, tipo, criada_em, encerrada_em FROM conversas")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_conversas_db.values())


@router.post("/conversas", response_model=ConversaSchema, status_code=status.HTTP_201_CREATED)
async def create_conversa(dados: ConversaSchema):
    new_id = str(uuid.uuid4())
    c_dict = dados.model_dump()
    c_dict["id"] = new_id
    c_dict["criada_em"] = datetime.now(timezone.utc)
    try:
        with get_db_cursor() as cur:
            cur.execute("INSERT INTO conversas (id, tipo, criada_em, criado_em, atualizado_em) VALUES (%s, %s, now(), now(), now())", (new_id, dados.tipo))
    except Exception:
        _conversas_db[new_id] = c_dict
    return c_dict


@router.get("/conversas/{conversa_id}/mensagens", response_model=List[MensagemSchema])
async def list_mensagens(conversa_id: str):
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, conversa_id, remetente_id, texto, lida_em, criado_em FROM mensagens WHERE conversa_id = %s ORDER BY criado_em ASC", (conversa_id,))
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return [m for m in _mensagens_db.values() if m.get("conversa_id") == conversa_id]


@router.post("/conversas/{conversa_id}/mensagens", response_model=MensagemSchema, status_code=status.HTTP_201_CREATED)
async def send_mensagem(conversa_id: str, texto: str, current_user: UserResponse = Depends(get_current_user)):
    new_id = str(uuid.uuid4())
    m_dict = {
        "id": new_id,
        "conversa_id": conversa_id,
        "remetente_id": current_user.id,
        "texto": texto,
        "lida_em": None,
        "criado_em": datetime.now(timezone.utc),
    }
    try:
        with get_db_cursor() as cur:
            cur.execute("INSERT INTO mensagens (id, conversa_id, remetente_id, texto, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, now(), now())", (new_id, conversa_id, current_user.id, texto))
    except Exception:
        _mensagens_db[new_id] = m_dict
    return m_dict


@router.get("/feed", response_model=List[FeedPostSchema])
async def list_feed():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, autor_id, titulo, conteudo, criado_em FROM feed_posts ORDER BY criado_em DESC")
            return [dict(r) for r in cur.fetchall()]
    except Exception:
        return list(_feed_db.values())


@router.post("/feed", response_model=FeedPostSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "polo", "professor"]))])
async def create_feed_post(dados: FeedPostSchema, current_user: UserResponse = Depends(get_current_user)):
    new_id = str(uuid.uuid4())
    f_dict = dados.model_dump()
    f_dict["id"] = new_id
    f_dict["autor_id"] = current_user.id
    f_dict["criado_em"] = datetime.now(timezone.utc)
    try:
        with get_db_cursor() as cur:
            cur.execute("INSERT INTO feed_posts (id, autor_id, titulo, conteudo, criado_em, atualizado_em) VALUES (%s, %s, %s, %s, now(), now())", (new_id, current_user.id, dados.titulo, dados.conteudo))
    except Exception:
        _feed_db[new_id] = f_dict
    return f_dict
