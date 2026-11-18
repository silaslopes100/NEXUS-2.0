"""Questionários de DEMONSTRAÇÃO: uma avaliação genérica (8 questões) para cada Disciplina sem avaliação.

As avaliações ficam com origem='demo'. Quando o admin edita uma pelo editor (Disciplinas → Avaliação),
ela passa a origem='manual' e deixa de ser tratada como demonstração.

Uso (na pasta nexus-backend):
  .venv\\Scripts\\python.exe scripts\\demo_avaliacoes.py --status
  .venv\\Scripts\\python.exe scripts\\demo_avaliacoes.py --criar
  .venv\\Scripts\\python.exe scripts\\demo_avaliacoes.py --limpar

--limpar remove as avaliações demo e suas tentativas, mas PRESERVA as notas já lançadas
(nota é registro acadêmico). Recusa rodar com PAYMENT_ENV=producao, e com
ENVIRONMENT=production sem --permitir-producao.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import get_db_cursor  # noqa: E402

# (enunciado, correta, [erradas]) — {d} = nome da disciplina
MODELOS = [
    ("Qual é o principal objetivo de estudar {d}?",
     "Compreender os fundamentos da disciplina e aplicá-los com responsabilidade",
     ["Decorar conteúdos sem relação com a prática", "Substituir o estudo das demais disciplinas",
      "Apenas cumprir carga horária, sem aprendizado"]),
    ("Ao concluir {d}, espera-se que o aluno seja capaz de:",
     "Relacionar os conceitos estudados com situações reais",
     ["Ignorar os conceitos apresentados no material", "Repetir textos sem compreendê-los",
      "Dispensar a leitura do material de apoio"]),
    ("Qual atitude mais contribui para um bom aproveitamento em {d}?",
     "Ler o material com antecedência e revisar o conteúdo com regularidade",
     ["Estudar apenas na véspera da avaliação", "Evitar tirar dúvidas com o professor",
      "Faltar às aulas e consultar só resumos"]),
    ("O livro da disciplina {d} deve ser utilizado principalmente para:",
     "Apoiar o estudo, aprofundar os temas e servir de referência",
     ["Ser consultado apenas no dia da prova", "Substituir completamente as aulas",
      "Nenhuma finalidade no processo de aprendizagem"]),
    ("Em {d}, a leitura crítica de um texto significa:",
     "Analisar argumentos, contexto e fontes antes de tirar conclusões",
     ["Aceitar tudo o que está escrito sem refletir", "Rejeitar qualquer ideia diferente da própria",
      "Ler apenas o título e a conclusão"]),
    ("Qual é a melhor forma de esclarecer uma dúvida sobre o conteúdo de {d}?",
     "Consultar o material, o professor ou a coordenação do Polo",
     ["Deixar a dúvida para depois da avaliação", "Ignorar a dúvida e seguir adiante",
      "Copiar a resposta de um colega sem entender"]),
    ("Por que é importante relacionar {d} com as outras disciplinas do curso?",
     "Porque o conhecimento é integrado e uma disciplina complementa a outra",
     ["Porque as disciplinas não têm nenhuma relação", "Para reduzir a quantidade de estudo",
      "Não é importante fazer essa relação"]),
    ("Sobre a avaliação de {d}, é correto afirmar que:",
     "Ela verifica a compreensão dos conteúdos estudados na disciplina",
     ["Ela não tem relação com o conteúdo estudado", "Ela dispensa qualquer preparação",
      "Ela avalia apenas a velocidade de resposta"]),
]


def _questoes(nome: str, deslocamento: int) -> List[Dict[str, Any]]:
    """Monta as 8 questões; a alternativa correta muda de posição (determinístico por disciplina)."""
    questoes = []
    for n, (enunciado, correta, erradas) in enumerate(MODELOS):
        posicao = (n + deslocamento) % 4
        textos = list(erradas)
        textos.insert(posicao, correta)
        questoes.append({
            "enunciado": enunciado.format(d=nome),
            "peso": 1,
            "alternativas": [{"texto": t, "correta": i == posicao} for i, t in enumerate(textos)],
        })
    return questoes


def _checar_ambiente(permitir_producao: bool) -> None:
    if settings.PAYMENT_ENV == "producao":
        raise SystemExit("Recusado: PAYMENT_ENV=producao. Dados de demonstração só no sandbox.")
    if settings.ENVIRONMENT == "production" and not permitir_producao:
        raise SystemExit("Recusado: ENVIRONMENT=production. Use --permitir-producao apenas em banco de homologação.")
    host = urlparse(settings.PG_DSN or "").hostname or "?"
    print(f"Banco de destino: {host[:6]}…{host[-12:] if len(host) > 18 else ''}")


def status() -> None:
    with get_db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM disciplinas")
        total = cur.fetchone()["n"]
        cur.execute("SELECT origem, ativo, COUNT(*) AS n FROM avaliacoes GROUP BY origem, ativo ORDER BY origem, ativo")
        linhas = cur.fetchall()
        cur.execute("""SELECT COUNT(*) AS n FROM disciplinas d
                        WHERE NOT EXISTS (SELECT 1 FROM avaliacoes a WHERE a.disciplina_id = d.id)""")
        sem = cur.fetchone()["n"]
    print(f"Disciplinas: {total} | sem avaliação: {sem}")
    for r in linhas:
        print(f"  avaliações origem={r['origem']} ativo={r['ativo']}: {r['n']}")


def criar() -> None:
    from app.modules.avaliacoes.repository import PostgresAvaliacoesRepository

    repo = PostgresAvaliacoesRepository()
    with get_db_cursor() as cur:
        cur.execute("""SELECT d.id, d.nome FROM disciplinas d
                        WHERE NOT EXISTS (SELECT 1 FROM avaliacoes a WHERE a.disciplina_id = d.id)
                        ORDER BY d.nome""")
        disciplinas = cur.fetchall()
    for i, d in enumerate(disciplinas):
        nome = (d["nome"] or "a disciplina").strip()
        repo.salvar_avaliacao(
            str(d["id"]),
            {
                "titulo": f"Avaliação — {nome}",
                "instrucoes": "Leia cada questão com atenção e escolha uma alternativa. "
                              "Você tem 2 tentativas e vale a maior nota. Aprovação com nota 6,0.",
                "tempo_limite_min": None,
                "tentativas_max": 2,
                "nota_minima": 6.0,
                "embaralhar": True,
                "ativo": True,
            },
            _questoes(nome, i),
            None,
            origem="demo",
        )
    print(f"Criadas {len(disciplinas)} avaliação(ões) de demonstração (8 questões cada).")


def limpar() -> None:
    with get_db_cursor() as cur:
        cur.execute("""SELECT COUNT(*) AS n FROM avaliacao_tentativas t
                         JOIN avaliacoes a ON a.id = t.avaliacao_id WHERE a.origem = 'demo'""")
        tentativas = cur.fetchone()["n"]
        cur.execute("""SELECT COUNT(*) AS n FROM avaliacao_tentativas t
                         JOIN avaliacoes a ON a.id = t.avaliacao_id
                        WHERE a.origem = 'demo' AND t.nota_id IS NOT NULL""")
        notas = cur.fetchone()["n"]
        cur.execute("""DELETE FROM avaliacao_tentativas
                        WHERE avaliacao_id IN (SELECT id FROM avaliacoes WHERE origem = 'demo')""")
        cur.execute("DELETE FROM avaliacoes WHERE origem = 'demo'")
        removidas = cur.rowcount
    print(f"Removidas {removidas} avaliação(ões) demo e {tentativas} tentativa(s). "
          f"{notas} nota(s) lançada(s) por essas provas foram preservadas no histórico.")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--criar", action="store_true")
    grupo.add_argument("--limpar", action="store_true")
    grupo.add_argument("--status", action="store_true")
    parser.add_argument("--permitir-producao", action="store_true")
    args = parser.parse_args(argv)
    _checar_ambiente(args.permitir_producao)
    if args.criar:
        criar()
    elif args.limpar:
        limpar()
    status()


if __name__ == "__main__":
    main()
