"""Turmas e Calendarios Oficiais.

- `calendarios_oficiais` tem origem clara: as datas `datainicio`/`datafinal`
  de cada section (aulas acontecem na mesma data em todos os Polos).
- `turmas` e `turma_alunos` NAO tem equivalente confiavel no legado (o legado
  usa enrol como matricula direta). A tabela fica vazia na migracao para
  preenchimento pelo novo sistema — este mapper e intencionalmente um no-op.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .disciplinas_mapper import SECTION_COLUMNS


class CalendarioOficialMapper(BaseMapper):
    source_table: ClassVar[str] = "section"
    source_columns: ClassVar[list[str]] = SECTION_COLUMNS
    target_table: ClassVar[str] = "calendarios_oficiais"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        curso_id = self.registry.resolve("cursos", "course", row.get("course_id")) if self.registry else None
        disciplina_id = self.registry.resolve("disciplinas", "section", row.get("id")) if self.registry else None
        return {
            "curso_id": curso_id,
            "disciplina_id": disciplina_id,
            "data_liberacao": self.parse_date(row.get("datainicio")),
            "data_encerramento": self.parse_date(row.get("datafinal")),
        }


class TurmaMapper(BaseMapper):
    """No-op documentado: `turmas` nao tem origem legado confiavel."""

    source_table: ClassVar[str | None] = None
    source_columns: ClassVar[list[str]] = []
    target_table: ClassVar[str] = "turmas"

    def iter_source(self, source, last_run=None):
        return iter(())