"""Persistência do AVA (PostgreSQL, SQL puro).

O motor de conteúdo é compartilhado: um capítulo pertence a uma disciplina OU a um treinamento.
As funções da estrutura recebem um ``Dono`` = (coluna, id), com a coluna restrita a ``_DONOS``.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.core.database import get_db_cursor

Dono = Tuple[str, str]
_DONOS = {"disciplina_id", "treinamento_id"}

_CAMPOS_AULA = ("titulo", "descricao", "tipo", "avaliacao_id", "duracao_min", "publicado", "obrigatoria",
                "liberar_apos_dias", "capa_url")
_CAMPOS_ITEM = ("tipo", "titulo", "url", "provedor", "embed_id", "conteudo_html", "arquivo_pathname",
                "arquivo_nome", "arquivo_mime", "arquivo_tamanho", "permite_download")


def uuid_valido(valor: Any) -> bool:
    try:
        uuid.UUID(str(valor))
        return True
    except (ValueError, TypeError):
        return False


def _limpar(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    out: Dict[str, Any] = {}
    for k, v in dict(row).items():
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


def _coluna(dono: Dono) -> str:
    if dono[0] not in _DONOS:
        raise ValueError(f"Dono inválido: {dono[0]}")
    return dono[0]


class PostgresAvaRepository:
    # ------------------------------------------------------------------ disciplinas

    _SELECT_DISCIPLINA = """
        SELECT d.id, d.nome, d.curso_id, c.nome AS curso_nome, d.semestre, d.ordem,
               COALESCE(d.ativo, true) AS ativo,
               cfg.capa_url, COALESCE(cfg.publicado, false) AS publicado,
               COALESCE(cfg.sequencial, false) AS sequencial, cfg.atualizado_em,
               (SELECT COUNT(*) FROM ava_capitulos cap WHERE cap.disciplina_id = d.id) AS total_capitulos,
               (SELECT COUNT(*) FROM ava_aulas a JOIN ava_capitulos cap ON cap.id = a.capitulo_id
                 WHERE cap.disciplina_id = d.id) AS total_aulas
        FROM disciplinas d
        LEFT JOIN cursos c ON c.id = d.curso_id
        LEFT JOIN ava_disciplina_config cfg ON cfg.disciplina_id = d.id
    """

    def listar_disciplinas(self, curso_id: str, q: Optional[str]) -> List[Dict[str, Any]]:
        sql = self._SELECT_DISCIPLINA + " WHERE d.curso_id = %(curso)s"
        params: Dict[str, Any] = {"curso": curso_id}
        if q:
            sql += " AND d.nome ILIKE %(q)s"
            params["q"] = f"%{q}%"
        sql += " ORDER BY d.semestre NULLS LAST, d.ordem NULLS LAST, d.nome"
        with get_db_cursor() as cur:
            cur.execute(sql, params)
            return [_limpar(r) for r in cur.fetchall()]

    def get_disciplina(self, disciplina_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(disciplina_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(self._SELECT_DISCIPLINA + " WHERE d.id = %s", (disciplina_id,))
            return _limpar(cur.fetchone())

    def get_config(self, disciplina_id: str) -> Dict[str, Any]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM ava_disciplina_config WHERE disciplina_id = %s", (disciplina_id,))
            row = _limpar(cur.fetchone())
        return row or {"disciplina_id": disciplina_id, "capa_url": None, "descricao_ava": None,
                       "sequencial": False, "publicado": False}

    def salvar_config(self, disciplina_id: str, dados: Dict[str, Any]) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO ava_disciplina_config (disciplina_id, capa_url, descricao_ava, sequencial, publicado)
                   VALUES (%(d)s, %(capa_url)s, %(descricao_ava)s, %(sequencial)s, %(publicado)s)
                   ON CONFLICT (disciplina_id) DO UPDATE SET
                     capa_url = EXCLUDED.capa_url, descricao_ava = EXCLUDED.descricao_ava,
                     sequencial = EXCLUDED.sequencial, publicado = EXCLUDED.publicado, atualizado_em = now()""",
                {"d": disciplina_id, **dados},
            )

    # ------------------------------------------------------------------ estrutura

    def estrutura(self, dono: Dono, somente_publicados: bool = False) -> List[Dict[str, Any]]:
        """Capítulos com ``aulas`` (cada uma com ``itens``), já ordenados."""
        coluna = _coluna(dono)
        filtro_cap = " AND cap.publicado" if somente_publicados else ""
        filtro_aula = " AND a.publicado" if somente_publicados else ""
        with get_db_cursor() as cur:
            cur.execute(f"SELECT * FROM ava_capitulos cap WHERE cap.{coluna} = %s{filtro_cap} "
                        "ORDER BY cap.ordem, cap.criado_em", (dono[1],))
            capitulos = [_limpar(r) for r in cur.fetchall()]
            if not capitulos:
                return []
            ids = [c["id"] for c in capitulos]
            cur.execute(
                f"""SELECT a.*, av.titulo AS avaliacao_titulo, dav.nome AS avaliacao_disciplina_nome
                    FROM ava_aulas a
                    LEFT JOIN avaliacoes av ON av.id = a.avaliacao_id
                    LEFT JOIN disciplinas dav ON dav.id = av.disciplina_id
                    WHERE a.capitulo_id = ANY(%s::uuid[]){filtro_aula}
                    ORDER BY a.ordem, a.criado_em""",
                (ids,),
            )
            aulas = [_limpar(r) for r in cur.fetchall()]
            itens: List[Dict[str, Any]] = []
            if aulas:
                cur.execute("SELECT * FROM ava_aula_itens WHERE aula_id = ANY(%s::uuid[]) ORDER BY ordem, criado_em",
                            ([a["id"] for a in aulas],))
                itens = [_limpar(r) for r in cur.fetchall()]
        por_aula: Dict[str, List[Dict[str, Any]]] = {}
        for item in itens:
            por_aula.setdefault(item["aula_id"], []).append(item)
        por_cap: Dict[str, List[Dict[str, Any]]] = {}
        for aula in aulas:
            aula["itens"] = por_aula.get(aula["id"], [])
            por_cap.setdefault(aula["capitulo_id"], []).append(aula)
        for cap in capitulos:
            cap["aulas"] = por_cap.get(cap["id"], [])
        return capitulos

    # ------------------------------------------------------------------ capítulos

    def get_capitulo(self, capitulo_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(capitulo_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM ava_capitulos WHERE id = %s", (capitulo_id,))
            return _limpar(cur.fetchone())

    def criar_capitulo(self, dono: Dono, dados: Dict[str, Any]) -> str:
        coluna = _coluna(dono)
        with get_db_cursor() as cur:
            cur.execute(
                f"""INSERT INTO ava_capitulos ({coluna}, titulo, descricao, publicado, ordem)
                    VALUES (%(dono)s, %(titulo)s, %(descricao)s, %(publicado)s,
                            (SELECT COALESCE(MAX(ordem) + 1, 0) FROM ava_capitulos WHERE {coluna} = %(dono)s))
                    RETURNING id""",
                {"dono": dono[1], **dados},
            )
            return str(cur.fetchone()["id"])

    def atualizar_capitulo(self, capitulo_id: str, dados: Dict[str, Any]) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE ava_capitulos SET titulo = %(titulo)s, descricao = %(descricao)s,
                   publicado = %(publicado)s, atualizado_em = now() WHERE id = %(id)s""",
                {"id": capitulo_id, **dados},
            )

    def excluir_capitulo(self, capitulo_id: str) -> List[str]:
        """Exclui (cascata em aulas e itens) e devolve as URLs dos arquivos que estavam nos itens."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT i.url FROM ava_aula_itens i JOIN ava_aulas a ON a.id = i.aula_id
                   WHERE a.capitulo_id = %s AND i.arquivo_pathname IS NOT NULL""",
                (capitulo_id,),
            )
            urls = [r["url"] for r in cur.fetchall() if r["url"]]
            cur.execute("DELETE FROM ava_capitulos WHERE id = %s", (capitulo_id,))
        return urls

    def duplicar_capitulo(self, capitulo_id: str) -> str:
        """Cópia logo após o original (mesmos arquivos; a exclusão confere se ainda estão em uso)."""
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM ava_capitulos WHERE id = %s", (capitulo_id,))
            cap = cur.fetchone()
            coluna = "disciplina_id" if cap["disciplina_id"] else "treinamento_id"
            cur.execute(f"UPDATE ava_capitulos SET ordem = ordem + 1 WHERE {coluna} = %s AND ordem > %s",
                        (cap[coluna], cap["ordem"]))
            cur.execute(
                f"""INSERT INTO ava_capitulos ({coluna}, titulo, descricao, publicado, ordem)
                    VALUES (%s, %s, %s, false, %s) RETURNING id""",
                (cap[coluna], f"{cap['titulo']} (cópia)"[:255], cap["descricao"], cap["ordem"] + 1),
            )
            novo = cur.fetchone()["id"]
            cur.execute("SELECT * FROM ava_aulas WHERE capitulo_id = %s ORDER BY ordem", (capitulo_id,))
            for aula in cur.fetchall():
                colunas = ", ".join(_CAMPOS_AULA)
                cur.execute(
                    f"""INSERT INTO ava_aulas (capitulo_id, ordem, {colunas})
                        SELECT %s, ordem, {colunas} FROM ava_aulas WHERE id = %s RETURNING id""",
                    (novo, aula["id"]),
                )
                nova_aula = cur.fetchone()["id"]
                colunas_i = ", ".join(_CAMPOS_ITEM)
                cur.execute(
                    f"""INSERT INTO ava_aula_itens (aula_id, ordem, {colunas_i})
                        SELECT %s, ordem, {colunas_i} FROM ava_aula_itens WHERE aula_id = %s""",
                    (nova_aula, aula["id"]),
                )
            return str(novo)

    # ------------------------------------------------------------------ aulas

    def get_aula(self, aula_id: str) -> Optional[Dict[str, Any]]:
        """Aula + dono do capítulo (``disciplina_id``/``treinamento_id``)."""
        if not uuid_valido(aula_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT a.*, cap.disciplina_id, cap.treinamento_id FROM ava_aulas a
                   JOIN ava_capitulos cap ON cap.id = a.capitulo_id WHERE a.id = %s""",
                (aula_id,),
            )
            return _limpar(cur.fetchone())

    def criar_aula(self, capitulo_id: str, dados: Dict[str, Any]) -> str:
        colunas = ", ".join(_CAMPOS_AULA)
        valores = ", ".join(f"%({c})s" for c in _CAMPOS_AULA)
        with get_db_cursor() as cur:
            cur.execute(
                f"""INSERT INTO ava_aulas (capitulo_id, ordem, {colunas})
                    VALUES (%(cap)s, (SELECT COALESCE(MAX(ordem) + 1, 0) FROM ava_aulas WHERE capitulo_id = %(cap)s),
                            {valores})
                    RETURNING id""",
                {"cap": capitulo_id, **{c: dados.get(c) for c in _CAMPOS_AULA}},
            )
            return str(cur.fetchone()["id"])

    def atualizar_aula(self, aula_id: str, dados: Dict[str, Any]) -> None:
        sets = ", ".join(f"{c} = %({c})s" for c in _CAMPOS_AULA)
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE ava_aulas SET {sets}, atualizado_em = now() WHERE id = %(id)s",
                        {"id": aula_id, **{c: dados.get(c) for c in _CAMPOS_AULA}})

    def excluir_aula(self, aula_id: str) -> List[str]:
        with get_db_cursor() as cur:
            cur.execute("SELECT url FROM ava_aula_itens WHERE aula_id = %s AND arquivo_pathname IS NOT NULL",
                        (aula_id,))
            urls = [r["url"] for r in cur.fetchall() if r["url"]]
            cur.execute("DELETE FROM ava_aulas WHERE id = %s", (aula_id,))
        return urls

    def remover_itens_da_aula(self, aula_id: str) -> List[str]:
        """Usado quando a aula vira do tipo 'avaliacao' (não tem itens)."""
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM ava_aula_itens WHERE aula_id = %s RETURNING url, arquivo_pathname", (aula_id,))
            return [r["url"] for r in cur.fetchall() if r["url"] and r["arquivo_pathname"]]

    # ------------------------------------------------------------------ itens

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(item_id):
            return None
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM ava_aula_itens WHERE id = %s", (item_id,))
            return _limpar(cur.fetchone())

    def criar_item(self, aula_id: str, dados: Dict[str, Any]) -> str:
        colunas = ", ".join(_CAMPOS_ITEM)
        valores = ", ".join(f"%({c})s" for c in _CAMPOS_ITEM)
        with get_db_cursor() as cur:
            cur.execute(
                f"""INSERT INTO ava_aula_itens (aula_id, ordem, {colunas})
                    VALUES (%(aula)s, (SELECT COALESCE(MAX(ordem) + 1, 0) FROM ava_aula_itens WHERE aula_id = %(aula)s),
                            {valores})
                    RETURNING id""",
                {"aula": aula_id, **{c: dados.get(c) for c in _CAMPOS_ITEM}},
            )
            return str(cur.fetchone()["id"])

    def atualizar_item(self, item_id: str, dados: Dict[str, Any]) -> None:
        sets = ", ".join(f"{c} = %({c})s" for c in _CAMPOS_ITEM)
        with get_db_cursor() as cur:
            cur.execute(f"UPDATE ava_aula_itens SET {sets}, atualizado_em = now() WHERE id = %(id)s",
                        {"id": item_id, **{c: dados.get(c) for c in _CAMPOS_ITEM}})

    def excluir_item(self, item_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM ava_aula_itens WHERE id = %s", (item_id,))

    def urls_em_uso(self, urls: Sequence[str]) -> set:
        if not urls:
            return set()
        with get_db_cursor() as cur:
            cur.execute("SELECT DISTINCT url FROM ava_aula_itens WHERE url = ANY(%s)", (list(urls),))
            return {r["url"] for r in cur.fetchall()}

    # ------------------------------------------------------------------ ordenação

    def reordenar(self, dono: Dono, capitulos: Iterable[Dict[str, Any]], aulas: Iterable[Dict[str, Any]],
                  itens: Iterable[Dict[str, Any]]) -> None:
        """Aplica tudo numa transação; ids de outro dono são ignorados pelo filtro do WHERE."""
        coluna = _coluna(dono)
        with get_db_cursor() as cur:
            for c in capitulos:
                cur.execute(f"UPDATE ava_capitulos SET ordem = %s WHERE id = %s AND {coluna} = %s",
                            (c["ordem"], c["id"], dono[1]))
            for a in aulas:
                cur.execute(
                    f"""UPDATE ava_aulas SET ordem = %(ordem)s, capitulo_id = %(cap)s
                        WHERE id = %(id)s
                          AND capitulo_id IN (SELECT id FROM ava_capitulos WHERE {coluna} = %(dono)s)
                          AND %(cap)s IN (SELECT id FROM ava_capitulos WHERE {coluna} = %(dono)s)""",
                    {"ordem": a["ordem"], "cap": a["capitulo_id"], "id": a["id"], "dono": dono[1]},
                )
            for i in itens:
                cur.execute(
                    f"""UPDATE ava_aula_itens SET ordem = %(ordem)s WHERE id = %(id)s AND aula_id IN (
                          SELECT a.id FROM ava_aulas a JOIN ava_capitulos cap ON cap.id = a.capitulo_id
                          WHERE cap.{coluna} = %(dono)s)""",
                    {"ordem": i["ordem"], "id": i["id"], "dono": dono[1]},
                )

    # ------------------------------------------------------------------ avaliações

    def avaliacoes_do_curso(self, curso_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT av.id AS avaliacao_id, av.titulo, av.ativo, d.id AS disciplina_id, d.nome AS disciplina_nome,
                          (SELECT COUNT(*) FROM avaliacao_questoes q WHERE q.avaliacao_id = av.id) AS total_questoes
                   FROM avaliacoes av JOIN disciplinas d ON d.id = av.disciplina_id
                   WHERE d.curso_id = %s
                   ORDER BY d.semestre NULLS LAST, d.ordem NULLS LAST, d.nome, av.ativo DESC, av.criado_em DESC""",
                (curso_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def get_avaliacao(self, avaliacao_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(avaliacao_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT av.id, av.titulo, av.ativo, av.disciplina_id, d.curso_id
                   FROM avaliacoes av JOIN disciplinas d ON d.id = av.disciplina_id WHERE av.id = %s""",
                (avaliacao_id,),
            )
            return _limpar(cur.fetchone())

    def curso_existe(self, curso_id: str) -> bool:
        if not uuid_valido(curso_id):
            return False
        with get_db_cursor() as cur:
            cur.execute("SELECT 1 FROM cursos WHERE id = %s", (curso_id,))
            return cur.fetchone() is not None


def get_ava_repository() -> PostgresAvaRepository:
    return PostgresAvaRepository()
