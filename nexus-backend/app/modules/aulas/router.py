"""Endpoints do módulo `aulas`.

- `/aulas/me`: Diário de Aulas do professor (ata; materiais e chamada usam os
  endpoints já existentes `/professores/me/materiais` e `/presencas/chamadas`).
- `/aulas/auditoria`: visão da diretoria de ensino (admin) sobre todos os polos.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from vercel import blob

from app.core.file_storage import delete_academic_file
from app.modules.aulas.repository import AulasRepositoryInterface, get_aulas_repository
from app.modules.aulas.schemas import (
    AtividadeDocenteResponse,
    AulaCreateRequest,
    AulaDetalhe,
    AulaListResponse,
    AulaUpdateRequest,
    DisciplinaAulasResumo,
    FiltrosAuditoriaResponse,
    MessageResponse,
)
from app.modules.aulas.service import AulasService
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse

logger = logging.getLogger(__name__)

_DOCENTES = ["admin", "professor"]
_AUDITORIA = ["admin"]

router = APIRouter(prefix="/aulas", tags=["Aulas Ministradas"])


def get_aulas_service(
    repo: AulasRepositoryInterface = Depends(get_aulas_repository),
) -> AulasService:
    return AulasService(repo=repo)


async def _limpar_arquivos(chaves: List[Optional[str]]) -> None:
    for chave in chaves:
        if not chave:
            continue
        try:
            await delete_academic_file(chave)
        except (blob.BlobError, OSError, HTTPException):
            logger.exception("Não foi possível remover o arquivo da aula excluída")


# ---------------------------------------------------------------------------
# Diário de Aulas (professor)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=AulaListResponse, dependencies=[Depends(require_role(_DOCENTES))])
async def listar_minhas_aulas(
    disciplina_id: Optional[uuid.UUID] = None,
    vinculo_id: Optional[uuid.UUID] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    q: Optional[str] = Query(default=None, max_length=255),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    filtros = {
        "disciplina_id": disciplina_id,
        "vinculo_id": vinculo_id,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "q": q,
    }
    return service.listar(current_user, filtros, limit, offset)


@router.post(
    "/me",
    response_model=AulaDetalhe,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_DOCENTES))],
)
async def registrar_aula(
    dados: AulaCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    return service.criar(current_user, dados)


@router.get("/me/{aula_id}", response_model=AulaDetalhe, dependencies=[Depends(require_role(_DOCENTES))])
async def detalhe_minha_aula(
    aula_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    return service.detalhe(current_user, str(aula_id))


@router.put("/me/{aula_id}", response_model=AulaDetalhe, dependencies=[Depends(require_role(_DOCENTES))])
async def atualizar_minha_aula(
    aula_id: uuid.UUID,
    dados: AulaUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    return service.atualizar(current_user, str(aula_id), dados)


@router.delete("/me/{aula_id}", response_model=MessageResponse, dependencies=[Depends(require_role(_DOCENTES))])
async def excluir_minha_aula(
    aula_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    chaves = service.excluir(current_user, str(aula_id))
    await _limpar_arquivos(chaves)
    return MessageResponse(message="Aula excluída com a chamada e os materiais")


@router.delete(
    "/me/{aula_id}/materiais/{material_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role(_DOCENTES))],
)
async def excluir_material_da_aula(
    aula_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    chave = service.excluir_material(current_user, str(aula_id), str(material_id))
    await _limpar_arquivos([chave])
    return MessageResponse(message="Material removido")


# ---------------------------------------------------------------------------
# Auditoria (admin / diretoria de ensino)
# ---------------------------------------------------------------------------


@router.get(
    "/auditoria",
    response_model=AulaListResponse,
    dependencies=[Depends(require_role(_AUDITORIA))],
)
async def auditoria_listar(
    disciplina_id: Optional[uuid.UUID] = None,
    polo_id: Optional[uuid.UUID] = None,
    professor_id: Optional[uuid.UUID] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    q: Optional[str] = Query(default=None, max_length=255),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: AulasService = Depends(get_aulas_service),
):
    filtros = {
        "disciplina_id": disciplina_id,
        "polo_id": polo_id,
        "professor_id": professor_id,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "q": q,
    }
    return service.listar(None, filtros, limit, offset)


@router.get(
    "/auditoria/filtros",
    response_model=FiltrosAuditoriaResponse,
    dependencies=[Depends(require_role(_AUDITORIA))],
)
async def auditoria_filtros(
    disciplina_id: Optional[uuid.UUID] = None,
    service: AulasService = Depends(get_aulas_service),
):
    return service.filtros_auditoria(str(disciplina_id) if disciplina_id else None)


@router.get(
    "/auditoria/disciplinas",
    response_model=List[DisciplinaAulasResumo],
    dependencies=[Depends(require_role(_AUDITORIA))],
)
async def auditoria_resumo_disciplinas(service: AulasService = Depends(get_aulas_service)):
    return service.resumo_disciplinas()


@router.get(
    "/auditoria/atividade",
    response_model=AtividadeDocenteResponse,
    dependencies=[Depends(require_role(_AUDITORIA))],
)
async def auditoria_atividade(
    dias: int = Query(30, ge=1, le=365),
    dias_sem_registro: int = Query(14, ge=1, le=365),
    service: AulasService = Depends(get_aulas_service),
):
    return service.atividade(dias, dias_sem_registro)


@router.get(
    "/auditoria/{aula_id}",
    response_model=AulaDetalhe,
    dependencies=[Depends(require_role(_AUDITORIA))],
)
async def auditoria_detalhe(
    aula_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: AulasService = Depends(get_aulas_service),
):
    return service.detalhe(current_user, str(aula_id))
