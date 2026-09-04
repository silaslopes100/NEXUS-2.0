"""Presencas. Fonte legado: `presenca` (progresso por aula no AVA).

Sem um registro explicito "presente/faltou" no legado, assumimos: aula
assistida (progress > 0) conta como presenca. O % de presenca e calculado no
sistema como presencas.presente=true / disciplinas.qtd_aulas_prevista.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .matriculas_mapper import _first_int

PRESENCA_COLUMNS = ["id", "user_id", "lesson_id", "section_id", "course_id", "progress", "data"]


class PresencaMapper(BaseMapper):
    source_table: ClassVar[str] = "presenca"
    source_columns: ClassVar[list[str]] = PRESENCA_COLUMNS
    target_table: ClassVar[str] = "presencas"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        aluno_id = (
            self.registry.resolve("alunos", "users", _first_int(row.get("user_id")))
            if self.registry
            else None
        )
        if not aluno_id:
            return None  # presenca orfã (sem aluno migrado) e ignorada
        return {
            "aluno_id": aluno_id,
            "professor_disciplina_id": None,
            "numero_aula": None,
            "data_aula": self.parse_date(row.get("data")),
            "presente": self.as_int(row.get("progress")) > 0,
        }