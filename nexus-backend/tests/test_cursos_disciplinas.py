from __future__ import annotations

from contextlib import contextmanager
import uuid

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.modules import cursos_disciplinas
from app.modules import turmas as turmas_module
from app.modules.auth.schemas import PerfilResponse, UserResponse


def _course_payload(disciplina_ids: list[uuid.UUID]):
    return cursos_disciplinas.CursoCreateSchema(
        nome="Curso de teste",
        descricao="Descrição do curso",
        modalidade="hibrido",
        carga_horaria_total=120,
        semestres=2,
        status="ativo",
        nivel_academico="bacharelado",
        disciplina_ids=disciplina_ids,
    )


@pytest.mark.asyncio
async def test_create_course_updates_multiple_disciplines_in_same_transaction(monkeypatch):
    discipline_ids = [
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
        uuid.UUID("00000000-0000-0000-0000-000000000002"),
    ]

    class Cursor:
        def __init__(self):
            self.executions = []

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchall(self):
            return [{"id": discipline_id} for discipline_id in discipline_ids]

    class CursorContext:
        def __init__(self, cursor):
            self.cursor = cursor
            self.committed = False
            self.rolled_back = False

        def __enter__(self):
            return self.cursor

        def __exit__(self, exc_type, exc_value, traceback):
            self.rolled_back = exc_type is not None
            self.committed = exc_type is None
            return False

    cursor = Cursor()
    context = CursorContext(cursor)
    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", lambda: context)

    course = await cursos_disciplinas.create_curso(_course_payload(discipline_ids))

    assert len(cursor.executions) == 2
    insert_sql, insert_params = cursor.executions[0]
    update_sql, update_params = cursor.executions[1]
    assert insert_sql.startswith("\n            INSERT INTO cursos")
    assert "UPDATE disciplinas" in update_sql
    assert update_params == (course["id"], [str(item) for item in discipline_ids])
    assert len(insert_params) == 8
    assert context.committed
    assert not context.rolled_back


@pytest.mark.asyncio
async def test_create_course_rolls_back_if_discipline_id_is_missing(monkeypatch):
    discipline_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    class Cursor:
        def __init__(self):
            self.executions = []

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchall(self):
            return []

    class CursorContext:
        def __init__(self):
            self.cursor = Cursor()
            self.rolled_back = False

        def __enter__(self):
            return self.cursor

        def __exit__(self, exc_type, exc_value, traceback):
            self.rolled_back = exc_type is not None
            return False

    context = CursorContext()
    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", lambda: context)

    with pytest.raises(HTTPException) as exc_info:
        await cursos_disciplinas.create_curso(_course_payload([discipline_id]))

    assert exc_info.value.status_code == 404
    assert len(context.cursor.executions) == 2
    assert context.rolled_back


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("has_references", "expected_status", "delete_expected"),
    [(True, 409, False), (False, None, True)],
)
async def test_delete_disciplina_checks_database_references(
    monkeypatch,
    has_references: bool,
    expected_status: int | None,
    delete_expected: bool,
):
    disciplina_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    class Cursor:
        def __init__(self):
            self.executions = []
            self.fetchone_calls = 0

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchone(self):
            self.fetchone_calls += 1
            if self.fetchone_calls == 1:
                return {"id": disciplina_id}
            return {"em_uso": has_references}

    cursor = Cursor()

    @contextmanager
    def database_cursor():
        yield cursor

    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", database_cursor)

    if expected_status:
        with pytest.raises(HTTPException) as exc_info:
            await cursos_disciplinas.delete_disciplina(disciplina_id)
        assert exc_info.value.status_code == expected_status
    else:
        response = await cursos_disciplinas.delete_disciplina(disciplina_id)
        assert response.status_code == 204

    assert len(cursor.executions) == (2 if has_references else 3)
    if has_references:
        reference_sql, params = cursor.executions[1]
        assert "professor_disciplinas" in reference_sql
        assert "disciplina_conteudos" in reference_sql
        assert params == (str(disciplina_id),) * 10
    assert (cursor.executions[-1][0].startswith("DELETE")) is delete_expected


