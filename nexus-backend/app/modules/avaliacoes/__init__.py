"""Avaliações (questionários por Disciplina): editor do admin, prova online do aluno e base do AVA."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.avaliacoes.repository import AvaliacoesRepositoryInterface, get_avaliacoes_repository
from app.modules.avaliacoes.schemas import (
    AvaliacaoAluno,
    AvaliacaoOut,
    AvaliacaoResumo,
    AvaliacaoSalvar,
    RespostasIn,
    ResultadoOut,
    TentativaOut,
)
from app.modules.avaliacoes.service import AvaliacoesService

router = APIRouter(prefix="/avaliacoes", tags=["Avaliações"])

# Edição: admin (o editor fica em Disciplinas → Ações). Professor por disciplina vinculada fica para o AVA.
_EDITORES = ["admin"]


def get_service(repo: AvaliacoesRepositoryInterface = Depends(get_avaliacoes_repository)) -> AvaliacoesService:
    return AvaliacoesService(repo)


# --------------------------- aluno (declaradas antes das rotas /{id}) ---------------------------

@router.get("/minhas", response_model=List[AvaliacaoAluno], dependencies=[Depends(require_role(["aluno"]))])
async def minhas_avaliacoes(
    current_user: UserResponse = Depends(get_current_user),
    service: AvaliacoesService = Depends(get_service),
):
    """Disciplinas com licença ativa e a situação da avaliação de cada uma."""
    return service.minhas(current_user.id)


@router.put("/tentativas/{tentativa_id}/respostas", dependencies=[Depends(require_role(["aluno"]))])
async def salvar_respostas(
    tentativa_id: str,
    payload: RespostasIn,
    current_user: UserResponse = Depends(get_current_user),
    service: AvaliacoesService = Depends(get_service),
):
    """Salva o progresso (as respostas não se perdem se a conexão cair)."""
    return service.salvar_respostas(tentativa_id, payload.respostas, current_user.id)


@router.post("/tentativas/{tentativa_id}/finalizar", response_model=ResultadoOut, dependencies=[Depends(require_role(["aluno"]))])
async def finalizar_tentativa(
    tentativa_id: str,
    payload: Optional[RespostasIn] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: AvaliacoesService = Depends(get_service),
):
    """Corrige no servidor, grava a nota (maior nota vale; aprovado >= mínimo) e devolve o resultado."""
    return service.finalizar(tentativa_id, payload.respostas if payload else None, current_user.id)


# --------------------------- editor (admin) ---------------------------

@router.get("", response_model=List[AvaliacaoResumo], dependencies=[Depends(require_role(_EDITORES))])
async def listar(disciplina_id: Optional[str] = None, service: AvaliacoesService = Depends(get_service)):
    """Questionários cadastrados (o AVA usará esta lista para escolher o questionário da disciplina)."""
    return service.listar(disciplina_id)


@router.get("/disciplina/{disciplina_id}", response_model=Optional[AvaliacaoOut], dependencies=[Depends(require_role(_EDITORES))])
async def da_disciplina(disciplina_id: str, service: AvaliacoesService = Depends(get_service)):
    return service.da_disciplina(disciplina_id)


@router.put("/disciplina/{disciplina_id}", response_model=AvaliacaoOut, dependencies=[Depends(require_role(_EDITORES))])
async def salvar(
    disciplina_id: str,
    payload: AvaliacaoSalvar,
    current_user: UserResponse = Depends(get_current_user),
    service: AvaliacoesService = Depends(get_service),
):
    """Salva a avaliação inteira (regras + questões e alternativas) da disciplina."""
    return service.salvar(disciplina_id, payload, current_user.id)


@router.post("/{avaliacao_id}/ativar", response_model=AvaliacaoOut, dependencies=[Depends(require_role(_EDITORES))])
async def ativar(avaliacao_id: str, service: AvaliacoesService = Depends(get_service)):
    return service.definir_ativo(avaliacao_id, True)


@router.post("/{avaliacao_id}/desativar", response_model=AvaliacaoOut, dependencies=[Depends(require_role(_EDITORES))])
async def desativar(avaliacao_id: str, service: AvaliacoesService = Depends(get_service)):
    return service.definir_ativo(avaliacao_id, False)


@router.get("/{avaliacao_id}/previa", response_model=AvaliacaoOut, dependencies=[Depends(require_role(_EDITORES))])
async def previa(avaliacao_id: str, service: AvaliacoesService = Depends(get_service)):
    """Como o aluno verá (sem gabarito)."""
    return service.previa(avaliacao_id)


@router.post("/{avaliacao_id}/iniciar", response_model=TentativaOut, dependencies=[Depends(require_role(["aluno"]))])
async def iniciar(
    avaliacao_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: AvaliacoesService = Depends(get_service),
):
    """Inicia (ou retoma) a tentativa. Questões sem gabarito."""
    return service.iniciar(avaliacao_id, current_user.id)
