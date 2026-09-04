"""Cursos. Fonte legado: `pacotes`.

Confirmado em producao: a tabela que descreve os cursos (titulo, descricao,
modalidade, preco, status) e `pacotes`. A tabela `course` do dicionario nao
corresponde ao schema real do MySQL e deixou de ser usada.

- modalidade: de `pacotes.modalidade` (polo/ead/hibrido); senao 'hibrido'.
- semestres: padrao 3 (definido pela Diretoria Pedagogica).
- `courses` (longtext, lista de ids) e ignorado por ora — preservado para
  refinamento do vinculo curso/disciplina na revisao com a equipe.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

MODALIDADES = {"polo", "ead", "hibrido"}

PACOTES_COLUMNS = [
    "id", "title", "description", "short_description", "status", "date_added",
    "price", "discount_flag", "discounted_price", "modalidade", "exibir_home",
]


def _normalize_modalidade(*candidatos) -> str | None:
    for c in candidatos:
        if c:
            m = str(c).strip().lower()
            if m in MODALIDADES:
                return m
    return None


class CursoMapper(BaseMapper):
    source_table: ClassVar[str] = "pacotes"
    source_columns: ClassVar[list[str]] = PACOTES_COLUMNS
    target_table: ClassVar[str] = "cursos"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        modalidade = _normalize_modalidade(row.get("modalidade")) or "hibrido"
        status = "ativo" if str(row.get("status") or "").lower() in ("active", "1", "ativo", "") else "inativo"
        return {
            "nome": self.str_clean(row.get("title"), 255) or f"Curso {row['id']}",
            "descricao": self.str_clean(row.get("description")),
            "modalidade": modalidade,
            "carga_horaria_total": None,  # `carga_horaria` nao existe em pacotes
            "semestres": 3,
            "status": status,
        }