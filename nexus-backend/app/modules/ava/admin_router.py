"""Endpoints do gestor de conteúdo do AVA (admin): /ava/admin."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.modules.auth.dependencies import require_role
from app.modules.ava.repository import get_ava_repository
from app.modules.ava.schemas import (
    AulaCreateIn,
    AulaIn,
    AulaOut,
    AvaliacaoOpcaoOut,
    CapituloIn,
    CapituloOut,
    ConfigIn,
    ConfigOut,
    DisciplinaAvaOut,
    EmbedIn,
    EmbedOut,
    EstruturaOut,
    ItemIn,
    ItemOut,
    ReordenarIn,
    UploadIn,
    UploadOut,
)
from app.modules.ava.service import AVA_UPLOAD, AvaAdminService

router = APIRouter(prefix="/ava", tags=["AVA: Gestor de Conteúdo"])

_admin = [Depends(require_role(["admin"]))]


def get_service() -> AvaAdminService:
    return AvaAdminService(get_ava_repository())


# ---------------------------------------------------------------------------
# Arquivos (upload direto; rotas locais só em desenvolvimento)
# ---------------------------------------------------------------------------

@router.post("/admin/uploads", response_model=UploadOut, dependencies=_admin)
async def preparar_upload(payload: UploadIn):
    return AVA_UPLOAD.emitir_upload(payload.nome, payload.mime, payload.tamanho)


@router.post("/arquivos/local", dependencies=_admin)
async def upload_local(pathname: str, arquivo: UploadFile = File(...)):
    """Somente desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN)."""
    return await AVA_UPLOAD.salvar_local(pathname, arquivo)


@router.get("/arquivos/local/{arquivo}")
async def ler_local(arquivo: str):
    """Somente desenvolvimento: serve o arquivo salvo em disco (nome aleatório de 128 bits)."""
    return FileResponse(AVA_UPLOAD.caminho_local(arquivo), headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------------------
# Disciplinas e estrutura
# ---------------------------------------------------------------------------

@router.get("/admin/cursos/{curso_id}/disciplinas", response_model=List[DisciplinaAvaOut], dependencies=_admin)
async def listar_disciplinas(curso_id: str, q: Optional[str] = Query(default=None, max_length=255),
                             service: AvaAdminService = Depends(get_service)):
    return service.disciplinas(curso_id, q)


@router.get("/admin/cursos/{curso_id}/avaliacoes", response_model=List[AvaliacaoOpcaoOut], dependencies=_admin)
async def avaliacoes_do_curso(curso_id: str, service: AvaAdminService = Depends(get_service)):
    return service.avaliacoes_do_curso(curso_id)


@router.get("/admin/disciplinas/{disciplina_id}/estrutura", response_model=EstruturaOut, dependencies=_admin)
async def estrutura(disciplina_id: str, service: AvaAdminService = Depends(get_service)):
    return service.estrutura(disciplina_id)


@router.put("/admin/disciplinas/{disciplina_id}/config", response_model=ConfigOut, dependencies=_admin)
async def salvar_config(disciplina_id: str, payload: ConfigIn, service: AvaAdminService = Depends(get_service)):
    return service.salvar_config(disciplina_id, payload)


@router.put("/admin/disciplinas/{disciplina_id}/reordenar", response_model=EstruturaOut, dependencies=_admin)
async def reordenar(disciplina_id: str, payload: ReordenarIn, service: AvaAdminService = Depends(get_service)):
    return service.reordenar_disciplina(disciplina_id, payload)


# ---------------------------------------------------------------------------
# Capítulos
# ---------------------------------------------------------------------------

@router.post("/admin/disciplinas/{disciplina_id}/capitulos", response_model=CapituloOut,
             status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def criar_capitulo(disciplina_id: str, payload: CapituloIn, service: AvaAdminService = Depends(get_service)):
    return service.criar_capitulo_disciplina(disciplina_id, payload)


@router.put("/admin/capitulos/{capitulo_id}", response_model=CapituloOut, dependencies=_admin)
async def atualizar_capitulo(capitulo_id: str, payload: CapituloIn, service: AvaAdminService = Depends(get_service)):
    return service.atualizar_capitulo(capitulo_id, payload)


@router.post("/admin/capitulos/{capitulo_id}/duplicar", response_model=CapituloOut,
             status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def duplicar_capitulo(capitulo_id: str, service: AvaAdminService = Depends(get_service)):
    return service.duplicar_capitulo(capitulo_id)


@router.delete("/admin/capitulos/{capitulo_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin)
async def excluir_capitulo(capitulo_id: str, service: AvaAdminService = Depends(get_service)):
    await service.excluir_capitulo(capitulo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Aulas
# ---------------------------------------------------------------------------

@router.post("/admin/aulas", response_model=AulaOut, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def criar_aula(payload: AulaCreateIn, service: AvaAdminService = Depends(get_service)):
    return service.criar_aula(payload)


@router.get("/admin/aulas/{aula_id}", response_model=AulaOut, dependencies=_admin)
async def obter_aula(aula_id: str, service: AvaAdminService = Depends(get_service)):
    return service.aula(aula_id)


@router.put("/admin/aulas/{aula_id}", response_model=AulaOut, dependencies=_admin)
async def atualizar_aula(aula_id: str, payload: AulaIn, service: AvaAdminService = Depends(get_service)):
    return await service.atualizar_aula(aula_id, payload)


@router.delete("/admin/aulas/{aula_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin)
async def excluir_aula(aula_id: str, service: AvaAdminService = Depends(get_service)):
    await service.excluir_aula(aula_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Itens de conteúdo
# ---------------------------------------------------------------------------

@router.post("/admin/aulas/{aula_id}/itens", response_model=ItemOut, status_code=status.HTTP_201_CREATED,
             dependencies=_admin)
async def criar_item(aula_id: str, payload: ItemIn, service: AvaAdminService = Depends(get_service)):
    return service.criar_item(aula_id, payload)


@router.put("/admin/itens/{item_id}", response_model=ItemOut, dependencies=_admin)
async def atualizar_item(item_id: str, payload: ItemIn, service: AvaAdminService = Depends(get_service)):
    return await service.atualizar_item(item_id, payload)


@router.delete("/admin/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin)
async def excluir_item(item_id: str, service: AvaAdminService = Depends(get_service)):
    await service.excluir_item(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/embed/resolver", response_model=EmbedOut, dependencies=_admin)
async def resolver_embed(payload: EmbedIn, service: AvaAdminService = Depends(get_service)):
    return service.resolver_embed(payload.url)
