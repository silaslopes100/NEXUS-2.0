from __future__ import annotations

import io
from contextlib import contextmanager
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.security import create_access_token
from app.main import app
from app.modules.alunos import perfil as perfil_module
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository

admin_router_module = import_module("app.modules.admin.router")


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
                "foto_url": None,
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
            elif query.startswith("select foto_url from usuarios"):
                user = self.database.users.get(params[0])
                self.result = {"foto_url": user.get("foto_url")} if user else None
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
                if "set foto_url" in query:
                    user = self.database.users.get(params[1])
                    if user:
                        user["foto_url"] = params[0]
                else:
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


def _image_bytes(image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (4, 4), color="blue")
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


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
            "telefone": " (11) 93333-4444 ",
            "celular": " ",
            "cep": " 01000-000 ",
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
    assert body["telefone"] == "11933334444"
    assert body["celular"] is None
    assert body["endereco"]["logradouro"] == "Rua Central"
    assert body["endereco"]["cep"] == "01000000"
    assert body["endereco"]["uf"] == "SP"
    assert profile_database.users["aluno-1"]["email"] == "ana.nova@example.com"
    assert profile_database.users["aluno-1"]["telefone"] == "11933334444"
    assert profile_database.users["aluno-1"]["cep"] == "01000000"
    assert len(profile_database.audit_logs) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "expected_detail"),
    [
        ("telefone", "(11) 3333-4444", "O telefone deve conter 11 dígitos"),
        ("celular", "(11) 99999-123", "O celular deve conter 11 dígitos"),
        ("cep", "01000-00", "O CEP deve conter 8 dígitos"),
    ],
)
async def test_profile_update_rejects_contact_fields_with_wrong_digit_count(
    client, profile_database, field, value, expected_detail
):
    response = await client.put(
        "/alunos/meu-perfil",
        headers=_headers("aluno-1", "aluno"),
        json={"email": "ana@example.com", field: value},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail
    assert not profile_database.audit_logs


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("image_format", "media_type", "extension"),
    [
        ("JPEG", "image/jpeg", "jpg"),
        ("PNG", "image/png", "png"),
        ("WEBP", "image/webp", "webp"),
    ],
)
async def test_student_uploads_and_reads_own_profile_photo(
    client, profile_database, monkeypatch, tmp_path, image_format, media_type, extension
):
    monkeypatch.setattr(perfil_module, "PHOTO_DIRECTORY", tmp_path)
    headers = _headers("aluno-1", "aluno")

    upload_response = await client.post(
        "/alunos/meu-perfil/foto",
        headers=headers,
        files={"foto": (f"avatar.{extension}", _image_bytes(image_format), media_type)},
    )

    assert upload_response.status_code == 200
    photo_url = upload_response.json()["foto_url"]
    assert photo_url.startswith("/alunos/meu-perfil/foto?v=")
    stored_filename = profile_database.users["aluno-1"]["foto_url"]
    assert (tmp_path / stored_filename).is_file()

    profile_response = await client.get("/alunos/meu-perfil", headers=headers)
    assert profile_response.json()["foto_url"] == photo_url

    contact_update_response = await client.put(
        "/alunos/meu-perfil",
        headers=headers,
        json={"email": "ana@example.com", "telefone": "11999990000"},
    )
    assert contact_update_response.status_code == 200
    assert contact_update_response.json()["foto_url"] == photo_url

    photo_response = await client.get("/alunos/meu-perfil/foto", headers=headers)
    assert photo_response.status_code == 200
    assert photo_response.headers["content-type"] == media_type
    assert Image.open(io.BytesIO(photo_response.content)).format == image_format
    assert photo_response.headers["cache-control"] == "private, no-store"

    other_user_response = await client.get(
        "/alunos/meu-perfil/foto",
        headers=_headers("aluno-2", "aluno"),
    )
    assert other_user_response.status_code == 404


