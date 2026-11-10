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
        assert params == (str(disciplina_id),) * 11
    assert (cursor.executions[-1][0].startswith("DELETE")) is delete_expected


@pytest.mark.asyncio
async def test_list_professores_vinculados_a_disciplina_inclui_dados_do_usuario_e_unidades(
    monkeypatch,
):
    disciplina_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    professores = [
        {
            "professor_id": "00000000-0000-0000-0000-000000000002",
            "usuario_id": "00000000-0000-0000-0000-000000000003",
            "nome": "Ana Souza",
            "email": "ana@example.com",
            "polo_nome": "Polo Central",
            "escola_nome": "Escola Norte",
            "valor_hora_aula": 120.5,
            "quantidade_aulas": 40,
        },
        {
            "professor_id": "00000000-0000-0000-0000-000000000004",
            "usuario_id": "00000000-0000-0000-0000-000000000005",
            "nome": "Bruno Lima",
            "email": "bruno@example.com",
            "polo_nome": None,
            "escola_nome": None,
            "valor_hora_aula": None,
            "quantidade_aulas": 0,
        },
    ]

    class Cursor:
        def __init__(self):
            self.executions = []
            self.fetchone_calls = 0

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchone(self):
            self.fetchone_calls += 1
            return {"id": disciplina_id}

        def fetchall(self):
            return professores

    cursor = Cursor()

    @contextmanager
    def database_cursor():
        yield cursor

    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", database_cursor)

    result = await cursos_disciplinas.list_professores_disciplina(disciplina_id)

    assert len(result) == 2
    assert result[0] == professores[0]
    assert result[1]["nome"] == "Bruno Lima"
    assert result[1]["quantidade_aulas"] == 0
    query, params = cursor.executions[1]
    assert "professor_disciplina_vinculos" in query
    assert "jsonb_array_elements_text" in query
    assert params == (str(disciplina_id), str(disciplina_id))


@pytest.mark.asyncio
async def test_list_professores_disciplina_retorna_404_quando_disciplina_nao_existe(monkeypatch):
    disciplina_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    class Cursor:
        def __init__(self):
            self.executions = []

        def execute(self, sql, params=()):
            self.executions.append((sql, params))

        def fetchone(self):
            return None

    cursor = Cursor()

    @contextmanager
    def database_cursor():
        yield cursor

    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", database_cursor)

    with pytest.raises(HTTPException) as exc_info:
        await cursos_disciplinas.list_professores_disciplina(disciplina_id)

    assert exc_info.value.status_code == 404
    assert len(cursor.executions) == 1


COURSE_ID = uuid.UUID("00000000-0000-0000-0000-00000000000a")


def _course_update_payload(disciplina_ids=None, **overrides):
    values = {
        "nome": "Curso editado",
        "descricao": "Descrição editada",
        "modalidade": "ead",
        "carga_horaria_total": 200,
        "semestres": 4,
        "status": "ativo",
        "nivel_academico": "licenciatura",
        "disciplina_ids": disciplina_ids,
        **overrides,
    }
    return cursos_disciplinas.CursoUpdateSchema(**values)


class _CourseCursor:
    """Cursor falso: responde fetchone/fetchall com as filas informadas."""

    def __init__(self, fetchone_rows=(), fetchall_rows=()):
        self.executions = []
        self.fetchone_rows = list(fetchone_rows)
        self.fetchall_rows = list(fetchall_rows)

    def execute(self, sql, params=()):
        self.executions.append((sql, params))

    def fetchone(self):
        return self.fetchone_rows.pop(0) if self.fetchone_rows else None

    def fetchall(self):
        return self.fetchall_rows


def _use_course_cursor(monkeypatch, cursor):
    @contextmanager
    def database_cursor():
        yield cursor

    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(cursos_disciplinas, "get_db_cursor", database_cursor)


@pytest.mark.asyncio
async def test_update_course_replaces_discipline_links(monkeypatch):
    discipline_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    cursor = _CourseCursor(
        fetchone_rows=[{"id": COURSE_ID, "nome": "Curso editado"}],
        fetchall_rows=[{"id": discipline_id}],
    )
    _use_course_cursor(monkeypatch, cursor)

    course = await cursos_disciplinas.update_curso(COURSE_ID, _course_update_payload([discipline_id]))

    assert course["nome"] == "Curso editado"
    assert len(cursor.executions) == 3
    assert "UPDATE cursos" in cursor.executions[0][0]
    assert "curso_id = NULL" in cursor.executions[1][0]
    assert cursor.executions[1][1] == (str(COURSE_ID), [str(discipline_id)])
    assert cursor.executions[2][1] == (str(COURSE_ID), [str(discipline_id)])


