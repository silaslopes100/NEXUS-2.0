"""Valores e fórmulas da gamificação (ajuste aqui; o catálogo de conquistas fica no banco)."""
from __future__ import annotations

import math
from typing import Dict, Tuple

XP_AULA = 10
XP_CAPITULO = 50
XP_DISCIPLINA = 200
XP_AVALIACAO = 100
XP_AVALIACAO_EXCELENTE = 50  # nota >= NOTA_EXCELENTE
NOTA_EXCELENTE = 9.0
XP_STREAK_POR_DIA = 5
STREAK_TETO = 7  # o bônus diário cresce até 7 dias seguidos

ROTULOS: Dict[str, str] = {
    "aula_concluida": "Aula concluída",
    "capitulo_concluido": "Capítulo concluído",
    "disciplina_concluida": "Disciplina concluída",
    "avaliacao_aprovada": "Avaliação aprovada",
    "avaliacao_excelente": "Nota de excelência",
    "streak_dia": "Sequência de estudos",
    "conquista": "Conquista desbloqueada",
}

_NOMES_NIVEL = ["Calouro", "Explorador", "Aprendiz", "Dedicado", "Focado", "Brilhante", "Expert", "Mestre", "Lenda"]


def xp_streak(dias: int) -> int:
    return XP_STREAK_POR_DIA * max(1, min(dias, STREAK_TETO))


def nivel_de(xp: int) -> int:
    """Nível 1 com 0 XP; o nível n começa em 50·(n-1)² XP (50, 200, 450, 800…)."""
    return int(math.floor(math.sqrt(max(xp, 0) / 50))) + 1


def xp_inicio_nivel(nivel: int) -> int:
    return 50 * (nivel - 1) ** 2


def nome_nivel(nivel: int) -> str:
    return _NOMES_NIVEL[nivel - 1] if nivel <= len(_NOMES_NIVEL) else f"Lenda Nexus {nivel - len(_NOMES_NIVEL)}"


def faixa(xp: int) -> Tuple[int, str, int, int, int]:
    """(nível, nome, xp no início do nível, xp do próximo nível, % do nível)."""
    n = nivel_de(xp)
    inicio, fim = xp_inicio_nivel(n), xp_inicio_nivel(n + 1)
    return n, nome_nivel(n), inicio, fim, int((xp - inicio) * 100 / (fim - inicio))
