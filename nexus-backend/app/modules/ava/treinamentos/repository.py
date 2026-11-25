"""Persistência dos Treinamentos (PostgreSQL, SQL puro)."""
from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional, Sequence, Tuple

from psycopg2.errors import UniqueViolation

from app.core.database import get_db_cursor
from app.modules.ava.repository import _CAMPOS_AULA, _CAMPOS_ITEM, _limpar, uuid_valido

_CAMPOS = ("titulo", "descricao", "capa_url", "categoria", "carga_horaria", "perfis_alvo", "certificado_ativo",
           "sequencial", "data_inicio", "data_fim", "publicado")

# Aulas publicadas de capítulos publicados do treinamento `t`.
_AULAS_T = """
    SELECT a.id, a.obrigatoria, a.duracao_min FROM ava_aulas a
    JOIN ava_capitulos cap ON cap.id = a.capitulo_id
    WHERE cap.treinamento_id = t.id AND cap.publicado AND a.publicado
"""

_SELECT = """
    SELECT t.*,
           (SELECT COUNT(*) FROM ava_capitulos cap WHERE cap.treinamento_id = t.id) AS total_capitulos,
           (SELECT COUNT(*) FROM ava_aulas a JOIN ava_capitulos cap ON cap.id = a.capitulo_id
             WHERE cap.treinamento_id = t.id) AS total_aulas,
           (SELECT COUNT(DISTINCT p.usuario_id) FROM ava_progresso p JOIN ava_aulas a ON a.id = p.aula_id
              JOIN ava_capitulos cap ON cap.id = a.capitulo_id WHERE cap.treinamento_id = t.id) AS total_participantes,
           (SELECT COUNT(*) FROM ava_treinamento_conclusoes tc WHERE tc.treinamento_id = t.id) AS total_concluintes
    FROM ava_treinamentos t
"""


def _codigo() -> str:
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(10))


