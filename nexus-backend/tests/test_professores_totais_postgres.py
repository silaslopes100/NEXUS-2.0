"""Teste da migração apenas em banco de teste explicitamente configurado."""
from __future__ import annotations

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Event

import psycopg2
import pytest
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from app.modules.professores import repository as professores_repository


@pytest.mark.skipif(
    not os.environ.get("NEXUS_TEST_POSTGRES_DSN"),
    reason="NEXUS_TEST_POSTGRES_DSN não configurado para banco de teste isolado",
)
def test_migracao_sincroniza_totais_em_postgres(monkeypatch):
    dsn = os.environ["NEXUS_TEST_POSTGRES_DSN"]
    schema = f"teste_totais_{uuid.uuid4().hex}"
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            cur.execute("""
                CREATE TABLE professores (
                    id uuid PRIMARY KEY, horas_totais integer, quantidade_aulas integer
                );
                CREATE TABLE disciplinas (
                    id uuid PRIMARY KEY, carga_horaria integer, qtd_aulas_prevista integer,
                    nome text, curso_id uuid
                );
                CREATE TABLE professor_disciplina_vinculos (
                    professor_id uuid REFERENCES professores(id) ON DELETE CASCADE,
                    disciplina_id uuid REFERENCES disciplinas(id) ON DELETE CASCADE,
                    UNIQUE (professor_id, disciplina_id)
                );
            """)
            professor, outro, disciplina, segunda = [str(uuid.uuid4()) for _ in range(4)]
            cur.execute("INSERT INTO professores VALUES (%s, 900, 900), (%s, 800, 800)", (professor, outro))
            cur.execute(
                "INSERT INTO disciplinas (id, carga_horaria, qtd_aulas_prevista, nome) VALUES "
                "(%s, 40, 10, 'Primeira'), (%s, NULL, 5, 'Segunda')", (disciplina, segunda)
            )
            cur.execute("INSERT INTO professor_disciplina_vinculos VALUES (%s, %s)", (professor, disciplina))
            migration = Path(__file__).resolve().parents[1] / "scripts" / "migrations" / "013_totais_professores_disciplinas.sql"
            cur.execute(migration.read_text(encoding="utf-8"))

            def totais(professor_id):
                cur.execute("SELECT horas_totais, quantidade_aulas FROM professores WHERE id = %s", (professor_id,))
                return cur.fetchone()

            assert totais(professor) == (40, 10)
            assert totais(outro) == (0, 0)
            cur.execute("INSERT INTO professor_disciplina_vinculos VALUES (%s, %s)", (professor, segunda))
            assert totais(professor) == (40, 15)
            cur.execute("UPDATE disciplinas SET carga_horaria = 60, qtd_aulas_prevista = 12 WHERE id = %s", (disciplina,))
            assert totais(professor) == (60, 17)
            cur.execute("UPDATE professores SET horas_totais = 999, quantidade_aulas = 999 WHERE id = %s", (professor,))
            assert totais(professor) == (60, 17)
            cur.execute("UPDATE professor_disciplina_vinculos SET professor_id = %s WHERE professor_id = %s AND disciplina_id = %s", (outro, professor, disciplina))
            assert totais(professor) == (0, 5)
            assert totais(outro) == (60, 12)
            cur.execute("DELETE FROM professor_disciplina_vinculos WHERE professor_id = %s", (outro,))
            assert totais(outro) == (0, 0)

            cur.execute("""
                CREATE TABLE cursos (id uuid PRIMARY KEY, nome text);
                CREATE TABLE polos (id uuid PRIMARY KEY, nome text);
                CREATE TABLE escolas (id uuid PRIMARY KEY, nome text);
                CREATE TABLE turmas (id uuid PRIMARY KEY, nome text, polo_id uuid, escola_id uuid);
                CREATE TABLE professor_disciplinas (
                    professor_id uuid, disciplina_id uuid, turma_id uuid, ativo boolean
                );
                CREATE TABLE usuarios (id uuid PRIMARY KEY, nome text, sobrenome text, email text);
                CREATE TABLE alunos (id uuid PRIMARY KEY, usuario_id uuid, numero_matricula text);
                CREATE TABLE turma_alunos (turma_id uuid, aluno_id uuid, status text);
            """)
            polo, outro_polo, escola, turma, turma_fora, usuario, aluno = [str(uuid.uuid4()) for _ in range(7)]
            cur.execute("INSERT INTO polos VALUES (%s, 'Polo'), (%s, 'Outro')", (polo, outro_polo))
            cur.execute("INSERT INTO escolas VALUES (%s, 'Escola')", (escola,))
            cur.execute("INSERT INTO turmas VALUES (%s, 'Turma', %s, %s), (%s, 'Fora', %s, NULL)", (turma, polo, escola, turma_fora, outro_polo))
            cur.execute("INSERT INTO usuarios VALUES (%s, 'Maria', 'Silva', 'maria@example.test')", (usuario,))
            cur.execute("INSERT INTO alunos VALUES (%s, %s, '123')", (aluno, usuario))
            cur.execute("INSERT INTO turma_alunos VALUES (%s, %s, 'ativo')", (turma, aluno))
            cur.execute("INSERT INTO professor_disciplina_vinculos VALUES (%s, %s)", (professor, disciplina))
            cur.execute(
                "INSERT INTO professor_disciplinas VALUES (%s, %s, %s, true), (%s, %s, %s, true), (%s, %s, %s, true)",
                (professor, disciplina, turma, professor, segunda, turma, professor, disciplina, turma_fora),
            )
            cur.execute(
                "INSERT INTO professor_disciplinas VALUES (%s, %s, NULL, true), (%s, %s, NULL, true)",
                (professor, disciplina, professor, segunda),
            )

            @contextmanager
            def cursor_real():
                with conn.cursor(cursor_factory=RealDictCursor) as db_cursor:
                    yield db_cursor

            monkeypatch.setattr(professores_repository, "get_db_cursor", cursor_real)
            repo = professores_repository.PostgresProfessoresRepository()
            assert len(repo.list_disciplinas_cadastro(professor)) == 2
            rows = repo.list_turmas_alunos(professor, polo, None)
            assert len(rows) == 1
            assert rows[0]["aluno_id"] == aluno
            assert rows[0]["aluno_nome"] == "Maria Silva"
            assert len(repo.list_turmas_alunos(professor, None, None)) == 2

            concorrente, d1, d2 = [str(uuid.uuid4()) for _ in range(3)]
            cur.execute("INSERT INTO professores VALUES (%s, 0, 0)", (concorrente,))
            cur.execute("INSERT INTO disciplinas (id, carga_horaria, qtd_aulas_prevista) VALUES (%s, 20, 2), (%s, 30, 3)", (d1, d2))
            primeira = psycopg2.connect(dsn)
            segunda_conn = psycopg2.connect(dsn)
            try:
                for connection in (primeira, segunda_conn):
                    with connection.cursor() as c:
                        c.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                with primeira.cursor() as c:
                    c.execute("INSERT INTO professor_disciplina_vinculos VALUES (%s, %s)", (concorrente, d1))
                iniciou = Event()

                def inserir_segundo():
                    with segunda_conn.cursor() as c:
                        iniciou.set()
                        c.execute("INSERT INTO professor_disciplina_vinculos VALUES (%s, %s)", (concorrente, d2))
                    segunda_conn.commit()

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(inserir_segundo)
                    assert iniciou.wait(5)
                    bloqueado = False
                    try:
                        limite = time.monotonic() + 5
                        while time.monotonic() < limite and not bloqueado:
                            cur.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", (segunda_conn.get_backend_pid(),))
                            bloqueado = cur.fetchone()[0]
                            if not bloqueado:
                                time.sleep(0.02)
                    finally:
                        primeira.commit()
                    future.result(timeout=10)
                    assert bloqueado
                assert totais(concorrente) == (50, 5)
            finally:
                primeira.close()
                segunda_conn.close()
    finally:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        conn.close()
