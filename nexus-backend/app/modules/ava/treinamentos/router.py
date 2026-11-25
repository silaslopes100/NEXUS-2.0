"""Endpoints dos Treinamentos do AVA: /ava/treinamentos.

(O prefixo /treinamentos é do módulo legado de polos_escolas, com a tabela `treinamentos`.)
- ``/ava/treinamentos/admin/...``: gestão (admin). Aulas, itens e capítulos existentes usam /ava/admin/...
- ``/ava/treinamentos/...``: trilha de Polo, Escola e Professor (o admin entra em pré-visualização).
- ``/ava/treinamentos/certificados/validar/{codigo}``: validação pública do certificado.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.config import settings
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.ava.aluno_repository import get_ava_aluno_repository
from app.modules.ava.aluno_schemas import (
    AnotacaoIn,
    AnotacaoOut,
    AulaAlunoOut,
    ConclusaoOut,
    DisciplinaPlayerOut,
    NotaAulaIn,
    ProgressoIn,
)
from app.modules.ava.repository import get_ava_repository
from app.modules.ava.schemas import CapituloIn, CapituloOut, ReordenarIn
from app.modules.ava.service import AvaAdminService
from app.modules.ava.treinamentos.repository import get_treinamentos_repository
from app.modules.ava.treinamentos.schemas import (
    CertificadoValidacaoOut,
    EstruturaTreinamentoOut,
    ParticipanteOut,
    TreinamentoCatalogoOut,
    TreinamentoIn,
    TreinamentoOut,
    TreinamentosPage,
    UnidadesOut,
)
from app.modules.ava.treinamentos.service import TreinamentosAdminService, TreinamentoUsuarioService

router = APIRouter(prefix="/ava/treinamentos", tags=["AVA: Treinamentos"])

_admin = [Depends(require_role(["admin"]))]
_publico = ["polo", "escola", "professor", "admin"]

Ctx = Dict[str, Any]


def get_admin() -> TreinamentosAdminService:
    return TreinamentosAdminService(get_treinamentos_repository(), AvaAdminService(get_ava_repository()))


def get_usuario() -> TreinamentoUsuarioService:
    return TreinamentoUsuarioService(get_ava_aluno_repository(), get_ava_repository(), get_treinamentos_repository())


async def contexto(user: UserResponse = Depends(require_role(_publico))) -> Ctx:
    return {"user": user, "aluno": None, "previa": perfil_do_usuario(user) == "admin"}


async def contexto_escrita(ctx: Ctx = Depends(contexto)) -> Ctx:
    if ctx["previa"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Pré-visualização: nada é gravado.")
    return ctx


# ===========================================================================
# Admin
# ===========================================================================

@router.get("/admin", response_model=TreinamentosPage, dependencies=_admin)
async def listar(q: Optional[str] = Query(None, max_length=255),
                 situacao: Literal["todos", "publicado", "rascunho"] = "todos",
                 limite: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 service: TreinamentosAdminService = Depends(get_admin)):
    return service.listar(q, situacao, limite, offset)


@router.get("/admin/unidades", response_model=UnidadesOut, dependencies=_admin)
async def unidades(service: TreinamentosAdminService = Depends(get_admin)):
    return service.unidades()


@router.post("/admin", response_model=TreinamentoOut, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def criar(payload: TreinamentoIn, user: UserResponse = Depends(get_current_user),
                service: TreinamentosAdminService = Depends(get_admin)):
    return service.salvar(None, payload, user)


@router.get("/admin/{treinamento_id}", response_model=TreinamentoOut, dependencies=_admin)
async def obter(treinamento_id: str, service: TreinamentosAdminService = Depends(get_admin)):
    return service.obter(treinamento_id)


@router.put("/admin/{treinamento_id}", response_model=TreinamentoOut, dependencies=_admin)
async def atualizar(treinamento_id: str, payload: TreinamentoIn, user: UserResponse = Depends(get_current_user),
                    service: TreinamentosAdminService = Depends(get_admin)):
    return service.salvar(treinamento_id, payload, user)


@router.post("/admin/{treinamento_id}/alternar", response_model=TreinamentoOut, dependencies=_admin)
async def alternar(treinamento_id: str, service: TreinamentosAdminService = Depends(get_admin)):
    return service.alternar(treinamento_id)


@router.post("/admin/{treinamento_id}/duplicar", response_model=TreinamentoOut, status_code=status.HTTP_201_CREATED,
             dependencies=_admin)
async def duplicar(treinamento_id: str, user: UserResponse = Depends(get_current_user),
                   service: TreinamentosAdminService = Depends(get_admin)):
    return service.duplicar(treinamento_id, user)


@router.delete("/admin/{treinamento_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin)
async def excluir(treinamento_id: str, service: TreinamentosAdminService = Depends(get_admin)):
    await service.excluir(treinamento_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/{treinamento_id}/estrutura", response_model=EstruturaTreinamentoOut, dependencies=_admin)
async def estrutura(treinamento_id: str, service: TreinamentosAdminService = Depends(get_admin)):
    return service.estrutura(treinamento_id)


@router.post("/admin/{treinamento_id}/capitulos", response_model=CapituloOut, status_code=status.HTTP_201_CREATED,
             dependencies=_admin)
async def criar_capitulo(treinamento_id: str, payload: CapituloIn, service: TreinamentosAdminService = Depends(get_admin)):
    return service.criar_capitulo(treinamento_id, payload)


@router.put("/admin/{treinamento_id}/reordenar", response_model=EstruturaTreinamentoOut, dependencies=_admin)
async def reordenar(treinamento_id: str, payload: ReordenarIn, service: TreinamentosAdminService = Depends(get_admin)):
    return service.reordenar(treinamento_id, payload)


@router.get("/admin/{treinamento_id}/participantes", response_model=List[ParticipanteOut], dependencies=_admin)
async def participantes(treinamento_id: str, service: TreinamentosAdminService = Depends(get_admin)):
    return service.participantes(treinamento_id)


# ===========================================================================
# Público (validação do certificado)
# ===========================================================================

@router.get("/certificados/validar/{codigo}", response_model=CertificadoValidacaoOut)
async def validar_certificado(codigo: str, service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.validar(codigo)


# ===========================================================================
# Usuário (Polo, Escola, Professor)
# ===========================================================================

@router.get("/meus", response_model=List[TreinamentoCatalogoOut])
async def meus(ctx: Ctx = Depends(contexto), service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.catalogo(ctx["user"])


@router.get("/aulas/{aula_id}", response_model=AulaAlunoOut)
async def aula(aula_id: str, ctx: Ctx = Depends(contexto), service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.aula(ctx, aula_id)


@router.post("/aulas/{aula_id}/progresso", response_model=Optional[ConclusaoOut])
async def progresso(aula_id: str, payload: ProgressoIn, ctx: Ctx = Depends(contexto_escrita),
                    service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.progresso(ctx, aula_id, payload)


@router.post("/aulas/{aula_id}/concluir", response_model=ConclusaoOut)
async def concluir(aula_id: str, ctx: Ctx = Depends(contexto_escrita),
                   service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.concluir(ctx, aula_id)


@router.put("/aulas/{aula_id}/minha-nota", status_code=status.HTTP_204_NO_CONTENT)
async def avaliar_aula(aula_id: str, payload: NotaAulaIn, ctx: Ctx = Depends(contexto_escrita),
                       service: TreinamentoUsuarioService = Depends(get_usuario)):
    service.avaliar_aula(ctx, aula_id, payload.nota)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/aulas/{aula_id}/anotacoes", response_model=AnotacaoOut, status_code=status.HTTP_201_CREATED)
async def criar_anotacao(aula_id: str, payload: AnotacaoIn, ctx: Ctx = Depends(contexto_escrita),
                         service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.criar_anotacao(ctx, aula_id, payload)


@router.put("/anotacoes/{anotacao_id}", response_model=AnotacaoOut)
async def atualizar_anotacao(anotacao_id: str, payload: AnotacaoIn, ctx: Ctx = Depends(contexto_escrita),
                             service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.atualizar_anotacao(ctx, anotacao_id, payload)


@router.delete("/anotacoes/{anotacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_anotacao(anotacao_id: str, ctx: Ctx = Depends(contexto_escrita),
                           service: TreinamentoUsuarioService = Depends(get_usuario)):
    service.excluir_anotacao(ctx, anotacao_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{treinamento_id}/certificado")
async def certificado(treinamento_id: str, request: Request, ctx: Ctx = Depends(contexto_escrita),
                      service: TreinamentoUsuarioService = Depends(get_usuario)):
    origem = request.headers.get("origin") or ""
    if not origem and request.headers.get("referer"):
        ref = urlparse(request.headers["referer"])
        origem = f"{ref.scheme}://{ref.netloc}"
    if not origem:
        origem = next((o for o in settings.CORS_ORIGINS if o.startswith("http")), "")
    conteudo, nome = service.certificado(ctx["user"], treinamento_id, origem)
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"', "Cache-Control": "private, no-store"})


@router.get("/{treinamento_id}", response_model=DisciplinaPlayerOut)
async def treinamento(treinamento_id: str, ctx: Ctx = Depends(contexto),
                      service: TreinamentoUsuarioService = Depends(get_usuario)):
    return service.disciplina(ctx, treinamento_id)
