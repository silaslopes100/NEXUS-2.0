"""Notificações internas (sino do topo).

Destino: um usuário, ou toda a equipe de um Polo / de uma Escola. A notificação de unidade é
compartilhada: quando alguém da unidade marca como lida, ela fica lida para a unidade.
Uso pelos outros módulos: ``notificar(titulo=..., destino_polo_id=..., link=...)``. Falha ao
notificar nunca derruba a operação principal.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.database import get_db_cursor
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse

logger = logging.getLogger(__name__)


class NotificacaoOut(BaseModel):
    id: str
    titulo: str
    mensagem: Optional[str] = None
    link: Optional[str] = None
    lida: bool = False
    criado_em: Optional[datetime] = None


class ResumoOut(BaseModel):
    nao_lidas: int


def _escopo(user: UserResponse) -> Dict[str, Optional[str]]:
    """Usuário vê as próprias e as da sua unidade (Polo para coordenação, Escola para secretaria)."""
    perfil = perfil_do_usuario(user)
    return {
        "usuario_id": str(user.id),
        "polo_id": str(user.polo_id) if perfil == "polo" and user.polo_id else None,
        "escola_id": str(user.escola_id) if perfil == "escola" and user.escola_id else None,
    }


class NotificacoesRepositoryInterface(Protocol):
    def criar(self, dados: Dict[str, Any]) -> str: ...
    def listar(self, escopo: Dict[str, Optional[str]], limite: int) -> List[Dict[str, Any]]: ...
    def contar_nao_lidas(self, escopo: Dict[str, Optional[str]]) -> int: ...
    def marcar_lida(self, notificacao_id: str, escopo: Dict[str, Optional[str]]) -> bool: ...
    def marcar_todas(self, escopo: Dict[str, Optional[str]]) -> int: ...


_FILTRO = ("(usuario_id = %s OR (%s::uuid IS NOT NULL AND destino_polo_id = %s::uuid) "
           "OR (%s::uuid IS NOT NULL AND destino_escola_id = %s::uuid))")


def _params(e: Dict[str, Optional[str]]) -> tuple:
    return (e["usuario_id"], e["polo_id"], e["polo_id"], e["escola_id"], e["escola_id"])


class PostgresNotificacoesRepository:
    def criar(self, dados: Dict[str, Any]) -> str:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO notificacoes (usuario_id, destino_polo_id, destino_escola_id, titulo, mensagem, link)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (dados.get("destino_usuario_id"), dados.get("destino_polo_id"), dados.get("destino_escola_id"),
                 dados["titulo"], dados.get("mensagem"), dados.get("link")),
            )
            return str(cur.fetchone()["id"])

    def listar(self, escopo, limite):
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT id, titulo, mensagem, link, lida_em IS NOT NULL AS lida, criado_em
                              FROM notificacoes WHERE {_FILTRO} ORDER BY criado_em DESC LIMIT %s""",
                        (*_params(escopo), limite))
            return [{**dict(r), "id": str(r["id"])} for r in cur.fetchall()]

    def contar_nao_lidas(self, escopo):
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM notificacoes WHERE lida_em IS NULL AND {_FILTRO}", _params(escopo))
            return int(cur.fetchone()["n"])

    def marcar_lida(self, notificacao_id, escopo):
        try:
            uuid.UUID(str(notificacao_id))
        except ValueError:
            return False
        with get_db_cursor() as cur:
            cur.execute(f"""UPDATE notificacoes SET lida_em = COALESCE(lida_em, now()), lida = true
                             WHERE id = %s AND {_FILTRO}""", (str(notificacao_id), *_params(escopo)))
            return cur.rowcount > 0

    def marcar_todas(self, escopo):
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE notificacoes SET lida_em = now(), lida = true WHERE lida_em IS NULL AND {_FILTRO}", _params(escopo))
            return cur.rowcount


