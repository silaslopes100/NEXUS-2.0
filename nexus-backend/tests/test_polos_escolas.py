"""Testes do módulo `polos_escolas` (NEXUS 2.0) — arquitetura em camadas + InMemoryRepository."""
from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.polos_escolas.repository import (
    InMemoryPolosEscolasRepository,
    set_polos_escolas_repository,
)

# Perfis compartilhados entre o repositorio de autenticacao e o de polos_escolas,
# para que usuarios criados via polos_escolas sejam resolvidos no login (mesma
# tabela `usuarios` em producao; em memoria usamos o mesmo dict compartilhado).
_PERFIS = {
    "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador"},
    "p-secgeral": {"id": "p-secgeral", "nome": "secretario_geral", "descricao": "Secretario Geral"},
    "p-coordpolo": {"id": "p-coordpolo", "nome": "coordenador_polo", "descricao": "Coordenador de Polo"},
    "p-secescola": {"id": "p-secescola", "nome": "secretario_escola", "descricao": "Secretario de Escola"},
    "p-professor": {"id": "p-professor", "nome": "professor", "descricao": "Professor"},
    "p-aluno": {"id": "p-aluno", "nome": "aluno", "descricao": "Aluno"},
}


@pytest.fixture
def repos():
    auth_repo = InMemoryAuthRepository()
    auth_repo.perfis = dict(_PERFIS)

    polos_repo = InMemoryPolosEscolasRepository()
    polos_repo.perfis = {v["nome"]: k for k, v in _PERFIS.items()}
    # Compartilha o dicionario de usuarios: em producao ambos os repositorios
    # leem/escrevem na mesma tabela `usuarios` do PostgreSQL.
    polos_repo.usuarios = auth_repo.usuarios

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

    set_auth_repository(auth_repo)
    set_polos_escolas_repository(polos_repo)
    return auth_repo, polos_repo


@pytest_asyncio.fixture
async def client(repos):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _token(user_id: str) -> str:
    return create_access_token({"sub": user_id, "tipo": "access"})


