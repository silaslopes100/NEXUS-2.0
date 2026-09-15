"""Cache em memoria de mapeamento legacy_id -> uuid, por tabela destino.

Os mappers filhos (matriculas, notas, presencas...) precisam resolver a FK
do registro pai a partir do id legado. O registro e carregado uma vez por
tabela (SELECT) e alimentado a cada novo upsert (RETURNING id).
"""
from __future__ import annotations

from .target_postgres import PostgresTarget


class IdRegistry:
    def __init__(self, target: PostgresTarget) -> None:
        self._target = target
        self._cache: dict[str, dict[int, str]] = {}

    def load(self, target_table: str) -> None:
        """Carrega (legacy_table, legacy_id) -> uuid para uma tabela destino."""
        key = target_table
        if key in self._cache:
            return
        mapping: dict[tuple[str, int], str] = {}
        sql = (
            f"SELECT legacy_table, legacy_id, id FROM {target_table} "
            f"WHERE legacy_id IS NOT NULL AND legacy_id <> 0"
        )
        with self._target.conn.cursor() as cur:
            cur.execute(sql)
            for row in cur.fetchall():
                mapping[(row[0], int(row[1]))] = str(row[2])
        self._cache[key] = mapping  # type: ignore[assignment]

    def resolve(
        self, target_table: str, legacy_table: str, legacy_id: int | str | None
    ) -> str | None:
        """uuid do registro pai, ou None se ainda nao migrado."""
        if legacy_id in (None, "", "0", 0):
            return None
        try:
            lid = int(legacy_id)
        except (TypeError, ValueError):
            return None
        self.load(target_table)
        return self._cache[target_table].get((legacy_table, lid))  # type: ignore[index]

    def register(
        self, target_table: str, legacy_table: str, legacy_id: int, new_uuid: str
    ) -> None:
        key = target_table
        self.load(target_table)
        self._cache[key][(legacy_table, legacy_id)] = new_uuid  # type: ignore[index]

    # --- mapas custom (chave arbitraria -> uuid) para casos especiais ---
    _custom: dict[str, dict[str, str]]

    def set_value(self, namespace: str, key: str, value: str) -> None:
        if not hasattr(self, "_custom"):
            self._custom = {}
        self._custom.setdefault(namespace, {})[str(key)] = value

    def get_value(self, namespace: str, key: str) -> str | None:
        if not hasattr(self, "_custom"):
            return None
        return self._custom.get(namespace, {}).get(str(key))

    def usuario_polo(self, user_legacy_id: int | str | None) -> str | None:
        """polo_id (uuid) de um usuario legado, via usuarios.polo_id."""
        if user_legacy_id in (None, "", 0):
            return None
        try:
            lid = int(user_legacy_id)
        except (TypeError, ValueError):
            return None
        if not hasattr(self, "_usuario_polo_cache"):
            self._usuario_polo_cache: dict[int, str | None] = {}
        if lid in self._usuario_polo_cache:
            return self._usuario_polo_cache[lid]
        sql = "SELECT polo_id FROM usuarios WHERE legacy_table = 'users' AND legacy_id = %s"
        with self._target.conn.cursor() as cur:
            cur.execute(sql, (lid,))
            row = cur.fetchone()
        res = str(row[0]) if row and row[0] else None
        self._usuario_polo_cache[lid] = res
        return res

    def role_to_perfil_nome(self, role_id: int | str | None) -> str | None:
        """Nome do perfil mapeado para uma role legada (ex.: role 2 -> 'aluno')."""
        if role_id in (None, "", 0):
            return None
        try:
            rid = int(role_id)
        except (TypeError, ValueError):
            return None
        if not hasattr(self, "_role_perfil_cache"):
            self._role_perfil_cache: dict[int, str] = {}
            sql = (
                "SELECT legacy_id, nome FROM perfis "
                "WHERE legacy_table = 'role' AND legacy_id IS NOT NULL"
            )
            with self._target.conn.cursor() as cur:
                cur.execute(sql)
                for r in cur.fetchall():
                    if r[0] is not None:
                        self._role_perfil_cache[int(r[0])] = r[1]
        return self._role_perfil_cache.get(rid)