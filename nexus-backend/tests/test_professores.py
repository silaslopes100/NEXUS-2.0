"""Testes do módulo `professores` (NEXUS 2.0) — arquitetura em camadas + InMemoryRepository."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.professores.repository import (
    InMemoryProfessoresRepository,
    set_professores_repository,
)

_PERFIS = {
    "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador"},
    "p-polo": {"id": "p-polo", "nome": "polo", "descricao": "Gestor de Polo"},
    "p-professor": {"id": "p-professor", "nome": "professor", "descricao": "Professor"},
}


@pytest.fixture
def repos():
    auth_repo = InMemoryAuthRepository()
    auth_repo.perfis = dict(_PERFIS)

    professores_repo = InMemoryProfessoresRepository()
    # Em produção os dois repositorios leem a mesma tabela `usuarios`.
    professores_repo.usuarios = auth_repo.usuarios
    professores_repo.polos["polo-1"] = {"id": "polo-1", "nome": "Polo Central"}

    auth_repo.usuarios["admin-1"] = {
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
    }
    auth_repo.usuarios["prof-1"] = {
        "id": "prof-1",
        "nome": "Ana",
        "sobrenome": "Souza",
        "email": "ana.souza@nexus.com.br",
        "cpf": "22222222222",
        "senha_hash": hash_password("prof1234"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-professor",
        "polo_id": "polo-1",
        "escola_id": None,
    }
    auth_repo.usuarios["gestor-1"] = {
        "id": "gestor-1",
        "nome": "Gestor",
        "sobrenome": "Polo",
        "email": "gestor@nexus.com.br",
        "cpf": "33333333333",
        "senha_hash": hash_password("polo1234"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": "p-polo",
        "polo_id": "polo-1",
        "escola_id": None,
    }

    set_auth_repository(auth_repo)
    set_professores_repository(professores_repo)
    return auth_repo, professores_repo


@pytest_asyncio.fixture
async def client(repos):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _token(user_id: str) -> str:
    return create_access_token({"sub": user_id, "tipo": "access"})


def _payload(**overrides):
    payload = {
        "usuario_id": "prof-1",
        "polo_id": "polo-1",
        "escola_id": None,
        "materias": ["Matemática", "Física"],
        "data_inicio": "2026-02-01",
        "quantidade_aulas": 40,
        "horas_totais": 80,
        "valor_hora_aula": 120.5,
        "pix": "ana.souza@nexus.com.br",
        "conteudo_programatico": "Álgebra linear e cinemática.",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_criar_e_listar_professor(client: AsyncClient):
    t_admin = _token("admin-1")

    c_res = await client.post(
        "/professores/",
        json=_payload(),
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert c_res.status_code == 201
    criado = c_res.json()
    assert criado["nome"] == "Ana"
    assert criado["email"] == "ana.souza@nexus.com.br"
    assert criado["polo_nome"] == "Polo Central"
    assert criado["materias"] == ["Matemática", "Física"]
    assert criado["horas_totais"] == 80
    assert criado["status"] == "ativo"

    l_res = await client.get(
        "/professores/?search=ana&disciplina=Física&status=ativo",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert l_res.status_code == 200
    body = l_res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == criado["id"]

    vazio = await client.get(
        "/professores/?search=inexistente",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert vazio.status_code == 200
    assert vazio.json()["total"] == 0


@pytest.mark.asyncio
async def test_atualizar_e_desativar_professor(client: AsyncClient):
    t_admin = _token("admin-1")

    c_res = await client.post(
        "/professores/",
        json=_payload(),
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    professor_id = c_res.json()["id"]

    g_res = await client.get(
        f"/professores/{professor_id}",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert g_res.status_code == 200

    u_res = await client.put(
        f"/professores/{professor_id}",
        json={"materias": ["Química"], "horas_totais": 120, "status": "inativo"},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert u_res.status_code == 200
    atualizado = u_res.json()
    assert atualizado["materias"] == ["Química"]
    assert atualizado["horas_totais"] == 120
    assert atualizado["status"] == "inativo"

    d_res = await client.delete(
        f"/professores/{professor_id}",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert d_res.status_code == 204

    l_res = await client.get(
        "/professores/?status=inativo",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert l_res.status_code == 200
    assert l_res.json()["total"] == 1


@pytest.mark.asyncio
async def test_validacoes_e_permissoes(client: AsyncClient):
    t_admin = _token("admin-1")
    t_gestor = _token("gestor-1")

    # Usuário inexistente
    invalido = await client.post(
        "/professores/",
        json=_payload(usuario_id="nao-existe"),
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert invalido.status_code == 400

    # Vínculo duplicado: o mesmo usuário não pode virar dois professores
    assert (
        await client.post(
            "/professores/",
            json=_payload(),
            headers={"Authorization": f"Bearer {t_admin}"},
        )
    ).status_code == 201
    duplicado = await client.post(
        "/professores/",
        json=_payload(),
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert duplicado.status_code == 400
    assert "vinculado" in duplicado.json()["detail"]

    # Escrita restrita ao administrador
    negado = await client.post(
        "/professores/",
        json=_payload(usuario_id="gestor-1"),
        headers={"Authorization": f"Bearer {t_gestor}"},
    )
    assert negado.status_code == 403

    # Leitura permitida ao gestor de polo (com escopo do próprio polo)
    l_res = await client.get("/professores/", headers={"Authorization": f"Bearer {t_gestor}"})
    assert l_res.status_code == 200
    assert l_res.json()["total"] == 1
    assert l_res.json()["items"][0]["polo_nome"] == "Polo Central"

    # 404 para professor inexistente
    nao_encontrado = await client.get(
        "/professores/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert nao_encontrado.status_code == 404
