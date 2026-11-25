"""Endpoints da gamificação do aluno EAD: /ava/gamificacao."""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.ava.acesso import require_aluno_ead
from app.modules.ava.gamificacao.repository import get_gamificacao_repository
from app.modules.ava.gamificacao.schemas import PerfilGamificacaoOut, PreferenciasIn, RankingOut
from app.modules.ava.gamificacao.service import GamificacaoService

router = APIRouter(prefix="/ava/gamificacao", tags=["AVA: Gamificação"])


def get_service() -> GamificacaoService:
    return GamificacaoService(get_gamificacao_repository())


@router.get("/perfil", response_model=PerfilGamificacaoOut)
async def perfil(ctx: Dict[str, Any] = Depends(require_aluno_ead), service: GamificacaoService = Depends(get_service)):
    """XP, nível, sequência de dias, conquistas (obtidas e bloqueadas) e histórico recente."""
    return service.perfil(str(ctx["user"].id))


@router.get("/ranking", response_model=RankingOut)
async def ranking(periodo: Literal["semana", "geral"] = "semana", curso_id: Optional[str] = None,
                  limite: int = Query(10, ge=3, le=50),
                  ctx: Dict[str, Any] = Depends(require_aluno_ead), service: GamificacaoService = Depends(get_service)):
    """Ranking do curso (semana corrente ou geral). Nomes abreviados; quem saiu do ranking não aparece."""
    return service.ranking(str(ctx["user"].id), periodo, curso_id, limite)


@router.put("/preferencias", status_code=status.HTTP_204_NO_CONTENT)
async def preferencias(payload: PreferenciasIn, ctx: Dict[str, Any] = Depends(require_aluno_ead),
                       service: GamificacaoService = Depends(get_service)):
    service.definir_ranking_visivel(str(ctx["user"].id), payload.ranking_visivel)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
