"""Central de Estágio ETADEMP (/estagios).

Aluno: downloads, vídeo, envio das etapas (Teologia do Ministério → Homilética) e comprovantes.
Admin (Coordenação): análise, aprovação/negativa com feedback, relatórios e arquivos-base.
Polo e Escola: consulta dos estágios dos próprios alunos (somente leitura).
"""
from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.estagios.repository import get_estagios_repository
from app.modules.estagios.schemas import (
    ArquivoBaseOut,
    ArquivoIn,
    AvaliacaoIn,
    CentralAlunoOut,
    ConfigIn,
    EnvioIn,
    FiltrosRelatorio,
    FiltrosSubmissoes,
    RelatorioOut,
    ResumoOut,
    SubmissaoDetalheOut,
    SubmissaoOut,
    SubmissoesPage,
    UploadIn,
    UploadOut,
)
from app.modules.estagios.service import ESCOPO_UPLOAD, EstagiosService

router = APIRouter(prefix="/estagios", tags=["Central de Estágio"])

_aluno = [Depends(require_role(["aluno"]))]
_admin = [Depends(require_role(["admin"]))]
_gestao = [Depends(require_role(["admin", "polo", "escola"]))]
_upload = [Depends(require_role(["aluno", "admin"]))]
_todos = [Depends(require_role(["aluno", "admin", "polo", "escola"]))]


def get_service() -> EstagiosService:
    return EstagiosService(get_estagios_repository())


def _filtros_submissoes(
    status: Optional[Literal["em_analise", "aprovado", "negado"]] = None,
    etapa: Optional[Literal["teologia_ministerio", "homiletica"]] = None,
    polo_id: Optional[str] = None,
    escola_id: Optional[str] = None,
    de: Optional[date] = None,
    ate: Optional[date] = None,
    busca: Optional[str] = None,
) -> FiltrosSubmissoes:
    return FiltrosSubmissoes(status=status, etapa=etapa, polo_id=polo_id or None, escola_id=escola_id or None,
                             de=de, ate=ate, busca=busca)


def _filtros_relatorio(
    situacao: Optional[Literal["concluido", "pendente"]] = None,
    polo_id: Optional[str] = None,
    escola_id: Optional[str] = None,
    de: Optional[date] = None,
    ate: Optional[date] = None,
) -> FiltrosRelatorio:
    return FiltrosRelatorio(situacao=situacao, polo_id=polo_id or None, escola_id=escola_id or None, de=de, ate=ate)


# ---------------------------------------------------------------------------
# Uploads (envio direto ao armazenamento)
# ---------------------------------------------------------------------------

@router.post("/uploads", response_model=UploadOut, dependencies=_upload)
async def preparar_upload(payload: UploadIn, service: EstagiosService = Depends(get_service)):
    return service.emitir_upload(payload.nome, payload.mime, payload.tamanho)


@router.post("/arquivos/local", dependencies=_upload)
async def upload_local(pathname: str, arquivo: UploadFile = File(...)):
    """Somente desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN)."""
    return await ESCOPO_UPLOAD.salvar_local(pathname, arquivo)


@router.get("/arquivos/local/{arquivo}")
async def ler_local(arquivo: str):
    """Somente desenvolvimento: serve o arquivo salvo em disco (nome aleatório de 128 bits)."""
    return FileResponse(ESCOPO_UPLOAD.caminho_local(arquivo), headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------------------
# Aluno
# ---------------------------------------------------------------------------

@router.get("/central", response_model=CentralAlunoOut, dependencies=_aluno)
async def central(user: UserResponse = Depends(get_current_user), service: EstagiosService = Depends(get_service)):
    return service.central(user)


@router.get("/me/resumo", response_model=ResumoOut, dependencies=_aluno)
async def resumo_aluno(user: UserResponse = Depends(get_current_user),
                       service: EstagiosService = Depends(get_service)):
    return {"pendentes": service.resumo_aluno(user)}


@router.post("/etapas/{etapa}/enviar", response_model=SubmissaoOut, dependencies=_aluno)
async def enviar(etapa: str, payload: EnvioIn, user: UserResponse = Depends(get_current_user),
                 service: EstagiosService = Depends(get_service)):
    return await service.enviar(user, etapa, payload)


@router.get("/submissoes/{submissao_id}/comprovante.pdf", dependencies=_todos)
async def comprovante(submissao_id: str, user: UserResponse = Depends(get_current_user),
                      service: EstagiosService = Depends(get_service)):
    return service.comprovante(user, submissao_id)


# ---------------------------------------------------------------------------
# Admin e unidade (Polo/Escola só leitura, filtrado pelo vínculo)
# ---------------------------------------------------------------------------

@router.get("/submissoes", response_model=SubmissoesPage, dependencies=_gestao)
async def listar(filtros: FiltrosSubmissoes = Depends(_filtros_submissoes),
                 limite: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0),
                 user: UserResponse = Depends(get_current_user), service: EstagiosService = Depends(get_service)):
    return service.listar(user, filtros, limite, offset)


@router.get("/submissoes/{submissao_id}", response_model=SubmissaoDetalheOut, dependencies=_gestao)
async def detalhe(submissao_id: str, user: UserResponse = Depends(get_current_user),
                  service: EstagiosService = Depends(get_service)):
    return service.detalhe(user, submissao_id)


@router.get("/relatorio", response_model=RelatorioOut, dependencies=_gestao)
async def relatorio(filtros: FiltrosRelatorio = Depends(_filtros_relatorio),
                    user: UserResponse = Depends(get_current_user), service: EstagiosService = Depends(get_service)):
    return service.relatorio(user, filtros)


@router.get("/relatorio/exportar", dependencies=_gestao)
async def exportar(formato: Literal["pdf", "xlsx", "csv"] = "pdf",
                   filtros: FiltrosRelatorio = Depends(_filtros_relatorio),
                   user: UserResponse = Depends(get_current_user), service: EstagiosService = Depends(get_service)):
    return service.exportar(user, filtros, formato)


@router.get("/admin/resumo", response_model=ResumoOut, dependencies=_admin)
async def resumo_admin(service: EstagiosService = Depends(get_service)):
    return {"pendentes": service.resumo_admin()}


@router.post("/admin/submissoes/{submissao_id}/avaliar", response_model=SubmissaoDetalheOut, dependencies=_admin)
async def avaliar(submissao_id: str, payload: AvaliacaoIn, user: UserResponse = Depends(get_current_user),
                  service: EstagiosService = Depends(get_service)):
    return service.avaliar(user, submissao_id, payload)


@router.get("/admin/arquivos-base", response_model=List[ArquivoBaseOut], dependencies=_admin)
async def arquivos_base(service: EstagiosService = Depends(get_service)):
    return service.arquivos_base()


@router.put("/admin/arquivos-base/{chave}", response_model=List[ArquivoBaseOut], dependencies=_admin)
async def substituir_base(chave: str, payload: ArquivoIn, user: UserResponse = Depends(get_current_user),
                          service: EstagiosService = Depends(get_service)):
    return await service.substituir_base(user, chave, payload)


@router.get("/admin/config", dependencies=_admin)
async def config(service: EstagiosService = Depends(get_service)):
    return service.config()


@router.put("/admin/config", dependencies=_admin)
async def salvar_config(payload: ConfigIn, service: EstagiosService = Depends(get_service)):
    return service.salvar_config(payload.video_url)
