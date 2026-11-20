"""Persistência do Feed de Notícias e dos Avisos (PostgreSQL, SQL puro)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.database import get_db_cursor
from app.modules.auth.roles import nomes_equivalentes

_NOME = "TRIM(COALESCE({a}.nome, '') || ' ' || COALESCE({a}.sobrenome, ''))"
_NOME_U = _NOME.format(a="u")

# Contexto de quem consulta: {"me", "perfil", "admin", "tambem_aluno", "polo", "escola"}
Contexto = Dict[str, Any]


def uuid_valido(valor: Any) -> bool:
    try:
        uuid.UUID(str(valor))
        return True
    except (ValueError, TypeError):
        return False


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in dict(row).items()}


def _arr(valores: Optional[Sequence[str]]) -> Optional[List[str]]:
    return list(valores) if valores else None


# ---------------------------------------------------------------------------
# Filtros de visibilidade
# ---------------------------------------------------------------------------

# Público do post: admin e o autor sempre veem; demais conforme perfis e unidade.
_POST_VISIVEL = """
    p.excluido_em IS NULL AND (
        %(admin)s OR p.autor_id = %(me)s::uuid OR (
            (p.publico_perfis IS NULL OR %(perfil)s = ANY(p.publico_perfis)
             OR (%(tambem_aluno)s AND 'aluno' = ANY(p.publico_perfis)))
            AND (p.polo_id IS NULL OR p.polo_id = %(polo)s::uuid)
            AND (p.escola_id IS NULL OR p.escola_id = %(escola)s::uuid)
        )
    )
"""

# Comentário: aprovado para todos; o autor vê os próprios (inclusive pendentes/rejeitados, sem saber);
# quem modera o post (admin ou autor do post) vê também os pendentes.
_COMENTARIO_VISIVEL = """
    c.excluido_em IS NULL AND (
        c.status = 'aprovado' OR c.autor_id = %(me)s::uuid
        OR (c.status = 'pendente' AND (%(admin)s OR p.autor_id = %(me)s::uuid))
    )
"""

_AVISO_PUBLICO = """
    (a.publico_tipo = 'todos'
     OR (a.publico_tipo = 'perfis' AND (%(perfil)s = ANY(a.perfis) OR (%(tambem_aluno)s AND 'aluno' = ANY(a.perfis))))
     OR (a.publico_tipo = 'usuarios' AND EXISTS (
            SELECT 1 FROM avisos_popup_usuarios x WHERE x.aviso_id = a.id AND x.usuario_id = %(me)s::uuid)))
    AND (a.polo_id IS NULL OR a.polo_id = %(polo)s::uuid)
    AND (a.escola_id IS NULL OR a.escola_id = %(escola)s::uuid)
"""

_STATUS_AVISO = """
    CASE WHEN NOT a.ativo THEN 'inativo'
         WHEN now() < a.inicio_em THEN 'agendado'
         WHEN now() > a.fim_em THEN 'expirado'
         ELSE 'ativo' END
