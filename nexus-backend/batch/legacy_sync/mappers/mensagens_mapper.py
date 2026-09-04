"""Chat. Fontes legado: `message_thread` (conversas) e `message` (mensagens).

- Uma conversa por `message_thread_code` unico (dedup).
- Membros (conversa_membros) sao sender/receiver do thread.
- remetentes que nao existem como usuarios migrados sao ignorados (nao quebra).
- O fluxo de negocio (proibir aluno<>aluno, admin encerrar/exportar) e do
  modulo Chat, nao da migracao.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .matriculas_mapper import _first_int

THREAD_COLUMNS = [
    "message_thread_id", "message_thread_code", "sender", "receiver",
    "last_message_timestamp",
]

MESSAGE_COLUMNS = [
    "message_id", "message_thread_code", "message", "sender", "timestamp",
    "read_status", "receiver",
]


class ConversaMapper(BaseMapper):
    source_table: ClassVar[str] = "message_thread"
    source_columns: ClassVar[list[str]] = THREAD_COLUMNS
    target_table: ClassVar[str] = "conversas"
    order_by: ClassVar[str | None] = "message_thread_id"

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._vistos: set[str] = set()

    def iter_source(self, source, last_run=None):
        for row in source.stream(self.source_table, self.source_columns, order=self.order_by):
            code = row.get("message_thread_code")
            if not code:
                continue
            if code in self._vistos:
                continue
            self._vistos.add(code)
            yield row

    def map(self, row: dict) -> dict | None:
        if self.registry:
            self.registry.set_value("thread_code", str(row["message_thread_code"]), row["message_thread_id"])
        return {
            "tipo": "individual",
            "criada_em": self.parse_ts(row.get("last_message_timestamp")),
            "encerrada_em": None,
        }


class ConversaMembroMapper(BaseMapper):
    """Popula conversa_membros a partir do par sender/receiver do thread."""

    source_table: ClassVar[str] = "message_thread"
    source_columns: ClassVar[list[str]] = THREAD_COLUMNS
    target_table: ClassVar[str] = "conversa_membros"
    order_by: ClassVar[str | None] = "message_thread_id"
    has_tracking: ClassVar[bool] = False
    conflict_columns: ClassVar[list[str]] = ["conversa_id", "usuario_id"]

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._pending: list[tuple[str, int]] = []

    def map(self, row: dict) -> dict | None:
        if not self.registry:
            return None
        thread_id = self.registry.get_value("thread_code", str(row["message_thread_code"]))
        conversa_id = self.registry.resolve("conversas", "message_thread", thread_id)
        if not conversa_id:
            return None
        membros = set()
        for who in (row.get("sender"), row.get("receiver")):
            uid = _first_int(who)
            if uid is not None:
                membros.add(uid)
        # O mapper retorna 1 linha por vez; a 1a vira a linha do par.
        self._pending = [(conversa_id, uid) for uid in sorted(membros)]
        return self._emit()

    def _emit(self) -> dict | None:
        if not self._pending:
            return None
        conversa_id, uid = self._pending.pop(0)
        usuario_id = self.registry.resolve("usuarios", "users", uid)
        if not usuario_id:
            return self._emit()
        return {"conversa_id": conversa_id, "usuario_id": usuario_id}

    def current_legacy_id(self, row: dict) -> int:
        # conversa_membros nao tem coluna legacy; usa um id sintetico unico.
        return int(row["message_thread_id"]) if row.get("message_thread_id") else 0


class MensagemMapper(BaseMapper):
    source_table: ClassVar[str] = "message"
    source_columns: ClassVar[list[str]] = MESSAGE_COLUMNS
    target_table: ClassVar[str] = "mensagens"
    order_by: ClassVar[str | None] = "message_id"

    def map(self, row: dict) -> dict | None:
        if not self.registry:
            return None
        thread_id = self.registry.get_value("thread_code", str(row["message_thread_code"]))
        conversa_id = self.registry.resolve("conversas", "message_thread", thread_id)
        if not conversa_id:
            return None
        remetente_id = self.registry.resolve("usuarios", "users", _first_int(row.get("sender")))
        return {
            "conversa_id": conversa_id,
            "remetente_id": remetente_id,
            "texto": self.str_clean(row.get("message")),
            "lida_em": self.parse_ts(row.get("timestamp")) if self.as_int(row.get("read_status")) else None,
            "criado_em": self.parse_ts(row.get("timestamp")),
        }