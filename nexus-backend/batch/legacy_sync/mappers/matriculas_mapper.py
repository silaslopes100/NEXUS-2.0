"""Matriculas EAD. Fonte legado: `enrol` (114k+ linhas, a base de matriculas).

Nota de premissa: `enrol.user_id` e `enrol.course_id` sao TEXT e podem conter
varios ids (ex.: "12,13") — usamos o primeiro valor parseavel. `enrol.tipo`
distingue Polo/EAD; todas as linhas sao preservadas em `matriculas_ead`
(com a origem legada) e a classificacao fina entre Polo e EAD sera revisada
com a equipe antes de liberar o sistema.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper


def _first_int(value) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    for part in s.split(","):
        part = part.strip()
        try:
            return int(float(part))
        except ValueError:
            continue
    return None


ENROL_COLUMNS = [
    "id", "user_id", "course_id", "date_added", "last_modified", "count",
    "data_limite", "vendedor", "valor", "tipo", "licence_id", "pacote_id", "token",
]


class MatriculaMapper(BaseMapper):
    source_table: ClassVar[str] = "enrol"
    source_columns: ClassVar[list[str]] = ENROL_COLUMNS
    target_table: ClassVar[str] = "matriculas_ead"
    order_by: ClassVar[str | None] = "id"
    incremental_column: ClassVar[str | None] = "last_modified"

    def map(self, row: dict) -> dict | None:
        user_id = _first_int(row.get("user_id"))
        course_id = _first_int(row.get("course_id"))
        aluno_id = self.registry.resolve("alunos", "users", user_id) if self.registry else None
        if not aluno_id:
            self.warn(f"enrol sem aluno migrado: enrol={row.get('id')} user={user_id}")
            return None
        curso_id = None
        if self.registry:
            curso_id = self.registry.resolve("cursos", "course", course_id)
            if not curso_id:
                curso_id = self.registry.resolve("cursos", "pacotes", course_id)
        return {
            "aluno_id": aluno_id,
            "curso_id": curso_id,
            "ativa_automaticamente": self.as_bool(row.get("licence_id")) or True,
            "data_matricula": self.parse_ts(row.get("date_added")),
        }