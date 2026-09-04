"""Fakes para testar mappers sem banco real."""
from __future__ import annotations


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        pass

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, perfis=None):
        self.perfis = perfis or [
            ("admin", "u-admin"),
            ("polo", "u-polo"),
            ("escola", "u-escola"),
            ("professor", "u-prof"),
            ("aluno", "u-aluno"),
        ]

    def cursor(self):
        return FakeCursor(self.perfis)


class FakeTarget:
    def __init__(self):
        self.conn = FakeConn()


class FakeRegistry:
    """Imita IdRegistry para uso em testes de mapper."""

    def __init__(self, mapping=None, user_polos=None):
        # mapping: (target_table, legacy_table, legacy_id) -> uuid
        self._mapping = {
            (t, lt, int(lid)): uuid
            for (t, lt, lid), uuid in (mapping or {}).items()
        }
        self._user_polos = {int(k): v for k, v in (user_polos or {}).items()}
        self._custom: dict[str, dict[str, str]] = {}
        self._target = FakeTarget()

    def resolve(self, target_table, legacy_table, legacy_id):
        if legacy_id in (None, "", 0):
            return None
        try:
            lid = int(legacy_id)
        except (TypeError, ValueError):
            return None
        return self._mapping.get((target_table, legacy_table, lid))

    def register(self, target_table, legacy_table, legacy_id, new_uuid):
        self._mapping[(target_table, legacy_table, int(legacy_id))] = new_uuid

    def set_value(self, namespace, key, value):
        self._custom.setdefault(namespace, {})[str(key)] = value

    def get_value(self, namespace, key):
        return self._custom.get(namespace, {}).get(str(key))

    def usuario_polo(self, user_legacy_id):
        if user_legacy_id in (None, "", 0):
            return None
        return self._user_polos.get(int(user_legacy_id))

    def role_to_perfil_nome(self, role_id):
        uuid = self.resolve("perfis", "role", role_id)
        if not uuid:
            return None
        for nome, uid in self._target.conn.perfis:
            if uid == uuid:
                return nome
        return None