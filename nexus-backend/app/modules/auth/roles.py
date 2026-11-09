"""Equivalência entre os nomes de perfil usados no NEXUS 2.0.

O mesmo papel tem dois nomes: os curtos vêm da carga do legado e os longos do
cadastro de polos e escolas. As comparações de perfil devem passar por aqui.
"""
from __future__ import annotations

from typing import Optional, Tuple

from app.modules.auth.schemas import UserResponse

_ALIASES = {"coordenador_polo": "polo", "secretario_escola": "escola"}


def _limpar(nome: Optional[str]) -> str:
    return (nome or "").lower().strip()


def perfil_canonico(nome: Optional[str]) -> str:
    """Retorna o nome canônico (curto) do perfil."""
    limpo = _limpar(nome)
    return _ALIASES.get(limpo, limpo)


def perfil_do_usuario(user: UserResponse) -> str:
    """Retorna o nome canônico do perfil do usuário, ou vazio se não houver perfil."""
    return perfil_canonico(user.perfil.nome if user.perfil else None)


def nomes_equivalentes(nome: Optional[str]) -> Tuple[str, ...]:
    """Retorna todos os nomes do papel, começando pelo nome informado."""
    limpo = _limpar(nome)
    canonico = perfil_canonico(limpo)
    longos = [longo for longo, curto in _ALIASES.items() if curto == canonico]
    return tuple(dict.fromkeys([limpo, canonico, *longos]))
