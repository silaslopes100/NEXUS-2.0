"""Perfis (RBAC). Fonte legado: `role` + regras de negocio do plano.

Garante os 5 perfis padrao do sistema (admin, polo, escola, professor, aluno)
e importa as linhas da tabela `role` como perfis adicionais, preservando o id
legado para rastreabilidade. O usuarios_mapper resolve o perfil de cada user
pela `role_id` quando possivel; senao usa heuristica por flags.
"""
from __future__ import annotations

import logging
from typing import ClassVar

from .base import BaseMapper

logger = logging.getLogger(__name__)

PERFIS_PADRAO = ["admin", "polo", "escola", "professor", "aluno"]

# Sinonimos comuns de nomes de role no legado -> perfil padrao.
# Roles desconhecidas retornam None e caem na heuristica por flags.
ALIASES = {
    "admin": "admin", "administrator": "admin", "administrador": "admin",
    "secretaria": "admin", "coordenador": "admin", "diretor": "admin",
    "secretary": "admin", "secretaria_geral": "admin", "coordenador_geral": "admin",
    "polo": "polo", "coordenador_polo": "polo", "coordenador_de_polo": "polo",
    "vendedor": "polo",
    "escola": "escola", "secretario_escola": "escola", "secretario_da_escola": "escola",
    "professor": "professor", "instructor": "professor", "prof": "professor",
    "aluno": "aluno", "student": "aluno", "estudante": "aluno", "aluna": "aluno",
}

# Heuristica usada pelo usuarios_mapper quando a role_id nao resolve.
# Ordem de prioridade: staff central > professor > polo > escola > aluno.
FLAG_TO_PERFIL = [
    (("is_pedag",), "admin"),
    (("is_exec",), "admin"),
    (("is_secret",), "admin"),
    (("is_instructor",), "professor"),
    (("is_vendedor",), "polo"),
]


class PerfilMapper(BaseMapper):
    source_table: ClassVar[str] = "role"
    source_columns: ClassVar[list[str]] = ["id", "name", "date_added", "last_modified"]
    target_table: ClassVar[str] = "perfis"
    # perfis.nome e UNIQUE e varias roles legadas colidem no mesmo nome padrao;
    # o upsert precisa usar nome como alvo do conflito, nao (legacy_table, legacy_id).
    upsert_conflict_columns: ClassVar[tuple[str, ...]] = ("nome",)

    @staticmethod
    def normalize_name(name):
        """Traduz nomes de role do legado para os perfis padrao; None se desconhecida."""
        if not name:
            return "aluno"
        n = str(name).strip().lower().replace(" ", "_")
        return ALIASES.get(n)

    def map(self, row: dict) -> dict | None:
        nome = self.normalize_name(row.get("name"))
        if not nome:
            return None  # role desconhecida: usuarios caem na heuristica por flags
        return {"nome": nome[:32], "descricao": f"Perfil migrado da role legada {row.get('name')}"}


def ensure_defaults(target) -> None:
    """Cria os 5 perfis padrao caso ainda nao existam (idempotente)."""
    from ..target_postgres import PostgresTarget

    for nome in PERFIS_PADRAO:
        target.execute(
            "INSERT INTO perfis (nome, descricao) VALUES (%s, %s) "
            "ON CONFLICT (nome) DO NOTHING",
            (nome, f"Perfil padrão {nome}"),
        )
    target.commit()


def resolve_profile_for_row(row: dict) -> str:
    """Decide o perfil de um user legado quando a role_id nao mapeia."""
    for flags, perfil in FLAG_TO_PERFIL:
        if all(BaseMapper.as_bool(row.get(f)) for f in flags):
            return perfil
    if row.get("polo") not in (None, "", 0) and row.get("escola") in (None, "", 0):
        return "polo"
    if row.get("escola") not in (None, "", 0):
        return "escola"
    return "aluno"


def perfil_nome(registry, row: dict) -> str | None:
    """Perfil de um user legado: 1o pela role mapeada, senao pela heuristica.

    Usado por usuarios/alunos/professores para classificar de forma CONSISTENTE.
    """
    role_id = BaseMapper.as_int(row.get("role_id"))
    if registry is not None and role_id:
        nome = registry.role_to_perfil_nome(role_id)
        if nome:
            return nome
    return resolve_profile_for_row(row)