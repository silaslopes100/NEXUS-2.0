"""Migracao exercitada apenas em um PostgreSQL de teste explicitamente configurado."""
from __future__ import annotations

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import psycopg2
import pytest
from fastapi import HTTPException
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from app.modules.professores.repository import PostgresProfessoresRepository

pytestmark = pytest.mark.skipif(
    not os.environ.get("NEXUS_TEST_POSTGRES_DSN"),
    reason="NEXUS_TEST_POSTGRES_DSN não configurado para banco de teste isolado",
)

MIGRATIONS = Path(__file__).resolve().parents[1] / "scripts" / "migrations"


@pytest.fixture
def banco():
    conn = psycopg2.connect(os.environ["NEXUS_TEST_POSTGRES_DSN"])
    conn.autocommit = True
    schema = f"teste_unificar_{uuid.uuid4().hex}"
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        cur.execute("""
            CREATE TABLE professores (
                id uuid PRIMARY KEY, horas_totais integer, quantidade_aulas integer
            );
            CREATE TABLE disciplinas (
                id uuid PRIMARY KEY, carga_horaria integer, qtd_aulas_prevista integer
            );
            CREATE TABLE professor_disciplinas (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                professor_id uuid REFERENCES professores(id),
                disciplina_id uuid REFERENCES disciplinas(id),
                turma_id uuid, ativo boolean NOT NULL DEFAULT true,
                criado_em timestamptz DEFAULT now(), atualizado_em timestamptz DEFAULT now(),
                conteudo_programatico text
            );
            CREATE TABLE professor_disciplina_vinculos (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                professor_id uuid NOT NULL REFERENCES professores(id),
                disciplina_id uuid NOT NULL REFERENCES disciplinas(id),
                criado_em timestamptz NOT NULL DEFAULT now(),
                atualizado_em timestamptz NOT NULL DEFAULT now(),
                UNIQUE (professor_id, disciplina_id)
            );
            CREATE TABLE materiais (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                professor_disciplina_id uuid REFERENCES professor_disciplinas(id) ON DELETE CASCADE
            );
        """)
        cur.execute((MIGRATIONS / "013_totais_professores_disciplinas.sql").read_text(encoding="utf-8"))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        conn.close()


def migrar(cur):
    cur.execute((MIGRATIONS / "014_unificar_professor_disciplinas.sql").read_text(encoding="utf-8"))


def test_migracao_preserva_dados_e_sincroniza_totais(banco):
    professor, d1, d2, d3, turma, antigo, academico = [str(uuid.uuid4()) for _ in range(7)]
    with banco.cursor() as cur:
        cur.execute("INSERT INTO professores VALUES (%s, 0, 0)", (professor,))
        cur.execute(
            "INSERT INTO disciplinas VALUES (%s, 40, 10), (%s, 20, 5), (%s, 30, 8)",
            (d1, d2, d3),
        )
        cur.execute(
            "INSERT INTO professor_disciplina_vinculos (professor_id, disciplina_id, criado_em, atualizado_em) "
            "VALUES (%s, %s, '2020-01-01', '2020-02-01'), (%s, %s, '2021-01-01', '2021-02-01')",
            (professor, d1, professor, d2),
        )
        cur.execute(
            "INSERT INTO professor_disciplinas (id, professor_id, disciplina_id, turma_id, ativo, conteudo_programatico) "
            "VALUES (%s, %s, %s, NULL, false, 'preservado'), (%s, %s, %s, %s, true, 'turma'), "
            "(gen_random_uuid(), %s, %s, NULL, true, 'adicional')",
            (antigo, professor, d1, academico, professor, d2, turma, professor, d3),
        )
        cur.execute("INSERT INTO materiais (professor_disciplina_id) VALUES (%s), (%s)", (antigo, academico))
        cur.execute("SELECT * FROM professor_disciplinas ORDER BY id")
        antes = cur.fetchall()
        migrar(cur)
        cur.execute("SELECT * FROM professor_disciplinas WHERE id = ANY(%s::uuid[]) ORDER BY id", ([str(row[0]) for row in antes],))
        assert cur.fetchall() == antes
        cur.execute("SELECT criado_em::date, atualizado_em::date FROM professor_disciplinas WHERE professor_id = %s AND disciplina_id = %s AND turma_id IS NULL", (professor, d2))
        assert tuple(str(value) for value in cur.fetchone()) == ("2021-01-01", "2021-02-01")
        cur.execute("SELECT horas_totais, quantidade_aulas FROM professores WHERE id = %s", (professor,))
        assert cur.fetchone() == (90, 23)
        migrar(cur)
        cur.execute("SELECT count(*) FROM professor_disciplinas")
        assert cur.fetchone()[0] == 4
        cur.execute("DELETE FROM professor_disciplinas WHERE professor_id = %s AND disciplina_id = %s AND turma_id IS NULL", (professor, d2))
        migrar(cur)
        cur.execute("SELECT count(*) FROM professor_disciplinas WHERE disciplina_id = %s AND turma_id IS NULL", (d2,))
        assert cur.fetchone()[0] == 0
        cur.execute("UPDATE disciplinas SET carga_horaria = 50 WHERE id = %s", (d1,))
        cur.execute("SELECT horas_totais, quantidade_aulas FROM professores WHERE id = %s", (professor,))
        assert cur.fetchone() == (80, 18)
        cur.execute("SELECT count(*) FROM professor_disciplina_vinculos")
        assert cur.fetchone()[0] == 2
        cur.execute("SELECT count(*) FROM materiais")
        assert cur.fetchone()[0] == 2

    banco.autocommit = False
    with banco.cursor(cursor_factory=RealDictCursor) as cur:
        with pytest.raises(HTTPException) as exc:
            PostgresProfessoresRepository._sync_disciplina_ids(cur, professor, [d3])
        assert exc.value.status_code == 409
    banco.rollback()
    banco.autocommit = True
    with banco.cursor() as cur:
        cur.execute("SELECT count(*) FROM professor_disciplinas WHERE id IN (%s, %s)", (antigo, academico))
        assert cur.fetchone()[0] == 2
        cur.execute("SELECT id FROM professor_disciplinas WHERE professor_id = %s AND disciplina_id = %s AND turma_id IS NULL", (professor, d3))
        adicional = cur.fetchone()[0]
        cur.execute("DELETE FROM materiais WHERE professor_disciplina_id = %s", (antigo,))

    banco.autocommit = False
    with banco.cursor(cursor_factory=RealDictCursor) as cur:
        PostgresProfessoresRepository._sync_disciplina_ids(cur, professor, [d2, d3])
    banco.commit()
    banco.autocommit = True
    with banco.cursor() as cur:
        cur.execute("SELECT id::text, disciplina_id::text, turma_id::text FROM professor_disciplinas WHERE professor_id = %s", (professor,))
        rows = cur.fetchall()
        assert (str(adicional), d3, None) in rows
        assert (academico, d2, turma) in rows
        assert any(row[1:] == (d2, None) for row in rows)
        assert all(row[0] != antigo for row in rows)


