"""Dependências FastAPI (injeção de serviço, guards de perfil e escopo) do módulo `polos_escolas`."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.polos_escolas.repository import (
    PolosEscolasRepositoryInterface,
    get_polos_escolas_repository,
)
from app.modules.polos_escolas.service import PolosEscolasService

__all__ = [
    "get_polos_escolas_service",
    "get_client_ip",
    "require_role",
    "check_polo_scope",
    "check_escola_scope",
    "require_pedagogico_autor",
]


def get_polos_escolas_service(
    repo: PolosEscolasRepositoryInterface = Depends(get_polos_escolas_repository),
) -> PolosEscolasService:
    """Provedor injetável da camada de serviço de Polos & Escolas."""
    return PolosEscolasService(repo=repo)


def _perfil_nome(current_user: UserResponse) -> str:
    return (current_user.perfil.nome if current_user.perfil else "").lower().strip()


def check_polo_scope(current_user: UserResponse, polo_id: str) -> None:
    """RN-09: multi-tenancy — coordenador_polo só acessa o próprio polo."""
    perfil = _perfil_nome(current_user)
    if perfil in ("admin", "secretario_geral"):
        return
    if perfil == "coordenador_polo":
        if str(current_user.polo_id) != str(polo_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a este Polo")
        return
    if perfil == "secretario_escola":
        if str(current_user.polo_id) != str(polo_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a este Polo")
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para este recurso")


def check_escola_scope(current_user: UserResponse, escola_id: str) -> None:
    """RN-09: multi-tenancy — secretario_escola só acessa a própria escola."""
    perfil = _perfil_nome(current_user)
    if perfil in ("admin", "secretario_geral", "coordenador_polo"):
        return
    if perfil == "secretario_escola":
        if str(current_user.escola_id) != str(escola_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Escola")
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para este recurso")


def require_pedagogico_autor(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """RN-08: apenas professores, coordenadores, diretores e admin publicam no feed."""
    perfil = _perfil_nome(current_user)
    if perfil not in ("professor", "coordenador_polo", "secretario_escola", "admin", "diretor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado a publicar no feed pedagógico")
    return current_user