@pytest.mark.asyncio
async def test_update_course_without_discipline_ids_keeps_links(monkeypatch):
    cursor = _CourseCursor(fetchone_rows=[{"id": COURSE_ID, "nome": "Curso editado"}])
    _use_course_cursor(monkeypatch, cursor)

    await cursos_disciplinas.update_curso(COURSE_ID, _course_update_payload())

    assert len(cursor.executions) == 1


@pytest.mark.asyncio
async def test_update_course_with_empty_list_unlinks_all_disciplines(monkeypatch):
    cursor = _CourseCursor(fetchone_rows=[{"id": COURSE_ID, "nome": "Curso editado"}])
    _use_course_cursor(monkeypatch, cursor)

    await cursos_disciplinas.update_curso(COURSE_ID, _course_update_payload([]))

    assert len(cursor.executions) == 2
    assert "curso_id = NULL" in cursor.executions[1][0]


@pytest.mark.asyncio
async def test_update_missing_course_returns_404(monkeypatch):
    cursor = _CourseCursor()
    _use_course_cursor(monkeypatch, cursor)

    with pytest.raises(HTTPException) as exc_info:
        await cursos_disciplinas.update_curso(COURSE_ID, _course_update_payload([]))

    assert exc_info.value.status_code == 404
    assert len(cursor.executions) == 1


@pytest.mark.asyncio
async def test_update_course_preserves_legacy_values_in_memory(monkeypatch):
    uid = str(COURSE_ID)
    courses = {uid: {"id": uid, "nome": "Legado", "modalidade": "polo", "status": "inativo"}}
    disciplines = {
        "removida": {"id": "removida", "curso_id": uid},
        "de-outro-curso": {"id": "de-outro-curso", "curso_id": "outro"},
    }
    monkeypatch.setattr(settings, "PG_DSN", "")
    monkeypatch.setattr(cursos_disciplinas, "_cursos_db", courses)
    monkeypatch.setattr(cursos_disciplinas, "_disciplinas_db", disciplines)

    course = await cursos_disciplinas.update_curso(
        COURSE_ID,
        _course_update_payload([], modalidade="polo", status="inativo"),
    )

    assert course["modalidade"] == "polo"
    assert course["status"] == "inativo"
    assert disciplines["removida"]["curso_id"] is None
    assert disciplines["de-outro-curso"]["curso_id"] == "outro"


@pytest.mark.asyncio
@pytest.mark.parametrize(("has_references", "delete_expected"), [(True, False), (False, True)])
async def test_delete_course_checks_database_references(
    monkeypatch,
    has_references: bool,
    delete_expected: bool,
):
    cursor = _CourseCursor(fetchone_rows=[{"id": COURSE_ID}, {"em_uso": has_references}])
    _use_course_cursor(monkeypatch, cursor)

    if has_references:
        with pytest.raises(HTTPException) as exc_info:
            await cursos_disciplinas.delete_curso(COURSE_ID)
        assert exc_info.value.status_code == 409
    else:
        response = await cursos_disciplinas.delete_curso(COURSE_ID)
        assert response.status_code == 204

    assert "FOR UPDATE" in cursor.executions[0][0]
    reference_sql, params = cursor.executions[1]
    for table in ("disciplinas", "turmas", "calendarios_oficiais", "matriculas_ead", "certificados"):
        assert f"FROM {table} " in reference_sql
    assert params == (str(COURSE_ID),) * 5
    assert cursor.executions[-1][0].startswith("DELETE") is delete_expected


@pytest.mark.asyncio
async def test_delete_missing_course_returns_404(monkeypatch):
    cursor = _CourseCursor()
    _use_course_cursor(monkeypatch, cursor)

    with pytest.raises(HTTPException) as exc_info:
        await cursos_disciplinas.delete_curso(COURSE_ID)

    assert exc_info.value.status_code == 404
    assert len(cursor.executions) == 1


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
