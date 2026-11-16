"""Teste da listagem de alunos em banco PostgreSQL de teste."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import os

import psycopg2
from psycopg2.extras import RealDictCursor
import pytest

from app.core.config import settings
from app.modules import notas_historico


@pytest.mark.skipif(
    not os.environ.get("NEXUS_TEST_POSTGRES_DSN"),
    reason="NEXUS_TEST_POSTGRES_DSN não configurado para banco de teste isolado",
)
def test_listagem_alunos_distintos_postgres(monkeypatch):
    with closing(psycopg2.connect(os.environ["NEXUS_TEST_POSTGRES_DSN"])) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TEMP TABLE usuarios (id text PRIMARY KEY, nome text, sobrenome text, email text, cpf text);
                CREATE TEMP TABLE alunos (id text PRIMARY KEY, usuario_id text, numero_matricula text);
                CREATE TEMP TABLE disciplinas (id text PRIMARY KEY, nome text);
                CREATE TEMP TABLE turmas (id text PRIMARY KEY, nome text);
                CREATE TEMP TABLE notas (
                    id text PRIMARY KEY, aluno_id text, disciplina_id text, turma_id text,
                    origem text, valor numeric, lancado_por text, lancado_em timestamptz,
                    atualizado_em timestamptz
                );
                INSERT INTO disciplinas VALUES ('d1', 'Teologia'), ('d2', 'História');
            """)
            for indice in range(32):
                aluno_id = f"aluno-{indice:02}"
                cur.execute("INSERT INTO usuarios VALUES (%s, %s, 'Teste', %s, %s)", (
                    aluno_id, f"Pessoa {indice:02}", f"pessoa{indice:02}@example.com", f"12345678{indice:03}",
                ))
                cur.execute("INSERT INTO alunos VALUES (%s, %s, %s)", (aluno_id, aluno_id, f"MAT-{indice:02}"))
                cur.execute(
                    "INSERT INTO notas (id, aluno_id, disciplina_id, origem, valor, atualizado_em) VALUES (%s, %s, 'd1', 'manual', 7, %s)",
                    (f"nota-{indice:02}", aluno_id, datetime.fromtimestamp(indice, timezone.utc)),
                )
            cur.execute(
                "INSERT INTO notas (id, aluno_id, disciplina_id, origem, valor, atualizado_em) VALUES "
                "('extra', 'aluno-00', 'd2', 'manual', 8, %s), ('sem-data', 'aluno-01', 'd2', 'manual', 9, NULL)",
                (datetime.fromtimestamp(100, timezone.utc),),
            )

        @contextmanager
        def cursor_real():
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur

        monkeypatch.setattr(settings, "PG_DSN", "teste")
        monkeypatch.setattr(notas_historico, "get_db_cursor", cursor_real)
        listar = notas_historico._listar_notas_admin
        primeira = listar(None, None, None, None, 30, 0, por_aluno=True)
        segunda = listar(None, None, None, None, 30, 30, por_aluno=True)
        ids = [row["aluno_id"] for row in primeira["items"] + segunda["items"]]
        assert primeira["total"] == segunda["total"] == 32
        assert len(primeira["items"]) == 30 and len(segunda["items"]) == 2
        assert len(set(ids)) == 32 and ids[0] == "aluno-00"
        filtrada = listar(None, None, None, "teolog", 30, 0, por_aluno=True)
        assert filtrada["total"] == 32
        assert filtrada["items"][0]["aluno_id"] == "aluno-31"
        historia = listar(None, None, "d2", None, 30, 0, por_aluno=True)
        assert [row["aluno_id"] for row in historia["items"]] == ["aluno-00", "aluno-01"]
        assert historia["items"][1]["atualizado_em"] is None
        busca = listar("123.456.780-00", None, None, None, 30, 0, por_aluno=True)
        assert [row["aluno_id"] for row in busca["items"]] == ["aluno-00"]
        detalhes = listar(None, "aluno-00", None, None, 30, 0)
        assert {row["id"] for row in detalhes["items"]} == {"nota-00", "extra"}
