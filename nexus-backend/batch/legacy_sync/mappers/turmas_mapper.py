"""Turmas.

- O calendario da turma vem do Calendario Academico do curso (migration 029);
  `calendarios_oficiais` foi removida na migration 030.
- `turmas` e `turma_alunos` NAO tem equivalente confiavel no legado (o legado
  usa enrol como matricula direta). A tabela fica vazia na migracao para
  preenchimento pelo novo sistema — este mapper e intencionalmente um no-op.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper


class TurmaMapper(BaseMapper):
    """No-op documentado: `turmas` nao tem origem legado confiavel."""

    source_table: ClassVar[str | None] = None
    source_columns: ClassVar[list[str]] = []
    target_table: ClassVar[str] = "turmas"

    def iter_source(self, source, last_run=None):
        return iter(())