"""Feed de noticias e lembretes. Fontes legado: `blogs` (feed) e `noticeboard`
(lembretes/avisos).

A regra de autorizacao (so professor/coordenador/diretor/admin postam) e do
modulo Notificacoes, nao da migracao.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper

BLOGS_COLUMNS = [
    "blog_id", "blog_category_id", "user_id", "title", "description",
    "thumbnail", "banner", "is_popular", "likes", "added_date", "updated_date", "status",
]

NOTICEBOARD_COLUMNS = [
    "id", "course_id", "title", "description", "status", "date_added", "date_updated",
]


class FeedPostMapper(BaseMapper):
    source_table: ClassVar[str] = "blogs"
    source_columns: ClassVar[list[str]] = BLOGS_COLUMNS
    target_table: ClassVar[str] = "feed_posts"
    order_by: ClassVar[str | None] = "blog_id"

    def current_legacy_id(self, row: dict) -> int:
        return int(row["blog_id"])

    def map(self, row: dict) -> dict | None:
        autor_id = self.registry.resolve("usuarios", "users", row.get("user_id")) if self.registry else None
        return {
            "autor_id": autor_id,
            "titulo": self.str_clean(row.get("title"), 255),
            "conteudo": self.str_clean(row.get("description")),
            "criado_em": self.parse_ts(row.get("added_date")),
        }


class LembreteMapper(BaseMapper):
    source_table: ClassVar[str] = "noticeboard"
    source_columns: ClassVar[list[str]] = NOTICEBOARD_COLUMNS
    target_table: ClassVar[str] = "lembretes"
    order_by: ClassVar[str | None] = "id"

    def map(self, row: dict) -> dict | None:
        if str(row.get("status") or "").lower() not in ("1", "active", "ativo"):
            return None
        return {
            "usuario_destino_id": None,
            "perfil_destino": None,
            "titulo": self.str_clean(row.get("title"), 255),
            "mensagem": self.str_clean(row.get("description")),
            "exibir_de": self.parse_date(row.get("date_added")),
            "exibir_ate": self.parse_date(row.get("date_updated")),
        }