def test_migracao_rejeita_duplicatas_sem_alterar_o_banco(banco):
    professor, disciplina = str(uuid.uuid4()), str(uuid.uuid4())
    with banco.cursor() as cur:
        cur.execute("INSERT INTO professores VALUES (%s, 0, 0)", (professor,))
        cur.execute("INSERT INTO disciplinas VALUES (%s, 10, 2)", (disciplina,))
        cur.execute(
            "INSERT INTO professor_disciplinas (professor_id, disciplina_id) VALUES (%s, %s), (%s, %s)",
            (professor, disciplina, professor, disciplina),
        )
        with pytest.raises(psycopg2.Error, match="duplicados"):
            migrar(cur)
        cur.execute("ROLLBACK")
        cur.execute("SELECT count(*) FROM professor_disciplinas")
        assert cur.fetchone()[0] == 2
        cur.execute("SELECT to_regclass('migracao_professor_disciplinas')")
        assert cur.fetchone()[0] is None


def test_totais_com_escritas_concorrentes_e_mudanca_de_turma(banco):
    professor, d1, d2, turma = [str(uuid.uuid4()) for _ in range(4)]
    with banco.cursor() as cur:
        cur.execute("SELECT current_schema()")
        schema = cur.fetchone()[0]
        cur.execute("INSERT INTO professores VALUES (%s, 0, 0)", (professor,))
        cur.execute("INSERT INTO disciplinas VALUES (%s, 20, 2), (%s, 30, 3)", (d1, d2))
        migrar(cur)

    primeira = psycopg2.connect(os.environ["NEXUS_TEST_POSTGRES_DSN"])
    segunda = psycopg2.connect(os.environ["NEXUS_TEST_POSTGRES_DSN"])
    try:
        for conn in (primeira, segunda):
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        with primeira.cursor() as cur:
            cur.execute("INSERT INTO professor_disciplinas (professor_id, disciplina_id) VALUES (%s, %s)", (professor, d1))
        iniciou = Event()

        def inserir_segundo():
            with segunda.cursor() as cur:
                iniciou.set()
                cur.execute("INSERT INTO professor_disciplinas (professor_id, disciplina_id) VALUES (%s, %s)", (professor, d2))
            segunda.commit()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(inserir_segundo)
            assert iniciou.wait(5)
            bloqueado = False
            try:
                limite = time.monotonic() + 5
                while time.monotonic() < limite and not bloqueado:
                    with banco.cursor() as cur:
                        cur.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", (segunda.get_backend_pid(),))
                        bloqueado = cur.fetchone()[0]
                    if not bloqueado:
                        time.sleep(0.02)
            finally:
                primeira.commit()
            future.result(timeout=10)
            assert bloqueado
    finally:
        primeira.close()
        segunda.close()

    with banco.cursor() as cur:
        cur.execute("SELECT horas_totais, quantidade_aulas FROM professores WHERE id = %s", (professor,))
        assert cur.fetchone() == (50, 5)
        cur.execute("UPDATE professor_disciplinas SET turma_id = %s WHERE professor_id = %s AND disciplina_id = %s", (turma, professor, d1))
        cur.execute("SELECT horas_totais, quantidade_aulas FROM professores WHERE id = %s", (professor,))
        assert cur.fetchone() == (30, 3)
        cur.execute("UPDATE professor_disciplinas SET turma_id = NULL WHERE professor_id = %s AND disciplina_id = %s", (professor, d1))
        cur.execute("SELECT horas_totais, quantidade_aulas FROM professores WHERE id = %s", (professor,))
        assert cur.fetchone() == (50, 5)
