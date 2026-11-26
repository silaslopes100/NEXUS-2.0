"""Gestão de Matrículas EAD (admin): /ead/admin."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.ead_vendas.admin_repository import get_gestao_ead_repository
from app.modules.ead_vendas.admin_schemas import (
    AlunoEadBusca,
    FichaEadOut,
    LiberacaoIn,
    MatriculaCriadaOut,
    MatriculaEadItem,
    MatriculaManualIn,
    MatriculaPatchIn,
    MatriculasEadPage,
    MotivoIn,
    MovimentacoesPage,
    ResumoEadOut,
    TurmaEadOpcao,
)
from app.modules.ead_vendas.admin_service import GestaoEadService
from app.modules.ead_vendas.repository import get_vendas_ead_repository

router = APIRouter(prefix="/ead/admin", tags=["Vendas EAD — gestão de matrículas"],
                   dependencies=[Depends(require_role(["admin"]))])


def get_service() -> GestaoEadService:
    return GestaoEadService(get_gestao_ead_repository(), get_vendas_ead_repository())


@router.get("/resumo", response_model=ResumoEadOut)
async def resumo(data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
                 service: GestaoEadService = Depends(get_service)):
    return service.resumo(data_inicio, data_fim)


@router.get("/turmas", response_model=List[TurmaEadOpcao])
async def turmas(service: GestaoEadService = Depends(get_service)):
    return service.turmas()


@router.get("/alunos", response_model=List[AlunoEadBusca])
async def buscar_alunos(q: str = Query("", max_length=120), service: GestaoEadService = Depends(get_service)):
    return service.buscar_alunos(q)


@router.get("/matriculas", response_model=MatriculasEadPage)
async def matriculas(
    busca: Optional[str] = Query(None, max_length=120), turma_id: Optional[str] = None,
    tipo: Optional[str] = None, origem: Optional[str] = None, status_matricula: Optional[str] = Query(None, alias="status"),
    data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
    limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0),
    service: GestaoEadService = Depends(get_service),
):
    filtros = {"busca": busca, "turma_id": turma_id, "tipo": tipo, "origem": origem, "status": status_matricula,
               "data_inicio": data_inicio, "data_fim": data_fim}
    return service.matriculas(filtros, limit, offset)


@router.post("/matriculas", response_model=MatriculaCriadaOut, status_code=status.HTTP_201_CREATED)
async def matricular(payload: MatriculaManualIn, user: UserResponse = Depends(get_current_user),
                     ip: Optional[str] = Depends(get_client_ip), service: GestaoEadService = Depends(get_service)):
    return service.matricular(payload, user, ip)


@router.patch("/matriculas/{matricula_id}", response_model=MatriculaEadItem)
async def atualizar(matricula_id: str, payload: MatriculaPatchIn, user: UserResponse = Depends(get_current_user),
                    ip: Optional[str] = Depends(get_client_ip), service: GestaoEadService = Depends(get_service)):
    return service.atualizar(matricula_id, payload, user, ip)


@router.post("/matriculas/{matricula_id}/cancelar", response_model=MatriculaEadItem)
async def cancelar(matricula_id: str, payload: MotivoIn, user: UserResponse = Depends(get_current_user),
                   service: GestaoEadService = Depends(get_service)):
    return service.cancelar(matricula_id, payload.motivo, user)


@router.post("/matriculas/{matricula_id}/reativar", response_model=MatriculaEadItem)
async def reativar(matricula_id: str, user: UserResponse = Depends(get_current_user),
                   ip: Optional[str] = Depends(get_client_ip), service: GestaoEadService = Depends(get_service)):
    return service.reativar(matricula_id, user, ip)


@router.get("/alunos/{aluno_id}", response_model=FichaEadOut)
async def ficha(aluno_id: str, service: GestaoEadService = Depends(get_service)):
    return service.ficha(aluno_id)


@router.post("/alunos/{aluno_id}/disciplinas/{disciplina_id}/liberar", response_model=FichaEadOut)
async def liberar(aluno_id: str, disciplina_id: str, payload: LiberacaoIn, user: UserResponse = Depends(get_current_user),
                  service: GestaoEadService = Depends(get_service)):
    return service.liberar(aluno_id, disciplina_id, payload, user)


@router.post("/compras/{compra_id}/revogar", response_model=FichaEadOut)
async def revogar(compra_id: str, payload: MotivoIn, user: UserResponse = Depends(get_current_user),
                  ip: Optional[str] = Depends(get_client_ip), service: GestaoEadService = Depends(get_service)):
    return service.revogar(compra_id, payload.motivo, user, ip)


@router.get("/movimentacoes", response_model=MovimentacoesPage)
async def movimentacoes(
    busca: Optional[str] = Query(None, max_length=120), evento: Optional[str] = None, turma_id: Optional[str] = None,
    aluno_id: Optional[str] = None, data_inicio: Optional[date] = None, data_fim: Optional[date] = None,
    limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0),
    service: GestaoEadService = Depends(get_service),
):
    filtros = {"busca": busca, "evento": evento, "turma_id": turma_id, "aluno_id": aluno_id,
               "data_inicio": data_inicio, "data_fim": data_fim}
    return service.movimentacoes(filtros, limit, offset)
