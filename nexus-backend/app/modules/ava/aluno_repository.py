"""Persistência do AVA do aluno: disciplinas liberadas, progresso, anotações e avaliação das aulas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.database import get_db_cursor
from app.modules.ava.repository import _limpar, uuid_valido

# Aulas publicadas de capítulos publicados da disciplina (base do progresso do aluno).
_AULAS_PUBLICADAS = """
    SELECT a.id, a.obrigatoria, a.duracao_min FROM ava_aulas a
    JOIN ava_capitulos cap ON cap.id = a.capitulo_id
    WHERE cap.disciplina_id = d.id AND cap.publicado AND a.publicado
"""


class PostgresAvaAlunoRepository:
    # ------------------------------------------------------------------ disciplinas

    def disciplinas_do_aluno(self, aluno_id: str, usuario_id: str) -> List[Dict[str, Any]]:
        """Disciplinas dos cursos EAD matriculados + as compradas/licenciadas avulsas, com compra e progresso."""
        sql = f"""
            WITH base AS (
                SELECT d.id FROM disciplinas d
                 WHERE COALESCE(d.ativo, true)
                   AND d.curso_id IN (SELECT m.curso_id FROM matriculas_ead m
                                       WHERE m.aluno_id = %(a)s AND m.curso_id IS NOT NULL
                                         AND COALESCE(m.status, 'ativa') = 'ativa')
                UNION
                SELECT c.disciplina_id FROM compras_disciplina_ead c
                 WHERE c.aluno_id = %(a)s AND c.disciplina_id IS NOT NULL
                UNION
                SELECT l.materia_id FROM licencas_alunos l
                 WHERE l.aluno_id = %(a)s AND l.status = 'ativa' AND l.materia_id IS NOT NULL
            )
            SELECT d.id, d.nome, d.curso_id, cu.nome AS curso_nome, d.semestre, d.ordem,
                   cfg.capa_url, cfg.descricao_ava, COALESCE(cfg.publicado, false) AS publicado,
                   COALESCE(cfg.sequencial, false) AS sequencial,
                   compra.id AS compra_id, compra.status_pagamento, compra.liberada_em, compra.prazo_conclusao,
                   COALESCE(compra.reprovado_por_prazo, false) AS reprovado_por_prazo,
                   lic.ativada_em AS licenca_em,
                   (SELECT MIN(m.data_matricula) FROM matriculas_ead m
                     WHERE m.aluno_id = %(a)s AND m.curso_id = d.curso_id) AS matricula_em,
                   EXISTS (SELECT 1 FROM matriculas_ead m WHERE m.aluno_id = %(a)s AND m.curso_id = d.curso_id
                              AND m.status = 'ativa' AND m.tipo = 'bolsista') AS bolsista,
                   (SELECT COUNT(*) FROM ({_AULAS_PUBLICADAS}) x) AS total_aulas,
                   (SELECT COUNT(*) FROM ({_AULAS_PUBLICADAS}) x WHERE x.obrigatoria) AS total_obrigatorias,
                   (SELECT COALESCE(SUM(x.duracao_min), 0) FROM ({_AULAS_PUBLICADAS}) x) AS duracao_min,
                   (SELECT COUNT(*) FROM ({_AULAS_PUBLICADAS}) x
                      JOIN ava_progresso p ON p.aula_id = x.id AND p.usuario_id = %(u)s AND p.status = 'concluida'
                   ) AS aulas_concluidas,
                   (SELECT COUNT(*) FROM ({_AULAS_PUBLICADAS}) x
                      JOIN ava_progresso p ON p.aula_id = x.id AND p.usuario_id = %(u)s AND p.status = 'concluida'
                     WHERE x.obrigatoria) AS obrigatorias_concluidas,
                   (SELECT MAX(p.ultimo_acesso_em) FROM ({_AULAS_PUBLICADAS}) x
                      JOIN ava_progresso p ON p.aula_id = x.id AND p.usuario_id = %(u)s) AS ultimo_acesso_em,
                   (SELECT MAX(p.concluido_em) FROM ({_AULAS_PUBLICADAS}) x
                      JOIN ava_progresso p ON p.aula_id = x.id AND p.usuario_id = %(u)s AND p.status = 'concluida'
                   ) AS ultima_conclusao_em
            FROM base
            JOIN disciplinas d ON d.id = base.id
            LEFT JOIN cursos cu ON cu.id = d.curso_id
            LEFT JOIN ava_disciplina_config cfg ON cfg.disciplina_id = d.id
            LEFT JOIN LATERAL (
                SELECT c.* FROM compras_disciplina_ead c
                 WHERE c.aluno_id = %(a)s AND c.disciplina_id = d.id
                   AND COALESCE(c.status_pagamento, '') NOT IN ('cancelado', 'cancelada')
                 -- a liberada mais recente vale (recompra depois do prazo vencido); senão, a pendente mais nova
                 ORDER BY (c.liberada_em IS NOT NULL) DESC, c.liberada_em DESC NULLS LAST,
                          c.criado_em DESC NULLS LAST LIMIT 1
            ) compra ON true
            LEFT JOIN LATERAL (
                SELECT l.ativada_em FROM licencas_alunos l
                 WHERE l.aluno_id = %(a)s AND l.materia_id = d.id AND l.status = 'ativa'
                 ORDER BY l.ativada_em DESC NULLS LAST LIMIT 1
            ) lic ON true
            ORDER BY cu.nome NULLS LAST, d.semestre NULLS LAST, d.ordem NULLS LAST, d.nome
        """
        with get_db_cursor() as cur:
            cur.execute(sql, {"a": aluno_id, "u": usuario_id})
            return [_limpar(r) for r in cur.fetchall()]

    def disciplina_previa(self, disciplina_id: str) -> Optional[Dict[str, Any]]:
        """Dados da disciplina para a pré-visualização do admin."""
        if not uuid_valido(disciplina_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT d.id, d.nome, d.curso_id, cu.nome AS curso_nome, d.semestre, cfg.capa_url, cfg.descricao_ava,
                          COALESCE(cfg.publicado, false) AS publicado, COALESCE(cfg.sequencial, false) AS sequencial
                   FROM disciplinas d LEFT JOIN cursos cu ON cu.id = d.curso_id
                   LEFT JOIN ava_disciplina_config cfg ON cfg.disciplina_id = d.id WHERE d.id = %s""",
                (disciplina_id,),
            )
            return _limpar(cur.fetchone())

    # ------------------------------------------------------------------ progresso

    def progresso(self, usuario_id: str, aula_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        if not aula_ids:
            return {}
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM ava_progresso WHERE usuario_id = %s AND aula_id = ANY(%s::uuid[])",
                        (usuario_id, list(aula_ids)))
            return {r["aula_id"]: r for r in (_limpar(x) for x in cur.fetchall())}

    def ultima_aula(self, usuario_id: str, disciplina_ids: Sequence[str]) -> Optional[Dict[str, Any]]:
        if not disciplina_ids:
            return None
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT p.aula_id, p.ultimo_acesso_em, p.status, a.titulo AS aula_titulo, cap.titulo AS capitulo_titulo,
                          cap.disciplina_id
                   FROM ava_progresso p
                   JOIN ava_aulas a ON a.id = p.aula_id AND a.publicado
                   JOIN ava_capitulos cap ON cap.id = a.capitulo_id AND cap.publicado
                   WHERE p.usuario_id = %s AND cap.disciplina_id = ANY(%s::uuid[])
                   ORDER BY p.ultimo_acesso_em DESC LIMIT 1""",
                (usuario_id, list(disciplina_ids)),
            )
            return _limpar(cur.fetchone())

    def registrar_acesso(self, usuario_id: str, aula_id: str, percentual: int = 0,
                         posicao_seg: Optional[int] = None) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO ava_progresso (usuario_id, aula_id, percentual, posicao_seg)
                   VALUES (%(u)s, %(a)s, %(p)s, %(pos)s)
                   ON CONFLICT (usuario_id, aula_id) DO UPDATE SET
                     percentual = GREATEST(ava_progresso.percentual, EXCLUDED.percentual),
                     posicao_seg = COALESCE(EXCLUDED.posicao_seg, ava_progresso.posicao_seg),
                     ultimo_acesso_em = now()""",
                {"u": usuario_id, "a": aula_id, "p": percentual, "pos": posicao_seg},
            )

    def concluir(self, usuario_id: str, aula_id: str) -> bool:
        """Marca como concluída; devolve True se já estava concluída."""
        with get_db_cursor() as cur:
            cur.execute("SELECT status FROM ava_progresso WHERE usuario_id = %s AND aula_id = %s", (usuario_id, aula_id))
            atual = cur.fetchone()
            if atual and atual["status"] == "concluida":
                cur.execute("UPDATE ava_progresso SET ultimo_acesso_em = now() WHERE usuario_id = %s AND aula_id = %s",
                            (usuario_id, aula_id))
                return True
            cur.execute(
                """INSERT INTO ava_progresso (usuario_id, aula_id, status, percentual, concluido_em)
                   VALUES (%s, %s, 'concluida', 100, now())
                   ON CONFLICT (usuario_id, aula_id) DO UPDATE SET
                     status = 'concluida', percentual = 100, concluido_em = now(), ultimo_acesso_em = now()""",
                (usuario_id, aula_id),
            )
            return False

    def minutos_estudados(self, usuario_id: str) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT COALESCE(SUM(a.duracao_min), 0) AS total FROM ava_progresso p
                   JOIN ava_aulas a ON a.id = p.aula_id WHERE p.usuario_id = %s AND p.status = 'concluida'""",
                (usuario_id,),
            )
            return int(cur.fetchone()["total"] or 0)

    # ------------------------------------------------------------------ anotações / nota da aula

    def anotacoes(self, usuario_id: str, aula_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM ava_anotacoes WHERE usuario_id = %s AND aula_id = %s ORDER BY criado_em DESC",
                        (usuario_id, aula_id))
            return [_limpar(r) for r in cur.fetchall()]

    def criar_anotacao(self, usuario_id: str, aula_id: str, texto: str, posicao_seg: Optional[int]) -> Dict[str, Any]:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO ava_anotacoes (usuario_id, aula_id, texto, posicao_seg) VALUES (%s, %s, %s, %s)
                   RETURNING *""",
                (usuario_id, aula_id, texto, posicao_seg),
            )
            return _limpar(cur.fetchone())

    def atualizar_anotacao(self, usuario_id: str, anotacao_id: str, texto: str) -> Optional[Dict[str, Any]]:
        if not uuid_valido(anotacao_id):
            return None
        with get_db_cursor() as cur:
            cur.execute(
                """UPDATE ava_anotacoes SET texto = %s, atualizado_em = now() WHERE id = %s AND usuario_id = %s
                   RETURNING *""",
                (texto, anotacao_id, usuario_id),
            )
            return _limpar(cur.fetchone())

    def excluir_anotacao(self, usuario_id: str, anotacao_id: str) -> bool:
        if not uuid_valido(anotacao_id):
            return False
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM ava_anotacoes WHERE id = %s AND usuario_id = %s", (anotacao_id, usuario_id))
            return cur.rowcount > 0

    def nota_da_aula(self, usuario_id: str, aula_id: str) -> Optional[int]:
        with get_db_cursor() as cur:
            cur.execute("SELECT nota FROM ava_aula_avaliacoes WHERE usuario_id = %s AND aula_id = %s", (usuario_id, aula_id))
            row = cur.fetchone()
            return int(row["nota"]) if row else None

    def avaliar_aula(self, usuario_id: str, aula_id: str, nota: int) -> None:
        with get_db_cursor() as cur:
            cur.execute(
                """INSERT INTO ava_aula_avaliacoes (usuario_id, aula_id, nota) VALUES (%s, %s, %s)
                   ON CONFLICT (usuario_id, aula_id) DO UPDATE SET nota = EXCLUDED.nota, criado_em = now()""",
                (usuario_id, aula_id, nota),
            )


def get_ava_aluno_repository() -> PostgresAvaAlunoRepository:
    return PostgresAvaAlunoRepository()
