from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository


@pytest.fixture
def memory_repo() -> InMemoryAuthRepository:
    repo = InMemoryAuthRepository()

    repo.usuarios["admin-1"] = {
        "id": "admin-1",
        "nome": "Admin",
        "sobrenome": "Nexus",
        "email": "admin@nexus.com.br",
        "cpf": "11111111111",
        "senha_hash": hash_password("admin123"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-admin",
        "polo_id": None,
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
    }

    repo.usuarios["polo-1"] = {
        "id": "polo-1",
        "nome": "Maria",
        "sobrenome": "Polo",
        "email": "polo1@nexus.com.br",
        "cpf": "22222222222",
        "senha_hash": hash_password("polo123"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-polo",
        "polo_id": "polo-uuid-1",
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
    }

    repo.usuarios["polo-2"] = {
        "id": "polo-2",
        "nome": "Joao",
        "sobrenome": "Polo2",
        "email": "polo2@nexus.com.br",
        "cpf": "33333333333",
        "senha_hash": hash_password("polo456"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-polo",
        "polo_id": "polo-uuid-2",
        "escola_id": None,
        "telefone": None,
        "celular": None,
        "foto_url": None,
        "ultimo_login_em": None,
    }

    set_auth_repository(repo)
    return repo


@pytest_asyncio.fixture
async def client(memory_repo: InMemoryAuthRepository):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _token(user_id: str, perfil: str) -> str:
    return create_access_token({
        "sub": user_id,
        "email": f"{user_id}@nexus.com.br",
        "perfil": perfil,
        "permissoes": [],
    })


@pytest.mark.asyncio
async def test_create_polo_and_coordenador(client: AsyncClient):
    admin_token = _token("admin-1", "admin")

    payload = {
        "nome": "Polo Central",
        "responsavel_nome": "Carlos Responsavel",
        "responsavel_cpf": "12345678900",
        "responsavel_email": "responsavel@polo.com",
        "endereco_completo": {
            "logradouro": "Rua A",
            "numero": "100",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "01000-000",
        },
    }

    res = await client.post("/polos", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 201, res.text
    polo = res.json()
    assert polo["nome"] == "Polo Central"
    assert polo["status"] == "ativo"

    coord_res = await client.post(
        f"/polos/{polo['id']}/coordenador",
        json={
            "nome": "João Coordenador",
            "cpf": "98765432100",
            "email": "coord@polo.com",
            "senha": "senha_segura_123",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert coord_res.status_code == 201, coord_res.text
    coord = coord_res.json()
    assert coord["perfil"] == "polo"
    assert coord["polo_id"] == polo["id"]
    assert "senha" not in coord
    assert "senha_hash" not in coord


@pytest.mark.asyncio
async def test_resumo_polo_restrito_a_polo_dono(client: AsyncClient, memory_repo: InMemoryAuthRepository):
    token = _token("polo-1", "polo")
    # criar escola vinculada ao polo-1
    admin_token = _token("admin-1", "admin")
    polo_res = await client.post(
        "/polos",
        json={
            "nome": "Polo A",
            "responsavel_nome": "Resp A",
            "responsavel_cpf": "55555555555",
            "responsavel_email": "resp_a@polo.com",
            "endereco_completo": {
                "logradouro": "Rua A",
                "numero": "10",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "02000-000",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    polo_id = polo_res.json()["id"]
    memory_repo.usuarios["polo-1"]["polo_id"] = polo_id
    await client.post(
        f"/polos/{polo_id}/escolas",
        json={
            "nome": "Escola A",
            "responsavel_nome": "Diretor A",
            "responsavel_cpf": "44444444444",
            "responsavel_email": "diretor_a@escola.com",
            "endereco_completo": {
                "logradouro": "Rua B",
                "numero": "20",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "03000-000",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    res = await client.get(f"/polos/{polo_id}/resumo", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["polo_id"] == polo_id
    assert body["total_escolas_vinculadas"] >= 1
    assert "materias_em_estoque" in body

    other_token = _token("polo-2", "polo")
    forbidden = await client.get(f"/polos/{polo_id}/resumo", headers={"Authorization": f"Bearer {other_token}"})
    assert forbidden.status_code == 403
