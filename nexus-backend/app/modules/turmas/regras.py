"""Regras puras da turma: situação derivada, código automático e nome sugerido."""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any, Dict, Iterable, Literal, Optional

from fastapi import HTTPException, status

Situacao = Literal["planejada", "em_andamento", "concluida", "cancelada"]
SITUACOES = ("planejada", "em_andamento", "concluida", "cancelada")
ROTULO_SITUACAO = {
    "planejada": "planejada",
    "em_andamento": "em andamento",
    "concluida": "concluída",
    "cancelada": "cancelada",
}

# Mesma regra da situação, em SQL, para filtrar a listagem (alias da tabela de turmas: t).
SQL_SITUACAO = """
    CASE
        WHEN t.cancelada_em IS NOT NULL THEN 'cancelada'
        WHEN t.concluida_em IS NOT NULL THEN 'concluida'
        WHEN t.data_inicio IS NOT NULL AND t.data_inicio > CURRENT_DATE THEN 'planejada'
        ELSE 'em_andamento'
    END
"""

_PALAVRAS_IGNORADAS = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "para"}


def situacao(turma: Dict[str, Any], hoje: Optional[date] = None) -> Situacao:
    if turma.get("cancelada_em"):
        return "cancelada"
    if turma.get("concluida_em"):
        return "concluida"
    inicio = turma.get("data_inicio")
    if isinstance(inicio, str):
        inicio = date.fromisoformat(inicio[:10])
    if inicio and inicio > (hoje or date.today()):
        return "planejada"
    return "em_andamento"


def periodo_encerrado(turma: Dict[str, Any], hoje: Optional[date] = None) -> bool:
    """Em andamento depois do fim do período: falta o admin concluir."""
    fim = turma.get("data_fim")
    if isinstance(fim, str):
        fim = date.fromisoformat(fim[:10])
    return situacao(turma, hoje) == "em_andamento" and bool(fim) and fim < (hoje or date.today())


def exigir_turma_editavel(turma: Optional[Dict[str, Any]]) -> None:
    """Turma concluída ou cancelada fica só leitura (dados, alunos, professores, cronograma e atas)."""
    if not turma:
        return
    s = situacao(turma)
    if s in ("concluida", "cancelada"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Turma {ROTULO_SITUACAO[s]}: somente leitura. Reabra a turma para alterar.",
        )


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def sigla_curso(nome_curso: Optional[str]) -> str:
    """Iniciais das palavras significativas, até 4 letras ("Curso de Formação Teológica" → CFT)."""
    palavras = [p for p in re.split(r"\s+", nome_curso or "") if p and p[0].isalpha()]
    iniciais = "".join(p[0] for p in palavras if p.lower() not in _PALAVRAS_IGNORADAS)
    return _sem_acento(iniciais).upper()[:4] or "TUR"


def proximo_codigo(sigla: str, ano: int, existentes: Iterable[str]) -> str:
    prefixo = f"{sigla}-{ano}-"
    seqs = [int(c[len(prefixo):]) for c in existentes if c and c.startswith(prefixo) and c[len(prefixo):].isdigit()]
    return f"{prefixo}{(max(seqs) + 1) if seqs else 1:03d}"


def nome_sugerido(codigo: str, unidade: Optional[str], modalidade: str) -> str:
    seq = codigo.rsplit("-", 1)[-1].lstrip("0") or "1"
    sufixo = "EAD" if modalidade == "ead" else (unidade or "")
    return f"Turma {seq.zfill(2)}" + (f" — {sufixo}" if sufixo else "")
