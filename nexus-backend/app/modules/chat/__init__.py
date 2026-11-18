"""Rotas do Chat Interno Moderado (/chat)."""
from __future__ import annotations

import hmac
from datetime import datetime
from typing import List, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.modules.auth.dependencies import get_client_ip, get_current_user, require_role
from app.modules.auth.schemas import UserResponse
from app.modules.chat import anexos as anexos_mod
from app.modules.chat.regras import PERFIS_CHAT
from app.modules.chat.repository import get_chat_repository
from app.modules.chat.schemas import (
    AlterarMembrosIn,
    ContatoOut,
    ConversaDetalheOut,
    ConversaOut,
    ConversasAdminPage,
    CriarGrupoIn,
    EnviarMensagemIn,
    IniciarIndividualIn,
    MensagemOut,
    ResumoOut,
    RotacaoOut,
    TurmaChatOut,
    UploadIn,
    UploadOut,
)
from app.modules.chat.service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat Interno"])

_acesso = [Depends(require_role(list(PERFIS_CHAT)))]
_admin = [Depends(require_role(["admin"]))]


def get_service() -> ChatService:
    return ChatService(get_chat_repository())


# ---------------------------------------------------------------------------
# Conversas
# ---------------------------------------------------------------------------

@router.get("/conversas", response_model=List[ConversaOut], dependencies=_acesso)
async def listar_conversas(tipo: Optional[Literal["individual", "grupo"]] = None,
                           limite: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                           user: UserResponse = Depends(get_current_user),
                           service: ChatService = Depends(get_service)):
    """Minhas conversas (sem as ocultadas), da mais recente para a mais antiga, com não lidas."""
    return service.listar(user, tipo, limite, offset)


@router.get("/resumo", response_model=ResumoOut, dependencies=_acesso)
async def resumo(user: UserResponse = Depends(get_current_user), service: ChatService = Depends(get_service)):
    return ResumoOut(nao_lidas=service.resumo(user))


@router.get("/contatos", response_model=List[ContatoOut], dependencies=_acesso)
async def contatos(busca: Optional[str] = Query(None, max_length=100), limite: int = Query(20, ge=1, le=50),
                   user: UserResponse = Depends(get_current_user), service: ChatService = Depends(get_service)):
    """Usuários com quem posso iniciar conversa (aluno não vê outros alunos)."""
    return service.contatos(user, busca, limite)


@router.get("/turmas", response_model=List[TurmaChatOut], dependencies=_acesso)
async def turmas(busca: Optional[str] = Query(None, max_length=100), limite: int = Query(30, ge=1, le=100),
                 user: UserResponse = Depends(get_current_user), service: ChatService = Depends(get_service)):
    """Turmas cujo grupo posso abrir (aluno: matriculado; professor: vínculo ativo; gestão: sua unidade)."""
    return service.turmas(user, busca, limite)