@pytest.mark.asyncio
async def test_disciplina_database_errors_are_not_hidden(monkeypatch):
    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")

    def fail_database():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", fail_database)

    with pytest.raises(RuntimeError, match="database unavailable"):
        await cursos_disciplinas.list_disciplinas()


@pytest.mark.asyncio
async def test_list_courses_paginates_and_searches_all_results(monkeypatch):
    courses = {
        f"course-{index:02}": {
            "id": f"course-{index:02}",
            "nome": f"Curso {index:02}",
            "descricao": "Formação em educação" if index == 17 else "Outro curso",
            "modalidade": "ead",
            "carga_horaria_total": 120,
            "semestres": 2,
            "status": "ativo",
            "nivel_academico": "bacharelado",
        }
        for index in range(23)
    }
    monkeypatch.setattr(settings, "PG_DSN", "")
    monkeypatch.setattr(cursos_disciplinas, "_cursos_db", courses)

    page = await cursos_disciplinas.list_cursos_paginados(
        q=None, limit=10, offset=10
    )
    assert page["total"] == 23
    assert page["limit"] == 10
    assert page["offset"] == 10
    assert len(page["items"]) == 10
    assert [course["nome"] for course in page["items"]] == [
        f"Curso {index:02}" for index in range(10, 20)
    ]

    searched = await cursos_disciplinas.list_cursos_paginados(
        q="  EDUCAÇÃO  ",
        limit=10,
        offset=0,
    )
    assert searched["total"] == 1
    assert [course["id"] for course in searched["items"]] == ["course-17"]


@pytest.mark.asyncio
async def test_list_courses_postgres_uses_fixed_number_of_queries(monkeypatch):
    class Cursor:
        def __init__(self):
            self.executions = []

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchone(self):
            return {"total": 250}

        def fetchall(self):
            return [{"id": "course-1", "nome": "Curso 1"}]

    class CursorContext:
        def __init__(self, cursor):
            self.cursor = cursor

        def __enter__(self):
            return self.cursor

        def __exit__(self, *exc):
            return False

    cursor = Cursor()
    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(
        cursos_disciplinas,
        "get_db_cursor",
        lambda: CursorContext(cursor),
    )

    page = await cursos_disciplinas.list_cursos_paginados(
        q="curso",
        limit=10,
        offset=20,
    )

    assert page["total"] == 250
    assert len(cursor.executions) == 2
    assert "COUNT(*)" in cursor.executions[0][0]
    assert "ORDER BY nome, id" in cursor.executions[1][0]
    assert cursor.executions[1][1] == ("%curso%", "%curso%", 10, 20)


@pytest.mark.asyncio
async def test_course_details_uses_one_connection_for_disciplines_and_classes(monkeypatch):
    course_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    class Cursor:
        def __init__(self):
            self.executions = []

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchall(self):
            if "FROM disciplinas" in self.executions[-1][0]:
                return [{"id": "discipline-1", "nome": "Disciplina"}]
            return [{"id": "class-1", "nome": "Turma"}]

    class CursorContext:
        def __init__(self, cursor):
            self.cursor = cursor
            self.entries = 0

        def __enter__(self):
            self.entries += 1
            return self.cursor

        def __exit__(self, *exc):
            return False

    cursor = Cursor()
    context = CursorContext(cursor)
    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(turmas_module, "get_db_cursor", lambda: context)
    user = UserResponse(
        id="admin-1",
        nome="Admin",
        perfil=PerfilResponse(nome="admin"),
    )

    details = await turmas_module.get_detalhes_curso(course_id, user)

    assert context.entries == 1
    assert len(cursor.executions) == 2
    assert details.disciplinas[0]["id"] == "discipline-1"
    assert details.turmas[0].id == "class-1"
