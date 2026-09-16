"""Endpoints FastAPI do módulo `polos_escolas` do NEXUS 2.0."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.polos_escolas import pdf as pdf_gen
from app.modules.polos_escolas.dependencies import (
    check_escola_scope,
    check_polo_scope,
    get_polos_escolas_service,
)
from app.modules.polos_escolas.schemas import (
    AlertaListResponse,
    AlunoCreateRequest,
    AlunoDesistenteListResponse,
    AlunoDrilldownEscolaListResponse,
    AlunoPoloListResponse,
    AlunoPoloResponse,
    AlunoUpdateRequest,
    AnexoAulaResponse,
    AtaResponse,
    BoletoListResponse,
    CalendarioEadCreateRequest,
    CalendarioEadResponse,
    ChamadaResponse,
    CompraLicencaListResponse,
    DashboardDrilldownResponse,
    DashboardEscolaKpisResponse,
    DashboardFunilResponse,
    DashboardPoloKpisResponse,
    DashboardTreemapResponse,
    DonutResponse,
    EscolaCreateRequest,
    EscolaListResponse,
    EscolaResponse,
    EscolaUpdateRequest,
    EvolucaoResponse,
    FeedPostCreateRequest,
    FeedPostResponse,
    LembreteCreateRequest,
    LembreteResponse,
    LicencaCompraRequest,
    LicencaDevolverEscolaRequest,
    LicencaDistribuirRequest,
    LicencaVenderRequest,
    MessageResponse,
    MigracaoModalidadeRequest,
    MovimentacaoListResponse,
    NotaCreateRequest,
    PerfilFotoResponse,
    PerfilSenhaUpdateRequest,
    PerfilUpdateRequest,
    PerfilUsuarioResponse,
    PoloCreateRequest,
    PoloListResponse,
    PoloResponse,
    PoloUpdateRequest,
    ProfessorCardResponse,
    ProfessorCreateRequest,
    ProfessorDashboardResponse,
    ProfessorListResponse,
    ProfessorUpdateRequest,
    RelatorioDrilldownResponse,
    RequisicaoListResponse,
    RequisicaoResponse,
    TopAlunoResponse,
    TreinamentoInscricaoResponse,
    TreinamentoResponse,
    TrocaPoloRequest,
)
from app.modules.polos_escolas.service import PolosEscolasService

router = APIRouter(tags=["Polos & Escolas"])

_PERFIS_GESTAO = ["admin", "secretario_geral", "coordenador_polo"]
_PERFIS_ESCOLA = _PERFIS_GESTAO + ["secretario_escola"]
_PERFIS_PROFESSOR = _PERFIS_ESCOLA + ["professor"]


# =========================================================================
# 1. Polos (RN-01)
# =========================================================================

@router.post("/polos", response_model=PoloResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "secretario_geral"]))])
async def create_polo(
    payload: PoloCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.create_polo(payload, current_user.id, client_ip)


@router.get("/polos", response_model=PoloListResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def list_polos(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_polos(limit=limit, offset=offset)


@router.get("/polos/{polo_id}", response_model=PoloResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def get_polo(
    polo_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.get_polo(polo_id)


@router.put("/polos/{polo_id}", response_model=PoloResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def update_polo(
    polo_id: str,
    payload: PoloUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.update_polo(polo_id, payload, current_user.id, client_ip)


@router.delete("/polos/{polo_id}", response_model=MessageResponse, dependencies=[Depends(require_role(["admin", "secretario_geral"]))])
async def delete_polo(
    polo_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.delete_polo(polo_id, current_user.id, client_ip)


# =========================================================================
# 2. Escolas (RN-01)
# =========================================================================

@router.post("/polos/{polo_id}/escolas", response_model=EscolaResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def create_escola(
    polo_id: str,
    payload: EscolaCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.create_escola(polo_id, payload, current_user.id, client_ip)


@router.get("/polos/{polo_id}/escolas", response_model=EscolaListResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def list_escolas(
    polo_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_escolas(polo_id=polo_id, limit=limit, offset=offset)


@router.get("/escolas/{escola_id}", response_model=EscolaResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def get_escola(
    escola_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_escola_scope(current_user, escola_id)
    return service.get_escola(escola_id)


@router.put("/escolas/{escola_id}", response_model=EscolaResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def update_escola(
    escola_id: str,
    payload: EscolaUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_escola_scope(current_user, escola_id)
    return service.update_escola(escola_id, payload, current_user.id, client_ip)


# =========================================================================
# 3. Dashboard do Polo (RN-03, RN-04)
# =========================================================================

@router.get("/polos/{polo_id}/dashboard/kpis", response_model=DashboardPoloKpisResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def dashboard_kpis_polo(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.dashboard_kpis_polo(polo_id)


@router.get("/polos/{polo_id}/dashboard/funil", response_model=DashboardFunilResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def dashboard_funil(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.dashboard_funil(polo_id)


@router.get("/polos/{polo_id}/dashboard/treemap", response_model=DashboardTreemapResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def dashboard_treemap(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.dashboard_treemap(polo_id)


@router.get("/polos/{polo_id}/dashboard/drilldown", response_model=DashboardDrilldownResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def dashboard_drilldown(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.dashboard_drilldown(polo_id)


@router.get("/polos/{polo_id}/dashboard/alertas", response_model=AlertaListResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def dashboard_alertas_polo(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.dashboard_alertas(polo_id)


# =========================================================================
# 4. Relatório Dinâmico Hierárquico
# =========================================================================

@router.get("/polos/{polo_id}/relatorios/drilldown", response_model=RelatorioDrilldownResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def relatorio_drilldown(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.relatorio_drilldown(polo_id)


@router.get("/polos/{polo_id}/relatorios/drilldown/pdf", dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def relatorio_drilldown_pdf(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    relatorio = service.relatorio_drilldown(polo_id)
    conteudo = pdf_gen.gerar_relatorio_drilldown_pdf(relatorio)
    return Response(content=conteudo, media_type="application/pdf")


# =========================================================================
# 5. Fluxo de Licenças (RN-02)
# =========================================================================

@router.post("/polos/{polo_id}/licencas/compra", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def comprar_licencas(
    polo_id: str,
    payload: LicencaCompraRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.comprar_licencas(polo_id, payload, current_user.id, client_ip)


@router.post("/polos/{polo_id}/licencas/distribuir", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def distribuir_licencas(
    polo_id: str,
    payload: LicencaDistribuirRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.distribuir_licencas(polo_id, payload, current_user.id, client_ip)


@router.post("/escolas/{escola_id}/licencas/vender", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def vender_licencas(
    escola_id: str,
    payload: LicencaVenderRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_escola_scope(current_user, escola_id)
    return service.vender_licencas(escola_id, payload, current_user.id, client_ip)


@router.post("/escolas/{escola_id}/licencas/devolver", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def devolver_licencas_escola(
    escola_id: str,
    payload: LicencaDevolverEscolaRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_escola_scope(current_user, escola_id)
    return service.devolver_escola(escola_id, payload, current_user.id, client_ip)


@router.post("/alunos/{aluno_id}/licencas/devolver", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def devolver_licenca_aluno(
    aluno_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.devolver_aluno(aluno_id, current_user.id, client_ip)


@router.get("/polos/{polo_id}/licencas/movimentacoes", response_model=MovimentacaoListResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def list_movimentacoes(
    polo_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_movimentacoes(polo_id, limit=limit, offset=offset)


# =========================================================================
# 6. Dashboard da Escola
# =========================================================================

@router.get("/escolas/{escola_id}/dashboard/kpis", response_model=DashboardEscolaKpisResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_kpis_escola(
    escola_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_escola_scope(current_user, escola_id)
    return service.dashboard_kpis_escola(escola_id)


@router.get("/escolas/{escola_id}/dashboard/donut", response_model=DonutResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_donut(
    escola_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_escola_scope(current_user, escola_id)
    return service.dashboard_donut(escola_id)


@router.get("/escolas/{escola_id}/dashboard/top-alunos", response_model=List[TopAlunoResponse], dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_top_alunos(
    escola_id: str,
    limit: int = Query(10, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_escola_scope(current_user, escola_id)
    return service.top_alunos_escola(escola_id, limit=limit)


@router.get("/escolas/{escola_id}/dashboard/alunos", response_model=AlunoDrilldownEscolaListResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_alunos_escola(
    escola_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_escola_scope(current_user, escola_id)
    return service.alunos_drilldown_escola(escola_id, limit=limit, offset=offset)


@router.get("/escolas/{escola_id}/dashboard/evolucao", response_model=EvolucaoResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_evolucao(
    escola_id: str,
    meses: int = Query(12, le=60),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_escola_scope(current_user, escola_id)
    return service.evolucao_escola(escola_id, meses=meses)


@router.get("/escolas/{escola_id}/dashboard/alertas", response_model=AlertaListResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_alertas_escola(
    escola_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_escola_scope(current_user, escola_id)
    return service.alertas_escola(escola_id)


# =========================================================================
# 7. Financeiro
# =========================================================================

@router.get("/polos/{polo_id}/financeiro/compras", response_model=CompraLicencaListResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def list_compras(
    polo_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_compras(polo_id, data_inicio, data_fim, limit, offset)


@router.get("/polos/{polo_id}/financeiro/boletos", response_model=BoletoListResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def list_boletos(
    polo_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_boletos(polo_id, data_inicio, data_fim, limit, offset)


@router.get("/polos/{polo_id}/financeiro/boletos/{boleto_id}/pdf", dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def get_boleto_pdf(
    polo_id: str,
    boleto_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    boleto = service.get_boleto(polo_id, boleto_id)
    conteudo = pdf_gen.gerar_boleto_pdf(boleto)
    return Response(content=conteudo, media_type="application/pdf")


# =========================================================================
# 8. Alunos
# =========================================================================

@router.get("/polos/{polo_id}/alunos", response_model=AlunoPoloListResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def list_alunos_polo(
    polo_id: str,
    q: Optional[str] = None,
    escola_id: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_alunos_polo(polo_id, q, escola_id, status_filter, limit, offset)


@router.put("/polos/{polo_id}/alunos/{aluno_id}", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def update_aluno(
    polo_id: str,
    aluno_id: str,
    payload: AlunoUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.update_aluno(polo_id, aluno_id, payload, current_user.id, client_ip)


@router.post("/polos/{polo_id}/alunos/{aluno_id}/notas", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def registrar_nota(
    polo_id: str,
    aluno_id: str,
    payload: NotaCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.registrar_nota(polo_id, aluno_id, payload, current_user.id, client_ip)


@router.post("/polos/{polo_id}/alunos", response_model=AlunoPoloResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def create_aluno(
    polo_id: str,
    payload: AlunoCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.create_aluno(polo_id, payload, current_user.id, client_ip)


@router.post("/polos/{polo_id}/alunos/{aluno_id}/troca-polo", response_model=RequisicaoResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def solicitar_troca_polo(
    polo_id: str,
    aluno_id: str,
    payload: TrocaPoloRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.solicitar_troca_polo(polo_id, aluno_id, payload, current_user.id, client_ip)


@router.post("/polos/{polo_id}/alunos/{aluno_id}/migracao-modalidade", response_model=RequisicaoResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def solicitar_migracao_modalidade(
    polo_id: str,
    aluno_id: str,
    payload: MigracaoModalidadeRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.solicitar_migracao_modalidade(polo_id, aluno_id, payload, current_user.id, client_ip)


@router.get("/polos/{polo_id}/requisicoes", response_model=RequisicaoListResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def list_requisicoes(
    polo_id: str,
    tipo: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_requisicoes(polo_id, tipo, status_filter, limit, offset)


@router.get("/polos/{polo_id}/alunos/desistentes", response_model=AlunoDesistenteListResponse, dependencies=[Depends(require_role(_PERFIS_GESTAO))])
async def list_alunos_desistentes(
    polo_id: str, current_user: UserResponse = Depends(get_current_user), service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    check_polo_scope(current_user, polo_id)
    return service.list_alunos_desistentes(polo_id)


# =========================================================================
# 9. Professores
# =========================================================================

@router.get("/polos/{polo_id}/professores/dashboard", response_model=ProfessorDashboardResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def dashboard_professores(
    polo_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.dashboard_professores(polo_id, data_inicio, data_fim)


@router.get("/polos/{polo_id}/professores", response_model=ProfessorListResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def list_professores(
    polo_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.list_professores(polo_id, data_inicio, data_fim, limit, offset)


@router.post("/polos/{polo_id}/professores", response_model=ProfessorCardResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def create_professor(
    polo_id: str,
    payload: ProfessorCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    check_polo_scope(current_user, polo_id)
    return service.create_professor(polo_id, payload, current_user.id, client_ip)


@router.get("/polos/{polo_id}/professores/{professor_id}", response_model=ProfessorCardResponse, dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def get_professor(
    polo_id: str,
    professor_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    check_polo_scope(current_user, polo_id)
    return service.get_professor_card(professor_id)


@router.put("/professores/{professor_id}", response_model=MessageResponse, dependencies=[Depends(require_role(_PERFIS_ESCOLA))])
async def update_professor(
    professor_id: str,
    payload: ProfessorUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.update_professor(professor_id, payload, current_user.id, client_ip)


@router.get("/professores/{professor_id}/anexos", response_model=List[AnexoAulaResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def list_anexos_professor(
    professor_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_anexos_professor(professor_id, data_inicio, data_fim)


@router.get("/professores/{professor_id}/atas", response_model=List[AtaResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def list_atas_professor(
    professor_id: str, service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    return service.list_atas_professor(professor_id)


@router.get("/professores/{professor_id}/chamada", response_model=ChamadaResponse, dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def list_chamada(
    professor_id: str,
    materia_id: str = Query(...),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_chamada(professor_id, materia_id)


# ---------- Gestão Pedagógica (RN-08) ----------

@router.post("/pedagogico/feed", response_model=FeedPostResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def create_feed_post(
    payload: FeedPostCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    perfil_nome = current_user.perfil.nome if current_user.perfil else ""
    return service.create_feed_post(payload, current_user.id, perfil_nome, client_ip)


@router.get("/pedagogico/feed", response_model=List[FeedPostResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR + ["aluno", "monitor"]))])
async def list_feed(
    polo_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_feed(polo_id, limit, offset)


@router.post("/pedagogico/lembretes", response_model=LembreteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def create_lembrete(
    payload: LembreteCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.create_lembrete(payload, current_user.id, client_ip)


@router.get("/pedagogico/lembretes", response_model=List[LembreteResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR + ["aluno", "monitor"]))])
async def list_lembretes(
    usuario_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_lembretes(usuario_id, limit, offset)


@router.post("/pedagogico/calendario-ead", response_model=CalendarioEadResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "coordenador_polo", "secretario_geral"]))])
async def create_calendario_ead(
    payload: CalendarioEadCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.create_calendario_ead(payload, current_user.id, client_ip)


@router.get("/pedagogico/calendario-ead", response_model=List[CalendarioEadResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR + ["aluno"]))])
async def list_calendario_ead(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_calendario_ead(limit, offset)


# =========================================================================
# 10. Treinamentos
# =========================================================================

@router.get("/treinamentos", response_model=List[TreinamentoResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def list_treinamentos(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.list_treinamentos(limit, offset)


@router.post("/treinamentos/{treinamento_id}/inscrever", response_model=TreinamentoInscricaoResponse, dependencies=[Depends(require_role(["professor"]))])
async def inscrever_treinamento(
    treinamento_id: str,
    professor_id: str = Query(...),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.inscrever_treinamento(treinamento_id, professor_id)


@router.get("/professores/{professor_id}/treinamentos", response_model=List[TreinamentoInscricaoResponse], dependencies=[Depends(require_role(_PERFIS_PROFESSOR))])
async def list_treinamentos_professor(
    professor_id: str, service: PolosEscolasService = Depends(get_polos_escolas_service)
):
    return service.list_treinamentos_professor(professor_id)


# =========================================================================
# 11. Perfil
# =========================================================================

@router.get("/perfil", response_model=PerfilUsuarioResponse)
async def get_perfil(
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
):
    return service.get_perfil(current_user.id)


@router.put("/perfil", response_model=PerfilUsuarioResponse)
async def update_perfil(
    payload: PerfilUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.update_perfil(current_user.id, payload, client_ip)


@router.post("/perfil/foto", response_model=PerfilFotoResponse)
async def update_foto_perfil(
    foto_url: str = Query(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.update_foto(current_user.id, foto_url, client_ip)


@router.put("/perfil/senha", response_model=MessageResponse)
async def update_senha_perfil(
    payload: PerfilSenhaUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: PolosEscolasService = Depends(get_polos_escolas_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.update_senha(current_user.id, payload, client_ip)
