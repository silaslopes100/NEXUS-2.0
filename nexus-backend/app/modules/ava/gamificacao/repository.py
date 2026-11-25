"""Persistência da gamificação (PostgreSQL, SQL puro)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.database import get_db_cursor
from app.modules.ava.repository import _limpar

_HOJE = "(now() AT TIME ZONE 'America/Sao_Paulo')::date"
_INICIO_SEMANA = "(date_trunc('week', now() AT TIME ZONE 'America/Sao_Paulo') AT TIME ZONE 'America/Sao_Paulo')"


class PostgresGamificacaoRepository:
    # ------------------------------------------------------------------ XP

    def xp_total(self, usuario_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(xp), 0) AS t FROM gam_eventos_xp WHERE usuario_id = %s", (usuario_id,))
            return int(cur.fetchone()["t"])

    def xp_semana(self, usuario_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COALESCE(SUM(xp), 0) AS t FROM gam_eventos_xp WHERE usuario_id = %s "
                        f"AND criado_em >= {_INICIO_SEMANA}", (usuario_id,))
            return int(cur.fetchone()["t"])

    def inserir_eventos(self, usuario_id: str, curso_id: Optional[str],
                        eventos: Sequence[Tuple[str, str, int, Optional[str]]]) -> List[Dict[str, Any]]:
        """Grava (tipo, referência, xp, descrição); devolve só os eventos novos (os repetidos são ignorados)."""
        novos: List[Dict[str, Any]] = []
        with get_db_cursor() as cur:
            for tipo, ref, xp, descricao in eventos:
                cur.execute(
                    """INSERT INTO gam_eventos_xp (usuario_id, tipo, referencia_id, xp, curso_id, descricao)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (usuario_id, tipo, referencia_id) DO NOTHING
                       RETURNING tipo, xp, descricao, criado_em""",
                    (usuario_id, tipo, str(ref)[:64], xp, curso_id, (descricao or "")[:255] or None),
                )
                row = cur.fetchone()
                if row:
                    novos.append(_limpar(row))
        return novos

    def contadores(self, usuario_id: str) -> Dict[str, int]:
        with get_db_cursor() as cur:
            cur.execute("SELECT tipo, COUNT(*) AS n FROM gam_eventos_xp WHERE usuario_id = %s GROUP BY tipo", (usuario_id,))
            return {r["tipo"]: int(r["n"]) for r in cur.fetchall()}

    def historico(self, usuario_id: str, limite: int = 20) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT tipo, xp, descricao, criado_em FROM gam_eventos_xp WHERE usuario_id = %s "
                        "ORDER BY criado_em DESC LIMIT %s", (usuario_id, limite))
            return [_limpar(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ sequência de dias

    def registrar_dia(self, usuario_id: str) -> Tuple[int, int, bool, date]:
        """Marca estudo hoje. Devolve (sequência atual, recorde, primeiro estudo do dia?, hoje)."""
        with get_db_cursor() as cur:
            cur.execute(f"SELECT {_HOJE} AS hoje")
            hoje: date = cur.fetchone()["hoje"]
            cur.execute("SELECT atual, recorde, ultimo_dia FROM gam_streak WHERE usuario_id = %s FOR UPDATE", (usuario_id,))
            row = cur.fetchone()
            if row and row["ultimo_dia"] == hoje:
                return int(row["atual"]), int(row["recorde"]), False, hoje
            atual = int(row["atual"]) + 1 if row and row["ultimo_dia"] == hoje - timedelta(days=1) else 1
            recorde = max(atual, int(row["recorde"]) if row else 0)
            cur.execute(
                """INSERT INTO gam_streak (usuario_id, atual, recorde, ultimo_dia) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (usuario_id) DO UPDATE SET atual = EXCLUDED.atual, recorde = EXCLUDED.recorde,
                     ultimo_dia = EXCLUDED.ultimo_dia""",
                (usuario_id, atual, recorde, hoje),
            )
            return atual, recorde, True, hoje

    def streak(self, usuario_id: str) -> Tuple[int, int, Optional[date], date]:
        """(atual já considerando dias perdidos, recorde, último dia, hoje)."""
        with get_db_cursor() as cur:
            cur.execute(f"SELECT {_HOJE} AS hoje")
            hoje: date = cur.fetchone()["hoje"]
            cur.execute("SELECT atual, recorde, ultimo_dia FROM gam_streak WHERE usuario_id = %s", (usuario_id,))
            row = cur.fetchone()
        if not row:
            return 0, 0, None, hoje
        vivo = row["ultimo_dia"] is not None and row["ultimo_dia"] >= hoje - timedelta(days=1)
        return (int(row["atual"]) if vivo else 0), int(row["recorde"]), row["ultimo_dia"], hoje

    # ------------------------------------------------------------------ conquistas

    def catalogo(self) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM gam_conquistas WHERE ativo ORDER BY ordem, nome")
            return [_limpar(r) for r in cur.fetchall()]

    def obtidas(self, usuario_id: str) -> Dict[str, Any]:
        """{conquista_id: obtida_em}"""
        with get_db_cursor() as cur:
            cur.execute("SELECT conquista_id, obtida_em FROM gam_conquistas_usuario WHERE usuario_id = %s", (usuario_id,))
            return {str(r["conquista_id"]): r["obtida_em"] for r in cur.fetchall()}

    def conceder(self, usuario_id: str, conquista_id: str) -> Optional[Any]:
        """Concede a conquista; devolve obtida_em, ou None se já tinha."""
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO gam_conquistas_usuario (usuario_id, conquista_id) VALUES (%s, %s)
                   ON CONFLICT DO NOTHING RETURNING obtida_em""",
                (usuario_id, conquista_id),
            )
            row = cur.fetchone()
            return row["obtida_em"] if row else None

    # ------------------------------------------------------------------ ranking

    def cursos_do_aluno(self, usuario_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT c.id, c.nome, MIN(m.data_matricula) AS desde FROM matriculas_ead m
                   JOIN alunos a ON a.id = m.aluno_id JOIN cursos c ON c.id = m.curso_id
                   WHERE a.usuario_id = %s GROUP BY c.id, c.nome ORDER BY desde NULLS LAST, c.nome""",
                (usuario_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def ranking(self, curso_id: str, semana: bool) -> List[Dict[str, Any]]:
        """XP por aluno no curso (todos, ordenado), com a preferência de visibilidade."""
        filtro = f" AND e.criado_em >= {_INICIO_SEMANA}" if semana else ""
        with get_db_cursor() as cur:
            cur.execute(
                f"""SELECT e.usuario_id, SUM(e.xp) AS xp, u.nome, u.sobrenome, u.foto_url,
                           COALESCE(BOOL_AND(a.ranking_visivel), true) AS visivel,
                           (SELECT COALESCE(SUM(t.xp), 0) FROM gam_eventos_xp t WHERE t.usuario_id = e.usuario_id) AS xp_total
                    FROM gam_eventos_xp e
                    JOIN usuarios u ON u.id = e.usuario_id
                    LEFT JOIN alunos a ON a.usuario_id = e.usuario_id
                    WHERE e.curso_id = %s{filtro}
                    GROUP BY e.usuario_id, u.nome, u.sobrenome, u.foto_url
                    HAVING SUM(e.xp) > 0
                    ORDER BY SUM(e.xp) DESC, MIN(e.criado_em) ASC""",
                (curso_id,),
            )
            return [_limpar(r) for r in cur.fetchall()]

    def ranking_visivel(self, usuario_id: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("SELECT COALESCE(BOOL_AND(ranking_visivel), true) AS v FROM alunos WHERE usuario_id = %s",
                        (usuario_id,))
            row = cur.fetchone()
            return bool(row["v"]) if row and row["v"] is not None else True

    def definir_ranking_visivel(self, usuario_id: str, visivel: bool) -> None:
        with get_db_cursor() as cur:
            cur.execute("UPDATE alunos SET ranking_visivel = %s WHERE usuario_id = %s", (visivel, usuario_id))


def get_gamificacao_repository() -> PostgresGamificacaoRepository:
    return PostgresGamificacaoRepository()
