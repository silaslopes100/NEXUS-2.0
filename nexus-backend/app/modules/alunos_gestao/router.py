"""Rotas da Central de Alunos."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.alunos_gestao.repository import (
    AlunosGestaoRepositoryInterface,
    get_alunos_gestao_repository,
)
from app.modules.alunos_gestao.schemas import (
    AcademicoResponse,
    AlunoGestaoListResponse,
    CursoAprendizadoResponse,
    MessageResponse,
    Observacao,
    ReingressoRequest,
    ReingressoResponse,
)
from app.modules.alunos_gestao.service import AlunosGestaoService
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.transferencias.service import ator_de

_APROVADORES = ["admin", "secretario_geral"]
_GESTAO = [*_APROVADORES, "polo", "escola"]

router = APIRouter(prefix="/alunos/gestao", tags=["Central de Alunos"])
router_aprendizado = APIRouter(
    prefix="/alunos/aprendizado",
    tags=["Central de Alunos"],
    dependencies=[Depends(require_role(["aluno"]))],
)


def get_alunos_gestao_service(
    repo: AlunosGestaoRepositoryInterface = Depends(get_alunos_gestao_repository),
) -> AlunosGestaoService:
    return AlunosGestaoService(repo=repo)


@router.get("", response_model=AlunoGestaoListResponse, dependencies=[Depends(require_role(_GESTAO))])
async def listar_alunos(
    polo_id: Optional[uuid.UUID] = None,
    escola_id: Optional[uuid.UUID] = None,
    somente_ead: bool = False,
    observacao: Optional[Observacao] = None,
    q: Optional[str] = Query(default=None, max_length=255),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
):
    return service.listar(
        ator_de(current_user),
        str(polo_id) if polo_id else None,
        str(escola_id) if escola_id else None,
        somente_ead,
        observacao,
        q,
        limit,
        offset,
    )


@router.get(
    "/{aluno_id}/academico",
    response_model=AcademicoResponse,
    dependencies=[Depends(require_role(_GESTAO))],
)
async def academico_aluno(
    aluno_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
):
    return service.academico(ator_de(current_user), str(aluno_id))


@router.post(
    "/{aluno_id}/churn",
    response_model=MessageResponse,
    dependencies=[Depends(require_role(_APROVADORES))],
)
async def confirmar_churn(
    aluno_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    service.confirmar_churn(str(aluno_id), current_user.id, client_ip)
    return MessageResponse(message="Aluno enviado para o Churn")


@router.post(
    "/{aluno_id}/reingresso",
    response_model=ReingressoResponse,
    dependencies=[Depends(require_role(_APROVADORES))],
)
async def reingressar_aluno(
    aluno_id: uuid.UUID,
    dados: ReingressoRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.reingressar(str(aluno_id), dados, current_user.id, client_ip)


@router_aprendizado.get("", response_model=List[CursoAprendizadoResponse])
async def meu_aprendizado(
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
):
    return service.aprendizado(current_user.id)


@router_aprendizado.put("/conteudos/{conteudo_id}/concluido", response_model=MessageResponse)
async def concluir_conteudo(
    conteudo_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
):
    service.marcar_conteudo(current_user.id, str(conteudo_id), True)
    return MessageResponse(message="Conteúdo concluído")


@router_aprendizado.delete("/conteudos/{conteudo_id}/concluido", response_model=MessageResponse)
async def desmarcar_conteudo(
    conteudo_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AlunosGestaoService = Depends(get_alunos_gestao_service),
):
    service.marcar_conteudo(current_user.id, str(conteudo_id), False)
    return MessageResponse(message="Conclusão removida")
