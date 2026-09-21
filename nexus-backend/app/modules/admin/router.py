"""Rotas HTTP da API Administrativa do NEXUS 2.0."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.admin.dependencies import get_admin_service, require_admin_user, require_permission
from app.modules.admin.schemas import (
    AjusteEstoqueRequest,
    AlunoCreateRequest,
    AlunoDesistenteListResponse,
    AlunoDesistenteResponse,
    AlunoDetalheResponse,
    AlunoListResponse,
    AlunoResponse,
    AlunoUpdateRequest,
    AnexoAulaResponse,
    AtaResponse,
    AulaCreateRequest,
    AulaListResponse,
    AulaResponse,
    BoletoCreateRequest,
    BoletoListResponse,
    BoletoResponse,
    CertificadoDetalheResponse,
    CertificadoEmitirRequest,
    CertificadoListResponse,
    CertificadoResponse,
    ChatMensagemCreateRequest,
    ChatMensagemResponse,
    ConversaCreateRequest,
    ConversaDetalheResponse,
    ConversaListResponse,
    ConversaResponse,
    ConfiguracaoBulkUpdateRequest,
    ConfiguracaoResponse,
    ConfiguracaoSetRequest,
    ContagemResponse,
    CursoCreateRequest,
    CursoListResponse,
    CursoResponse,
    DashboardResumoResponse,
    EadCalendarioCreateRequest,
    EadCalendarioListResponse,
    EadCalendarioResponse,
    EtlErroResponse,
    EtlSyncRunListResponse,
    FeedNoticiaCreateRequest,
    FeedNoticiaListResponse,
    FeedNoticiaResponse,
    LembreteCreateRequest,
    LembreteListResponse,
    LembreteResponse,
    MatriculaEadCreateRequest,
    MatriculaEadListResponse,
    MatriculaEadResponse,
    EscolaCreateRequest,
    EscolaDetalheResponse,
    EscolaListResponse,
    EscolaResponse,
    EscolaUpdateRequest,
    HistoricoListResponse,
    LembreteCreateRequest,
    LicencaEstoqueListResponse,
    LicencaEstoqueResponse,
    LogAuditoriaListResponse,
    MateriaListResponse,
    MateriaResponse,
    MatriculaListResponse,
    MatriculaResponse,
    MessageResponse,
    ModuloCreateRequest,
    ModuloListResponse,
    ModuloResponse,
    MovimentacaoListResponse,
    MovimentacaoResponse,
    NotaCreateRequest,
    NotaResponse,
    PedidoLivroCreateRequest,
    PedidoLivroListResponse,
    PedidoLivroResponse,
    PerfilItemResponse,
    PerfilMeUpdateRequest,
    PermissaoItemResponse,
    PresencaListaRequest,
    PresencaMateriaItem,
    PresencaProfessorItem,
    PresencaResponse,
    ProfessorDetalheResponse,
    PoloCreateRequest,
    PoloDetalheResponse,
    PoloListResponse,
    PoloResponse,
    PoloUpdateRequest,
    RankingPoloItem,
    RankingPolosResponse,
    ReingressoRequest,
    RequisicaoTrocaCreateRequest,
    RequisicaoTrocaDecisaoRequest,
    RequisicaoTrocaListResponse,
    RequisicaoTrocaResponse,
    UsuarioAdminResponse,
    UsuarioCreateRequest,
    UsuarioListResponse,
    UsuarioPermissoesUpdateRequest,
    UsuarioSenhaResetRequest,
    UsuarioUpdateRequest,
    VendaCreateRequest,
    VendaListResponse,
    VendaResponse,
)
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import get_client_ip
from app.modules.auth.schemas import UserResponse

router = APIRouter(
    prefix="/admin",
    tags=["Administração Geral"],
    dependencies=[Depends(require_admin_user)],
)

router_operacional = APIRouter(
    prefix="/admin/operacional",
    tags=["Operacional"],
    dependencies=[Depends(require_admin_user)],
)


# ==========================================
# 1. CRUD de Usuários Administrativos / Staff
# ==========================================

@router.get(
    "/usuarios",
    response_model=UsuarioListResponse,
    summary="Lista usuários do sistema com filtros e paginação",
)
async def list_usuarios(
    q: Optional[str] = Query(None, description="Busca por nome, sobrenome, e-mail ou CPF"),
    perfil_id: Optional[str] = Query(None, description="Filtra por ID do perfil"),
    perfil: Optional[str] = Query(None, description="Filtra por nome do perfil (admin, polo, escola, professor, aluno)"),
    status: Optional[str] = Query(None, description="Filtra por status (ativo, inativo, bloqueado)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioListResponse:
    return service.list_usuarios(
        query=q,
        perfil_id=perfil_id,
        perfil_nome=perfil,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioAdminResponse,
    summary="Obtém detalhes completos de um usuário e suas permissões",
)
async def get_usuario(
    usuario_id: str,
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    return service.get_usuario(usuario_id)


@router.post(
    "/usuarios",
    response_model=UsuarioAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuário interno ou administrativo com perfil e permissões",
)
async def create_usuario(
    dados: UsuarioCreateRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    client_ip = get_client_ip(request)
    return service.create_usuario(
        dados=dados,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioAdminResponse,
    summary="Atualiza dados cadastrais, perfil, status ou permissões de um usuário",
)
async def update_usuario(
    usuario_id: str,
    dados: UsuarioUpdateRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    client_ip = get_client_ip(request)
    return service.update_usuario(
        user_id=usuario_id,
        dados=dados,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.put(
    "/usuarios/{usuario_id}/permissoes",
    response_model=UsuarioAdminResponse,
    summary="Atualiza a lista de permissões granulares de um usuário",
)
async def update_usuario_permissoes(
    usuario_id: str,
    dados: UsuarioPermissoesUpdateRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    client_ip = get_client_ip(request)
    return service.update_usuario_permissoes(
        user_id=usuario_id,
        dados=dados,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.post(
    "/usuarios/{usuario_id}/reset-senha",
    response_model=MessageResponse,
    summary="Redefine a senha de um usuário administrativamente com Argon2id",
)
async def reset_usuario_senha(
    usuario_id: str,
    dados: UsuarioSenhaResetRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    resultado = service.reset_usuario_senha(
        user_id=usuario_id,
        nova_senha=dados.nova_senha,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )
    return MessageResponse(message=resultado["message"])


@router.delete(
    "/usuarios/{usuario_id}",
    response_model=MessageResponse,
    summary="Exclui um usuário do sistema com registro em auditoria",
)
async def delete_usuario(
    usuario_id: str,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    client_ip = get_client_ip(request)
    resultado = service.delete_usuario(
        user_id=usuario_id,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )
    return MessageResponse(message=resultado["message"])


# ==========================================
# 2. Perfis & Permissões Granulares
# ==========================================

@router.get(
    "/perfis",
    response_model=List[PerfilItemResponse],
    summary="Lista todos os perfis de acesso cadastrados",
)
async def list_perfis(
    service: AdminService = Depends(get_admin_service),
) -> List[PerfilItemResponse]:
    return service.list_perfis()


@router.get(
    "/permissoes",
    response_model=List[PermissaoItemResponse],
    summary="Lista todas as chaves de permissões granulares disponíveis",
)
async def list_permissoes(
    service: AdminService = Depends(get_admin_service),
) -> List[PermissaoItemResponse]:
    return service.list_permissoes()


# ==========================================
# 3. Logs de Auditoria
# ==========================================

@router.get(
    "/logs-auditoria",
    response_model=LogAuditoriaListResponse,
    summary="Consulta os logs de auditoria do sistema com filtros avançados",
)
async def list_audit_logs(
    usuario_id: Optional[str] = Query(None, description="Filtra por ID do usuário executor"),
    entidade: Optional[str] = Query(None, description="Filtra por entidade (usuarios, configuracoes, etc.)"),
    acao: Optional[str] = Query(None, description="Filtra por tipo de ação (ex: login_sucesso, configuracao_atualizada)"),
    data_inicio: Optional[datetime] = Query(None, description="Data/hora inicial (ISO 8601)"),
    data_fim: Optional[datetime] = Query(None, description="Data/hora final (ISO 8601)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> LogAuditoriaListResponse:
    return service.list_audit_logs(
        usuario_id=usuario_id,
        entidade=entidade,
        acao=acao,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )


# ==========================================
# 4. Parâmetros & Configurações Gerais
# ==========================================

@router.get(
    "/configuracoes",
    response_model=List[ConfiguracaoResponse],
    summary="Lista todos os parâmetros e configurações gerais do sistema",
)
async def list_configuracoes(
    service: AdminService = Depends(get_admin_service),
) -> List[ConfiguracaoResponse]:
    return service.list_configuracoes()


@router.get(
    "/configuracoes/{chave}",
    response_model=ConfiguracaoResponse,
    summary="Obtém uma configuração específica pela chave",
)
async def get_configuracao(
    chave: str,
    service: AdminService = Depends(get_admin_service),
) -> ConfiguracaoResponse:
    return service.get_configuracao(chave)


@router.put(
    "/configuracoes/{chave}",
    response_model=ConfiguracaoResponse,
    summary="Cria ou atualiza uma configuração (chave/valor JSONB) com registro em auditoria",
)
async def set_configuracao_by_key(
    chave: str,
    payload: Dict[str, Any],
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConfiguracaoResponse:
    client_ip = get_client_ip(request)
    # Se o corpo for {"valor": ...}, extrai valor, caso contrário usa o payload inteiro
    valor = payload.get("valor", payload) if isinstance(payload, dict) and "valor" in payload else payload
    return service.set_configuracao(
        chave=chave,
        valor=valor,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


@router.put(
    "/configuracoes",
    response_model=ConfiguracaoResponse,
    summary="Cria ou atualiza uma configuração via objeto ConfiguracaoSetRequest",
)
async def set_configuracao_body(
    dados: ConfiguracaoSetRequest,
    request: Request,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConfiguracaoResponse:
    client_ip = get_client_ip(request)
    return service.set_configuracao(
        chave=dados.chave,
        valor=dados.valor,
        actor_user_id=current_admin.id,
        client_ip=client_ip,
    )


# ==========================================
# 5. Execuções do Batch de Sincronização (ETL)
# ==========================================

@router.get(
    "/etl/execucoes",
    response_model=EtlSyncRunListResponse,
    summary="Lista as execuções do batch de sincronização diária (etl_sync_runs) com status e totais",
)
async def list_etl_execucoes(
    status: Optional[str] = Query(None, description="Filtra por status da execução (ex: sucesso, erro, rodando)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> EtlSyncRunListResponse:
    return service.list_etl_execucoes(
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/etl/execucoes/{execucao_id}/erros",
    response_model=List[EtlErroResponse],
    summary="Lista os erros detalhados de uma execução do ETL",
)
async def get_etl_execucao_erros(
    execucao_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> List[EtlErroResponse]:
    return service.get_etl_execucao_erros(
        execucao_id=execucao_id,
        limit=limit,
        offset=offset,
    )


# ==========================================
# RN-01: Polos (cadastro unificado)
# ==========================================

@router_operacional.get(
    "/polos", response_model=PoloListResponse,
    summary="Lista polos com paginação e escopo RN-02",
)
async def list_polos_operacional(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    polo_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PoloListResponse:
    return service.list_polos(actor=current_admin.model_dump(), query=q, status_filter=status, polo_id=polo_id, limit=limit, offset=offset)


@router_operacional.post(
    "/polos", response_model=PoloResponse, status_code=status.HTTP_201_CREATED,
    summary="Cria polo + coordenador (RN-01)",
)
async def create_polo_operacional(
    dados: PoloCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PoloResponse:
    polo_id, _ = service.create_polo_com_usuario(actor=current_admin.model_dump(), polo_data=dados)
    return service.get_polo(actor=current_admin.model_dump(), polo_id=polo_id)


@router_operacional.get(
    "/polos/{polo_id}", response_model=PoloDetalheResponse,
    summary="Detalhe do polo",
)
async def get_polo_operacional(
    polo_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PoloDetalheResponse:
    return service.get_polo(actor=current_admin.model_dump(), polo_id=polo_id)


@router_operacional.put(
    "/polos/{polo_id}", response_model=PoloResponse,
    summary="Atualiza polo + coordenador (RN-01 sincroniza)",
)
async def update_polo_operacional(
    polo_id: str,
    dados: PoloUpdateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PoloResponse:
    service.update_polo_sincronizar_usuario(actor=current_admin.model_dump(), polo_id=polo_id, polo_data=dados)
    return service.get_polo(actor=current_admin.model_dump(), polo_id=polo_id)


@router_operacional.delete(
    "/polos/{polo_id}", response_model=MessageResponse,
    summary="Exclui polo + coordenador (RN-01)",
)
async def delete_polo_operacional(
    polo_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    service.delete_polo(actor=current_admin.model_dump(), polo_id=polo_id)
    return MessageResponse(message="Polo desativado com sucesso")

# ==========================================
# Escolas (RN-01)
# ==========================================

@router_operacional.get(
    "/escolas", response_model=EscolaListResponse,
    summary="Lista escolas com paginação e escopo RN-02",
)
async def list_escolas_operacional(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    polo_id: Optional[str] = Query(None),
    escola_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> EscolaListResponse:
    return service.list_escolas(actor=current_admin.model_dump(), query=q, status_filter=status, polo_id=polo_id, escola_id=escola_id, limit=limit, offset=offset)


@router_operacional.post(
    "/escolas", response_model=EscolaResponse, status_code=status.HTTP_201_CREATED,
    summary="Cria escola + secretário (RN-01)",
)
async def create_escola_operacional(
    dados: EscolaCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> EscolaResponse:
    escola_id, _ = service.create_escola_com_usuario(actor=current_admin.model_dump(), escola_data=dados)
    return service.get_escola(actor=current_admin.model_dump(), escola_id=escola_id)


@router_operacional.get(
    "/escolas/{escola_id}", response_model=EscolaDetalheResponse,
    summary="Detalhe da escola",
)
async def get_escola_operacional(
    escola_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> EscolaDetalheResponse:
    return service.get_escola(actor=current_admin.model_dump(), escola_id=escola_id)


@router_operacional.put(
    "/escolas/{escola_id}", response_model=EscolaResponse,
    summary="Atualiza escola + secretário (RN-01 sincroniza)",
)
async def update_escola_operacional(
    escola_id: str,
    dados: EscolaUpdateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> EscolaResponse:
    service.update_escola_sincronizar_usuario(actor=current_admin.model_dump(), escola_id=escola_id, escola_data=dados)
    return service.get_escola(actor=current_admin.model_dump(), escola_id=escola_id)


@router_operacional.delete(
    "/escolas/{escola_id}", response_model=MessageResponse,
    summary="Exclui escola + secretário (RN-01)",
)
async def delete_escola_operacional(
    escola_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    service.delete_escola(actor=current_admin.model_dump(), escola_id=escola_id)
    return MessageResponse(message="Escola desativada com sucesso")

# ==========================================
# Cursos / Módulos / Matérias
# ==========================================

@router_operacional.get("/cursos", response_model=CursoListResponse, summary="Lista cursos")
async def list_cursos_operacional(
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> CursoListResponse:
    total, rows = service.list_cursos(actor=current_admin.model_dump(), query=q, limit=limit, offset=offset)
    return CursoListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/cursos", response_model=CursoResponse, status_code=status.HTTP_201_CREATED, summary="Cria curso")
async def create_curso_operacional(
    dados: CursoCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> CursoResponse:
    curso_id = service.create_curso(actor=current_admin.model_dump(), data=dados)
    return service.get_curso(actor=current_admin.model_dump(), curso_id=curso_id)


@router_operacional.get("/cursos/{curso_id}", response_model=CursoResponse, summary="Detalhe do curso")
async def get_curso_operacional(
    curso_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> CursoResponse:
    return service.get_curso(actor=current_admin.model_dump(), curso_id=curso_id)


@router_operacional.get("/modulos", response_model=ModuloListResponse, summary="Lista módulos")
async def list_modulos_operacional(
    curso_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ModuloListResponse:
    total, rows = service.list_modulos(actor=current_admin.model_dump(), curso_id=curso_id, limit=limit, offset=offset)
    return ModuloListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/modulos/{modulo_id}", response_model=ModuloResponse, summary="Detalhe do módulo")
async def get_modulo_operacional(
    modulo_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ModuloResponse:
    return service.get_modulo(actor=current_admin.model_dump(), modulo_id=modulo_id)


@router_operacional.get("/materias", response_model=MateriaListResponse, summary="Lista matérias")
async def list_materias_operacional(
    curso_id: Optional[str] = Query(None),
    modulo_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MateriaListResponse:
    total, rows = service.list_materias(actor=current_admin.model_dump(), curso_id=curso_id, modulo_id=modulo_id, query=q, limit=limit, offset=offset)
    return MateriaListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/materias/{materia_id}", response_model=MateriaResponse, summary="Detalhe da matéria")
async def get_materia_operacional(
    materia_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MateriaResponse:
    return service.get_materia(actor=current_admin.model_dump(), materia_id=materia_id)

# ==========================================
# Alunos (RN-02 scoped)
# ==========================================

@router_operacional.get("/alunos", response_model=AlunoListResponse, summary="Lista alunos com filtros RN-02")
async def list_alunos_operacional(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    polo_id: Optional[str] = Query(None),
    escola_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AlunoListResponse:
    filtros: Dict[str, Any] = {"status": status} if status else {}
    if polo_id:
        filtros["polo_id"] = polo_id
    if escola_id:
        filtros["escola_id"] = escola_id
    total, rows = service.list_alunos(actor=current_admin.model_dump(), filtros=filtros, limit=limit, offset=offset)
    return AlunoListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/alunos", response_model=AlunoResponse, status_code=status.HTTP_201_CREATED, summary="Cria aluno")
async def create_aluno_operacional(
    dados: AlunoCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AlunoResponse:
    aluno_id, _, _ = service.create_aluno(actor=current_admin.model_dump(), aluno_data=dados)
    return service.get_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id)


@router_operacional.get("/alunos/{aluno_id}", response_model=AlunoDetalheResponse, summary="Detalhe do aluno + histórico + presenças")
async def get_aluno_operacional(
    aluno_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AlunoDetalheResponse:
    return service.get_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id)


@router_operacional.put("/alunos/{aluno_id}", response_model=AlunoResponse, summary="Atualiza aluno")
async def update_aluno_operacional(
    aluno_id: str,
    dados: AlunoUpdateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AlunoResponse:
    service.update_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id, aluno_data=dados)
    return service.get_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id)

# ==========================================
# Matrículas / Notas / Histórico
# ==========================================

@router_operacional.get("/matriculas", response_model=MatriculaListResponse, summary="Lista matrículas")
async def list_matriculas_operacional(
    polo_id: Optional[str] = Query(None),
    escola_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MatriculaListResponse:
    filtros: Dict[str, Any] = {}
    if polo_id:
        filtros["polo_id"] = polo_id
    if escola_id:
        filtros["escola_id"] = escola_id
    if status:
        filtros["status"] = status
    total, rows = service.list_matriculas(actor=current_admin.model_dump(), filtros=filtros, limit=limit, offset=offset)
    return MatriculaListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/alunos/{aluno_id}/notas", response_model=NotaResponse, status_code=status.HTTP_201_CREATED, summary="Lança nota do aluno")
async def create_nota_operacional(
    aluno_id: str,
    dados: NotaCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> NotaResponse:
    nota_id = service.create_nota_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id, data=dados)
    rows = service.list_notas_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id)
    return next((r for r in rows if getattr(r, "id", None) == nota_id), rows[0])


@router_operacional.get("/alunos/{aluno_id}/historico", response_model=HistoricoListResponse, summary="Histórico do aluno (RN-07)")
async def get_historico_operacional(
    aluno_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> HistoricoListResponse:
    return service.get_historico_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id)

# ==========================================
# Dashboard
# ==========================================

@router_operacional.get("/dashboard/resumo", response_model=DashboardResumoResponse, summary="Cards da dashboard")
async def get_dashboard_resumo(
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> DashboardResumoResponse:
    return service.get_dashboard_resumo(actor=current_admin.model_dump())


@router_operacional.get("/dashboard/polo/{polo_id}", response_model=PoloDetalheResponse, summary="Card detalhe do polo")
async def get_dashboard_polo(
    polo_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PoloDetalheResponse:
    return service.get_dashboard_polo_detalhe(actor=current_admin.model_dump(), polo_id=polo_id)


@router_operacional.get("/dashboard/escola/{escola_id}", response_model=EscolaDetalheResponse, summary="Card detalhe da escola")
async def get_dashboard_escola(
    escola_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> EscolaDetalheResponse:
    return service.get_dashboard_escola_detalhe(actor=current_admin.model_dump(), escola_id=escola_id)


@router_operacional.get("/dashboard/professor/{professor_id}", response_model=ProfessorDetalheResponse, summary="Card detalhe do professor")
async def get_dashboard_professor(
    professor_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ProfessorDetalheResponse:
    return service.get_dashboard_professor_detalhe(actor=current_admin.model_dump(), professor_id=professor_id)


@router_operacional.get("/dashboard/contagem/{visualizador}", response_model=ContagemResponse, summary="Contagem de card clicável")
async def get_contagem(
    visualizador: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ContagemResponse:
    return service.get_contagem(actor=current_admin.model_dump(), visualizador=visualizador)

# ==========================================
# EAD
# ==========================================

@router_operacional.get("/ead/matriculas", response_model=MatriculaEadListResponse, summary="Lista matrículas EAD")
async def list_ead_matriculas_operacional(
    polo_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MatriculaEadListResponse:
    filtros: Dict[str, Any] = {}
    if polo_id:
        filtros["polo_id"] = polo_id
    total, rows = service.list_ead_matriculas(actor=current_admin.model_dump(), filtros=filtros, limit=limit, offset=offset)
    return MatriculaEadListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/ead/calendario", response_model=EadCalendarioListResponse, summary="Calendário de liberação EAD")
async def get_ead_calendario_operacional(
    curso_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> EadCalendarioListResponse:
    rows = service.get_ead_calendario(actor=current_admin.model_dump(), curso_id=curso_id, limit=limit, offset=offset)
    return EadCalendarioListResponse(total=len(rows), items=rows, limit=limit, offset=offset)


@router_operacional.post("/ead/matricula", response_model=MatriculaEadResponse, status_code=status.HTTP_201_CREATED, summary="Matrícula EAD (RN-03: 2 matérias/mês)")
async def create_ead_matricula_operacional(
    dados: MatriculaEadCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MatriculaEadResponse:
    matricula_id = service.create_ead_matricula(actor=current_admin.model_dump(), data=dados)
    return service.get_ead_matricula(actor=current_admin.model_dump(), matricula_ead_id=matricula_id) if hasattr(service, "get_ead_matricula") else MatriculaEadResponse(id=matricula_id)


@router_operacional.get("/ead/feed", response_model=FeedNoticiaListResponse, summary="Feed de notícias EAD")
async def get_ead_feed_operacional(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> FeedNoticiaListResponse:
    rows = service.get_ead_feed(actor=current_admin.model_dump(), limit=limit, offset=offset)
    return FeedNoticiaListResponse(total=len(rows), items=rows, limit=limit, offset=offset)


@router_operacional.get("/ead/lembretes", response_model=LembreteListResponse, summary="Lembretes EAD")
async def get_ead_lembretes_operacional(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> LembreteListResponse:
    rows = service.get_ead_lembretes(actor=current_admin.model_dump(), limit=limit, offset=offset)
    return LembreteListResponse(total=len(rows), items=rows, limit=limit, offset=offset)

# ==========================================
# Licenças / Aulas / Presenças / Anexos / Atas
# ==========================================

@router_operacional.get("/licencas/estoque", response_model=LicencaEstoqueListResponse, summary="Estoque de licenças")
async def get_licencas_estoque_operacional(
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> LicencaEstoqueListResponse:
    total, rows = service.get_licencas_estoque(actor=current_admin.model_dump(), query=q, limit=limit, offset=offset)
    return LicencaEstoqueListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/licencas/ajustar", response_model=LicencaEstoqueResponse, summary="Ajuste manual de estoque (auditado)")
async def ajustar_licenca_operacional(
    materia_id: str,
    tipo: str,
    delta: int,
    observacao: Optional[str] = Query(None),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> LicencaEstoqueResponse:
    return service.ajustar_licenca_estoque(actor=current_admin.model_dump(), materia_id=materia_id, tipo=tipo, delta=delta, observacao=observacao)


@router_operacional.get("/licencas/movimentacoes", response_model=MovimentacaoListResponse, summary="Histórico de movimentações")
async def list_movimentacoes_operacional(
    tipo: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MovimentacaoListResponse:
    filtros: Dict[str, Any] = {}
    if tipo:
        filtros["tipo_movimento"] = tipo
    total, rows = service.list_movimentacoes(actor=current_admin.model_dump(), filtros=filtros, limit=limit, offset=offset)
    return MovimentacaoListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/aulas", response_model=AulaListResponse, summary="Lista aulas")
async def list_aulas_operacional(
    professor_id: Optional[str] = Query(None),
    materia_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AulaListResponse:
    total, rows = service.list_aulas(actor=current_admin.model_dump(), professor_id=professor_id, materia_id=materia_id, limit=limit, offset=offset)
    return AulaListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/aulas", response_model=AulaResponse, status_code=status.HTTP_201_CREATED, summary="Cria aula")
async def create_aula_operacional(
    dados: AulaCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AulaResponse:
    aula_id = service.create_aula(actor=current_admin.model_dump(), data=dados)
    return service.get_aula(actor=current_admin.model_dump(), aula_id=aula_id)


@router_operacional.get("/aulas/{aula_id}", response_model=AulaResponse, summary="Detalhe da aula")
async def get_aula_operacional(
    aula_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AulaResponse:
    return service.get_aula(actor=current_admin.model_dump(), aula_id=aula_id)


@router_operacional.post("/presencas/registrar", response_model=MessageResponse, summary="Registra presença (lista de chamada - RN-07)")
async def registrar_presenca_operacional(
    aula_id: str,
    registros: List[Dict[str, Any]],
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    service.registrar_presenca(actor=current_admin.model_dump(), aula_id=aula_id, registros=registros)
    return MessageResponse(message="Presenças registradas")


@router_operacional.get("/presencas", response_model=PresencaResponse, tags=["Presença"], summary="Lista presenças")
async def list_presencas_operacional(
    aula_id: Optional[str] = Query(None),
    aluno_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PresencaResponse:
    total, rows = service.list_presencas(actor=current_admin.model_dump(), aula_id=aula_id, aluno_id=aluno_id, limit=limit, offset=offset)
    return PresencaResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/presencas/aluno/{aluno_id}", response_model=PresencaMateriaItem, tags=["Presença"], summary="Resumo de presenças do aluno")
async def presencas_aluno_operacional(
    aluno_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PresencaMateriaItem:
    rows = service.get_presencas_resumo_aluno(actor=current_admin.model_dump(), aluno_id=aluno_id)
    return PresencaMateriaItem(aluno_id=aluno_id, presencas=rows) if rows else PresencaMateriaItem(aluno_id=aluno_id, presencas=[])


@router_operacional.get("/presencas/professor/{professor_id}", response_model=PresencaProfessorItem, tags=["Presença"], summary="Resumo de presenças por professor")
async def presencas_professor_operacional(
    professor_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PresencaProfessorItem:
    rows = service.get_presencas_resumo_professor(actor=current_admin.model_dump(), professor_id=professor_id)
    return PresencaProfessorItem(professor_id=professor_id, presencas=rows) if rows else PresencaProfessorItem(professor_id=professor_id, presencas=[])


@router_operacional.get("/anexos", response_model=AnexoAulaResponse, tags=["Aula"], summary="Lista anexos de aula")
async def list_anexos_operacional(
    aula_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AnexoAulaResponse:
    total, rows = service.list_anexos_aula(actor=current_admin.model_dump(), aula_id=aula_id, limit=limit, offset=offset)
    return AnexoAulaResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/atas", response_model=AtaResponse, tags=["Aula"], summary="Lista atas de aula")
async def list_atas_operacional(
    aula_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AtaResponse:
    total, rows = service.list_atas(actor=current_admin.model_dump(), aula_id=aula_id, limit=limit, offset=offset)
    return AtaResponse(total=total, items=rows, limit=limit, offset=offset)

# ==========================================
# Certificados (RN-05)
# ==========================================

@router_operacional.post("/certificados/emitir", response_model=CertificadoResponse, status_code=status.HTTP_201_CREATED, summary="Emite certificado (RN-05: 2 estágios + histórico)")
async def emitir_certificado_operacional(
    aluno_id: str,
    dados: CertificadoEmitirRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> CertificadoResponse:
    certificado_id = service.emitir_certificado(actor=current_admin.model_dump(), aluno_id=aluno_id, data=dados)
    return service.get_certificado(actor=current_admin.model_dump(), certificado_id=certificado_id)


@router_operacional.get("/certificados", response_model=CertificadoListResponse, summary="Lista certificados")
async def list_certificados_operacional(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> CertificadoListResponse:
    total, rows = service.list_certificados(actor=current_admin.model_dump(), limit=limit, offset=offset)
    return CertificadoListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.get("/certificados/{certificado_id}", response_model=CertificadoDetalheResponse, summary="Detalhe do certificado")
async def get_certificado_operacional(
    certificado_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> CertificadoDetalheResponse:
    return service.get_certificado(actor=current_admin.model_dump(), certificado_id=certificado_id)

# ==========================================
# Chat (RN-06)
# ==========================================

@router_operacional.get("/chat/conversas", response_model=ConversaListResponse, summary="Lista conversas")
async def list_chat_conversas_operacional(
    usuario_id: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConversaListResponse:
    total, rows = service.list_chat_conversas(actor=current_admin.model_dump(), usuario_id=usuario_id, tipo=tipo, limit=limit, offset=offset)
    return ConversaListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/chat/conversas", response_model=ConversaResponse, status_code=status.HTTP_201_CREATED, summary="Cria conversa (RN-06: proibido aluno↔aluno)")
async def create_chat_conversa_operacional(
    dados: ConversaCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConversaResponse:
    conversa_id = service.create_chat_conversa(actor=current_admin.model_dump(), data=dados)
    conv = service.get_chat_conversa(actor=current_admin.model_dump(), conversa_id=conversa_id)
    return conv


@router_operacional.get("/chat/conversa/{conversa_id}", response_model=ConversaDetalheResponse, summary="Detalhe da conversa")
async def get_chat_conversa_operacional(
    conversa_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConversaDetalheResponse:
    return service.get_chat_conversa(actor=current_admin.model_dump(), conversa_id=conversa_id)


@router_operacional.post("/chat/mensagens/{conversa_id}", response_model=ChatMensagemResponse, status_code=status.HTTP_201_CREATED, summary="Envia mensagem (RN-06)")
async def send_chat_message_operacional(
    conversa_id: str,
    conteudo: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ChatMensagemResponse:
    mensagem_id = service.create_chat_mensagem(actor=current_admin.model_dump(), conversa_id=conversa_id, data=ChatMensagemCreateRequest(conteudo=conteudo))
    return ChatMensagemResponse(id=mensagem_id, conversa_id=conversa_id, conteudo=conteudo, remetente_id=current_admin.id)


@router_operacional.post("/chat/mensagens/{mensagem_id}/marcar-lida", response_model=MessageResponse, summary="Marca mensagem como lida")
async def mark_message_read_operacional(
    mensagem_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    service.marcar_mensagem_lida(actor=current_admin.model_dump(), mensagem_id=mensagem_id)
    return MessageResponse(message="Marcada como lida")


@router_operacional.delete("/chat/admin/excluir/{conversa_id}", response_model=MessageResponse, summary="Exclui chat (admin apenas)")
async def delete_chat_admin_operacional(
    conversa_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    service.excluir_chat_admin(actor=current_admin.model_dump(), conversa_id=conversa_id)
    return MessageResponse(message="Chat excluído")


@router_operacional.get("/chat/admin/baixar/{conversa_id}", response_model=ConversaDetalheResponse, summary="Baixa conversa (admin apenas)")
async def download_chat_operacional(
    conversa_id: str,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> ConversaDetalheResponse:
    return service.baixar_conversa_admin(actor=current_admin.model_dump(), conversa_id=conversa_id)

# ==========================================
# Financeiro
# ==========================================

@router_operacional.get("/financeiro/vendas", response_model=VendaListResponse, summary="Lista vendas")
async def list_vendas_operacional(
    polo_id: Optional[str] = Query(None),
    escola_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> VendaListResponse:
    filtros: Dict[str, Any] = {}
    if polo_id:
        filtros["polo_id"] = polo_id
    if escola_id:
        filtros["escola_id"] = escola_id
    total, rows, total_valor = service.list_vendas(actor=current_admin.model_dump(), filtros=filtros, limit=limit, offset=offset)
    return VendaListResponse(total=total, items=rows, limit=limit, offset=offset, total_valor=total_valor)


@router_operacional.post("/financeiro/vendas", response_model=VendaResponse, status_code=status.HTTP_201_CREATED, summary="Cria venda")
async def create_venda_operacional(
    dados: VendaCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> VendaResponse:
    venda_id = service.create_venda(actor=current_admin.model_dump(), data=dados)
    return service.get_venda(actor=current_admin.model_dump(), venda_id=venda_id) if hasattr(service, "get_venda") else VendaResponse(id=venda_id)


@router_operacional.get("/financeiro/boletos", response_model=BoletoListResponse, summary="Lista boletos (AsaaS stub)")
async def list_boletos_operacional(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> BoletoListResponse:
    total, rows = service.list_boletos(actor=current_admin.model_dump(), filtros={}, limit=limit, offset=offset)
    return BoletoListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/financeiro/boletos", response_model=BoletoResponse, status_code=status.HTTP_201_CREATED, summary="Cria boleto (AsaaS stub)")
async def create_boleto_operacional(
    dados: BoletoCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> BoletoResponse:
    boleto_id = service.create_boleto(actor=current_admin.model_dump(), data=dados)
    return BoletoResponse(id=boleto_id, status="gerado")

# ==========================================
# Logística
# ==========================================

@router_operacional.get("/logistica/pedidos", response_model=PedidoLivroListResponse, summary="Lista pedidos de livros")
async def list_pedidos_operacional(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PedidoLivroListResponse:
    filtros: Dict[str, Any] = {}
    if status:
        filtros["status"] = status
    total, rows = service.list_pedidos_livros(actor=current_admin.model_dump(), filtros=filtros, limit=limit, offset=offset)
    return PedidoLivroListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/logistica/pedidos", response_model=PedidoLivroResponse, status_code=status.HTTP_201_CREATED, summary="Cria pedido de livros")
async def create_pedido_operacional(
    dados: PedidoLivroCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PedidoLivroResponse:
    pedido_id = service.create_pedido_livro(actor=current_admin.model_dump(), data=dados)
    return PedidoLivroResponse(id=pedido_id, status="pendente")

# ==========================================
# Churn (RN-04)
# ==========================================

@router_operacional.get("/churn", response_model=AlunoDesistenteListResponse, summary="Lista alunos desistentes")
async def list_churn_operacional(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> AlunoDesistenteListResponse:
    total, rows = service.list_churn_alunos(actor=current_admin.model_dump(), limit=limit, offset=offset)
    return AlunoDesistenteListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/churn/{aluno_id}/reativar", response_model=MessageResponse, summary="Reativa aluno churn (RN-04)")
async def reativar_churn_operacional(
    aluno_id: str,
    dados: ReingressoRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> MessageResponse:
    resultado = service.reativar_aluno_churn(actor=current_admin.model_dump(), aluno_id=aluno_id, data=dados)
    return MessageResponse(message=resultado)

# ==========================================
# Requisições de Troca
# ==========================================

@router_operacional.get("/requisicoes-troca", response_model=RequisicaoTrocaListResponse, summary="Lista requisições de troca")
async def list_requisicoes_troca_operacional(
    status: Optional[str] = Query(None),
    aluno_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> RequisicaoTrocaListResponse:
    total, rows = service.list_requisicoes_troca(actor=current_admin.model_dump(), status=status, aluno_id=aluno_id, limit=limit, offset=offset)
    return RequisicaoTrocaListResponse(total=total, items=rows, limit=limit, offset=offset)


@router_operacional.post("/requisicoes-troca", response_model=RequisicaoTrocaResponse, status_code=status.HTTP_201_CREATED, summary="Solicita troca de polo/modalidade")
async def create_requisicao_troca_operacional(
    dados: RequisicaoTrocaCreateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> RequisicaoTrocaResponse:
    req_id = service.create_requisicao_troca(actor=current_admin.model_dump(), data=dados)
    return service.get_requisicao_troca(actor=current_admin.model_dump(), requisicao_id=req_id) if hasattr(service, "get_requisicao_troca") else RequisicaoTrocaResponse(id=req_id, status="pendente")

# ==========================================
# Configurações / Perfil
# ==========================================

@router_operacional.get("/perfil", response_model=UsuarioAdminResponse, summary="Perfil do usuário logado")
async def get_perfil_operacional(
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    return service.get_usuario(actor=current_admin.model_dump(), usuario_id=current_admin.id)


@router_operacional.put("/perfil", response_model=UsuarioAdminResponse, summary="Atualiza perfil do usuário logado")
async def update_perfil_operacional(
    dados: PerfilMeUpdateRequest,
    current_admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> UsuarioAdminResponse:
    return service.update_perfil_configuracao(actor=current_admin.model_dump(), data=dados)


# ==========================================
# Exportar router_operacional para o router principal
# ==========================================

router.include_router(router_operacional)