"""


class PostgresComunicacaoRepository:
    # ------------------------------------------------------------------ usuários

    def unidade_do_usuario(self, usuario_id: str) -> Dict[str, Optional[str]]:
        """Polo/Escola do usuário (para aluno, o vínculo vem do cadastro de aluno)."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT COALESCE(a.polo_id, u.polo_id) AS polo_id, COALESCE(a.escola_id, u.escola_id) AS escola_id
                     FROM usuarios u LEFT JOIN alunos a ON a.usuario_id = u.id
                    WHERE u.id = %s ORDER BY a.polo_id IS NULL LIMIT 1""",
                (usuario_id,),
            )
            r = _limpar(cur.fetchone()) or {}
            return {"polo": r.get("polo_id"), "escola": r.get("escola_id")}

    def get_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(usuario_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT u.id, {_NOME_U} AS nome, u.foto_url, p.nome AS perfil, u.status
                              FROM usuarios u LEFT JOIN perfis p ON p.id = u.perfil_id WHERE u.id = %s""",
                        (usuario_id,))
            return _limpar(cur.fetchone())

    def get_usuarios(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        ids = [str(i) for i in ids if uuid_valido(i)]
        if not ids:
            return []
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT u.id, {_NOME_U} AS nome, u.foto_url, p.nome AS perfil, u.status
                              FROM usuarios u LEFT JOIN perfis p ON p.id = u.perfil_id
                             WHERE u.id::text = ANY(%s) ORDER BY nome""", (ids,))
            return [_limpar(r) for r in cur.fetchall()]

    def buscar_usuarios(self, busca: Optional[str], limite: int) -> List[Dict[str, Any]]:
        filtros, params = ["COALESCE(u.status, 'ativo') = 'ativo'"], []
        if busca:
            filtros.append(f"({_NOME_U} ILIKE %s OR u.email ILIKE %s OR u.cpf ILIKE %s)")
            termo = f"%{busca.strip()}%"
            params += [termo, termo, termo]
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT u.id, {_NOME_U} AS nome, u.foto_url, u.email, p.nome AS perfil,
                           po.nome AS polo_nome, es.nome AS escola_nome
                      FROM usuarios u
                      LEFT JOIN perfis p ON p.id = u.perfil_id
                      LEFT JOIN polos po ON po.id = u.polo_id
                      LEFT JOIN escolas es ON es.id = u.escola_id
                     WHERE {' AND '.join(filtros)} ORDER BY nome LIMIT %s""",
                (*params, limite),
            )
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ posts

    _COLS_POST = f"""
        p.*, {_NOME.format(a='au')} AS autor_nome, au.foto_url AS autor_foto, ap.nome AS autor_perfil,
        po.nome AS polo_nome, es.nome AS escola_nome,
        EXISTS (SELECT 1 FROM feed_curtidas fc WHERE fc.post_id = p.id AND fc.usuario_id = %(me)s::uuid)
            AS curtido_por_mim,
        (SELECT count(*) FROM feed_comentarios c WHERE c.post_id = p.id AND {_COMENTARIO_VISIVEL})
            AS total_comentarios_visiveis,
        (SELECT count(*) FROM feed_comentarios c WHERE c.post_id = p.id AND c.status = 'pendente'
            AND c.excluido_em IS NULL) AS pendentes
    """
    _JOINS_POST = """
        JOIN usuarios au ON au.id = p.autor_id
        LEFT JOIN perfis ap ON ap.id = au.perfil_id
        LEFT JOIN polos po ON po.id = p.polo_id
        LEFT JOIN escolas es ON es.id = p.escola_id
    """

    def listar_posts(self, ctx: Contexto, cursor: Optional[Tuple[int, datetime, str]],
                     limite: int) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {**ctx, "lim": limite}
        filtro_cursor = ""
        if cursor:
            filtro_cursor = "AND (p.fixado::int, p.criado_em, p.id) < (%(cf)s, %(cc)s, %(ci)s::uuid)"
            params.update(cf=cursor[0], cc=cursor[1], ci=cursor[2])
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT {self._COLS_POST} FROM feed_publicacoes p {self._JOINS_POST}
                     WHERE {_POST_VISIVEL} {filtro_cursor}
                     ORDER BY p.fixado DESC, p.criado_em DESC, p.id DESC LIMIT %(lim)s""",
                params,
            )
            return [_limpar(r) for r in cur.fetchall()]

    def get_post(self, post_id: str, ctx: Contexto) -> Optional[Dict[str, Any]]:
        """Post visível para o contexto (None se não existe, foi excluído ou está fora do público)."""
        if not uuid_valido(post_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT {self._COLS_POST} FROM feed_publicacoes p {self._JOINS_POST}
                             WHERE p.id = %(pid)s AND {_POST_VISIVEL}""", {**ctx, "pid": post_id})
            return _limpar(cur.fetchone())

    def midias_e_links(self, post_ids: Sequence[str]) -> Tuple[Dict[str, List], Dict[str, List]]:
        midias: Dict[str, List] = {pid: [] for pid in post_ids}
        links: Dict[str, List] = {pid: [] for pid in post_ids}
        if not post_ids:
            return midias, links
        with get_db_cursor() as cur:
            cur.execute("""SELECT id, post_id, tipo, url, storage_key AS pathname, nome, mime, tamanho
                             FROM feed_midias WHERE post_id::text = ANY(%s) ORDER BY ordem, criado_em""",
                        (list(post_ids),))
            for r in cur.fetchall():
                r = _limpar(r)
                midias[r.pop("post_id")].append(r)
            cur.execute("""SELECT post_id, url, titulo, descricao, imagem_url, site_nome, embed_tipo, embed_id
                             FROM feed_links WHERE post_id::text = ANY(%s) ORDER BY ordem""", (list(post_ids),))
            for r in cur.fetchall():
                r = _limpar(r)
                links[r.pop("post_id")].append(r)
        return midias, links

    def _gravar_anexos(self, cur, post_id: str, midias: Sequence[Dict[str, Any]],
                       links: Sequence[Dict[str, Any]]) -> None:
        for i, m in enumerate(midias):
            cur.execute("""INSERT INTO feed_midias (post_id, tipo, url, storage_key, nome, mime, tamanho, ordem)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (post_id, m["tipo"], m["url"], m["storage_key"], m["nome"], m["mime"], m["tamanho"], i))
        for i, l in enumerate(links):
            cur.execute("""INSERT INTO feed_links (post_id, url, titulo, descricao, imagem_url, site_nome,
                                                   embed_tipo, embed_id, ordem)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (post_id, l["url"], l.get("titulo"), l.get("descricao"), l.get("imagem_url"),
                         l.get("site_nome"), l.get("embed_tipo"), l.get("embed_id"), i))

    def criar_post(self, dados: Dict[str, Any], midias: Sequence[Dict[str, Any]],
                   links: Sequence[Dict[str, Any]]) -> str:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO feed_publicacoes (autor_id, conteudo_html, conteudo_texto, publico_perfis, polo_id,
                                                 escola_id, permite_comentarios)
                   VALUES (%s, %s, %s, %s::text[], %s, %s, %s) RETURNING id""",
                (dados["autor_id"], dados["conteudo_html"], dados["conteudo_texto"], _arr(dados["publico_perfis"]),
                 dados["polo_id"], dados["escola_id"], dados["permite_comentarios"]),
            )
            post_id = str(cur.fetchone()["id"])
            self._gravar_anexos(cur, post_id, midias, links)
            return post_id

    def atualizar_post(self, post_id: str, dados: Dict[str, Any], midias: Sequence[Dict[str, Any]],
                       links: Sequence[Dict[str, Any]]) -> List[str]:
        """Substitui conteúdo, mídias e links. Retorna os arquivos que deixaram de ser usados."""
        with get_db_cursor() as cur:
            cur.execute("SELECT url, storage_key FROM feed_midias WHERE post_id = %s", (post_id,))
            antigos = {r["storage_key"]: r["url"] for r in cur.fetchall()}
            cur.execute(
                """UPDATE feed_publicacoes SET conteudo_html = %s, conteudo_texto = %s, publico_perfis = %s::text[],
                          polo_id = %s, escola_id = %s, permite_comentarios = %s, editado = true, atualizado_em = now()
                    WHERE id = %s""",
                (dados["conteudo_html"], dados["conteudo_texto"], _arr(dados["publico_perfis"]), dados["polo_id"],
                 dados["escola_id"], dados["permite_comentarios"], post_id),
            )
            cur.execute("DELETE FROM feed_midias WHERE post_id = %s", (post_id,))
            cur.execute("DELETE FROM feed_links WHERE post_id = %s", (post_id,))
            self._gravar_anexos(cur, post_id, midias, links)
        mantidos = {m["storage_key"] for m in midias}
        return [url or key for key, url in antigos.items() if key not in mantidos]

    def excluir_post(self, post_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE feed_publicacoes SET excluido_em = now() WHERE id = %s AND excluido_em IS NULL",
                        (post_id,))

    def alternar_fixado(self, post_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("UPDATE feed_publicacoes SET fixado = NOT fixado WHERE id = %s RETURNING fixado", (post_id,))
            r = cur.fetchone()
            return bool(r and r["fixado"])

    # ------------------------------------------------------------------ curtidas

    def curtir(self, post_id: str, usuario_id: str, curtir: bool) -> int:
        with get_db_cursor() as cur:
            if curtir:
                cur.execute("""INSERT INTO feed_curtidas (post_id, usuario_id) VALUES (%s, %s)
                               ON CONFLICT DO NOTHING""", (post_id, usuario_id))
                delta = cur.rowcount
            else:
                cur.execute("DELETE FROM feed_curtidas WHERE post_id = %s AND usuario_id = %s", (post_id, usuario_id))
                delta = -cur.rowcount
            cur.execute("""UPDATE feed_publicacoes SET total_curtidas = GREATEST(total_curtidas + %s, 0)
                            WHERE id = %s RETURNING total_curtidas""", (delta, post_id))
            return int(cur.fetchone()["total_curtidas"])

    def curtidas(self, post_id: str, limite: int) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT u.id, {_NOME_U} AS nome, u.foto_url, p.nome AS perfil
                              FROM feed_curtidas fc JOIN usuarios u ON u.id = fc.usuario_id
                              LEFT JOIN perfis p ON p.id = u.perfil_id
                             WHERE fc.post_id = %s ORDER BY fc.criado_em DESC LIMIT %s""", (post_id, limite))
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ comentários

    _COLS_COMENTARIO = f"""
        c.id, c.post_id, c.parent_id, c.autor_id, c.texto, c.status, c.criado_em, c.moderado_em,
        c.motivo_rejeicao, p.autor_id AS post_autor_id,
        {_NOME_U} AS autor_nome, u.foto_url AS autor_foto, pf.nome AS autor_perfil
    """
    _JOINS_COMENTARIO = """
        JOIN feed_publicacoes p ON p.id = c.post_id
        JOIN usuarios u ON u.id = c.autor_id
        LEFT JOIN perfis pf ON pf.id = u.perfil_id
    """

    def comentarios_recentes(self, post_ids: Sequence[str], ctx: Contexto, por_post: int) -> Dict[str, List]:
        """Últimos comentários de 1º nível visíveis de cada post (para o card do feed)."""
        saida: Dict[str, List] = {pid: [] for pid in post_ids}
        if not post_ids:
            return saida
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT * FROM (
                        SELECT {self._COLS_COMENTARIO},
                               row_number() OVER (PARTITION BY c.post_id ORDER BY c.criado_em DESC, c.id DESC) AS rn
                          FROM feed_comentarios c {self._JOINS_COMENTARIO}
                         WHERE c.post_id::text = ANY(%(ids)s) AND c.parent_id IS NULL AND {_COMENTARIO_VISIVEL}
                    ) x WHERE rn <= %(n)s ORDER BY criado_em, id""",
                {**ctx, "ids": list(post_ids), "n": por_post},
            )
            for r in cur.fetchall():
                r = _limpar(r)
                saida[r["post_id"]].append(r)
        return saida

    def listar_comentarios(self, post_id: str, ctx: Contexto, cursor: Optional[Tuple[datetime, str]],
                           limite: int) -> List[Dict[str, Any]]:
        """Comentários e respostas visíveis do post, em ordem cronológica."""
        params: Dict[str, Any] = {**ctx, "pid": post_id, "lim": limite}
        filtro = ""
        if cursor:
            filtro = "AND (c.criado_em, c.id) > (%(cc)s, %(ci)s::uuid)"
            params.update(cc=cursor[0], ci=cursor[1])
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT {self._COLS_COMENTARIO} FROM feed_comentarios c {self._JOINS_COMENTARIO}
                     WHERE c.post_id = %(pid)s AND {_COMENTARIO_VISIVEL} {filtro}
                     ORDER BY c.criado_em, c.id LIMIT %(lim)s""",
                params,
            )
            return [_limpar(r) for r in cur.fetchall()]

    def get_comentario(self, comentario_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(comentario_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT {self._COLS_COMENTARIO}, p.excluido_em AS post_excluido_em
                              FROM feed_comentarios c {self._JOINS_COMENTARIO}
                             WHERE c.id = %s AND c.excluido_em IS NULL""", (comentario_id,))
            return _limpar(cur.fetchone())

    def criar_comentario(self, dados: Dict[str, Any]) -> str:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO feed_comentarios (post_id, autor_id, parent_id, texto, status, moderado_por, moderado_em)
                   VALUES (%(post_id)s, %(autor_id)s, %(parent_id)s, %(texto)s, %(status)s,
                           CASE WHEN %(status)s = 'aprovado' THEN %(autor_id)s::uuid END,
                           CASE WHEN %(status)s = 'aprovado' THEN now() END)
                   RETURNING id""",
                dados,
            )
            cid = str(cur.fetchone()["id"])
            if dados["status"] == "aprovado":
                cur.execute("""UPDATE feed_publicacoes SET total_comentarios_aprovados = total_comentarios_aprovados + 1
                                WHERE id = %s""", (dados["post_id"],))
            return cid

    def moderar(self, comentario_id: str, novo_status: str, por: str, motivo: Optional[str]) -> Optional[str]:
        """Aplica a moderação. Retorna o status anterior (None se o comentário não existe)."""
        with get_db_cursor() as cur:
            cur.execute("SELECT status, post_id FROM feed_comentarios WHERE id = %s AND excluido_em IS NULL FOR UPDATE",
                        (comentario_id,))
            atual = cur.fetchone()
            if not atual:
                return None
            cur.execute("""UPDATE feed_comentarios SET status = %s, moderado_por = %s, moderado_em = now(),
                                  motivo_rejeicao = %s WHERE id = %s""",
                        (novo_status, por, motivo if novo_status == "rejeitado" else None, comentario_id))
            delta = (novo_status == "aprovado") - (atual["status"] == "aprovado")
            if delta:
                cur.execute("""UPDATE feed_publicacoes
                                  SET total_comentarios_aprovados = GREATEST(total_comentarios_aprovados + %s, 0)
                                WHERE id = %s""", (delta, atual["post_id"]))
            return atual["status"]

    def excluir_comentario(self, comentario_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("""UPDATE feed_comentarios SET excluido_em = now()
                            WHERE (id = %s OR parent_id = %s) AND excluido_em IS NULL
                        RETURNING post_id, status""", (comentario_id, comentario_id))
            linhas = cur.fetchall()
            aprovados = sum(1 for r in linhas if r["status"] == "aprovado")
            if aprovados:
                cur.execute("""UPDATE feed_publicacoes
                                  SET total_comentarios_aprovados = GREATEST(total_comentarios_aprovados - %s, 0)
                                WHERE id = %s""", (aprovados, linhas[0]["post_id"]))

    def listar_moderacao(self, status: str, autor_post_id: Optional[str], limite: int,
                         offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        filtros = ["c.excluido_em IS NULL", "p.excluido_em IS NULL", "c.status = %(st)s"]
        params: Dict[str, Any] = {"st": status, "lim": limite, "off": offset}
        if autor_post_id:
            filtros.append("p.autor_id = %(ap)s::uuid")
            params["ap"] = autor_post_id
        where = " AND ".join(filtros)
        ordem = "c.criado_em" if status == "pendente" else "c.moderado_em DESC NULLS LAST, c.criado_em DESC"
        with get_db_cursor() as cur:
            cur.execute(f"SELECT count(*) AS n FROM feed_comentarios c JOIN feed_publicacoes p ON p.id = c.post_id "
                        f"WHERE {where}", params)
            total = int(cur.fetchone()["n"])
            cur.execute(
                f"""SELECT {self._COLS_COMENTARIO}, left(p.conteudo_texto, 160) AS post_trecho,
                           {_NOME.format(a='pa')} AS post_autor_nome, {_NOME.format(a='mo')} AS moderado_por_nome
                      FROM feed_comentarios c {self._JOINS_COMENTARIO}
                      JOIN usuarios pa ON pa.id = p.autor_id
                      LEFT JOIN usuarios mo ON mo.id = c.moderado_por
                     WHERE {where} ORDER BY {ordem} LIMIT %(lim)s OFFSET %(off)s""",
                params,
            )
            return total, [_limpar(r) for r in cur.fetchall()]

    def contar_pendentes(self, autor_post_id: Optional[str]) -> int:
        filtro = "AND p.autor_id = %s" if autor_post_id else ""
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT count(*) AS n FROM feed_comentarios c JOIN feed_publicacoes p ON p.id = c.post_id
                             WHERE c.status = 'pendente' AND c.excluido_em IS NULL AND p.excluido_em IS NULL {filtro}""",
                        (autor_post_id,) if autor_post_id else ())
            return int(cur.fetchone()["n"])

    # ------------------------------------------------------------------ cache de prévias

    def cache_preview(self, url_hash: str, dias: int) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("""SELECT dados FROM feed_link_cache
                            WHERE url_hash = %s AND buscado_em > now() - make_interval(days => %s)""",
                        (url_hash, dias))
            r = cur.fetchone()
            return dict(r["dados"]) if r else None

    def salvar_preview(self, url_hash: str, url: str, dados: Dict[str, Any]) -> None:
        with get_db_cursor() as cur:
            cur.execute("""INSERT INTO feed_link_cache (url_hash, url, dados, buscado_em) VALUES (%s, %s, %s, now())
                           ON CONFLICT (url_hash) DO UPDATE SET dados = EXCLUDED.dados, buscado_em = now()""",
                        (url_hash, url, json.dumps(dados)))

    # ------------------------------------------------------------------ avisos (admin)

    _COLS_AVISO = f"""
        a.*, {_STATUS_AVISO} AS status, {_NOME_U} AS criado_por_nome, po.nome AS polo_nome, es.nome AS escola_nome,
        (SELECT count(*) FROM avisos_popup_visualizacoes v WHERE v.aviso_id = a.id) AS total_visualizacoes,
        (SELECT count(*) FROM avisos_popup_visualizacoes v WHERE v.aviso_id = a.id AND v.confirmado_em IS NOT NULL)
            AS total_confirmacoes
    """
    _JOINS_AVISO = """
        LEFT JOIN usuarios u ON u.id = a.criado_por
        LEFT JOIN polos po ON po.id = a.polo_id
        LEFT JOIN escolas es ON es.id = a.escola_id
    """

    def listar_avisos(self, status: Optional[str], busca: Optional[str], limite: int,
                      offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        filtros, params = ["a.excluido_em IS NULL"], {"lim": limite, "off": offset}
        if status:
            filtros.append(f"({_STATUS_AVISO}) = %(st)s")
            params["st"] = status
        if busca:
            filtros.append("a.titulo ILIKE %(b)s")
            params["b"] = f"%{busca.strip()}%"
        where = " AND ".join(filtros)
        with get_db_cursor() as cur:
            cur.execute(f"SELECT count(*) AS n FROM avisos_popup a WHERE {where}", params)
            total = int(cur.fetchone()["n"])
            cur.execute(f"""SELECT {self._COLS_AVISO} FROM avisos_popup a {self._JOINS_AVISO}
                             WHERE {where} ORDER BY a.inicio_em DESC, a.criado_em DESC
                             LIMIT %(lim)s OFFSET %(off)s""", params)
            return total, [_limpar(r) for r in cur.fetchall()]

    def get_aviso(self, aviso_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(aviso_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT {self._COLS_AVISO} FROM avisos_popup a {self._JOINS_AVISO}
                             WHERE a.id = %s AND a.excluido_em IS NULL""", (aviso_id,))
            aviso = _limpar(cur.fetchone())
            if not aviso:
                return None
            cur.execute("SELECT usuario_id FROM avisos_popup_usuarios WHERE aviso_id = %s", (aviso_id,))
            aviso["usuario_ids"] = [str(r["usuario_id"]) for r in cur.fetchall()]
        aviso["midias"] = self.midias_avisos([aviso_id])[aviso_id]
        return aviso

    def midias_avisos(self, aviso_ids: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
        saida: Dict[str, List] = {aid: [] for aid in aviso_ids}
        if not aviso_ids:
            return saida
        with get_db_cursor() as cur:
            cur.execute("""SELECT id, aviso_id, tipo, url, storage_key AS pathname, nome, mime, tamanho,
                                  embed_tipo, embed_id
                             FROM avisos_popup_midias WHERE aviso_id::text = ANY(%s) ORDER BY ordem""",
                        (list(aviso_ids),))
            for r in cur.fetchall():
                r = _limpar(r)
                saida[r.pop("aviso_id")].append(r)
        return saida

    def salvar_aviso(self, aviso_id: Optional[str], dados: Dict[str, Any], usuarios: Sequence[str],
                     midias: Sequence[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Cria (aviso_id=None) ou substitui o aviso. Retorna (id, arquivos que deixaram de ser usados)."""
        campos = ("titulo", "conteudo_html", "publico_tipo", "perfis", "polo_id", "escola_id", "inicio_em", "fim_em",
                  "frequencia", "exige_confirmacao", "prioridade", "ativo", "cor_destaque", "largura")
        valores = {**dados, "perfis": _arr(dados.get("perfis"))}
        antigos: Dict[str, str] = {}
        with get_db_cursor() as cur:
            if aviso_id is None:
                cur.execute(
                    f"""INSERT INTO avisos_popup ({', '.join(campos)}, criado_por)
                        VALUES ({', '.join(f'%({c})s' + ('::text[]' if c == 'perfis' else '') for c in campos)},
                                %(criado_por)s) RETURNING id""",
                    valores,
                )
                aviso_id = str(cur.fetchone()["id"])
            else:
                cur.execute("SELECT url, storage_key FROM avisos_popup_midias WHERE aviso_id = %s AND storage_key IS NOT NULL",
                            (aviso_id,))
                antigos = {r["storage_key"]: r["url"] for r in cur.fetchall()}
                sets = ", ".join(f"{c} = %({c})s" + ("::text[]" if c == "perfis" else "") for c in campos)
                cur.execute(f"UPDATE avisos_popup SET {sets}, atualizado_em = now() WHERE id = %(id)s",
                            {**valores, "id": aviso_id})
                cur.execute("DELETE FROM avisos_popup_usuarios WHERE aviso_id = %s", (aviso_id,))
                cur.execute("DELETE FROM avisos_popup_midias WHERE aviso_id = %s", (aviso_id,))
            for uid in usuarios:
                cur.execute("""INSERT INTO avisos_popup_usuarios (aviso_id, usuario_id) VALUES (%s, %s)
                               ON CONFLICT DO NOTHING""", (aviso_id, uid))
            for i, m in enumerate(midias):
                cur.execute("""INSERT INTO avisos_popup_midias (aviso_id, tipo, url, storage_key, nome, mime, tamanho,
                                                               embed_tipo, embed_id, ordem)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (aviso_id, m["tipo"], m["url"], m.get("storage_key"), m.get("nome"), m.get("mime"),
                             m.get("tamanho"), m.get("embed_tipo"), m.get("embed_id"), i))
        mantidos = {m.get("storage_key") for m in midias}
        sobras = {key: url for key, url in antigos.items() if key not in mantidos}
        if sobras:
            # Cópias (duplicar) compartilham arquivos: só remove o que nenhum outro aviso usa.
            with get_db_cursor() as cur:
                cur.execute("SELECT DISTINCT storage_key FROM avisos_popup_midias WHERE storage_key = ANY(%s)",
                            (list(sobras),))
                for r in cur.fetchall():
                    sobras.pop(r["storage_key"], None)
        return aviso_id, [url or key for key, url in sobras.items()]

    def excluir_aviso(self, aviso_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("UPDATE avisos_popup SET excluido_em = now() WHERE id = %s AND excluido_em IS NULL",
                        (aviso_id,))
            return cur.rowcount > 0

    def alternar_aviso(self, aviso_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE avisos_popup SET ativo = NOT ativo, atualizado_em = now() WHERE id = %s", (aviso_id,))

    def estatisticas(self, aviso: Dict[str, Any], limite: int, offset: int) -> Dict[str, Any]:
        aid = aviso["id"]
        with get_db_cursor() as cur:
            # Público estimado: usuários ativos que casam com o público e a unidade do aviso.
            filtros = ["COALESCE(u.status, 'ativo') = 'ativo'"]
            params: Dict[str, Any] = {"aid": aid}
            if aviso["publico_tipo"] == "perfis":
                nomes = sorted({n for p in (aviso.get("perfis") or []) for n in nomes_equivalentes(p)})
                filtros.append("lower(pf.nome) = ANY(%(nomes)s)")
                params["nomes"] = nomes
            elif aviso["publico_tipo"] == "usuarios":
                filtros.append("u.id IN (SELECT usuario_id FROM avisos_popup_usuarios WHERE aviso_id = %(aid)s)")
            if aviso.get("polo_id"):
                filtros.append("COALESCE(al.polo_id, u.polo_id) = %(polo)s::uuid")
                params["polo"] = aviso["polo_id"]
            if aviso.get("escola_id"):
                filtros.append("COALESCE(al.escola_id, u.escola_id) = %(escola)s::uuid")
                params["escola"] = aviso["escola_id"]
            cur.execute(f"""SELECT count(DISTINCT u.id) AS n FROM usuarios u
                              LEFT JOIN perfis pf ON pf.id = u.perfil_id
                              LEFT JOIN alunos al ON al.usuario_id = u.id
                             WHERE {' AND '.join(filtros)}""", params)
            publico = int(cur.fetchone()["n"])
            cur.execute("""SELECT count(*) AS vis, count(confirmado_em) AS conf
                             FROM avisos_popup_visualizacoes WHERE aviso_id = %s""", (aid,))
            r = cur.fetchone()
            cur.execute(
                f"""SELECT v.*, u.id AS uid, {_NOME_U} AS nome, u.foto_url, pf.nome AS perfil
                      FROM avisos_popup_visualizacoes v JOIN usuarios u ON u.id = v.usuario_id
                      LEFT JOIN perfis pf ON pf.id = u.perfil_id
                     WHERE v.aviso_id = %s ORDER BY v.ultima_vez_em DESC LIMIT %s OFFSET %s""",
                (aid, limite, offset),
            )
            itens = [_limpar(x) for x in cur.fetchall()]
        return {"publico_estimado": publico, "visualizacoes": int(r["vis"]), "confirmacoes": int(r["conf"]),
                "total": int(r["vis"]), "itens": itens}

    # ------------------------------------------------------------------ avisos (usuário)

    def avisos_pendentes(self, ctx: Contexto, limite: int) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT a.id, a.titulo, a.conteudo_html, a.frequencia, a.exige_confirmacao, a.cor_destaque, a.largura
                      FROM avisos_popup a
                      LEFT JOIN avisos_popup_visualizacoes v ON v.aviso_id = a.id AND v.usuario_id = %(me)s::uuid
                     WHERE a.excluido_em IS NULL AND a.ativo AND now() BETWEEN a.inicio_em AND a.fim_em
                       AND {_AVISO_PUBLICO}
                       AND (a.frequencia = 'toda_sessao'
                            OR (a.exige_confirmacao AND v.confirmado_em IS NULL)
                            OR (NOT a.exige_confirmacao AND a.frequencia = 'uma_vez' AND v.aviso_id IS NULL))
                     ORDER BY a.prioridade DESC, a.inicio_em LIMIT %(lim)s""",
                {**ctx, "lim": limite},
            )
            return [_limpar(r) for r in cur.fetchall()]

    def aviso_vigente_para(self, aviso_id: str, ctx: Contexto) -> bool:
        if not uuid_valido(aviso_id):
            return False
        with get_db_cursor() as cur:
            cur.execute(f"""SELECT 1 FROM avisos_popup a
                             WHERE a.id = %(aid)s AND a.excluido_em IS NULL AND a.ativo
                               AND now() BETWEEN a.inicio_em AND a.fim_em AND {_AVISO_PUBLICO}""",
                        {**ctx, "aid": aviso_id})
            return cur.fetchone() is not None

    def registrar_visualizacao(self, aviso_id: str, usuario_id: str, confirmar: bool) -> None:
        with get_db_cursor() as cur:
            if confirmar:
                cur.execute("""INSERT INTO avisos_popup_visualizacoes (aviso_id, usuario_id, confirmado_em)
                               VALUES (%s, %s, now())
                               ON CONFLICT (aviso_id, usuario_id) DO UPDATE
                                  SET confirmado_em = COALESCE(avisos_popup_visualizacoes.confirmado_em, now())""",
                            (aviso_id, usuario_id))
            else:
                cur.execute("""INSERT INTO avisos_popup_visualizacoes (aviso_id, usuario_id) VALUES (%s, %s)
                               ON CONFLICT (aviso_id, usuario_id) DO UPDATE
                                  SET vezes = avisos_popup_visualizacoes.vezes + 1, ultima_vez_em = now()""",
                            (aviso_id, usuario_id))


_repo: Optional[PostgresComunicacaoRepository] = None


def get_comunicacao_repository() -> PostgresComunicacaoRepository:
    global _repo
    if _repo is None:
        _repo = PostgresComunicacaoRepository()
    return _repo


def set_comunicacao_repository(repo: Optional[PostgresComunicacaoRepository]) -> None:
    global _repo
    _repo = repo
