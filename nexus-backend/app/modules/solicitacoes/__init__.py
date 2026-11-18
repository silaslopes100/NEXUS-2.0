"""Rotas: solicitações Escola → Polo e Nota de Prestação de Contas."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Response

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.polos_escolas.dependencies import check_escola_scope, check_polo_scope
from app.modules.polos_escolas.repository import get_polos_escolas_repository
from app.modules.solicitacoes.repository import get_solicitacoes_repository
from app.modules.solicitacoes.service import (
    SolicitacaoAtender,
    SolicitacaoCriar,
    SolicitacaoOut,
    SolicitacaoRecusar,
    SolicitacoesService,
)

_GESTAO = ["admin", "secretario_geral", "coordenador_polo"]
_ESCOLA = _GESTAO + ["secretario_escola"]

router = APIRouter(tags=["Solicitações Escola → Polo"])


def get_service() -> SolicitacoesService:
    return SolicitacoesService(get_solicitacoes_repository(), get_polos_escolas_repository())


@router.post("/escolas/{escola_id}/solicitacoes", response_model=SolicitacaoOut, status_code=201,
             dependencies=[Depends(require_role(_ESCOLA))])
async def criar_solicitacao(escola_id: str, payload: SolicitacaoCriar,
                            user: UserResponse = Depends(get_current_user),
                            service: SolicitacoesService = Depends(get_service),
                            ip: Optional[str] = Depends(get_client_ip)):
    """Escola pede licenças + livros (Kit Disciplina) ao seu Polo, sem pagamento online."""
    check_escola_scope(user, escola_id)
    return service.criar(escola_id, payload, user.id, ip)


@router.get("/escolas/{escola_id}/solicitacoes", response_model=List[SolicitacaoOut],
            dependencies=[Depends(require_role(_ESCOLA))])
async def solicitacoes_da_escola(escola_id: str, user: UserResponse = Depends(get_current_user),
                                 service: SolicitacoesService = Depends(get_service)):
    check_escola_scope(user, escola_id)
    return service.listar_escola(escola_id)


@router.get("/polos/{polo_id}/solicitacoes", response_model=List[SolicitacaoOut],
            dependencies=[Depends(require_role(_GESTAO))])
async def solicitacoes_do_polo(polo_id: str, status: Optional[str] = None,
                               user: UserResponse = Depends(get_current_user),
                               service: SolicitacoesService = Depends(get_service)):
    check_polo_scope(user, polo_id)
    return service.listar_polo(polo_id, status)


@router.get("/solicitacoes/{solicitacao_id}", response_model=SolicitacaoOut, dependencies=[Depends(require_role(_ESCOLA))])
async def detalhe(solicitacao_id: str, user: UserResponse = Depends(get_current_user),
                  service: SolicitacoesService = Depends(get_service)):
    return service.detalhe(service.checar_escopo(solicitacao_id, user))


@router.post("/polos/{polo_id}/solicitacoes/{solicitacao_id}/atender", response_model=SolicitacaoOut,
             dependencies=[Depends(require_role(_GESTAO))])
async def atender(polo_id: str, solicitacao_id: str, payload: SolicitacaoAtender,
                  user: UserResponse = Depends(get_current_user),
                  service: SolicitacoesService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    """Transfere as licenças do Polo para a Escola, emite a Nota e notifica a Escola."""
    check_polo_scope(user, polo_id)
    return service.atender(polo_id, solicitacao_id, payload, user.id, ip)


@router.post("/polos/{polo_id}/solicitacoes/{solicitacao_id}/recusar", response_model=SolicitacaoOut,
             dependencies=[Depends(require_role(_GESTAO))])
async def recusar(polo_id: str, solicitacao_id: str, payload: SolicitacaoRecusar,
                  user: UserResponse = Depends(get_current_user),
                  service: SolicitacoesService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    check_polo_scope(user, polo_id)
    return service.recusar(polo_id, solicitacao_id, payload, user.id, ip)


@router.post("/polos/{polo_id}/prestacoes/{nota_id}/repasse-recebido", response_model=SolicitacaoOut,
             dependencies=[Depends(require_role(_GESTAO))])
async def repasse_recebido(polo_id: str, nota_id: str, user: UserResponse = Depends(get_current_user),
                           service: SolicitacoesService = Depends(get_service),
                           ip: Optional[str] = Depends(get_client_ip)):
    check_polo_scope(user, polo_id)
    return service.repasse_recebido(polo_id, nota_id, user.id, ip)


@router.get("/solicitacoes/{solicitacao_id}/nota.pdf", dependencies=[Depends(require_role(_ESCOLA))])
async def nota_pdf(solicitacao_id: str, user: UserResponse = Depends(get_current_user),
                   service: SolicitacoesService = Depends(get_service)):
    s = service.checar_escopo(solicitacao_id, user)
    conteudo = service.nota_pdf(s)
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{s.get("nota_numero") or "nota"}.pdf"',
                             "Cache-Control": "private, no-store"})
