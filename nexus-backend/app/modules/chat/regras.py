"""Regras puras do Chat Interno (sem acesso a banco)."""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from app.modules.auth.roles import perfil_canonico

# Namespace fixo: o id de cada conversa é uuid5(NAMESPACE, chave), portanto determinístico.
NAMESPACE_CHAT = uuid.UUID("6f3d8a52-2b1e-4c7a-9d0e-4a1f5c9b7e21")

# Perfis canônicos com acesso ao chat.
PERFIS_CHAT = ("admin", "polo", "escola", "professor", "aluno", "financeiro", "logistica",
               "secretario_geral", "coordenador_ead", "monitor")

# Retenção das mensagens.
HORAS_TABELA_ATIVA = 48
DIAS_HISTORICO = 90


def chave_individual(usuario_a: str, usuario_b: str) -> str:
    """Chave única do chat individual: concatenação ordenada dos IDs dos dois usuários."""
    a, b = sorted((str(usuario_a).lower(), str(usuario_b).lower()))
    return f"ind:{a}_{b}"


def chave_turma(turma_id: str) -> str:
    return f"turma:{str(turma_id).lower()}"


def chave_grupo_livre() -> str:
    return f"grupo:{uuid.uuid4()}"


def id_da_chave(chave: str) -> str:
    return str(uuid.uuid5(NAMESPACE_CHAT, chave))


def eh_aluno(perfil: Optional[str]) -> bool:
    return perfil_canonico(perfil) == "aluno"


def pode_conversar(perfil_a: Optional[str], perfil_b: Optional[str]) -> bool:
    """RN-06: é proibido chat individual aluno↔aluno."""
    return not (eh_aluno(perfil_a) and eh_aluno(perfil_b))


def grupo_livre_valido(perfis_membros: Iterable[Optional[str]]) -> bool:
    """Alunos só conversam entre si nos grupos de turma: grupo livre aceita no máximo 1 aluno."""
    return sum(1 for p in perfis_membros if eh_aluno(p)) <= 1


def pode_encerrar(*, perfil: str, tipo: str, papel: Optional[str], criado_por: Optional[str], usuario_id: str) -> bool:
    """Admin sempre; individual: participante que não seja aluno; grupo: moderador ou criador."""
    if perfil == "admin":
        return True
    if papel is None:
        return False
    if tipo == "individual":
        return not eh_aluno(perfil)
    return papel == "moderador" or (criado_por is not None and str(criado_por) == str(usuario_id))