class InMemoryNotificacoesRepository:
    def __init__(self) -> None:
        self.itens: List[Dict[str, Any]] = []

    def _visivel(self, n: Dict[str, Any], e: Dict[str, Optional[str]]) -> bool:
        return (n.get("destino_usuario_id") == e["usuario_id"]
                or (e["polo_id"] is not None and n.get("destino_polo_id") == e["polo_id"])
                or (e["escola_id"] is not None and n.get("destino_escola_id") == e["escola_id"]))

    def criar(self, dados):
        item = {**dados, "id": str(uuid.uuid4()), "lida_em": None, "criado_em": datetime.now(timezone.utc)}
        self.itens.append(item)
        return item["id"]

    def listar(self, escopo, limite):
        visiveis = [n for n in reversed(self.itens) if self._visivel(n, escopo)][:limite]
        return [{**n, "lida": n["lida_em"] is not None} for n in visiveis]

    def contar_nao_lidas(self, escopo):
        return sum(1 for n in self.itens if n["lida_em"] is None and self._visivel(n, escopo))

    def marcar_lida(self, notificacao_id, escopo):
        for n in self.itens:
            if n["id"] == notificacao_id and self._visivel(n, escopo):
                n["lida_em"] = n["lida_em"] or datetime.now(timezone.utc)
                return True
        return False

    def marcar_todas(self, escopo):
        total = 0
        for n in self.itens:
            if n["lida_em"] is None and self._visivel(n, escopo):
                n["lida_em"] = datetime.now(timezone.utc)
                total += 1
        return total


_repo: Optional[NotificacoesRepositoryInterface] = None


def get_notificacoes_repository() -> NotificacoesRepositoryInterface:
    global _repo
    if _repo is None:
        _repo = PostgresNotificacoesRepository()
    return _repo


def set_notificacoes_repository(repo: Optional[NotificacoesRepositoryInterface]) -> None:
    global _repo
    _repo = repo


def notificar(*, titulo: str, mensagem: Optional[str] = None, link: Optional[str] = None,
              destino_usuario_id: Optional[str] = None, destino_polo_id: Optional[str] = None,
              destino_escola_id: Optional[str] = None) -> Optional[str]:
    if not (destino_usuario_id or destino_polo_id or destino_escola_id):
        return None
    try:
        return get_notificacoes_repository().criar({
            "titulo": titulo[:255], "mensagem": mensagem, "link": link,
            "destino_usuario_id": destino_usuario_id, "destino_polo_id": destino_polo_id,
            "destino_escola_id": destino_escola_id,
        })
    except Exception:  # noqa: BLE001 — notificação é acessória
        logger.exception("Falha ao registrar notificação '%s'", titulo)
        return None


def notificar_perfil(perfil: str, *, titulo: str, mensagem: Optional[str] = None,
                     link: Optional[str] = None) -> int:
    """Uma notificação para cada usuário ativo do perfil (cada um marca a sua como lida)."""
    from app.core.config import settings
    from app.modules.auth.roles import nomes_equivalentes

    if not settings.PG_DSN:
        return 0
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT u.id FROM usuarios u JOIN perfis p ON p.id = u.perfil_id
                    WHERE lower(p.nome) = ANY(%s) AND COALESCE(u.status, 'ativo') = 'ativo'""",
                (list(nomes_equivalentes(perfil)),),
            )
            ids = [str(r["id"]) for r in cur.fetchall()]
    except Exception:  # noqa: BLE001 — notificação é acessória
        logger.exception("Falha ao listar usuários do perfil %s para notificar", perfil)
        return 0
    return sum(1 for uid in ids if notificar(titulo=titulo, mensagem=mensagem, link=link, destino_usuario_id=uid))


router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=List[NotificacaoOut])
async def listar(limite: int = 30, user: UserResponse = Depends(get_current_user),
                 repo: NotificacoesRepositoryInterface = Depends(get_notificacoes_repository)):
    return repo.listar(_escopo(user), max(1, min(limite, 100)))


@router.get("/resumo", response_model=ResumoOut)
async def resumo(user: UserResponse = Depends(get_current_user),
                 repo: NotificacoesRepositoryInterface = Depends(get_notificacoes_repository)):
    return ResumoOut(nao_lidas=repo.contar_nao_lidas(_escopo(user)))


@router.post("/lidas", response_model=ResumoOut)
async def marcar_todas(user: UserResponse = Depends(get_current_user),
                       repo: NotificacoesRepositoryInterface = Depends(get_notificacoes_repository)):
    repo.marcar_todas(_escopo(user))
    return ResumoOut(nao_lidas=0)


@router.post("/{notificacao_id}/lida", response_model=ResumoOut)
async def marcar_lida(notificacao_id: str, user: UserResponse = Depends(get_current_user),
                      repo: NotificacoesRepositoryInterface = Depends(get_notificacoes_repository)):
    escopo = _escopo(user)
    if not repo.marcar_lida(notificacao_id, escopo):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notificação não encontrada")
    return ResumoOut(nao_lidas=repo.contar_nao_lidas(escopo))
