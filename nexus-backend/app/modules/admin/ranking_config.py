"""Pesos do índice de desempenho (Histórico da Turma e ranking de Polos) — tabela config_ranking_polos (036)."""
from __future__ import annotations

import logging
from typing import Dict, Optional

from app.core.database import get_db_cursor

logger = logging.getLogger(__name__)

PESOS_PADRAO: Dict[str, float] = {"peso_notas": 40.0, "peso_frequencia": 30.0, "peso_compras": 30.0}


def obter_pesos() -> Dict[str, float]:
    """Pesos atuais; os padrões (40/30/30) se a tabela ainda não existir."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT peso_notas, peso_frequencia, peso_compras, atualizado_em FROM config_ranking_polos WHERE id = 1")
            r = cur.fetchone()
    except Exception:  # migração 036 ainda não aplicada
        logger.warning("config_ranking_polos indisponível; usando os pesos padrão")
        return dict(PESOS_PADRAO)
    if not r:
        return dict(PESOS_PADRAO)
    return {"peso_notas": float(r["peso_notas"]), "peso_frequencia": float(r["peso_frequencia"]),
            "peso_compras": float(r["peso_compras"]), "atualizado_em": r.get("atualizado_em")}


def salvar_pesos(pesos: Dict[str, float], usuario_id: Optional[str]) -> Dict[str, float]:
    with get_db_cursor() as cur:
        cur.execute(
            """INSERT INTO config_ranking_polos (id, peso_notas, peso_frequencia, peso_compras, atualizado_por, atualizado_em)
               VALUES (1, %(n)s, %(f)s, %(c)s, %(u)s, now())
               ON CONFLICT (id) DO UPDATE SET peso_notas = EXCLUDED.peso_notas, peso_frequencia = EXCLUDED.peso_frequencia,
                   peso_compras = EXCLUDED.peso_compras, atualizado_por = EXCLUDED.atualizado_por, atualizado_em = now()""",
            {"n": pesos["peso_notas"], "f": pesos["peso_frequencia"], "c": pesos["peso_compras"], "u": usuario_id},
        )
    return obter_pesos()


def indice(componentes: Dict[str, Optional[float]], pesos: Dict[str, float]) -> Optional[float]:
    """Média ponderada (0–100) dos componentes {notas, frequencia, compras}.

    Componente None conta 0; componente ausente do dicionário não entra (ex.: frequência na turma EAD).
    """
    mapa = {"notas": "peso_notas", "frequencia": "peso_frequencia", "compras": "peso_compras"}
    usados = {k: v for k, v in componentes.items() if k in mapa}
    soma_pesos = sum(float(pesos.get(mapa[k], 0)) for k in usados)
    if not usados or soma_pesos <= 0 or all(v is None for v in usados.values()):
        return None
    total = sum(float(pesos.get(mapa[k], 0)) * float(v or 0) for k, v in usados.items())
    return round(total / soma_pesos, 1)