@pytest.mark.asyncio
async def test_profile_photo_helpers_use_private_vercel_blob(monkeypatch):
    put_blob = AsyncMock()
    get_blob = AsyncMock(return_value=SimpleNamespace(body=b"processed-image"))
    delete_blob = AsyncMock()
    monkeypatch.setattr(perfil_module, "_uses_blob_storage", lambda: True)
    monkeypatch.setattr(perfil_module.blob, "put_blob", put_blob)
    monkeypatch.setattr(perfil_module.blob, "get_blob", get_blob)
    monkeypatch.setattr(perfil_module.blob, "delete_blob", delete_blob)

    filename = await perfil_module._write_photo(b"processed-image", "png")
    pathname = f"profile_photos/{filename}"

    put_blob.assert_awaited_once_with(
        pathname,
        b"processed-image",
        access="private",
        content_type="image/png",
    )
    assert await perfil_module._read_photo(filename) == b"processed-image"
    get_blob.assert_awaited_once_with(pathname, access="private")
    await perfil_module._remove_photo(filename)
    delete_blob.assert_awaited_once_with(pathname)


@pytest.mark.asyncio
async def test_admin_and_student_share_the_same_profile_photo(
    client, profile_database, monkeypatch, tmp_path
):
    monkeypatch.setattr(perfil_module, "PHOTO_DIRECTORY", tmp_path)
    monkeypatch.setattr(admin_router_module, "get_db_cursor", profile_database.cursor_context)
    student_headers = _headers("aluno-1", "aluno")
    admin_headers = _headers("admin-1", "admin")

    student_upload = await client.post(
        "/alunos/meu-perfil/foto",
        headers=student_headers,
        files={"foto": ("aluno.png", _image_bytes(), "image/png")},
    )
    assert student_upload.status_code == 200
    student_filename = profile_database.users["aluno-1"]["foto_url"]

    admin_read = await client.get(
        "/admin/usuarios/aluno-1/foto",
        headers=admin_headers,
    )
    assert admin_read.status_code == 200
    assert Image.open(io.BytesIO(admin_read.content)).format == "PNG"

    admin_upload = await client.post(
        "/admin/usuarios/aluno-1/foto",
        headers=admin_headers,
        files={"foto": ("admin.png", _image_bytes("PNG"), "image/png")},
    )
    assert admin_upload.status_code == 200
    admin_filename = profile_database.users["aluno-1"]["foto_url"]
    assert admin_filename != student_filename
    assert not (tmp_path / student_filename).exists()

    student_read = await client.get(
        "/alunos/meu-perfil/foto",
        headers=student_headers,
    )
    assert student_read.status_code == 200
    assert Image.open(io.BytesIO(student_read.content)).format == "PNG"


@pytest.mark.asyncio
async def test_student_photo_upload_rejects_unsupported_and_invalid_images(client, monkeypatch, tmp_path):
    monkeypatch.setattr(perfil_module, "PHOTO_DIRECTORY", tmp_path)
    headers = _headers("aluno-1", "aluno")

    unsupported = await client.post(
        "/alunos/meu-perfil/foto",
        headers=headers,
        files={"foto": ("avatar.gif", b"GIF89a", "image/gif")},
    )
    invalid_image = await client.post(
        "/alunos/meu-perfil/foto",
        headers=headers,
        files={"foto": ("avatar.png", b"not an image", "image/png")},
    )
    mismatched_format = await client.post(
        "/alunos/meu-perfil/foto",
        headers=headers,
        files={"foto": ("avatar.png", b"\xff\xd8\xff" + b"x" * 20, "image/png")},
    )

    assert unsupported.status_code == 415
    assert invalid_image.status_code == 415
    assert mismatched_format.status_code == 415
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_student_photo_upload_rejects_files_over_four_megabytes(client):
    response = await client.post(
        "/alunos/meu-perfil/foto",
        headers=_headers("aluno-1", "aluno"),
        files={"foto": ("avatar.png", b"x" * (perfil_module.MAX_PHOTO_BYTES + 1), "image/png")},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_student_photo_replacement_removes_old_file(client, profile_database, monkeypatch, tmp_path):
    monkeypatch.setattr(perfil_module, "PHOTO_DIRECTORY", tmp_path)
    headers = _headers("aluno-1", "aluno")

    for _ in range(2):
        response = await client.post(
            "/alunos/meu-perfil/foto",
            headers=headers,
            files={"foto": ("avatar.png", _image_bytes(), "image/png")},
        )
        assert response.status_code == 200

    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].name == profile_database.users["aluno-1"]["foto_url"]


@pytest.mark.asyncio
async def test_profile_photo_upload_requires_authenticated_student(client):
    response = await client.post(
        "/alunos/meu-perfil/foto",
        files={"foto": ("avatar.png", _image_bytes(), "image/png")},
    )

    assert response.status_code == 401
