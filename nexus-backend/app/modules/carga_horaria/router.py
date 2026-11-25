"""Endpoints do módulo `carga_horaria`: Calendário Acadêmico, cronograma, andamento e frequência."""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.carga_horaria.repository import CargaHorariaRepositoryInterface, get_carga_horaria_repository
from app.modules.carga_horaria.schemas import (
    AndamentoResponse,
    CalendarioResponse,
    CalendarioWrite,
    ConclusaoResponse,
    CronogramaResponse,
    DatasLetivasResponse,
    FrequenciaResponse,
    RegrasCalendario,
)
from app.modules.carga_horaria.service import CargaHorariaService

router = APIRouter(tags=["Calendário Acadêmico & Carga Horária"])

_ADMIN = ["admin"]
_LEITURA = ["admin", "polo", "escola"]
_GERAR = ["admin", "polo"]


def get_carga_horaria_service(
    repo: CargaHorariaRepositoryInterface = Depends(get_carga_horaria_repository),
) -> CargaHorariaService:
    return CargaHorariaService(repo=repo)


# ---------------------------------------------------------------------------
# Calendário Acadêmico
# ---------------------------------------------------------------------------


@router.get("/calendarios-academicos/regras-padrao", response_model=RegrasCalendario,
            dependencies=[Depends(require_role(_LEITURA))])
async def regras_padrao():
    """Regras sugeridas para um novo calendário (padrões do documento de regras de negócio)."""
    return RegrasCalendario()


@router.get("/calendarios-academicos", response_model=List[CalendarioResponse],
            dependencies=[Depends(require_role(_LEITURA))])
async def listar_calendarios(service: CargaHorariaService = Depends(get_carga_horaria_service)):
    return service.listar_calendarios()


@router.post("/calendarios-academicos", response_model=CalendarioResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_role(_ADMIN))])
async def criar_calendario(
    dados: CalendarioWrite,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.criar_calendario(current_user, dados, ip)


@router.get("/calendarios-academicos/{calendario_id}", response_model=CalendarioResponse,
            dependencies=[Depends(require_role(_LEITURA))])
async def obter_calendario(calendario_id: uuid.UUID, service: CargaHorariaService = Depends(get_carga_horaria_service)):
    return service.obter_calendario(str(calendario_id))


@router.put("/calendarios-academicos/{calendario_id}", response_model=CalendarioResponse,
            dependencies=[Depends(require_role(_ADMIN))])
async def atualizar_calendario(
    calendario_id: uuid.UUID,
    dados: CalendarioWrite,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.atualizar_calendario(current_user, str(calendario_id), dados, ip)


@router.delete("/calendarios-academicos/{calendario_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_role(_ADMIN))])
async def excluir_calendario(
    calendario_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
) -> Response:
    service.excluir_calendario(current_user, str(calendario_id), ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/calendarios-academicos/{calendario_id}/datas-letivas", response_model=DatasLetivasResponse,
            dependencies=[Depends(require_role(_LEITURA))])
async def datas_letivas(
    calendario_id: uuid.UUID,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.datas_letivas(str(calendario_id), inicio, fim)


# ---------------------------------------------------------------------------
# Turma: cronograma, andamento, frequência e conclusão
# ---------------------------------------------------------------------------


@router.get("/turmas/{turma_id}/cronograma", response_model=CronogramaResponse,
            dependencies=[Depends(require_role(_LEITURA))])
async def obter_cronograma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.cronograma(current_user, str(turma_id))


@router.post("/turmas/{turma_id}/cronograma/gerar", response_model=CronogramaResponse,
             dependencies=[Depends(require_role(_GERAR))])
async def gerar_cronograma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.gerar_cronograma(current_user, str(turma_id), ip)


@router.get("/turmas/{turma_id}/andamento", response_model=AndamentoResponse,
            dependencies=[Depends(require_role(_LEITURA))])
async def obter_andamento(
    turma_id: uuid.UUID,
    data_referencia: Optional[date] = Query(None, description="Padrão: hoje"),
    current_user: UserResponse = Depends(get_current_user),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.andamento(current_user, str(turma_id), data_referencia)


@router.get("/turmas/{turma_id}/frequencia", response_model=FrequenciaResponse,
            dependencies=[Depends(require_role(_LEITURA))])
async def obter_frequencia(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.frequencia(current_user, str(turma_id))


@router.post("/turmas/{turma_id}/concluir", response_model=ConclusaoResponse,
             dependencies=[Depends(require_role(_ADMIN))])
async def concluir_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    ip: Optional[str] = Depends(get_client_ip),
    service: CargaHorariaService = Depends(get_carga_horaria_service),
):
    return service.concluir(current_user, str(turma_id), ip)
