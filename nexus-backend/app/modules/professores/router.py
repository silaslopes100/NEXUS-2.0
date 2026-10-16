"""Endpoints FastAPI do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.professores.repository import (
    ProfessoresRepositoryInterface,
    get_professores_repository,
)
from app.modules.professores.schemas import (
    ProfessorCreateRequest,
    ProfessorListResponse,
    ProfessorResponse,
    ProfessorUpdateRequest,
)
from app.modules.professores.service import ProfessoresService

# Professores & Docentes — a leitura é compartilhada com Polo/Escola (com
# escopo de visibilidade RN-09), a escrita é exclusiva do administrador.
_PERFIS_LEITURA = ["admin", "polo", "escola"]
_PERFIS_ESCRITA = ["admin"]

router = APIRouter(prefix="/professores", tags=["Professores & Docência"])


def get_professores_service(
    repo: ProfessoresRepositoryInterface = Depends(get_professores_repository),
) -> ProfessoresService:
    """Provedor injetável da camada de serviço de Professores."""
    return ProfessoresService(repo=repo)


def _escopo_usuario(current_user: UserResponse) -> Tuple[Optional[str], Optional[str]]:
    """RN-09: multi-tenancy — retorna (polo_id, escola_id) obrigatórios do perfil."""
    perfil = (current_user.perfil.nome if current_user.perfil else "").lower()
    if perfil == "admin":
        return None, None
    if perfil == "polo":
        if not current_user.polo_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo")
        return str(current_user.polo_id), None
    if perfil == "escola":
        if not current_user.escola_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo")
        return None, str(current_user.escola_id)
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para este recurso")


@router.get(
    "/",
    response_model=ProfessorListResponse,
    dependencies=[Depends(require_role(_PERFIS_LEITURA))],
    summary="Lista professores com filtros de busca, polo, escola, disciplina e status",
)
async def listar_professores(
    search: Optional[str] = Query(None, description="Busca por nome ou e-mail do docente"),
    polo_id: Optional[str] = Query(None),
    escola_id: Optional[str] = Query(None),
    disciplina: Optional[str] = Query(None, description="Filtra por disciplina/ministério (texto parcial)"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    escopo_polo, escopo_escola = _escopo_usuario(current_user)
    return service.list_professores(
        search=search,
        polo_id=polo_id,
        escola_id=escola_id,
        disciplina=disciplina,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        escopo_polo_id=escopo_polo,
        escopo_escola_id=escopo_escola,
    )


@router.get(
    "/{professor_id}",
    response_model=ProfessorResponse,
    dependencies=[Depends(require_role(_PERFIS_LEITURA))],
    summary="Obtém um professor pelo identificador",
)
async def obter_professor(
    professor_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    professor = service.get_professor(professor_id)
    escopo_polo, escopo_escola = _escopo_usuario(current_user)
    if escopo_polo and professor.polo_id != escopo_polo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    if escopo_escola and professor.escola_id != escopo_escola:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    return professor


@router.post(
    "/",
    response_model=ProfessorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_PERFIS_ESCRITA))],
    summary="Cadastra um novo professor/docente",
)
async def criar_professor(
    dados: ProfessorCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.create_professor(dados, actor_id=current_user.id, ip=client_ip)


@router.put(
    "/{professor_id}",
    response_model=ProfessorResponse,
    dependencies=[Depends(require_role(_PERFIS_ESCRITA))],
    summary="Atualiza o cadastro de um professor",
)
async def atualizar_professor(
    professor_id: str,
    dados: ProfessorUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.update_professor(professor_id, dados, actor_id=current_user.id, ip=client_ip)


@router.delete(
    "/{professor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_PERFIS_ESCRITA))],
    summary="Desativa um professor (soft delete: status inativo)",
)
async def deletar_professor(
    professor_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    service.delete_professor(professor_id, actor_id=current_user.id, ip=client_ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
