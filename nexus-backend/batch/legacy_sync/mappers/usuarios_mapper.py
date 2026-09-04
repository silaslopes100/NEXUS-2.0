"""Usuarios (unificacao da tabela `users`, 62 colunas -> modelo normalizado).

Normalizacoes:
- perfil: `role_id` quando mapeia; senao heuristica por flags (perfis_mapper).
- Polo/Escola sao extraidos nas tabelas proprias; aqui apenas as FKs.
- e-mail e CPF duplicados no legado viram NULL no destino (unicidade garantida
  por indice parcial) e sao listados como aviso no relatorio da execucao.
- senha: migrada como esta (hash legado), marcada `senha_algoritmo='legacy_bcrypt'`
  para o lazy rehash do modulo Login.
- o campo `users.status` (int, sem dicionario) mapeia para ativo/inativo.
"""
from __future__ import annotations

from typing import ClassVar

from .base import BaseMapper
from .perfis_mapper import perfil_nome

USERS_COLUMNS = [
    "id", "first_name", "last_name", "email", "password", "role_id",
    "date_added", "last_modified", "status", "is_instructor", "image",
    "celular", "is_vendedor", "cpf", "p_cadastro", "p_edicao", "p_acomp",
    "p_vendas", "p_matriculas", "p_matricula_manual", "p_ranking", "polo",
    "escola", "telefone", "nascimento", "revalidacao", "is_secret", "is_exec",
    "is_pedag", "p_cursos", "p_users", "p_chat", "p_academico", "p_financeiro",
    "legacy_id", "duplicata_id", "rg", "nome_escola",
]

STATUS_ATIVOS = {None, 0, 1}


class UsuarioMapper(BaseMapper):
    source_table: ClassVar[str] = "users"
    source_columns: ClassVar[list[str]] = USERS_COLUMNS
    target_table: ClassVar[str] = "usuarios"
    order_by: ClassVar[str | None] = "id"
    incremental_column: ClassVar[str | None] = "last_modified"

    def __init__(self, registry=None) -> None:
        super().__init__(registry)
        self._seen_cpf: set[str] = set()

    def _perfil_uuid(self, nome: str) -> str | None:
        if not nome:
            return None
        if not self.registry:
            return None
        key = "perfis_by_nome"
        cache = getattr(self.registry, "_nome_cache", None)
        if cache is None:
            cache = {}
            setattr(self.registry, "_nome_cache", cache)
        if key not in cache:
            sql = f"SELECT nome, id FROM perfis"
            with self.registry._target.conn.cursor() as cur:
                cur.execute(sql)
                cache[key] = {r[0]: str(r[1]) for r in cur.fetchall()}
        return cache[key].get(nome)

    def map(self, row: dict) -> dict | None:
        email = self._dedup_email(self.str_clean(row.get("email"), 255))
        cpf = self.str_clean(row.get("cpf"), 20)
        if cpf:
            key = cpf
            if key in self._seen_cpf:
                self.warn(f"cpf duplicado ignorado: {cpf}")
                cpf = None
            else:
                self._seen_cpf.add(key)

        # perfil consistente: role mapeada -> heuristica por flags
        perfil_id = self._perfil_uuid(perfil_nome(self.registry, row))

        status_raw = row.get("status")
        status_int = self.as_int(status_raw) if status_raw not in (None, "") else None
        status = "ativo" if status_int in STATUS_ATIVOS else "inativo"
        return {
            "nome": self.str_clean(row.get("first_name"), 255) or "",
            "sobrenome": self.str_clean(row.get("last_name"), 255) or "",
            "email": email,
            "cpf": cpf,
            "senha_hash": self.str_clean(row.get("password"), 255),
            "senha_algoritmo": "legacy_bcrypt",
            "telefone": self.str_clean(row.get("telefone"), 64),
            "celular": self.str_clean(row.get("celular"), 64),
            "foto_url": self.str_clean(row.get("image"), 500),
            "perfil_id": perfil_id,
            "polo_id": self.registry.resolve("polos", "users", row.get("polo")) if self.registry else None,
            "escola_id": self.registry.resolve("escolas", "users", row.get("escola")) if self.registry else None,
            "status": status,
            "ultimo_login_em": None,
        }

    def _perfil_uuid(self, nome: str) -> str | None:
        if not self.registry:
            return None
        key = "perfis_by_nome"
        cache = getattr(self.registry, "_nome_cache", None)
        if cache is None:
            cache = {}
            setattr(self.registry, "_nome_cache", cache)
        if key not in cache:
            sql = f"SELECT nome, id FROM perfis"
            with self.registry._target.conn.cursor() as cur:
                cur.execute(sql)
                cache[key] = {r[0]: str(r[1]) for r in cur.fetchall()}
        return cache[key].get(nome)