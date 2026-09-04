"""Certificados. Fonte legado: `certificates`.

As datas dos 2 estagios (Teologia do Ministerio e Homiletica) sao campos novos
do modulo Historico e vem NULL; a emissao real passa a ser validada pelo novo
sistema. `emitido_em` usa a data do certificado legado quando disponivel.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

CERTIFICADOS_COLUMNS = ["id", "student_id", "course_id", "shareable_url"]


class CertificadoMapper(BaseMapper):
    source_table: ClassVar[str] = "certificates"
    source_columns: ClassVar[list[str]] = CERTIFICADOS_COLUMNS
    target_table: ClassVar[str] = "certificados"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        aluno_id = self.registry.resolve("alunos", "users", row.get("student_id")) if self.registry else None
        if not aluno_id:
            self.warn(f"certificado sem aluno migrado: cert={row.get('id')} student={row.get('student_id')}")
            return None
        curso_id = None
        if self.registry:
            curso_id = self.registry.resolve("cursos", "pacotes", row.get("course_id"))
            if not curso_id:
                curso_id = self.registry.resolve("cursos", "course", row.get("course_id"))
        return {
            "aluno_id": aluno_id,
            "curso_id": curso_id,
            "data_estagio_teologia_ministerio": None,
            "data_estagio_homiletica": None,
            "emitido_em": None,
            "url_arquivo": self.str_clean(row.get("shareable_url"), 500),
        }