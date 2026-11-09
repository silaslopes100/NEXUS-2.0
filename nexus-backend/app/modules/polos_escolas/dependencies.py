"""Dependências FastAPI (injeção de serviço, guards de perfil e escopo) do módulo `polos_escolas`."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.roles import perfil_do_usuario
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
    "polo_do_coordenador",
    "require_pedagogico_autor",
]


def get_polos_escolas_service(
    repo: PolosEscolasRepositoryInterface = Depends(get_polos_escolas_repository),
) -> PolosEscolasService:
    """Provedor injetável da camada de serviço de Polos & Escolas."""
    return PolosEscolasService(repo=repo)


def polo_do_coordenador(current_user: UserResponse) -> Optional[str]:
    """Retorna o polo a que o coordenador está restrito; None para os demais perfis."""
    if perfil_do_usuario(current_user) != "polo":
        return None
    if not current_user.polo_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo")
    return str(current_user.polo_id)


def check_polo_scope(current_user: UserResponse, polo_id: str) -> None:
    """RN-09: multi-tenancy — coordenador de polo só acessa o próprio polo."""
    perfil = perfil_do_usuario(current_user)
    if perfil in ("admin", "secretario_geral"):
        return
    if perfil == "polo":
        if str(current_user.polo_id) != str(polo_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a este Polo")
        return
    if perfil == "escola":
        if str(current_user.polo_id) != str(polo_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a este Polo")
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para este recurso")


def check_escola_scope(current_user: UserResponse, escola_id: str) -> None:
    """Aplica escopo de escola para secretaria e escopo de polo para coordenadores."""
    perfil = perfil_do_usuario(current_user)
    if perfil in ("admin", "secretario_geral", "polo"):
        if perfil == "polo":
            if not current_user.polo_id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo")
            escola = get_polos_escolas_repository().get_escola(escola_id)
            if escola and str(escola.get("polo_id")) != str(current_user.polo_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Escola")
        return
    if perfil == "escola":
        if str(current_user.escola_id) != str(escola_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Escola")
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para este recurso")


def require_pedagogico_autor(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """RN-08: apenas professores, coordenadores, diretores e admin publicam no feed."""
    perfil = perfil_do_usuario(current_user)
    if perfil not in ("professor", "polo", "escola", "admin", "diretor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado a publicar no feed pedagógico")
    return current_user