@router.post("/conversas/individual",response_model=ConversaDetalheOut, dependencies=_acesso)
async def iniciar_individual(payload: IniciarIndividualIn, user: UserResponse = Depends(get_current_user),
                             service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    """Abre a conversa individual pela chave determinística (reaproveita a existente e seu histórico)."""
    return service.iniciar_individual(user, payload.usuario_id, ip)


@router.post("/grupos", response_model=ConversaDetalheOut, status_code=status.HTTP_201_CREATED, dependencies=_acesso)
async def criar_grupo(payload: CriarGrupoIn, user: UserResponse = Depends(get_current_user),
                      service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    return service.criar_grupo(user, payload, ip)


@router.post("/grupos/turma/{turma_id}", response_model=ConversaDetalheOut, dependencies=_acesso)
async def grupo_turma(turma_id: str, user: UserResponse = Depends(get_current_user),
                      service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    """Abre (ou cria) o grupo da turma e sincroniza os participantes com matrículas e vínculos ativos."""
    return service.abrir_grupo_turma(user, turma_id, ip)


@router.patch("/grupos/{conversa_id}/membros", response_model=ConversaDetalheOut, dependencies=_acesso)
async def alterar_membros(conversa_id: str, payload: AlterarMembrosIn, user: UserResponse = Depends(get_current_user),
                          service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    return service.alterar_membros(user, conversa_id, payload, ip)


@router.get("/conversas/{conversa_id}", response_model=ConversaDetalheOut, dependencies=_acesso)
async def detalhe(conversa_id: str, user: UserResponse = Depends(get_current_user),
                  service: ChatService = Depends(get_service)):
    return service.detalhe(conversa_id, user)


@router.get("/conversas/{conversa_id}/mensagens", response_model=List[MensagemOut], dependencies=_acesso)
async def mensagens(conversa_id: str, antes: Optional[datetime] = None, depois: Optional[datetime] = None,
                    limite: int = Query(50, ge=1, le=200), user: UserResponse = Depends(get_current_user),
                    service: ChatService = Depends(get_service)):
    """Mensagens (tabela ativa + histórico). `antes` pagina para trás; `depois` busca as novas (polling)."""
    return service.mensagens(conversa_id, user, antes=antes, depois=depois, limite=limite)


@router.post("/conversas/{conversa_id}/mensagens", response_model=MensagemOut, status_code=status.HTTP_201_CREATED,
             dependencies=_acesso)
async def enviar(conversa_id: str, payload: EnviarMensagemIn, user: UserResponse = Depends(get_current_user),
                 service: ChatService = Depends(get_service)):
    return service.enviar(user, conversa_id, payload)


@router.post("/conversas/{conversa_id}/lida", status_code=status.HTTP_204_NO_CONTENT, dependencies=_acesso)
async def marcar_lida(conversa_id: str, user: UserResponse = Depends(get_current_user),
                      service: ChatService = Depends(get_service)):
    service.marcar_lida(user, conversa_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversas/{conversa_id}/encerrar", response_model=ConversaDetalheOut, dependencies=_acesso)
async def encerrar(conversa_id: str, user: UserResponse = Depends(get_current_user),
                   service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    return service.encerrar(user, conversa_id, ip)


@router.post("/conversas/{conversa_id}/reabrir", response_model=ConversaDetalheOut, dependencies=_acesso)
async def reabrir(conversa_id: str, user: UserResponse = Depends(get_current_user),
                  service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    return service.reabrir(user, conversa_id, ip)


@router.delete("/conversas/{conversa_id}/minha", status_code=status.HTTP_204_NO_CONTENT, dependencies=_acesso)
async def ocultar(conversa_id: str, user: UserResponse = Depends(get_current_user),
                  service: ChatService = Depends(get_service)):
    """Exclui a conversa só para mim (oculta). Ela reaparece se chegar mensagem nova."""
    service.ocultar(user, conversa_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Anexos
# ---------------------------------------------------------------------------

@router.post("/anexos/upload", response_model=UploadOut, dependencies=_acesso)
async def preparar_upload(payload: UploadIn, _user: UserResponse = Depends(get_current_user)):
    """Valida tipo/tamanho e devolve o token para envio direto ao armazenamento."""
    return anexos_mod.emitir_upload(payload.nome, payload.mime, payload.tamanho)


@router.post("/anexos/local", dependencies=_acesso)
async def upload_local(pathname: str, arquivo: UploadFile = File(...),
                       _user: UserResponse = Depends(get_current_user)):
    """Somente desenvolvimento (sem CHAT_BLOB_READ_WRITE_TOKEN)."""
    return await anexos_mod.salvar_local(pathname, arquivo)


@router.get("/anexos/local/{arquivo}")
async def ler_local(arquivo: str):
    """Somente desenvolvimento: serve o anexo salvo em disco (nome aleatório de 128 bits)."""
    return FileResponse(anexos_mod.caminho_local(arquivo), headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.get("/admin/conversas", response_model=ConversasAdminPage, dependencies=_admin)
async def admin_conversas(usuario_id: Optional[str] = None, tipo: Optional[Literal["individual", "grupo"]] = None,
                          busca: Optional[str] = Query(None, max_length=100),
                          limite: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
                          service: ChatService = Depends(get_service)):
    return service.admin_listar(usuario_id=usuario_id, tipo=tipo, busca=busca, limite=limite, offset=offset)


@router.get("/conversas/{conversa_id}/exportar", dependencies=_admin)
async def exportar(conversa_id: str, user: UserResponse = Depends(get_current_user),
                   service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    conteudo, detalhe_conv = service.exportar_pdf(user, conversa_id, ip)
    nome = f"conversa-{detalhe_conv.titulo[:60]}.pdf"
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome, safe='')}",
                             "Cache-Control": "private, no-store"})


@router.delete("/conversas/{conversa_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin)
async def excluir(conversa_id: str, user: UserResponse = Depends(get_current_user),
                  service: ChatService = Depends(get_service), ip: Optional[str] = Depends(get_client_ip)):
    """Exclusão definitiva (conversa, mensagens das duas tabelas e anexos). Somente Admin."""
    await service.excluir(user, conversa_id, ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Cron (Vercel Cron envia "Authorization: Bearer <CRON_SECRET>")
# ---------------------------------------------------------------------------

@router.get("/cron/rotacionar", response_model=RotacaoOut)
async def cron_rotacionar(authorization: Optional[str] = Header(default=None),
                          service: ChatService = Depends(get_service)):
    """Move mensagens com mais de 48h para o histórico e mantém só 90 dias no histórico."""
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="CRON_SECRET não configurado")
    esperado = f"Bearer {settings.CRON_SECRET}"
    if not authorization or not hmac.compare_digest(authorization.encode(), esperado.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")
    return await service.rotacionar()
