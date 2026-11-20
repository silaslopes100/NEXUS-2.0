"""Regras do Feed de Notícias (posts, curtidas, comentários moderados, resposta via chat) e dos Avisos."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.core.blob_upload import MB, EscopoUpload
from app.modules.auth.roles import perfil_canonico, perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.comunicacao import link_preview
from app.modules.comunicacao.repository import Contexto, PostgresComunicacaoRepository, uuid_valido
from app.modules.comunicacao.sanitizar import sanitizar_html, texto_do_html
from app.modules.comunicacao.schemas import (
    MAX_LINKS,
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
    LinkPreviewOut,
    ModeracaoItemOut,
    ModeracaoPage,
    PostIn,
    PostOut,
    VisualizacaoOut,
)
from app.modules.notificacoes import notificar, notificar_perfil

logger = logging.getLogger(__name__)

_IMAGENS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
_VIDEOS = {"video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov"}
_DOCS = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
}
_CATEGORIAS = {"imagem": (10 * MB, _IMAGENS), "video": (100 * MB, _VIDEOS), "arquivo": (20 * MB, _DOCS)}

FEED_UPLOAD = EscopoUpload(prefixo="feed", categorias=_CATEGORIAS, rota_local="/comunicacao/feed/arquivos/local",
                           rotulo="feed", nome_item="Mídia")
AVISOS_UPLOAD = EscopoUpload(prefixo="avisos", categorias=_CATEGORIAS,
                             rota_local="/comunicacao/avisos/arquivos/local", rotulo="aviso", nome_item="Mídia")

_CACHE_PREVIEW_DIAS = 7
_COMENTARIOS_NO_CARD = 2
_PERFIS_ESCOPO_GLOBAL = {"admin", "financeiro", "logistica"}


# ---------------------------------------------------------------------------
# Cursores (opacos para o cliente)
# ---------------------------------------------------------------------------

def _cod_cursor(*partes: Any) -> str:
    bruto = json.dumps([p.isoformat() if isinstance(p, datetime) else p for p in partes])
    return base64.urlsafe_b64encode(bruto.encode()).decode().rstrip("=")


def _dec_cursor(cursor: Optional[str], n: int) -> Optional[list]:
    if not cursor:
        return None
    try:
        partes = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
        if not isinstance(partes, list) or len(partes) != n:
            raise ValueError
        return partes
    except Exception:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cursor inválido.")


def _autor(r: Dict[str, Any], prefixo: str = "autor") -> AutorOut:
    return AutorOut(id=str(r[f"{prefixo}_id"]), nome=r.get(f"{prefixo}_nome") or "Usuário",
                    perfil=r.get(f"{prefixo}_perfil"), foto_url=r.get(f"{prefixo}_foto"))


def _nome(user: UserResponse) -> str:
    return f"{user.nome} {user.sobrenome or ''}".strip()


def _trecho(texto: str, n: int = 80) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def _autor_eh_admin(post: Dict[str, Any]) -> bool:
    """O autor admin já recebe a notificação de moderação enviada a todos os admins."""
    return perfil_canonico(post.get("autor_perfil")) == "admin"


def _uuid_ou_422(valor: Optional[str], campo: str) -> Optional[str]:
    if valor and not uuid_valido(valor):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{campo} inválido.")
    return valor or None


class ComunicacaoService:
    def __init__(self, repo: PostgresComunicacaoRepository,
                 notificar_fn: Callable[..., Any] = notificar,
                 notificar_admins: Callable[..., Any] = lambda **kw: notificar_perfil("admin", **kw)) -> None:
        self.repo = repo
        self._notificar = notificar_fn
        self._notificar_admins = notificar_admins

    # ------------------------------------------------------------------ contexto

    def contexto(self, user: UserResponse) -> Contexto:
        perfil = perfil_do_usuario(user)
        unidade = {} if perfil in _PERFIS_ESCOPO_GLOBAL else self.repo.unidade_do_usuario(str(user.id))
        return {"me": str(user.id), "perfil": perfil, "admin": perfil == "admin",
                "tambem_aluno": bool(user.tambem_aluno), "polo": unidade.get("polo"),
                "escola": unidade.get("escola")}

    @staticmethod
    def pode_publicar(user: UserResponse) -> bool:
        return perfil_do_usuario(user) in PERFIS_PUBLICAR

    # ------------------------------------------------------------------ montagem

    def _comentario_out(self, r: Dict[str, Any], ctx: Contexto) -> ComentarioOut:
        moderador = ctx["admin"] or str(r["post_autor_id"]) == ctx["me"]
        return ComentarioOut(
            id=r["id"], post_id=r["post_id"], parent_id=r.get("parent_id"), autor=_autor(r), texto=r["texto"],
            criado_em=r["criado_em"], status=r["status"] if moderador else None,
            pode_excluir=ctx["admin"] or str(r["autor_id"]) == ctx["me"], pode_moderar=moderador,
        )

    def _posts_out(self, rows: List[Dict[str, Any]], ctx: Contexto) -> List[PostOut]:
        ids = [r["id"] for r in rows]
        midias, links = self.repo.midias_e_links(ids)
        comentarios = self.repo.comentarios_recentes(ids, ctx, _COMENTARIOS_NO_CARD)
        saida = []
        for r in rows:
            moderador = ctx["admin"] or str(r["autor_id"]) == ctx["me"]
            saida.append(PostOut(
                id=r["id"], autor=_autor(r), conteudo_html=r["conteudo_html"], midias=midias[r["id"]],
                links=links[r["id"]], publico_perfis=r.get("publico_perfis"), polo_id=r.get("polo_id"),
                polo_nome=r.get("polo_nome"), escola_id=r.get("escola_id"), escola_nome=r.get("escola_nome"),
                fixado=r["fixado"], permite_comentarios=r["permite_comentarios"],
                total_curtidas=r["total_curtidas"], total_comentarios=int(r.get("total_comentarios_visiveis") or 0),
                curtido_por_mim=bool(r.get("curtido_por_mim")), editado=r["editado"], criado_em=r["criado_em"],
                atualizado_em=r.get("atualizado_em"), pode_editar=moderador, pode_moderar=moderador,
                pendentes=int(r.get("pendentes") or 0) if moderador else 0,
                comentarios_recentes=[self._comentario_out(c, ctx) for c in comentarios[r["id"]]],
            ))
        return saida

    def _post_visivel(self, post_id: str, ctx: Contexto) -> Dict[str, Any]:
        post = self.repo.get_post(post_id, ctx)
        if not post:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Publicação não encontrada.")
        return post

    def _post_editavel(self, post_id: str, ctx: Contexto) -> Dict[str, Any]:
        post = self._post_visivel(post_id, ctx)
        if not (ctx["admin"] or str(post["autor_id"]) == ctx["me"]):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Somente o autor ou um administrador pode alterar.")
        return post

    # ------------------------------------------------------------------ feed: leitura

    def feed(self, user: UserResponse, cursor: Optional[str], limite: int) -> FeedPage:
        ctx = self.contexto(user)
        c = _dec_cursor(cursor, 3)
        rows = self.repo.listar_posts(ctx, (int(c[0]), datetime.fromisoformat(c[1]), c[2]) if c else None, limite + 1)
        proximo = None
        if len(rows) > limite:
            rows = rows[:limite]
            u = rows[-1]
            proximo = _cod_cursor(int(u["fixado"]), u["criado_em"], u["id"])
        return FeedPage(itens=self._posts_out(rows, ctx), proximo_cursor=proximo)

    def post(self, user: UserResponse, post_id: str) -> PostOut:
        ctx = self.contexto(user)
        return self._posts_out([self._post_visivel(post_id, ctx)], ctx)[0]

    # ------------------------------------------------------------------ feed: escrita

    async def _links(self, links: List[Any]) -> List[Dict[str, Any]]:
        saida, vistos = [], set()
        for item in links[:MAX_LINKS]:
            prev = await self.preview(item.url)
            if prev.url not in vistos:
                vistos.add(prev.url)
                saida.append(prev.model_dump())
        return saida

    def _midias(self, midias: List[Any]) -> List[Dict[str, Any]]:
        saida = []
        for m in midias:
            anexo = FEED_UPLOAD.validar_anexo(url=m.url, pathname=m.pathname, nome=m.nome, mime=m.mime,
                                              tamanho=m.tamanho)
            saida.append({"tipo": FEED_UPLOAD.categoria_do_mime(anexo.mime), "url": anexo.url,
                          "storage_key": anexo.storage_key, "nome": anexo.nome, "mime": anexo.mime,
                          "tamanho": anexo.tamanho})
        return saida

    def _dados_post(self, user: UserResponse, dados: PostIn) -> Dict[str, Any]:
        html = sanitizar_html(dados.conteudo_html, variante="post")
        return {
            "autor_id": str(user.id), "conteudo_html": html, "conteudo_texto": texto_do_html(html),
            "publico_perfis": dados.publico_perfis, "polo_id": _uuid_ou_422(dados.polo_id, "Polo"),
            "escola_id": _uuid_ou_422(dados.escola_id, "Escola"), "permite_comentarios": dados.permite_comentarios,
        }

    async def criar_post(self, user: UserResponse, dados: PostIn) -> PostOut:
        base = self._dados_post(user, dados)
        midias, links = self._midias(dados.midias), await self._links(dados.links)
        if not (base["conteudo_texto"] or midias or links):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Escreva algo ou anexe uma mídia/link para publicar.")
        post_id = self.repo.criar_post(base, midias, links)
        return self.post(user, post_id)

    async def editar_post(self, user: UserResponse, post_id: str, dados: PostIn) -> PostOut:
        ctx = self.contexto(user)
        self._post_editavel(post_id, ctx)
        base = self._dados_post(user, dados)
        midias, links = self._midias(dados.midias), await self._links(dados.links)
        if not (base["conteudo_texto"] or midias or links):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A publicação não pode ficar vazia.")
        removidos = self.repo.atualizar_post(post_id, base, midias, links)
        await FEED_UPLOAD.excluir(removidos)
        return self.post(user, post_id)

    def excluir_post(self, user: UserResponse, post_id: str) -> None:
        self._post_editavel(post_id, self.contexto(user))
        self.repo.excluir_post(post_id)

    def fixar(self, user: UserResponse, post_id: str) -> PostOut:
        self._post_visivel(post_id, self.contexto(user))
        self.repo.alternar_fixado(post_id)
        return self.post(user, post_id)

    async def preview(self, url: str) -> LinkPreviewOut:
        url = link_preview.normalizar_url(url)
        chave = hashlib.sha256(url.encode()).hexdigest()
        try:
            cache = self.repo.cache_preview(chave, _CACHE_PREVIEW_DIAS)
        except Exception:  # noqa: BLE001 — cache é acessório
            logger.exception("Falha ao ler o cache de prévias")
            cache = None
        if cache:
            return LinkPreviewOut(**cache)
        dados = await link_preview.buscar_preview(url)
        try:
            if dados.get("titulo") or dados.get("embed_tipo"):
                self.repo.salvar_preview(chave, url, dados)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao gravar o cache de prévias")
        return LinkPreviewOut(**dados)

    # ------------------------------------------------------------------ curtidas

    def curtir(self, user: UserResponse, post_id: str, curtir: bool) -> CurtidaOut:
        self._post_visivel(post_id, self.contexto(user))
        total = self.repo.curtir(post_id, str(user.id), curtir)
        return CurtidaOut(curtido=curtir, total_curtidas=total)

    def curtidas(self, user: UserResponse, post_id: str, limite: int) -> List[AutorOut]:
        self._post_visivel(post_id, self.contexto(user))
        return [AutorOut(id=r["id"], nome=r.get("nome") or "Usuário", perfil=r.get("perfil"),
                         foto_url=r.get("foto_url")) for r in self.repo.curtidas(post_id, limite)]

    # ------------------------------------------------------------------ comentários

    def comentarios(self, user: UserResponse, post_id: str, cursor: Optional[str], limite: int) -> ComentariosPage:
        ctx = self.contexto(user)
        self._post_visivel(post_id, ctx)
        c = _dec_cursor(cursor, 2)
        rows = self.repo.listar_comentarios(post_id, ctx, (datetime.fromisoformat(c[0]), c[1]) if c else None,
                                            limite + 1)
        proximo = None
        if len(rows) > limite:
            rows = rows[:limite]
            proximo = _cod_cursor(rows[-1]["criado_em"], rows[-1]["id"])
        return ComentariosPage(itens=[self._comentario_out(r, ctx) for r in rows], proximo_cursor=proximo)

    def comentar(self, user: UserResponse, post_id: str, dados: ComentarioIn) -> ComentarioOut:
        ctx = self.contexto(user)
        post = self._post_visivel(post_id, ctx)
        if not post["permite_comentarios"]:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Os comentários estão desativados nesta publicação.")
        parent_id = None
        pai = None
        if dados.parent_id:
            pai = self.repo.get_comentario(dados.parent_id)
            if not pai or pai["post_id"] != post_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comentário respondido não encontrado.")
            # Respostas têm um nível só: responder a uma resposta vai para o mesmo fio.
            parent_id = pai.get("parent_id") or pai["id"]
        autor_do_post = str(post["autor_id"]) == ctx["me"]
        situacao = "aprovado" if ctx["admin"] or autor_do_post else "pendente"
        cid = self.repo.criar_comentario({"post_id": post_id, "autor_id": ctx["me"], "parent_id": parent_id,
                                          "texto": dados.texto, "status": situacao})
        trecho = _trecho(dados.texto)
        if situacao == "pendente":
            self._notificar_admins(titulo="Comentário aguardando moderação",
                                   mensagem=f"{_nome(user)}: “{trecho}”", link="/admin/feed/moderacao")
            if not _autor_eh_admin(post):
                self._notificar(titulo="Novo comentário para aprovar na sua publicação",
                                mensagem=f"{_nome(user)}: “{trecho}”", link="/feed/moderacao",
                                destino_usuario_id=str(post["autor_id"]))
        else:
            self._avisar_aprovado(post, {"autor_id": ctx["me"], "parent_id": parent_id, "texto": dados.texto},
                                  autor_nome=_nome(user), pai=pai)
        com = self.repo.get_comentario(cid)
        return self._comentario_out(com, ctx)

    def _avisar_aprovado(self, post: Dict[str, Any], com: Dict[str, Any], *, autor_nome: str,
                         pai: Optional[Dict[str, Any]]) -> None:
        """Comentário visível: avisa o autor do post e, nas respostas, o autor do comentário respondido."""
        link = f"/feed/{post['id']}"
        trecho = _trecho(com["texto"])
        avisados = {str(com["autor_id"])}
        if str(post["autor_id"]) not in avisados:
            self._notificar(titulo=f"{autor_nome} comentou na sua publicação", mensagem=f"“{trecho}”",
                            link=link, destino_usuario_id=str(post["autor_id"]))
            avisados.add(str(post["autor_id"]))
        if pai is None and com.get("parent_id"):
            pai = self.repo.get_comentario(com["parent_id"])
        if pai and str(pai["autor_id"]) not in avisados:
            self._notificar(titulo=f"{autor_nome} respondeu ao seu comentário", mensagem=f"“{trecho}”",
                            link=link, destino_usuario_id=str(pai["autor_id"]))

    def excluir_comentario(self, user: UserResponse, comentario_id: str) -> None:
        ctx = self.contexto(user)
        com = self.repo.get_comentario(comentario_id)
        if not com:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comentário não encontrado.")
        if not (ctx["admin"] or str(com["autor_id"]) == ctx["me"] or str(com["post_autor_id"]) == ctx["me"]):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não pode excluir este comentário.")
        self.repo.excluir_comentario(comentario_id)

    # ------------------------------------------------------------------ moderação

    def _exigir_moderador(self, user: UserResponse, comentario_id: str) -> Tuple[Dict[str, Any], Contexto]:
        ctx = self.contexto(user)
        com = self.repo.get_comentario(comentario_id)
        if not com or com.get("post_excluido_em"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comentário não encontrado.")
        if not (ctx["admin"] or str(com["post_autor_id"]) == ctx["me"]):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Somente administradores ou o autor da publicação moderam comentários.")
        return com, ctx

    def moderar(self, user: UserResponse, comentario_id: str, acao: str, motivo: Optional[str]) -> None:
        com, _ = self._exigir_moderador(user, comentario_id)
        novo = "aprovado" if acao == "aprovar" else "rejeitado"
        anterior = self.repo.moderar(comentario_id, novo, str(user.id), (motivo or "").strip() or None)
        if anterior is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comentário não encontrado.")
        # O comentarista nunca é avisado da rejeição (para ele o comentário segue visível).
        if novo == "aprovado" and anterior != "aprovado":
            post = {"id": com["post_id"], "autor_id": com["post_autor_id"]}
            self._avisar_aprovado(post, com, autor_nome=com.get("autor_nome") or "Alguém", pai=None)

    def moderar_lote(self, user: UserResponse, ids: List[str], acao: str, motivo: Optional[str]) -> int:
        feitos = 0
        for cid in dict.fromkeys(ids):
            try:
                self.moderar(user, cid, acao, motivo)
                feitos += 1
            except HTTPException:
                continue
        return feitos

    def _autor_filtro(self, user: UserResponse) -> Optional[str]:
        """Admin modera tudo; o autor só os comentários das próprias publicações."""
        perfil = perfil_do_usuario(user)
        if perfil == "admin":
            return None
        if perfil not in PERFIS_PUBLICAR:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Sem acesso à moderação.")
        return str(user.id)

    def moderacao(self, user: UserResponse, situacao: str, limite: int, offset: int,
                  somente_meus: bool) -> ModeracaoPage:
        filtro = self._autor_filtro(user) or (str(user.id) if somente_meus else None)
        total, rows = self.repo.listar_moderacao(situacao, filtro, limite, offset)
        return ModeracaoPage(total=total, itens=[ModeracaoItemOut(
            id=r["id"], post_id=r["post_id"], post_trecho=_trecho(r.get("post_trecho") or "", 140) or "(publicação com mídia)",
            post_autor_nome=r.get("post_autor_nome"), parent_id=r.get("parent_id"), autor=_autor(r),
            texto=r["texto"], status=r["status"], criado_em=r["criado_em"], moderado_em=r.get("moderado_em"),
            moderado_por_nome=(r.get("moderado_por_nome") or None) if r.get("moderado_em") else None,
            motivo_rejeicao=r.get("motivo_rejeicao"),
        ) for r in rows])

    def resumo_moderacao(self, user: UserResponse) -> int:
        return self.repo.contar_pendentes(self._autor_filtro(user))

    # ------------------------------------------------------------------ resposta via chat

    def responder_chat(self, user: UserResponse, post_id: str, texto: str, ip: Optional[str]) -> str:
        from app.modules.chat.repository import PostgresChatRepository
        from app.modules.chat.schemas import EnviarMensagemIn
        from app.modules.chat.service import ChatService

        post = self._post_visivel(post_id, self.contexto(user))
        if str(post["autor_id"]) == str(user.id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Esta publicação é sua.")
        chat = ChatService(PostgresChatRepository())
        conversa = chat.iniciar_individual(user, str(post["autor_id"]), ip)
        chat.enviar(user, conversa.id, EnviarMensagemIn(texto=texto.strip()),
                    ref={"ref_tipo": "feed_post", "ref_id": post_id})
        return conversa.id

    # ------------------------------------------------------------------ avisos (admin)

    def _aviso_out(self, r: Dict[str, Any], midias: List[Dict[str, Any]],
                   usuarios: Optional[List[Dict[str, Any]]] = None) -> AvisoOut:
        return AvisoOut(
            id=r["id"], titulo=r["titulo"], conteudo_html=r["conteudo_html"], publico_tipo=r["publico_tipo"],
            perfis=r.get("perfis") or [],
            usuarios=[AutorOut(id=u["id"], nome=u.get("nome") or "Usuário", perfil=u.get("perfil"),
                               foto_url=u.get("foto_url")) for u in (usuarios or [])],
            polo_id=r.get("polo_id"), polo_nome=r.get("polo_nome"), escola_id=r.get("escola_id"),
            escola_nome=r.get("escola_nome"), inicio_em=r["inicio_em"], fim_em=r["fim_em"],
            frequencia=r["frequencia"], exige_confirmacao=r["exige_confirmacao"], prioridade=r["prioridade"],
            ativo=r["ativo"], cor_destaque=r.get("cor_destaque"), largura=r["largura"], midias=midias,
            status=r["status"], criado_por_nome=(r.get("criado_por_nome") or None), criado_em=r.get("criado_em"),
            atualizado_em=r.get("atualizado_em"), total_visualizacoes=int(r.get("total_visualizacoes") or 0),
            total_confirmacoes=int(r.get("total_confirmacoes") or 0),
        )

    def listar_avisos(self, situacao: Optional[str], busca: Optional[str], limite: int, offset: int) -> AvisosPage:
        total, rows = self.repo.listar_avisos(situacao, busca, limite, offset)
        midias = self.repo.midias_avisos([r["id"] for r in rows])
        return AvisosPage(total=total, itens=[self._aviso_out(r, midias[r["id"]]) for r in rows])

    def _aviso_existente(self, aviso_id: str) -> Dict[str, Any]:
        aviso = self.repo.get_aviso(aviso_id)
        if not aviso:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aviso não encontrado.")
        return aviso

    def aviso(self, aviso_id: str) -> AvisoOut:
        a = self._aviso_existente(aviso_id)
        return self._aviso_out(a, a["midias"], self.repo.get_usuarios(a["usuario_ids"]))

    def _midias_aviso(self, midias: List[Any]) -> List[Dict[str, Any]]:
        saida = []
        for m in midias:
            if m.tipo == "video_link":
                url = link_preview.normalizar_url(m.url)
                embed = link_preview.detectar_embed(url)
                if not embed:
                    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail="Link de vídeo inválido: use um link do YouTube ou do Vimeo.")
                saida.append({"tipo": "video_link", "url": url, **embed})
                continue
            a = m.arquivo
            anexo = AVISOS_UPLOAD.validar_anexo(url=a.url, pathname=a.pathname, nome=a.nome, mime=a.mime,
                                                tamanho=a.tamanho)
            saida.append({"tipo": AVISOS_UPLOAD.categoria_do_mime(anexo.mime), "url": anexo.url,
                          "storage_key": anexo.storage_key, "nome": anexo.nome, "mime": anexo.mime,
                          "tamanho": anexo.tamanho})
        return saida

    async def salvar_aviso(self, user: UserResponse, aviso_id: Optional[str], dados: AvisoIn) -> AvisoOut:
        if aviso_id:
            self._aviso_existente(aviso_id)
        usuarios = [u for u in dados.usuarios if uuid_valido(u)]
        if dados.publico_tipo == "usuarios":
            encontrados = {u["id"] for u in self.repo.get_usuarios(usuarios)}
            if not encontrados:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nenhum usuário válido selecionado.")
            usuarios = [u for u in usuarios if u in encontrados]
        html = sanitizar_html(dados.conteudo_html, variante="aviso")
        midias = self._midias_aviso(dados.midias)
        if not (texto_do_html(html) or midias):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Escreva o conteúdo ou anexe uma mídia.")
        registro = {
            "titulo": dados.titulo, "conteudo_html": html, "publico_tipo": dados.publico_tipo, "perfis": dados.perfis,
            "polo_id": _uuid_ou_422(dados.polo_id, "Polo"), "escola_id": _uuid_ou_422(dados.escola_id, "Escola"),
            "inicio_em": dados.inicio_em, "fim_em": dados.fim_em, "frequencia": dados.frequencia,
            "exige_confirmacao": dados.exige_confirmacao, "prioridade": dados.prioridade, "ativo": dados.ativo,
            "cor_destaque": dados.cor_destaque, "largura": dados.largura, "criado_por": str(user.id),
        }
        novo_id, removidos = self.repo.salvar_aviso(aviso_id, registro, usuarios, midias)
        await AVISOS_UPLOAD.excluir(removidos)
        return self.aviso(novo_id)

    async def duplicar_aviso(self, user: UserResponse, aviso_id: str) -> AvisoOut:
        a = self._aviso_existente(aviso_id)
        registro = {k: a[k] for k in ("conteudo_html", "publico_tipo", "perfis", "polo_id", "escola_id", "inicio_em",
                                      "fim_em", "frequencia", "exige_confirmacao", "prioridade", "cor_destaque",
                                      "largura")}
        registro.update(titulo=f"{a['titulo']} (cópia)"[:200], ativo=False, criado_por=str(user.id))
        # A cópia reaproveita os mesmos arquivos (a exclusão de arquivos confere se ainda estão em uso).
        midias = [{"tipo": m["tipo"], "url": m["url"], "storage_key": m.get("pathname"), "nome": m.get("nome"),
                   "mime": m.get("mime"), "tamanho": m.get("tamanho"), "embed_tipo": m.get("embed_tipo"),
                   "embed_id": m.get("embed_id")} for m in a["midias"]]
        novo_id, _ = self.repo.salvar_aviso(None, registro, a["usuario_ids"], midias)
        return self.aviso(novo_id)

    def alternar_aviso(self, aviso_id: str) -> AvisoOut:
        self._aviso_existente(aviso_id)
        self.repo.alternar_aviso(aviso_id)
        return self.aviso(aviso_id)

    def excluir_aviso(self, aviso_id: str) -> None:
        if not self.repo.excluir_aviso(aviso_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aviso não encontrado.")

    def estatisticas(self, aviso_id: str, limite: int, offset: int) -> EstatisticasOut:
        a = self._aviso_existente(aviso_id)
        e = self.repo.estatisticas(a, limite, offset)
        return EstatisticasOut(
            publico_estimado=e["publico_estimado"], visualizacoes=e["visualizacoes"], confirmacoes=e["confirmacoes"],
            total=e["total"],
            itens=[VisualizacaoOut(usuario=AutorOut(id=i["uid"], nome=i.get("nome") or "Usuário",
                                                    perfil=i.get("perfil"), foto_url=i.get("foto_url")),
                                   primeira_vez_em=i["primeira_vez_em"], ultima_vez_em=i["ultima_vez_em"],
                                   vezes=i["vezes"], confirmado_em=i.get("confirmado_em")) for i in e["itens"]],
        )

    def buscar_usuarios(self, busca: Optional[str], limite: int) -> List[Dict[str, Any]]:
        return self.repo.buscar_usuarios((busca or "").strip() or None, limite)

    # ------------------------------------------------------------------ avisos (usuário)

    def avisos_pendentes(self, user: UserResponse) -> List[AvisoPopupOut]:
        rows = self.repo.avisos_pendentes(self.contexto(user), 10)
        midias = self.repo.midias_avisos([r["id"] for r in rows])
        return [AvisoPopupOut(**r, midias=midias[r["id"]]) for r in rows]

    def registrar_aviso(self, user: UserResponse, aviso_id: str, confirmar: bool) -> None:
        if not self.repo.aviso_vigente_para(aviso_id, self.contexto(user)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aviso não encontrado.")
        self.repo.registrar_visualizacao(aviso_id, str(user.id), confirmar)
