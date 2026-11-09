from __future__ import annotations

from contextlib import contextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.modules.alunos import perfil as perfil_module
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository


class ProfileDatabase:
    def __init__(self):
        self.users = {
            "aluno-1": {
                "id": "aluno-1",
                "nome": "Ana",
                "sobrenome": "Aluna",
                "email": "ana@example.com",
                "telefone": None,
                "celular": "11999990000",
                "cep": None,
                "logradouro": None,
                "numero": None,
                "complemento": None,
                "bairro": None,
                "cidade": None,
                "uf": None,
            },
            "aluno-2": {
                "id": "aluno-2",
                "nome": "Bia",
                "sobrenome": "Estudante",
                "email": "bia@example.com",
            },
        }
        self.audit_logs = []
        self.cursor = self.Cursor(self)

    class Cursor:
        def __init__(self, database):
            self.database = database
            self.result = None

        def execute(self, sql, params=()):
            query = " ".join(sql.split()).lower()
            if query.startswith("select id, nome, sobrenome, email"):
                self.result = self.database.users.get(params[0])
            elif query.startswith("select id from usuarios"):
                self.result = next(
                    (
                        {"id": user_id}
                        for user_id, user in self.database.users.items()
                        if user_id != params[1]
                        and (user.get("email") or "").lower() == params[0].lower()
                    ),
                    None,
                )
            elif query.startswith("update usuarios"):
                keys = (
                    "email",
                    "telefone",
                    "celular",
                    "cep",
                    "logradouro",
                    "numero",
                    "complemento",
                    "bairro",
                    "cidade",
                    "uf",
                )
                user = self.database.users.get(params[-1])
                if user:
                    user.update(dict(zip(keys, params[:-1])))
                self.result = user
            elif query.startswith("insert into logs_auditoria"):
                self.database.audit_logs.append(params)
                self.result = None
            else:
                raise AssertionError(f"Consulta não esperada: {query}")

        def fetchone(self):
            result = self.result
            self.result = None
            return result

    @contextmanager
    def cursor_context(self):
        yield self.cursor


@pytest.fixture
def profile_database(monkeypatch):
    database = ProfileDatabase()
    monkeypatch.setattr(perfil_module, "get_db_cursor", database.cursor_context)
    return database


@pytest.fixture
def auth_repository():
    repository = InMemoryAuthRepository()
    repository.usuarios["aluno-1"] = {
        "id": "aluno-1",
        "nome": "Ana",
        "sobrenome": "Aluna",
        "email": "ana@example.com",
        "status": "ativo",
        "perfil_id": "p-aluno",
    }
    repository.usuarios["aluno-2"] = {
        "id": "aluno-2",
        "nome": "Bia",
        "email": "bia@example.com",
        "status": "ativo",
        "perfil_id": "p-aluno",
    }
    repository.usuarios["admin-1"] = {
        "id": "admin-1",
        "nome": "Admin",
        "email": "admin@example.com",
        "status": "ativo",
        "perfil_id": "p-admin",
    }
    set_auth_repository(repository)
    return repository


@pytest_asyncio.fixture
async def client(auth_repository, profile_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


def _headers(user_id: str, role: str) -> dict[str, str]:
    token = create_access_token({"sub": user_id, "perfil": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_student_reads_only_own_profile(client):
    response = await client.get(
        "/alunos/meu-perfil",
        headers=_headers("aluno-1", "aluno"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == "aluno-1"
    assert response.json()["nome"] == "Ana"
    assert response.json()["endereco"]["cep"] is None


@pytest.mark.asyncio
async def test_student_updates_email_contacts_and_address(client, profile_database):
    response = await client.put(
        "/alunos/meu-perfil",
        headers=_headers("aluno-1", "aluno"),
        json={
            "email": " ANA.NOVA@EXAMPLE.COM ",
            "telefone": " 1133334444 ",
            "celular": " ",
            "cep": "01000-000",
            "logradouro": "Rua Central",
            "numero": "42",
            "complemento": "Casa 2",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "uf": "sp",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ana.nova@example.com"
    assert body["telefone"] == "1133334444"
    assert body["celular"] is None
    assert body["endereco"]["logradouro"] == "Rua Central"
    assert body["endereco"]["uf"] == "SP"
    assert profile_database.users["aluno-1"]["email"] == "ana.nova@example.com"
    assert len(profile_database.audit_logs) == 1


@pytest.mark.asyncio
async def test_student_cannot_use_another_users_email(client, profile_database):
    response = await client.put(
        "/alunos/meu-perfil",
        headers=_headers("aluno-1", "aluno"),
        json={"email": "BIA@EXAMPLE.COM"},
    )

    assert response.status_code == 409
    assert profile_database.users["aluno-1"]["email"] == "ana@example.com"
    assert not profile_database.audit_logs


@pytest.mark.asyncio
async def test_profile_rejects_fields_outside_allowed_self_service(client):
    response = await client.put(
        "/alunos/meu-perfil",
        headers=_headers("aluno-1", "aluno"),
        json={"email": "ana@example.com", "status": "inativo"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_student_cannot_access_student_profile(client):
    response = await client.get(
        "/alunos/meu-perfil",
        headers=_headers("admin-1", "admin"),
    )

    assert response.status_code == 403
