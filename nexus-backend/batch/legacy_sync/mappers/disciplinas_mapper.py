"""Disciplinas e conteudos. Fontes legado: `section` (modulo/semestre) e
`lesson` (aula/conteudo do AVA).

- section  -> disciplinas (semestre = section.order)
- lesson   -> disciplina_conteudos (vinculado a disciplina pela section_id)
- `qtd_aulas_prevista` da disciplina = quantidade de lessons da section.
- `datainicio`/`datafinal` da section viram calendario oficial (calendarios_mapper).
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

SECTION_COLUMNS = [
    "id", "title", "course_id", "order", "datainicio", "datafinal", "cor",
]

LESSON_COLUMNS = [
    "id", "title", "course_id", "section_id", "video_type", "video_url",
    "lesson_type", "attachment", "attachment_type", "order", "duration",
    "date_added", "last_modified", "linkMeet",
]


class DisciplinaMapper(BaseMapper):
    source_table: ClassVar[str] = "section"
    source_columns: ClassVar[list[str]] = SECTION_COLUMNS
    target_table: ClassVar[str] = "disciplinas"
    order_by: ClassVar[str | None] = "course_id, `order`"

    def iter_source(self, source, last_run=None):
        sql = (
            f"SELECT s.id, s.title, s.course_id, s.`order`, s.datainicio, "
            f"s.datafinal, s.cor, COUNT(l.id) AS qtd_aulas "
            f"FROM section s LEFT JOIN lesson l ON l.section_id = s.id "
            f"GROUP BY s.id, s.title, s.course_id, s.`order`, s.datainicio, "
            f"s.datafinal, s.cor ORDER BY s.course_id, s.`order`"
        )
        cursor = source.conn.cursor()
        try:
            cursor.execute(sql)
            while True:
                rows = cursor.fetchmany(2000)
                if not rows:
                    break
                for r in rows:
                    yield r
        finally:
            cursor.close()

    def map(self, row: dict) -> dict | None:
        curso_id = self.registry.resolve("cursos", "course", row.get("course_id")) if self.registry else None
        if not curso_id:
            # section de curso ainda nao migrado -> tenta como pacote
            curso_id = self.registry.resolve("cursos", "pacotes", row.get("course_id")) if self.registry else None
            if not curso_id:
                self.warn(f"section sem curso migrado: section={row.get('id')} course={row.get('course_id')}")
                return None
        return {
            "curso_id": curso_id,
            "semestre": self.as_int(row.get("order")) or 0,
            "nome": self.str_clean(row.get("title"), 255) or f"Disciplina {row['id']}",
            "ordem": self.as_int(row.get("order")) or 0,
            "carga_horaria": None,
            "qtd_aulas_prevista": self.as_int(row.get("qtd_aulas")),
            "tipo": "presencial",
            "eh_extra_grade": False,
        }


class DisciplinaConteudoMapper(BaseMapper):
    source_table: ClassVar[str] = "lesson"
    source_columns: ClassVar[list[str]] = LESSON_COLUMNS
    target_table: ClassVar[str] = "disciplina_conteudos"
    order_by: ClassVar[str | None] = "section_id, `order`"
    incremental_column: ClassVar[str | None] = "last_modified"

    def map(self, row: dict) -> dict | None:
        disciplina_id = (
            self.registry.resolve("disciplinas", "section", row.get("section_id"))
            if self.registry
            else None
        )
        if not disciplina_id:
            self.warn(f"lesson sem disciplina migrada: lesson={row.get('id')} section={row.get('section_id')}")
            return None
        tipo_midia = self.str_clean(row.get("lesson_type")) or self.str_clean(row.get("video_type"))
        url = self.str_clean(row.get("video_url"), 500) or self.str_clean(row.get("attachment"), 500)
        if row.get("linkMeet"):
            tipo_midia = tipo_midia or "live"
            url = url or self.str_clean(row.get("linkMeet"), 500)
        return {
            "disciplina_id": disciplina_id,
            "titulo": self.str_clean(row.get("title"), 255),
            "tipo_midia": (tipo_midia or "video")[:32],
            "url_arquivo": url,
            "ordem": self.as_int(row.get("order")) or 0,
        }