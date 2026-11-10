"""Rotas de Transferências Acadêmicas."""
from __future__ import annotations

import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.transferencias.repository import (
    TransferenciasRepositoryInterface,
    get_transferencias_repository,
)
from app.modules.transferencias.schemas import (
    AlunoElegivelResponse,
    OpcaoResponse,
    PendenciasResumoResponse,
    TipoTransferencia,
    TransferenciaCreateRequest,
    TransferenciaListResponse,
    TransferenciaResolverRequest,
    TransferenciaResponse,
)
from app.modules.transferencias.service import TransferenciasService, ator_de

router = APIRouter(prefix="/transferencias", tags=["Transferências Acadêmicas"])

_APROVADORES = ["admin", "secretario_geral"]
_UNIDADES = ["polo", "escola"]
_SOLICITANTES = [*_UNIDADES, "aluno"]

EscopoAluno = Optional[Literal["aluno"]]
StatusTransferencia = Literal["pendente", "aprovada", "rejeitada", "churn"]


def get_transferencias_service(
    repo: TransferenciasRepositoryInterface = Depends(get_transferencias_repository),
) -> TransferenciasService:
    return TransferenciasService(repo=repo)


@router.get(
    "",
    response_model=TransferenciaListResponse,
    dependencies=[Depends(require_role([*_APROVADORES, *_SOLICITANTES]))],
)
async def list_transferencias(
    status_filter: Optional[StatusTransferencia] = Query(default=None, alias="status"),
    tipo: Optional[TipoTransferencia] = None,
    q: Optional[str] = Query(default=None, max_length=255),
    escopo: EscopoAluno = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferenciasService = Depends(get_transferencias_service),
):
    return service.listar(ator_de(current_user, escopo), status_filter, tipo, q, limit, offset)


@router.post(
    "",
    response_model=TransferenciaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_SOLICITANTES))],
)
async def solicitar_transferencia(
    dados: TransferenciaCreateRequest,
    escopo: EscopoAluno = None,
    current_user: UserResponse = Depends(get_current_user),
    service: TransferenciasService = Depends(get_transferencias_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.criar(ator_de(current_user, escopo), dados, client_ip)


@router.get(
    "/meu-cadastro",
    response_model=AlunoElegivelResponse,
    dependencies=[Depends(require_role(["aluno"]))],
)
async def meu_cadastro(
    current_user: UserResponse = Depends(get_current_user),
    service: TransferenciasService = Depends(get_transferencias_service),
):
    return service.meu_cadastro(ator_de(current_user, "aluno"))


@router.get(
    "/alunos",
    response_model=List[AlunoElegivelResponse],
    dependencies=[Depends(require_role(_UNIDADES))],
)
async def buscar_alunos(
    q: str = Query(min_length=3, max_length=255),
    desistentes: bool = False,
    current_user: UserResponse = Depends(get_current_user),
    service: TransferenciasService = Depends(get_transferencias_service),
):
    return service.buscar_alunos(ator_de(current_user), q, desistentes)


@router.get(
    "/opcoes/polos",
    response_model=List[OpcaoResponse],
    dependencies=[Depends(require_role([*_APROVADORES, *_SOLICITANTES]))],
)
async def opcoes_polos(service: TransferenciasService = Depends(get_transferencias_service)):
    return service.listar_polos()


@router.get(
    "/opcoes/polos/{polo_id}/escolas",
    response_model=List[OpcaoResponse],
    dependencies=[Depends(require_role([*_APROVADORES, *_SOLICITANTES]))],
)
async def opcoes_escolas(
    polo_id: uuid.UUID,
    service: TransferenciasService = Depends(get_transferencias_service),
):
    return service.listar_escolas(str(polo_id))


@router.get(
    "/pendentes/resumo",
    response_model=PendenciasResumoResponse,
    dependencies=[Depends(require_role(_APROVADORES))],
)
async def resumo_pendentes(service: TransferenciasService = Depends(get_transferencias_service)):
    return service.resumo_pendentes()


@router.put(
    "/{transferencia_id}/resolver",
    response_model=TransferenciaResponse,
    dependencies=[Depends(require_role(_APROVADORES))],
)
async def resolver_transferencia(
    transferencia_id: uuid.UUID,
    dados: TransferenciaResolverRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: TransferenciasService = Depends(get_transferencias_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.resolver(str(transferencia_id), dados, current_user.id, client_ip)