class PostgresTreinamentosRepository:
    # ------------------------------------------------------------------ admin

    def listar(self, q: Optional[str], situacao: str, limite: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
        filtros, params = [], {}
        if q:
            filtros.append("t.titulo ILIKE %(q)s")
            params["q"] = f"%{q}%"
        if situacao == "publicado":
            filtros.append("t.publicado")
        elif situacao == "rascunho":
            filtros.append("NOT t.publicado")
        where = f" WHERE {' AND '.join(filtros)}" if filtros else ""
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM ava_treinamentos t{where}", params)
            total = int(cur.fetchone()["n"])
            cur.execute(f"{_SELECT}{where} ORDER BY t.atualizado_em DESC LIMIT %(l)s OFFSET %(o)s",
                        {**params, "l": limite, "o": offset})
            return total, [_limpar(r) for r in cur.fetchall()]

    def obter(self, treinamento_id: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(treinamento_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(f"{_SELECT} WHERE t.id = %s", (treinamento_id,))
            return _limpar(cur.fetchone())

    def unidades(self, ids: Sequence[str]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """{treinamento_id: {"polos": [...], "escolas": [...]}}"""
        if not ids:
            return {}
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT tu.treinamento_id, p.id AS polo_id, p.nome AS polo_nome, e.id AS escola_id, e.nome AS escola_nome,
                          e.polo_id AS escola_polo_id
                   FROM ava_treinamento_unidades tu
                   LEFT JOIN polos p ON p.id = tu.polo_id LEFT JOIN escolas e ON e.id = tu.escola_id
                   WHERE tu.treinamento_id = ANY(%s::uuid[])""",
                (list(ids),),
            )
            saida: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
            for r in (_limpar(x) for x in cur.fetchall()):
                alvo = saida.setdefault(r["treinamento_id"], {"polos": [], "escolas": []})
                if r["polo_id"]:
                    alvo["polos"].append({"id": r["polo_id"], "nome": r["polo_nome"] or "Polo"})
                if r["escola_id"]:
                    alvo["escolas"].append({"id": r["escola_id"], "nome": r["escola_nome"] or "Escola",
                                            "polo_id": r["escola_polo_id"]})
            return saida

    def salvar(self, treinamento_id: Optional[str], dados: Dict[str, Any], polos: Sequence[str],
               escolas: Sequence[str], usuario_id: Optional[str]) -> str:
        with get_db_cursor() as cur:
            if treinamento_id:
                sets = ", ".join(f"{c} = %({c})s" for c in _CAMPOS)
                cur.execute(f"UPDATE ava_treinamentos SET {sets}, atualizado_em = now() WHERE id = %(id)s",
                            {**{c: dados.get(c) for c in _CAMPOS}, "id": treinamento_id})
            else:
                colunas = ", ".join(_CAMPOS)
                valores = ", ".join(f"%({c})s" for c in _CAMPOS)
                cur.execute(f"INSERT INTO ava_treinamentos ({colunas}, criado_por) VALUES ({valores}, %(u)s) RETURNING id",
                            {**{c: dados.get(c) for c in _CAMPOS}, "u": usuario_id})
                treinamento_id = str(cur.fetchone()["id"])
            cur.execute("DELETE FROM ava_treinamento_unidades WHERE treinamento_id = %s", (treinamento_id,))
            for polo in polos:
                cur.execute("INSERT INTO ava_treinamento_unidades (treinamento_id, polo_id) VALUES (%s, %s)", (treinamento_id, polo))
            for escola in escolas:
                cur.execute("INSERT INTO ava_treinamento_unidades (treinamento_id, escola_id) VALUES (%s, %s)",
                            (treinamento_id, escola))
            return treinamento_id

    def unidades_existem(self, polos: Sequence[str], escolas: Sequence[str]) -> bool:
        with get_db_cursor() as cur:
            if polos:
                cur.execute("SELECT COUNT(*) AS n FROM polos WHERE id = ANY(%s::uuid[])", (list(polos),))
                if int(cur.fetchone()["n"]) != len(set(polos)):
                    return False
            if escolas:
                cur.execute("SELECT COUNT(*) AS n FROM escolas WHERE id = ANY(%s::uuid[])", (list(escolas),))
                if int(cur.fetchone()["n"]) != len(set(escolas)):
                    return False
        return True

    def alternar_publicado(self, treinamento_id: str) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE ava_treinamentos SET publicado = NOT publicado, atualizado_em = now() WHERE id = %s",
                        (treinamento_id,))

    def excluir(self, treinamento_id: str) -> List[str]:
        """Exclui (cascata no conteúdo) e devolve as URLs dos arquivos dos itens."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT i.url FROM ava_aula_itens i JOIN ava_aulas a ON a.id = i.aula_id
                   JOIN ava_capitulos cap ON cap.id = a.capitulo_id
                   WHERE cap.treinamento_id = %s AND i.arquivo_pathname IS NOT NULL""",
                (treinamento_id,),
            )
            urls = [r["url"] for r in cur.fetchall() if r["url"]]
            cur.execute("DELETE FROM ava_treinamentos WHERE id = %s", (treinamento_id,))
        return urls

    def duplicar(self, treinamento_id: str, usuario_id: Optional[str]) -> str:
        """Copia o treinamento (como rascunho), o público e todo o conteúdo (mesmos arquivos)."""
        colunas = ", ".join(c for c in _CAMPOS if c not in ("titulo", "publicado"))
        colunas_a = ", ".join(_CAMPOS_AULA)
        colunas_i = ", ".join(_CAMPOS_ITEM)
        with get_db_cursor() as cur:
            cur.execute(
                f"""INSERT INTO ava_treinamentos (titulo, publicado, criado_por, {colunas})
                    SELECT LEFT(titulo || ' (cópia)', 255), false, %s, {colunas} FROM ava_treinamentos WHERE id = %s
                    RETURNING id""",
                (usuario_id, treinamento_id),
            )
            novo = str(cur.fetchone()["id"])
            cur.execute("""INSERT INTO ava_treinamento_unidades (treinamento_id, polo_id, escola_id)
                           SELECT %s, polo_id, escola_id FROM ava_treinamento_unidades WHERE treinamento_id = %s""",
                        (novo, treinamento_id))
            cur.execute("SELECT * FROM ava_capitulos WHERE treinamento_id = %s ORDER BY ordem", (treinamento_id,))
            for cap in cur.fetchall():
                cur.execute("""INSERT INTO ava_capitulos (treinamento_id, titulo, descricao, publicado, ordem)
                               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                            (novo, cap["titulo"], cap["descricao"], cap["publicado"], cap["ordem"]))
                novo_cap = cur.fetchone()["id"]
                cur.execute("SELECT id FROM ava_aulas WHERE capitulo_id = %s ORDER BY ordem", (cap["id"],))
                for aula in cur.fetchall():
                    cur.execute(f"""INSERT INTO ava_aulas (capitulo_id, ordem, {colunas_a})
                                    SELECT %s, ordem, {colunas_a} FROM ava_aulas WHERE id = %s RETURNING id""",
                                (novo_cap, aula["id"]))
                    nova_aula = cur.fetchone()["id"]
                    cur.execute(f"""INSERT INTO ava_aula_itens (aula_id, ordem, {colunas_i})
                                    SELECT %s, ordem, {colunas_i} FROM ava_aula_itens WHERE aula_id = %s""",
                                (nova_aula, aula["id"]))
            return novo

    def todas_unidades(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, nome FROM polos ORDER BY nome")
            polos = [_limpar(r) for r in cur.fetchall()]
            cur.execute("SELECT id, nome, polo_id FROM escolas ORDER BY nome")
            escolas = [_limpar(r) for r in cur.fetchall()]
        return polos, escolas

    def participantes(self, treinamento_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                f"""WITH aulas AS (
                        SELECT a.id FROM ava_aulas a JOIN ava_capitulos cap ON cap.id = a.capitulo_id
                        WHERE cap.treinamento_id = %(t)s AND cap.publicado AND a.publicado
                    ), prog AS (
                        SELECT p.usuario_id, COUNT(*) FILTER (WHERE p.status = 'concluida') AS concluidas,
                               MAX(p.ultimo_acesso_em) AS ultimo
                        FROM ava_progresso p WHERE p.aula_id IN (SELECT id FROM aulas) GROUP BY p.usuario_id
                    )
                    SELECT u.id AS usuario_id, TRIM(CONCAT_WS(' ', u.nome, u.sobrenome)) AS nome, pf.nome AS perfil,
                           COALESCE(e.nome, po.nome) AS unidade, COALESCE(prog.concluidas, 0) AS aulas_concluidas,
                           (SELECT COUNT(*) FROM aulas) AS total_aulas, prog.ultimo AS ultimo_acesso_em,
                           tc.concluido_em, tc.codigo_validacao
                    FROM prog
                    FULL JOIN (SELECT usuario_id, concluido_em, codigo_validacao FROM ava_treinamento_conclusoes
                               WHERE treinamento_id = %(t)s) tc ON tc.usuario_id = prog.usuario_id
                    JOIN usuarios u ON u.id = COALESCE(prog.usuario_id, tc.usuario_id)
                    LEFT JOIN perfis pf ON pf.id = u.perfil_id
                    LEFT JOIN escolas e ON e.id = u.escola_id
                    LEFT JOIN polos po ON po.id = u.polo_id
                    ORDER BY tc.concluido_em DESC NULLS LAST, prog.ultimo DESC NULLS LAST""",
                {"t": treinamento_id},
            )
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ público

    def unidades_do_usuario(self, usuario_id: str) -> Tuple[List[str], List[str]]:
        """(polos, escolas) do usuário: vínculo direto, cadastro de professor e o polo da escola."""
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT u.polo_id, u.escola_id, pr.polo_id AS pr_polo, pr.escola_id AS pr_escola,
                          e.polo_id AS e_polo, pe.polo_id AS pe_polo
                   FROM usuarios u
                   LEFT JOIN professores pr ON pr.usuario_id = u.id
                   LEFT JOIN escolas e ON e.id = u.escola_id
                   LEFT JOIN escolas pe ON pe.id = pr.escola_id
                   WHERE u.id = %s""",
                (usuario_id,),
            )
            r = cur.fetchone() or {}
        polos = sorted({str(v) for v in (r.get("polo_id"), r.get("pr_polo"), r.get("e_polo"), r.get("pe_polo")) if v})
        escolas = sorted({str(v) for v in (r.get("escola_id"), r.get("pr_escola")) if v})
        return polos, escolas

    def catalogo(self, usuario_id: str, perfil: str, polos: Sequence[str], escolas: Sequence[str],
                 somente: Optional[str] = None) -> List[Dict[str, Any]]:
        """Treinamentos publicados visíveis ao usuário, com o progresso dele."""
        filtro = " AND t.id = %(id)s" if somente else ""
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT t.*,
                       (SELECT COUNT(*) FROM ({_AULAS_T}) x) AS total_aulas,
                       (SELECT COUNT(*) FROM ({_AULAS_T}) x WHERE x.obrigatoria) AS total_obrigatorias,
                       (SELECT COALESCE(SUM(x.duracao_min), 0) FROM ({_AULAS_T}) x) AS duracao_min,
                       (SELECT COUNT(*) FROM ({_AULAS_T}) x JOIN ava_progresso p ON p.aula_id = x.id
                         AND p.usuario_id = %(u)s AND p.status = 'concluida') AS aulas_concluidas,
                       (SELECT MAX(p.ultimo_acesso_em) FROM ({_AULAS_T}) x JOIN ava_progresso p ON p.aula_id = x.id
                         AND p.usuario_id = %(u)s) AS ultimo_acesso_em,
                       tc.concluido_em, tc.codigo_validacao
                    FROM ava_treinamentos t
                    LEFT JOIN ava_treinamento_conclusoes tc ON tc.treinamento_id = t.id AND tc.usuario_id = %(u)s
                    WHERE t.publicado AND %(perfil)s = ANY(t.perfis_alvo)
                      AND (t.data_fim IS NULL OR t.data_fim >= CURRENT_DATE OR tc.id IS NOT NULL)
                      AND (NOT EXISTS (SELECT 1 FROM ava_treinamento_unidades tu WHERE tu.treinamento_id = t.id)
                           OR EXISTS (SELECT 1 FROM ava_treinamento_unidades tu WHERE tu.treinamento_id = t.id
                                      AND (tu.polo_id = ANY(%(polos)s::uuid[]) OR tu.escola_id = ANY(%(escolas)s::uuid[]))))
                      {filtro}
                    ORDER BY (tc.id IS NOT NULL), ultimo_acesso_em DESC NULLS LAST, t.criado_em DESC""",
                {"u": usuario_id, "perfil": perfil, "polos": list(polos), "escolas": list(escolas), "id": somente},
            )
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ conclusão / certificado

    def concluir(self, treinamento_id: str, usuario_id: str) -> Dict[str, Any]:
        """Registra a conclusão (uma vez) e devolve {concluido_em, codigo_validacao}."""
        for _ in range(5):
            try:
                with get_db_cursor() as cur:
                    cur.execute(
                        """INSERT INTO ava_treinamento_conclusoes (treinamento_id, usuario_id, codigo_validacao)
                           VALUES (%s, %s, %s) ON CONFLICT (treinamento_id, usuario_id) DO NOTHING""",
                        (treinamento_id, usuario_id, _codigo()),
                    )
                    cur.execute("SELECT concluido_em, codigo_validacao FROM ava_treinamento_conclusoes "
                                "WHERE treinamento_id = %s AND usuario_id = %s", (treinamento_id, usuario_id))
                    return _limpar(cur.fetchone())
            except UniqueViolation:  # colisão do código (raríssima): tenta outro
                continue
        raise RuntimeError("Não foi possível gerar o código do certificado.")

    def conclusao(self, treinamento_id: str, usuario_id: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT tc.concluido_em, tc.codigo_validacao, TRIM(CONCAT_WS(' ', u.nome, u.sobrenome)) AS nome, u.cpf
                   FROM ava_treinamento_conclusoes tc JOIN usuarios u ON u.id = tc.usuario_id
                   WHERE tc.treinamento_id = %s AND tc.usuario_id = %s""",
                (treinamento_id, usuario_id),
            )
            return _limpar(cur.fetchone())

    def validar(self, codigo: str) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT tc.codigo_validacao, tc.concluido_em, TRIM(CONCAT_WS(' ', u.nome, u.sobrenome)) AS nome,
                          t.titulo, t.categoria, t.carga_horaria
                   FROM ava_treinamento_conclusoes tc JOIN usuarios u ON u.id = tc.usuario_id
                   JOIN ava_treinamentos t ON t.id = tc.treinamento_id WHERE tc.codigo_validacao = %s""",
                (codigo.strip().upper(),),
            )
            return _limpar(cur.fetchone())


def get_treinamentos_repository() -> PostgresTreinamentosRepository:
    return PostgresTreinamentosRepository()
