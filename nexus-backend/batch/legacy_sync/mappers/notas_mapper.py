"""Notas (AVA) e Historico Unificado.

- `quiz` registra o resultado de avaliacoes do AVA -> `notas` (origem='ava').
- Apos o mapper, `compute_historico` materializa a REGRA DA MAIOR NOTA:
  historico_unificado.nota_final = MAX(notas.valor) por (aluno, disciplina);
  status = 'aprovado' quando >= 6.0. Roda de novo a cada execucao (idempotente).
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .matriculas_mapper import _first_int

QUIZ_COLUMNS = [
    "id", "user_id", "course_id", "lesson_id", "result", "total", "percent",
    "section_id", "data",
]


class NotaMapper(BaseMapper):
    source_table: ClassVar[str] = "quiz"
    source_columns: ClassVar[list[str]] = QUIZ_COLUMNS
    target_table: ClassVar[str] = "notas"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        aluno_id = (
            self.registry.resolve("alunos", "users", _first_int(row.get("user_id")))
            if self.registry
            else None
        )
        if not aluno_id:
            self.warn(f"quiz sem aluno migrado: quiz={row.get('id')} user={row.get('user_id')}")
            return None
        disciplina_id = (
            self.registry.resolve("disciplinas", "section", _first_int(row.get("section_id")))
            if self.registry
            else None
        )
        valor = self.as_float(row.get("result"))
        if valor is None:
            return None
        return {
            "aluno_id": aluno_id,
            "disciplina_id": disciplina_id,
            "turma_id": None,
            "origem": "ava",
            "valor": min(max(valor, 0.0), 10.0),
            "lancado_por": None,
            "lancado_em": self.parse_ts(row.get("data")),
        }


def compute_historico(target) -> None:
    """Materializa a regra da maior nota em historico_unificado (idempotente)."""
    target.execute(
        """
        INSERT INTO historico_unificado (aluno_id, disciplina_id, nota_final, status,
                                         eh_extra_grade, atualizado_em)
        SELECT n.aluno_id, n.disciplina_id, MAX(n.valor),
               CASE WHEN MAX(n.valor) >= 6 THEN 'aprovado' ELSE 'reprovado' END,
               false, now()
        FROM notas n
        WHERE n.disciplina_id IS NOT NULL
        GROUP BY n.aluno_id, n.disciplina_id
        ON CONFLICT (aluno_id, disciplina_id) DO UPDATE
        SET nota_final = EXCLUDED.nota_final,
            status = EXCLUDED.status,
            atualizado_em = now()
        """
    )
    target.commit()