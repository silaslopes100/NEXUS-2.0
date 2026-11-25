"""Endpoints da Sala de Aula Virtual do aluno EAD: /ava/aluno.

Leitura (disciplina e aula) também aceita o admin, em modo pré-visualização.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Response, status

from app.modules.ava.acesso import require_ava_leitura, require_aluno_ead
from app.modules.ava.aluno_repository import get_ava_aluno_repository
from app.modules.ava.aluno_schemas import (
    AnotacaoIn,
    AnotacaoOut,
    AulaAlunoOut,
    ConclusaoOut,
    DisciplinaPlayerOut,
    HomeOut,
    NotaAulaIn,
    ProgressoIn,
)
from app.modules.ava.aluno_service import AvaAlunoService
from app.modules.ava.gamificacao.repository import get_gamificacao_repository
from app.modules.ava.gamificacao.service import GamificacaoService
from app.modules.ava.repository import get_ava_repository
from app.modules.avaliacoes.repository import get_avaliacoes_repository
from app.modules.avaliacoes.schemas import TentativaOut
from app.modules.avaliacoes.service import AvaliacoesService

router = APIRouter(prefix="/ava/aluno", tags=["AVA: Sala de Aula Virtual"])

Ctx = Dict[str, Any]


def get_service() -> AvaAlunoService:
    return AvaAlunoService(get_ava_aluno_repository(), get_ava_repository(),
                           AvaliacoesService(get_avaliacoes_repository()),
                           GamificacaoService(get_gamificacao_repository()))


@router.get("/home", response_model=HomeOut)
async def home(ctx: Ctx = Depends(require_aluno_ead), service: AvaAlunoService = Depends(get_service)):
    return service.home(ctx)


@router.get("/disciplinas/{disciplina_id}", response_model=DisciplinaPlayerOut)
async def disciplina(disciplina_id: str, ctx: Ctx = Depends(require_ava_leitura),
                     service: AvaAlunoService = Depends(get_service)):
    return service.disciplina(ctx, disciplina_id)


@router.get("/aulas/{aula_id}", response_model=AulaAlunoOut)
async def aula(aula_id: str, ctx: Ctx = Depends(require_ava_leitura), service: AvaAlunoService = Depends(get_service)):
    return service.aula(ctx, aula_id)


@router.post("/aulas/{aula_id}/progresso", response_model=Optional[ConclusaoOut])
async def progresso(aula_id: str, payload: ProgressoIn, ctx: Ctx = Depends(require_aluno_ead),
                    service: AvaAlunoService = Depends(get_service)):
    return service.progresso(ctx, aula_id, payload)


@router.post("/aulas/{aula_id}/concluir", response_model=ConclusaoOut)
async def concluir(aula_id: str, ctx: Ctx = Depends(require_aluno_ead), service: AvaAlunoService = Depends(get_service)):
    return service.concluir(ctx, aula_id)


@router.post("/aulas/{aula_id}/avaliacao/iniciar", response_model=TentativaOut)
async def iniciar_avaliacao(aula_id: str, ctx: Ctx = Depends(require_aluno_ead),
                            service: AvaAlunoService = Depends(get_service)):
    """Inicia (ou retoma) a tentativa; respostas e envio usam /avaliacoes/tentativas/{id}/…"""
    return service.iniciar_avaliacao(ctx, aula_id)


@router.put("/aulas/{aula_id}/minha-nota", status_code=status.HTTP_204_NO_CONTENT)
async def avaliar_aula(aula_id: str, payload: NotaAulaIn, ctx: Ctx = Depends(require_aluno_ead),
                       service: AvaAlunoService = Depends(get_service)):
    service.avaliar_aula(ctx, aula_id, payload.nota)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/aulas/{aula_id}/anotacoes", response_model=AnotacaoOut, status_code=status.HTTP_201_CREATED)
async def criar_anotacao(aula_id: str, payload: AnotacaoIn, ctx: Ctx = Depends(require_aluno_ead),
                         service: AvaAlunoService = Depends(get_service)):
    return service.criar_anotacao(ctx, aula_id, payload)


@router.put("/anotacoes/{anotacao_id}", response_model=AnotacaoOut)
async def atualizar_anotacao(anotacao_id: str, payload: AnotacaoIn, ctx: Ctx = Depends(require_aluno_ead),
                             service: AvaAlunoService = Depends(get_service)):
    return service.atualizar_anotacao(ctx, anotacao_id, payload)


@router.delete("/anotacoes/{anotacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_anotacao(anotacao_id: str, ctx: Ctx = Depends(require_aluno_ead),
                           service: AvaAlunoService = Depends(get_service)):
    service.excluir_anotacao(ctx, anotacao_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