def _polo_payload(**overrides):
    payload = {
        "nome": "Polo Central",
        "endereco": {
            "logradouro": "Rua A",
            "numero": "100",
            "bairro": "Centro",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "cep": "01000-000",
        },
        "coordenador_nome": "Carlos Coordenador",
        "coordenador_cpf": "12345678900",
        "coordenador_email": "coordenador@polo.com",
        "coordenador_senha": "senha_segura_123",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_rn01_create_polo_gera_coordenador_sem_endpoint_separado(client: AsyncClient, repos):
    admin_token = _token("admin-1")

    res = await client.post("/polos", json=_polo_payload(), headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 201, res.text
    polo = res.json()
    assert polo["nome"] == "Polo Central"
    assert polo["coordenador_nome"] == "Carlos Coordenador"
    assert polo["coordenador_email"] == "coordenador@polo.com"

    auth_repo, _ = repos
    coordenador = auth_repo.get_user_by_email("coordenador@polo.com")
    assert coordenador is not None
    assert coordenador["perfil_id"] == "p-coordpolo"
    assert coordenador["polo_id"] == polo["id"]


@pytest.mark.asyncio
async def test_rn01_create_escola_gera_secretario(client: AsyncClient, repos):
    admin_token = _token("admin-1")
    polo_res = await client.post("/polos", json=_polo_payload(), headers={"Authorization": f"Bearer {admin_token}"})
    polo_id = polo_res.json()["id"]

    escola_payload = {
        "nome": "Escola Alfa",
        "endereco": {
            "logradouro": "Rua B",
            "numero": "20",
            "bairro": "Centro",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "cep": "02000-000",
        },
        "secretario_nome": "Diretora Ana",
        "secretario_cpf": "22233344455",
        "secretario_email": "secretaria@escola.com",
        "secretario_senha": "senha_segura_456",
    }
    res = await client.post(
        f"/polos/{polo_id}/escolas", json=escola_payload, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201, res.text
    escola = res.json()
    assert escola["secretario_nome"] == "Diretora Ana"

    auth_repo, _ = repos
    secretario = auth_repo.get_user_by_email("secretaria@escola.com")
    assert secretario is not None
    assert secretario["perfil_id"] == "p-secescola"
    assert secretario["escola_id"] == escola["id"]


@pytest.mark.asyncio
async def test_rn09_multi_tenancy_restringe_coordenador_a_proprio_polo(client: AsyncClient, repos):
    admin_token = _token("admin-1")
    auth_repo, _ = repos

    polo_a = (
        await client.post(
            "/polos", json=_polo_payload(coordenador_email="coordA@polo.com", coordenador_cpf="10000000001"),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    polo_b = (
        await client.post(
            "/polos", json=_polo_payload(coordenador_email="coordB@polo.com", coordenador_cpf="10000000002"),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    coord_a_id = auth_repo.get_user_by_email("coordA@polo.com")["id"]
    token_a = _token(coord_a_id)

    ok = await client.get(f"/polos/{polo_a['id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert ok.status_code == 200

    forbidden = await client.get(f"/polos/{polo_b['id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_rn02_fluxo_completo_de_licencas(client: AsyncClient, repos):
    admin_token = _token("admin-1")

    polo = (
        await client.post("/polos", json=_polo_payload(), headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    escola = (
        await client.post(
            f"/polos/{polo['id']}/escolas",
            json={
                "nome": "Escola Alfa",
                "secretario_nome": "Diretora Ana",
                "secretario_cpf": "22233344455",
                "secretario_email": "secretaria@escola.com",
                "secretario_senha": "senha_segura_456",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    # 3.1 Compra: Fornecedor -> Polo
    compra = await client.post(
        f"/polos/{polo['id']}/licencas/compra",
        json={"quantidade": 100, "fornecedor": "Editora XPTO", "valor_unitario": 45.0, "data": str(date.today())},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert compra.status_code == 200, compra.text

    kpis = (
        await client.get(f"/polos/{polo['id']}/dashboard/kpis", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    assert kpis["total_licencas_compradas"] == 100
    assert kpis["total_nao_vendidas_polo"] == 100

    # 3.2 Distribuicao: Polo -> Escola
    dist = await client.post(
        f"/polos/{polo['id']}/licencas/distribuir",
        json={"escola_id": escola["id"], "quantidade": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dist.status_code == 200, dist.text

    # RN-02: nao permite distribuir mais do que o Polo possui
    excesso = await client.post(
        f"/polos/{polo['id']}/licencas/distribuir",
        json={"escola_id": escola["id"], "quantidade": 999},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert excesso.status_code == 400

    # 3.3 Venda: Escola -> Aluno
    aluno_res = await client.post(
        f"/polos/{polo['id']}/alunos",
        json={
            "nome": "Joao",
            "sobrenome": "Aluno",
            "cpf": "99988877766",
            "email": "aluno@nexus.com.br",
            "data_nascimento": "2000-01-01",
            "escola_id": escola["id"],
            "modalidade": "escola",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert aluno_res.status_code == 201, aluno_res.text
    aluno_id = aluno_res.json()["id"]

    venda = await client.post(
        f"/escolas/{escola['id']}/licencas/vender",
        json={"aluno_id": aluno_id, "quantidade": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert venda.status_code == 200, venda.text

    escola_kpis = (
        await client.get(f"/escolas/{escola['id']}/dashboard/kpis", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    assert escola_kpis["licencas_vendidas"] == 1
    assert escola_kpis["licencas_nao_vendidas"] == 29

    # 3.5 Devolucao Aluno -> Escola
    devolucao_aluno = await client.post(
        f"/alunos/{aluno_id}/licencas/devolver", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert devolucao_aluno.status_code == 200, devolucao_aluno.text

    # 3.4 Devolucao Escola -> Polo
    devolucao_escola = await client.post(
        f"/escolas/{escola['id']}/licencas/devolver",
        json={"quantidade": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert devolucao_escola.status_code == 200, devolucao_escola.text

    kpis_finais = (
        await client.get(f"/polos/{polo['id']}/dashboard/kpis", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    assert kpis_finais["total_nao_vendidas_polo"] == 100
    assert kpis_finais["total_licencas_vendidas_alunos"] == 0
