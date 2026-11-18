"""Define o preço (Kit: 1 livro + 1 licença) das Disciplinas e sincroniza os kits do catálogo.

Uso (na pasta nexus-backend):
  .venv\\Scripts\\python.exe scripts\\definir_preco_disciplinas.py --status
  .venv\\Scripts\\python.exe scripts\\definir_preco_disciplinas.py --preco 70
  .venv\\Scripts\\python.exe scripts\\definir_preco_disciplinas.py --preco 70 --so-sem-preco
  .venv\\Scripts\\python.exe scripts\\definir_preco_disciplinas.py --preco 70 --curso <curso_id>

Depois, o preço de cada disciplina pode ser ajustado em Admin -> Disciplinas -> Editar.
Recusa rodar com ENVIRONMENT=production sem --permitir-producao.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import get_db_cursor  # noqa: E402


def _checar_ambiente(permitir_producao: bool) -> None:
    if settings.ENVIRONMENT == "production" and not permitir_producao:
        raise SystemExit("Recusado: ENVIRONMENT=production. Use --permitir-producao se for intencional.")
    host = urlparse(settings.PG_DSN or "").hostname or "?"
    print(f"Banco de destino: {host[:6]}…{host[-12:] if len(host) > 18 else ''}")


def status() -> None:
    with get_db_cursor() as cur:
        cur.execute("""SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE ativo) AS ativas,
                              COUNT(*) FILTER (WHERE preco > 0) AS com_preco FROM disciplinas""")
        d = cur.fetchone()
        cur.execute("SELECT COUNT(*) FILTER (WHERE ativo) AS ativos, COUNT(*) AS total FROM produtos WHERE tipo = 'kit'")
        k = cur.fetchone()
        cur.execute("""SELECT c.nome, COUNT(d.id) AS disciplinas, COALESCE(SUM(p.preco), 0) AS total
                         FROM cursos c JOIN disciplinas d ON d.curso_id = c.id AND d.ativo
                         LEFT JOIN produtos p ON p.disciplina_id = d.id AND p.tipo = 'kit' AND p.ativo
                        GROUP BY c.nome ORDER BY c.nome""")
        cursos = cur.fetchall()
    print(f"Disciplinas: {d['total']} | ativas: {d['ativas']} | com preço: {d['com_preco']}")
    print(f"Kits: {k['ativos']} à venda de {k['total']}")
    for c in cursos:
        print(f"  {c['nome']}: {c['disciplinas']} disciplina(s) ativa(s) · preço do curso R$ {float(c['total']):.2f}")


def definir(preco: float, curso_id: Optional[str], so_sem_preco: bool) -> None:
    from app.modules.cursos_disciplinas import _sincronizar_kit

    conds, params = [], [round(preco, 2)]
    if curso_id:
        conds.append("curso_id = %s")
        params.append(curso_id)
    if so_sem_preco:
        conds.append("(preco IS NULL OR preco = 0)")
    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    with get_db_cursor() as cur:  # uma transação: preço + kits juntos
        cur.execute(f"UPDATE disciplinas SET preco = %s, atualizado_em = now(){where} "
                    "RETURNING id, nome, preco, peso_livro_g, ativo", tuple(params))
        linhas = cur.fetchall()
        for row in linhas:
            _sincronizar_kit(cur, dict(row))
    print(f"Preço R$ {preco:.2f} aplicado em {len(linhas)} disciplina(s); kits sincronizados.")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--preco", type=float)
    grupo.add_argument("--status", action="store_true")
    parser.add_argument("--curso")
    parser.add_argument("--so-sem-preco", action="store_true")
    parser.add_argument("--permitir-producao", action="store_true")
    args = parser.parse_args(argv)
    _checar_ambiente(args.permitir_producao)
    if args.preco is not None:
        if not 0 < args.preco < 1_000_000:
            raise SystemExit("Informe um preço maior que zero.")
        definir(args.preco, args.curso, args.so_sem_preco)
    status()


if __name__ == "__main__":
    main()
