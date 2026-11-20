"""Módulo de Comunicação (/comunicacao): Feed de Notícias e Avisos (pop-ups). O chat fica em /chat.

Feed: a equipe Etademp (admin, polo, escola, professor, financeiro, logística) publica; todos curtem,
comentam (comentários de não-admin passam por moderação do admin ou do autor do post) e respondem
ao autor via chat. Avisos: o admin agenda pop-ups exibidos ao abrir a plataforma.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.comunicacao.repository import get_comunicacao_repository
from app.modules.comunicacao.schemas import (
    PERFIS,
    PERFIS_PUBLICAR,
    AutorOut,
    AvisoIn,
    AvisoOut,
    AvisoPopupOut,
    AvisosPage,
    ComentarioIn,
    ComentarioOut,
    ComentariosPage,
    CurtidaOut,
    EstatisticasOut,
    FeedPage,
    LinkPreviewIn,
    LinkPreviewOut,
    LoteModeracaoIn,
    ModeracaoPage,
    PostIn,
    PostOut,
    RejeitarIn,
    ResponderChatIn,
    ResponderChatOut,
    ResumoOut,
    UploadIn,
    UploadOut,
    UsuarioBuscaOut,
)
from app.modules.comunicacao.service import AVISOS_UPLOAD, FEED_UPLOAD, ComunicacaoService

router = APIRouter(prefix="/comunicacao", tags=["Comunicação: Feed & Avisos"])

_logado = [Depends(require_role(list(PERFIS)))]
_publicar = [Depends(require_role(list(PERFIS_PUBLICAR)))]
_admin = [Depends(require_role(["admin"]))]


def get_service() -> ComunicacaoService:
    return ComunicacaoService(get_comunicacao_repository())


# ===========================================================================
# Feed — uploads e prévia de links
# ===========================================================================

@router.post("/feed/uploads", response_model=UploadOut, dependencies=_publicar)
async def feed_preparar_upload(payload: UploadIn):
    return FEED_UPLOAD.emitir_upload(payload.nome, payload.mime, payload.tamanho)


@router.post("/feed/arquivos/local", dependencies=_publicar)
async def feed_upload_local(pathname: str, arquivo: UploadFile = File(...)):
    """Somente desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN)."""
    return await FEED_UPLOAD.salvar_local(pathname, arquivo)


@router.get("/feed/arquivos/local/{arquivo}")
async def feed_ler_local(arquivo: str):
    """Somente desenvolvimento: serve o arquivo salvo em disco (nome aleatório de 128 bits)."""
    return FileResponse(FEED_UPLOAD.caminho_local(arquivo), headers={"Cache-Control": "private, max-age=3600"})


@router.post("/feed/link-preview", response_model=LinkPreviewOut, dependencies=_publicar)
async def feed_link_preview(payload: LinkPreviewIn, service: ComunicacaoService = Depends(get_service)):
    return await service.preview(payload.url)


# ===========================================================================
# Feed — moderação (antes de /feed/{post_id})
# ===========================================================================

@router.get("/feed/moderacao", response_model=ModeracaoPage, dependencies=_publicar)
async def feed_moderacao(situacao: Literal["pendente", "aprovado", "rejeitado"] = Query("pendente", alias="status"),
                         somente_meus: bool = False,
                         limite: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
                         user: UserResponse = Depends(get_current_user),
                         service: ComunicacaoService = Depends(get_service)):
    return service.moderacao(user, situacao, limite, offset, somente_meus)


@router.get("/feed/moderacao/resumo", response_model=ResumoOut, dependencies=_publicar)
async def feed_moderacao_resumo(user: UserResponse = Depends(get_current_user),
                                service: ComunicacaoService = Depends(get_service)):
    return ResumoOut(pendentes=service.resumo_moderacao(user))


@router.post("/feed/moderacao/lote", dependencies=_publicar)
async def feed_moderar_lote(payload: LoteModeracaoIn, user: UserResponse = Depends(get_current_user),
                            service: ComunicacaoService = Depends(get_service)):
    return {"processados": service.moderar_lote(user, payload.ids, payload.acao, payload.motivo)}


@router.post("/feed/comentarios/{comentario_id}/aprovar", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=_publicar)
async def feed_aprovar(comentario_id: str, user: UserResponse = Depends(get_current_user),
                       service: ComunicacaoService = Depends(get_service)):
    service.moderar(user, comentario_id, "aprovar", None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/feed/comentarios/{comentario_id}/rejeitar", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=_publicar)
async def feed_rejeitar(comentario_id: str, payload: Optional[RejeitarIn] = None,
                        user: UserResponse = Depends(get_current_user),
                        service: ComunicacaoService = Depends(get_service)):
    service.moderar(user, comentario_id, "rejeitar", payload.motivo if payload else None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/feed/comentarios/{comentario_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_logado)
async def feed_excluir_comentario(comentario_id: str, user: UserResponse = Depends(get_current_user),
                                  service: ComunicacaoService = Depends(get_service)):
    service.excluir_comentario(user, comentario_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Feed — publicações
# ===========================================================================

@router.get("/feed", response_model=FeedPage, dependencies=_logado)
async def feed_listar(cursor: Optional[str] = None, limite: int = Query(10, ge=1, le=30),
                      user: UserResponse = Depends(get_current_user),
                      service: ComunicacaoService = Depends(get_service)):
    return service.feed(user, cursor, limite)


@router.post("/feed", response_model=PostOut, status_code=status.HTTP_201_CREATED, dependencies=_publicar)
async def feed_criar(payload: PostIn, user: UserResponse = Depends(get_current_user),
                     service: ComunicacaoService = Depends(get_service)):
    return await service.criar_post(user, payload)


@router.get("/feed/{post_id}", response_model=PostOut, dependencies=_logado)
async def feed_detalhe(post_id: str, user: UserResponse = Depends(get_current_user),
                       service: ComunicacaoService = Depends(get_service)):
    return service.post(user, post_id)


@router.patch("/feed/{post_id}", response_model=PostOut, dependencies=_publicar)
async def feed_editar(post_id: str, payload: PostIn, user: UserResponse = Depends(get_current_user),
                      service: ComunicacaoService = Depends(get_service)):
    return await service.editar_post(user, post_id, payload)


@router.delete("/feed/{post_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_publicar)
async def feed_excluir(post_id: str, user: UserResponse = Depends(get_current_user),
                       service: ComunicacaoService = Depends(get_service)):
    service.excluir_post(user, post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/feed/{post_id}/fixar", response_model=PostOut, dependencies=_admin)
async def feed_fixar(post_id: str, user: UserResponse = Depends(get_current_user),
                     service: ComunicacaoService = Depends(get_service)):
    return service.fixar(user, post_id)


@router.post("/feed/{post_id}/curtir", response_model=CurtidaOut, dependencies=_logado)
async def feed_curtir(post_id: str, user: UserResponse = Depends(get_current_user),
                      service: ComunicacaoService = Depends(get_service)):
    return service.curtir(user, post_id, True)


@router.delete("/feed/{post_id}/curtir", response_model=CurtidaOut, dependencies=_logado)
async def feed_descurtir(post_id: str, user: UserResponse = Depends(get_current_user),
                         service: ComunicacaoService = Depends(get_service)):
    return service.curtir(user, post_id, False)


@router.get("/feed/{post_id}/curtidas", response_model=List[AutorOut], dependencies=_logado)
async def feed_curtidas(post_id: str, limite: int = Query(50, ge=1, le=200),
                        user: UserResponse = Depends(get_current_user),
                        service: ComunicacaoService = Depends(get_service)):
    return service.curtidas(user, post_id, limite)


@router.get("/feed/{post_id}/comentarios", response_model=ComentariosPage, dependencies=_logado)
async def feed_comentarios(post_id: str, cursor: Optional[str] = None, limite: int = Query(50, ge=1, le=100),
                           user: UserResponse = Depends(get_current_user),
                           service: ComunicacaoService = Depends(get_service)):
    return service.comentarios(user, post_id, cursor, limite)


@router.post("/feed/{post_id}/comentarios", response_model=ComentarioOut, status_code=status.HTTP_201_CREATED,
             dependencies=_logado)
async def feed_comentar(post_id: str, payload: ComentarioIn, user: UserResponse = Depends(get_current_user),
                        service: ComunicacaoService = Depends(get_service)):
    return service.comentar(user, post_id, payload)


@router.post("/feed/{post_id}/responder-chat", response_model=ResponderChatOut, dependencies=_logado)
async def feed_responder_chat(post_id: str, payload: ResponderChatIn, request: Request,
                              user: UserResponse = Depends(get_current_user),
                              service: ComunicacaoService = Depends(get_service)):
    return ResponderChatOut(conversa_id=service.responder_chat(user, post_id, payload.texto, get_client_ip(request)))


# ===========================================================================
# Avisos (pop-ups) — usuário
# ===========================================================================

@router.get("/avisos/pendentes", response_model=List[AvisoPopupOut], dependencies=_logado)
async def avisos_pendentes(user: UserResponse = Depends(get_current_user),
                           service: ComunicacaoService = Depends(get_service)):
    return service.avisos_pendentes(user)


@router.post("/avisos/{aviso_id}/visualizado", status_code=status.HTTP_204_NO_CONTENT, dependencies=_logado)
async def aviso_visualizado(aviso_id: str, user: UserResponse = Depends(get_current_user),
                            service: ComunicacaoService = Depends(get_service)):
    service.registrar_aviso(user, aviso_id, confirmar=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/avisos/{aviso_id}/confirmar", status_code=status.HTTP_204_NO_CONTENT, dependencies=_logado)
async def aviso_confirmar(aviso_id: str, user: UserResponse = Depends(get_current_user),
                          service: ComunicacaoService = Depends(get_service)):
    service.registrar_aviso(user, aviso_id, confirmar=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Avisos (pop-ups) — admin
# ===========================================================================

@router.post("/avisos/uploads", response_model=UploadOut, dependencies=_admin)
async def avisos_preparar_upload(payload: UploadIn):
    return AVISOS_UPLOAD.emitir_upload(payload.nome, payload.mime, payload.tamanho)


@router.post("/avisos/arquivos/local", dependencies=_admin)
async def avisos_upload_local(pathname: str, arquivo: UploadFile = File(...)):
    """Somente desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN)."""
    return await AVISOS_UPLOAD.salvar_local(pathname, arquivo)


@router.get("/avisos/arquivos/local/{arquivo}")
async def avisos_ler_local(arquivo: str):
    """Somente desenvolvimento: serve o arquivo salvo em disco (nome aleatório de 128 bits)."""
    return FileResponse(AVISOS_UPLOAD.caminho_local(arquivo), headers={"Cache-Control": "private, max-age=3600"})


@router.get("/avisos/usuarios/busca", response_model=List[UsuarioBuscaOut], dependencies=_admin)
async def avisos_buscar_usuarios(q: Optional[str] = None, limite: int = Query(20, ge=1, le=50),
                                 service: ComunicacaoService = Depends(get_service)):
    return service.buscar_usuarios(q, limite)


@router.get("/avisos", response_model=AvisosPage, dependencies=_admin)
async def avisos_listar(situacao: Optional[Literal["agendado", "ativo", "expirado", "inativo"]] = Query(
                            None, alias="status"),
                        busca: Optional[str] = None,
                        limite: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                        service: ComunicacaoService = Depends(get_service)):
    return service.listar_avisos(situacao, busca, limite, offset)


@router.post("/avisos", response_model=AvisoOut, status_code=status.HTTP_201_CREATED, dependencies=_admin)
async def avisos_criar(payload: AvisoIn, user: UserResponse = Depends(get_current_user),
                       service: ComunicacaoService = Depends(get_service)):
    return await service.salvar_aviso(user, None, payload)


@router.get("/avisos/{aviso_id}", response_model=AvisoOut, dependencies=_admin)
async def avisos_detalhe(aviso_id: str, service: ComunicacaoService = Depends(get_service)):
    return service.aviso(aviso_id)


@router.patch("/avisos/{aviso_id}", response_model=AvisoOut, dependencies=_admin)
async def avisos_editar(aviso_id: str, payload: AvisoIn, user: UserResponse = Depends(get_current_user),
                        service: ComunicacaoService = Depends(get_service)):
    return await service.salvar_aviso(user, aviso_id, payload)


@router.delete("/avisos/{aviso_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin)
async def avisos_excluir(aviso_id: str, service: ComunicacaoService = Depends(get_service)):
    service.excluir_aviso(aviso_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/avisos/{aviso_id}/duplicar", response_model=AvisoOut, dependencies=_admin)
async def avisos_duplicar(aviso_id: str, user: UserResponse = Depends(get_current_user),
                          service: ComunicacaoService = Depends(get_service)):
    return await service.duplicar_aviso(user, aviso_id)


@router.post("/avisos/{aviso_id}/alternar", response_model=AvisoOut, dependencies=_admin)
async def avisos_alternar(aviso_id: str, service: ComunicacaoService = Depends(get_service)):
    return service.alternar_aviso(aviso_id)


@router.get("/avisos/{aviso_id}/estatisticas", response_model=EstatisticasOut, dependencies=_admin)
async def avisos_estatisticas(aviso_id: str, limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                              service: ComunicacaoService = Depends(get_service)):
    return service.estatisticas(aviso_id, limite, offset)
