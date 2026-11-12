"""Endpoints FastAPI do módulo `professores` do NEXUS 2.0."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from psycopg2 import Error as PsycopgError
from vercel import blob

from app.core.file_storage import (
    academic_file_response,
    delete_academic_file,
    store_academic_file,
)
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.professores.access import (
    exigir_vinculo_disciplina,
    exigir_vinculo_professor_disciplina,
)
from app.modules.professores.repository import (
    ProfessoresRepositoryInterface,
    get_professores_repository,
)
from app.modules.professores.schemas import (
    MessageResponse,
    ProfessorCreateRequest,
    ProfessorConteudoItem,
    ProfessorConteudosResponse,
    ProfessorDisciplinaListResponse,
    ProfessorListResponse,
    ProfessorMaterialResumo,
    ProfessorResponse,
    ProfessorTurmaVinculoCreateRequest,
    ProfessorTurmaVinculoResumo,
    ProfessorTurmaVinculosResponse,
    ProfessorUpdateRequest,
)
from app.modules.professores.service import ProfessoresService

logger = logging.getLogger(__name__)

# Professores & Docentes — a leitura é compartilhada com Polo/Escola (com
# escopo de visibilidade RN-09), a escrita é exclusiva do administrador.
_PERFIS_LEITURA = ["admin", "polo", "escola"]
_PERFIS_ESCRITA = ["admin"]

router = APIRouter(prefix="/professores", tags=["Professores & Docência"])


def get_professores_service(
    repo: ProfessoresRepositoryInterface = Depends(get_professores_repository),
) -> ProfessoresService:
    """Provedor injetável da camada de serviço de Professores."""
    return ProfessoresService(repo=repo)


def _escopo_usuario(current_user: UserResponse) -> Tuple[Optional[str], Optional[str]]:
    """RN-09: multi-tenancy — retorna (polo_id, escola_id) obrigatórios do perfil."""
    perfil = perfil_do_usuario(current_user)
    if perfil == "admin":
        return None, None
    if perfil == "polo":
        if not current_user.polo_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo")
        return str(current_user.polo_id), None
    if perfil == "escola":
        if not current_user.escola_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo")
        return None, str(current_user.escola_id)
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado para este recurso")


def _validated_external_url(url: Optional[str]) -> str:
    value = (url or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Informe um link externo válido usando HTTP ou HTTPS.",
        )
    return value


async def _media_source(
    mode: str,
    url: Optional[str],
    upload: Optional[UploadFile],
    old: Optional[Dict[str, Any]] = None,
    url_field: str = "url_arquivo",
) -> Tuple[Dict[str, Any], Optional[str]]:
    old_storage_key = old.get("arquivo_storage_key") if old else None
    has_url = bool((url or "").strip())

    if mode == "link":
        if upload or not has_url:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Escolha um link HTTP/HTTPS ou envie um arquivo.",
            )
        return (
            {
                url_field: _validated_external_url(url),
                "arquivo_storage_key": None,
                "arquivo_nome": None,
                "arquivo_mime_type": None,
                "arquivo_tamanho_bytes": None,
            },
            old_storage_key,
        )

    if mode != "arquivo" or has_url:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Escolha um link externo ou um arquivo, não ambos.",
        )
    if upload:
        stored = await store_academic_file(upload)
        return (
            {
                url_field: None,
                "arquivo_storage_key": stored.storage_key,
                "arquivo_nome": stored.filename,
                "arquivo_mime_type": stored.content_type,
                "arquivo_tamanho_bytes": stored.size_bytes,
            },
            old_storage_key,
        )
    if old_storage_key:
        return (
            {
                url_field: None,
                "arquivo_storage_key": old_storage_key,
                "arquivo_nome": old.get("arquivo_nome"),
                "arquivo_mime_type": old.get("arquivo_mime_type"),
                "arquivo_tamanho_bytes": old.get("arquivo_tamanho_bytes"),
            },
            None,
        )
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail="Selecione um arquivo para enviar.",
    )


async def _cleanup_unlinked_file(storage_key: Optional[str]) -> None:
    if not storage_key:
        return
    try:
        await delete_academic_file(storage_key)
    except (blob.BlobError, OSError, HTTPException):
        logger.exception("Não foi possível limpar arquivo acadêmico sem registro")


async def _cleanup_replaced_file(storage_key: Optional[str]) -> None:
    if not storage_key:
        return
    try:
        await delete_academic_file(storage_key)
    except (blob.BlobError, OSError, HTTPException):
        logger.exception("Não foi possível remover arquivo acadêmico substituído")


async def _download_response(row: Dict[str, Any]) -> Response:
    return await academic_file_response(row)


@router.get(
    "/",
    response_model=ProfessorListResponse,
    dependencies=[Depends(require_role(_PERFIS_LEITURA))],
    summary="Lista professores com filtros de busca, polo, escola, disciplina e status",
)
async def listar_professores(
    search: Optional[str] = Query(None, description="Busca por nome ou e-mail do docente"),
    polo_id: Optional[str] = Query(None),
    escola_id: Optional[str] = Query(None),
    disciplina: Optional[str] = Query(None, description="Filtra por disciplina/ministério (texto parcial)"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    escopo_polo, escopo_escola = _escopo_usuario(current_user)
    return service.list_professores(
        search=search,
        polo_id=polo_id,
        escola_id=escola_id,
        disciplina=disciplina,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        escopo_polo_id=escopo_polo,
        escopo_escola_id=escopo_escola,
    )


@router.get(
    "/me/disciplinas",
    response_model=ProfessorDisciplinaListResponse,
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Lista as disciplinas e turmas do docente autenticado",
)
async def listar_minhas_disciplinas_turmas(
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    return service.list_minhas_disciplinas_turmas(str(current_user.id))


@router.get(
    "/turmas/{turma_id}/vinculos",
    response_model=ProfessorTurmaVinculosResponse,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
    summary="Lista docentes vinculados a uma turma no escopo do gestor",
)
async def listar_vinculos_da_turma(
    turma_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    return service.listar_vinculos_turma(str(turma_id), current_user)


@router.post(
    "/turmas/{turma_id}/vinculos",
    response_model=ProfessorTurmaVinculoResumo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
    summary="Vincula um professor a uma disciplina de uma turma",
)
async def criar_vinculo_da_turma(
    turma_id: uuid.UUID,
    dados: ProfessorTurmaVinculoCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.criar_vinculo_turma(
        str(turma_id),
        str(dados.professor_id),
        str(dados.disciplina_id),
        current_user,
        client_ip,
    )


@router.delete(
    "/turmas/{turma_id}/vinculos/{vinculo_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role(["admin", "polo", "escola"]))],
    summary="Arquiva vínculo professor-disciplina-turma",
)
async def arquivar_vinculo_da_turma(
    turma_id: uuid.UUID,
    vinculo_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.arquivar_vinculo_turma(
        str(turma_id),
        str(vinculo_id),
        current_user,
        client_ip,
    )


@router.get(
    "/me/conteudos",
    response_model=ProfessorConteudosResponse,
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Lista conteúdos e materiais das disciplinas do docente autenticado",
)
async def listar_meus_conteudos_materiais(
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    return service.list_meus_conteudos_materiais(str(current_user.id))


@router.post(
    "/me/conteudos",
    response_model=ProfessorConteudoItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Cadastra link ou arquivo de conteúdo em uma disciplina vinculada",
)
async def criar_meu_conteudo(
    disciplina_id: str = Form(...),
    titulo: str = Form(..., min_length=1, max_length=255),
    tipo_midia: str = Form("documento", max_length=32),
    ordem: int = Form(0, ge=0),
    modo: str = Form(...),
    url_arquivo: Optional[str] = Form(None),
    arquivo: Optional[UploadFile] = File(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    exigir_vinculo_disciplina(current_user, disciplina_id)
    if not titulo.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="O título é obrigatório.")
    source, _ = await _media_source(modo, url_arquivo, arquivo)
    data = {
        "disciplina_id": disciplina_id,
        "titulo": titulo.strip(),
        "tipo_midia": tipo_midia.strip() or "documento",
        "ordem": ordem,
        **source,
    }
    new_storage_key = data.get("arquivo_storage_key")
    try:
        return service.create_conteudo(data)
    except (HTTPException, PsycopgError):
        await _cleanup_unlinked_file(new_storage_key)
        raise


@router.put(
    "/me/conteudos/{conteudo_id}",
    response_model=ProfessorConteudoItem,
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Edita conteúdo de uma disciplina vinculada",
)
async def atualizar_meu_conteudo(
    conteudo_id: uuid.UUID,
    titulo: str = Form(..., min_length=1, max_length=255),
    tipo_midia: str = Form("documento", max_length=32),
    ordem: int = Form(0, ge=0),
    modo: str = Form(...),
    url_arquivo: Optional[str] = Form(None),
    arquivo: Optional[UploadFile] = File(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    atual = service.get_conteudo(str(conteudo_id))
    exigir_vinculo_disciplina(current_user, str(atual["disciplina_id"]))
    if not titulo.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="O título é obrigatório.")
    source, replaced_storage_key = await _media_source(
        modo,
        url_arquivo,
        arquivo,
        old=atual,
    )
    data = {
        "titulo": titulo.strip(),
        "tipo_midia": tipo_midia.strip() or "documento",
        "ordem": ordem,
        **source,
    }
    new_storage_key = data.get("arquivo_storage_key")
    try:
        result = service.update_conteudo(str(conteudo_id), data)
    except (HTTPException, PsycopgError):
        if new_storage_key != atual.get("arquivo_storage_key"):
            await _cleanup_unlinked_file(new_storage_key)
        raise
    if replaced_storage_key and replaced_storage_key != new_storage_key:
        await _cleanup_replaced_file(replaced_storage_key)
    return result


@router.get(
    "/me/conteudos/{conteudo_id}/arquivo",
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Baixa arquivo de conteúdo disciplinar com autorização docente",
)
async def baixar_arquivo_conteudo_docente(
    conteudo_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    conteudo = service.get_conteudo(str(conteudo_id))
    exigir_vinculo_disciplina(current_user, str(conteudo["disciplina_id"]))
    return await _download_response(conteudo)


def _validar_vinculo_com_turma(
    current_user: UserResponse,
    professor_disciplina_id: str,
    service: ProfessoresService,
) -> Dict[str, Any]:
    vinculo = service.get_vinculo_academico(professor_disciplina_id)
    if not vinculo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vínculo acadêmico não encontrado")
    if not vinculo.get("turma_id"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Materiais docentes precisam estar vinculados a uma turma.",
        )
    exigir_vinculo_professor_disciplina(current_user, professor_disciplina_id)
    return vinculo


@router.post(
    "/me/materiais",
    response_model=ProfessorMaterialResumo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Cadastra link ou arquivo em uma turma vinculada",
)
async def criar_meu_material(
    professor_disciplina_id: str = Form(...),
    descricao: str = Form(..., min_length=1),
    modo: str = Form(...),
    url_arquivo: Optional[str] = Form(None),
    data_aula: Optional[date] = Form(None),
    expira_em: Optional[datetime] = Form(None),
    aula_id: Optional[uuid.UUID] = Form(None),
    arquivo: Optional[UploadFile] = File(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    _validar_vinculo_com_turma(current_user, professor_disciplina_id, service)
    if not descricao.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="A descrição é obrigatória.")
    if aula_id:
        # Material do Diário de Aulas: herda a data da aula a que pertence.
        # Import local: `aulas` depende de `professores.access` (evita ciclo).
        from app.modules.aulas.service import AulasService

        aula = AulasService().aula_do_material(current_user, str(aula_id), professor_disciplina_id)
        data_aula = aula["data_aula"]
    source, _ = await _media_source(
        modo,
        url_arquivo,
        arquivo,
        url_field="arquivo_url",
    )
    data = {
        "professor_disciplina_id": professor_disciplina_id,
        "descricao": descricao.strip(),
        "data_aula": data_aula,
        "expira_em": expira_em,
        **source,
    }
    if aula_id:
        data["aula_id"] = str(aula_id)
    new_storage_key = data.get("arquivo_storage_key")
    try:
        return service.create_material(data)
    except (HTTPException, PsycopgError):
        await _cleanup_unlinked_file(new_storage_key)
        raise


@router.put(
    "/me/materiais/{material_id}",
    response_model=ProfessorMaterialResumo,
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Edita material de uma turma vinculada",
)
async def atualizar_meu_material(
    material_id: uuid.UUID,
    descricao: str = Form(..., min_length=1),
    modo: str = Form(...),
    url_arquivo: Optional[str] = Form(None),
    data_aula: Optional[date] = Form(None),
    expira_em: Optional[datetime] = Form(None),
    arquivo: Optional[UploadFile] = File(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    atual = service.get_material(str(material_id))
    _validar_vinculo_com_turma(
        current_user,
        str(atual["professor_disciplina_id"]),
        service,
    )
    if not descricao.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="A descrição é obrigatória.")
    source, replaced_storage_key = await _media_source(
        modo,
        url_arquivo,
        arquivo,
        old=atual,
        url_field="arquivo_url",
    )
    data = {
        "descricao": descricao.strip(),
        "data_aula": data_aula,
        "expira_em": expira_em,
        **source,
    }
    new_storage_key = data.get("arquivo_storage_key")
    try:
        result = service.update_material(str(material_id), data)
    except (HTTPException, PsycopgError):
        if new_storage_key != atual.get("arquivo_storage_key"):
            await _cleanup_unlinked_file(new_storage_key)
        raise
    if replaced_storage_key and replaced_storage_key != new_storage_key:
        await _cleanup_replaced_file(replaced_storage_key)
    return result


@router.get(
    "/me/materiais/{material_id}/arquivo",
    dependencies=[Depends(require_role(["admin", "professor"]))],
    summary="Baixa arquivo de material de turma com autorização docente",
)
async def baixar_arquivo_material_docente(
    material_id: uuid.UUID,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    material = service.get_material(str(material_id))
    _validar_vinculo_com_turma(
        current_user,
        str(material["professor_disciplina_id"]),
        service,
    )
    return await _download_response(material)


@router.get(
    "/{professor_id}",
    response_model=ProfessorResponse,
    dependencies=[Depends(require_role(_PERFIS_LEITURA))],
    summary="Obtém um professor pelo identificador",
)
async def obter_professor(
    professor_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
):
    professor = service.get_professor(professor_id)
    escopo_polo, escopo_escola = _escopo_usuario(current_user)
    if escopo_polo and professor.polo_id != escopo_polo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    if escopo_escola and professor.escola_id != escopo_escola:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")
    return professor


@router.post(
    "/",
    response_model=ProfessorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(_PERFIS_ESCRITA))],
    summary="Cadastra um novo professor/docente",
)
async def criar_professor(
    dados: ProfessorCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.create_professor(dados, actor_id=current_user.id, ip=client_ip)


@router.put(
    "/{professor_id}",
    response_model=ProfessorResponse,
    dependencies=[Depends(require_role(_PERFIS_ESCRITA))],
    summary="Atualiza o cadastro de um professor",
)
async def atualizar_professor(
    professor_id: str,
    dados: ProfessorUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    return service.update_professor(professor_id, dados, actor_id=current_user.id, ip=client_ip)


@router.delete(
    "/{professor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(_PERFIS_ESCRITA))],
    summary="Desativa um professor (soft delete: status inativo)",
)
async def deletar_professor(
    professor_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: ProfessoresService = Depends(get_professores_service),
    client_ip: Optional[str] = Depends(get_client_ip),
):
    service.delete_professor(professor_id, actor_id=current_user.id, ip=client_ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
