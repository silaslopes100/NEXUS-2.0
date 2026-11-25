"""Rotas da ficha cadastral do usuário: edição por seção, inativação, exclusão e histórico."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.modules.admin.dependencies import get_admin_service, require_admin_user
from app.modules.admin.ficha_schemas import (
    AbaHistorico,
    AcessoUpdate,
    ContatoEmergenciaUpdate,
    DadosPessoaisUpdate,
    EnderecoUpdate,
    HistoricoResponse,
    IdentificacaoUpdate,
    InativarRequest,
    PodeExcluirResponse,
    VinculoAlunoUpdate,
    VinculoProfessorUpdate,
)
from app.modules.admin.schemas import UsuarioAdminResponse
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import get_client_ip
from app.modules.auth.schemas import UserResponse

router = APIRouter(
    prefix="/admin/usuarios/{usuario_id}",
    tags=["Administração Geral — Ficha do usuário"],
    dependencies=[Depends(require_admin_user)],
)


@router.put("/identificacao", response_model=UsuarioAdminResponse, summary="Nome, e-mail, CPF e telefones")
async def atualizar_identificacao(
    usuario_id: str,
    dados: IdentificacaoUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_identificacao(usuario_id, dados, admin.id, ip)


@router.put("/dados-pessoais", response_model=UsuarioAdminResponse,
            summary="Nascimento, documentos, sexo, estado civil e naturalidade")
async def atualizar_dados_pessoais(
    usuario_id: str,
    dados: DadosPessoaisUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_dados_pessoais(usuario_id, dados, admin.id, ip)


@router.put("/endereco", response_model=UsuarioAdminResponse, summary="Endereço do usuário")
async def atualizar_endereco(
    usuario_id: str,
    dados: EnderecoUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_endereco(usuario_id, dados, admin.id, ip)


@router.put("/contato-emergencia", response_model=UsuarioAdminResponse, summary="Contato de emergência")
async def atualizar_contato_emergencia(
    usuario_id: str,
    dados: ContatoEmergenciaUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_contato_emergencia(usuario_id, dados, admin.id, ip)


@router.put("/acesso", response_model=UsuarioAdminResponse, summary="Perfil, polo/escola e permissões")
async def atualizar_acesso(
    usuario_id: str,
    dados: AcessoUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_acesso(usuario_id, dados, admin.id, ip)


@router.put("/vinculo-aluno", response_model=UsuarioAdminResponse,
            summary="Matrícula e nascimento do aluno (polo/escola: via transferência)")
async def atualizar_vinculo_aluno(
    usuario_id: str,
    dados: VinculoAlunoUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_vinculo_aluno(usuario_id, dados, admin.id, ip)


@router.put("/vinculo-professor", response_model=UsuarioAdminResponse,
            summary="Lotação, valor da hora-aula, chave PIX e status do professor")
async def atualizar_vinculo_professor(
    usuario_id: str,
    dados: VinculoProfessorUpdate,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.atualizar_vinculo_professor(usuario_id, dados, admin.id, ip)


@router.post("/inativar", response_model=UsuarioAdminResponse,
             summary="Inativa ou bloqueia o usuário com motivo e encerra as sessões")
async def inativar_usuario(
    usuario_id: str,
    dados: InativarRequest,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.inativar_usuario(usuario_id, dados, admin.id, ip)


@router.post("/reativar", response_model=UsuarioAdminResponse, summary="Reativa um usuário inativo ou bloqueado")
async def reativar_usuario(
    usuario_id: str,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
    ip: Optional[str] = Depends(get_client_ip),
) -> UsuarioAdminResponse:
    return service.reativar_usuario(usuario_id, admin.id, ip)


@router.get("/pode-excluir", response_model=PodeExcluirResponse,
            summary="Diz se a exclusão definitiva é permitida (só sem histórico)")
async def pode_excluir(
    usuario_id: str,
    admin: UserResponse = Depends(require_admin_user),
    service: AdminService = Depends(get_admin_service),
) -> PodeExcluirResponse:
    return service.pode_excluir(usuario_id, admin.id)


@router.get("/historico/{aba}", response_model=HistoricoResponse,
            summary="Histórico acadêmico, financeiro, de movimentações ou de auditoria")
async def historico_usuario(
    usuario_id: str,
    aba: AbaHistorico,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: AdminService = Depends(get_admin_service),
) -> HistoricoResponse:
    return service.historico_usuario(usuario_id, aba, limit, offset)
