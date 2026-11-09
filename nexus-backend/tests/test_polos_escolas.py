"""Testes do módulo `polos_escolas` (NEXUS 2.0) — arquitetura em camadas + InMemoryRepository."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.polos_escolas import repository as polos_repository_module
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
    "p-polo": {"id": "p-polo", "nome": "polo", "descricao": "Gestor de Polo"},
    "p-escola": {"id": "p-escola", "nome": "escola", "descricao": "Gestor de Escola"},
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
async def test_list_polos_e_escolas_usam_carregamento_em_lote_de_usuarios(client: AsyncClient, repos):
    admin_token = _token("admin-1")
    _, polos_repo = repos

    class CountingRepo(InMemoryPolosEscolasRepository):
        def __init__(self, base):
            self._base = base
            self.get_usuarios_by_ids_calls = 0

        def __getattr__(self, name):
            return getattr(self._base, name)

        def get_usuarios_by_ids(self, usuario_ids):
            self.get_usuarios_by_ids_calls += 1
            return self._base.get_usuarios_by_ids(usuario_ids)

    counting_repo = CountingRepo(polos_repo)
    set_polos_escolas_repository(counting_repo)

    polo_a = (
        await client.post(
            "/polos", json=_polo_payload(nome="Polo A", coordenador_email="coordA@polo.com", coordenador_cpf="10000000001"),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    polo_b = (
        await client.post(
            "/polos", json=_polo_payload(nome="Polo B", coordenador_email="coordB@polo.com", coordenador_cpf="10000000002"),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    await client.post(
        f"/polos/{polo_a['id']}/escolas",
        json={
            "nome": "Escola A",
            "secretario_nome": "Secretaria A",
            "secretario_cpf": "55566677788",
            "secretario_email": "secretariaA@escola.com",
            "secretario_senha": "senha_segura_456",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    polos_res = await client.get("/polos", headers={"Authorization": f"Bearer {admin_token}"})
    escolas_res = await client.get(f"/polos/{polo_a['id']}/escolas", headers={"Authorization": f"Bearer {admin_token}"})

    assert polos_res.status_code == 200, polos_res.text
    assert escolas_res.status_code == 200, escolas_res.text
    assert counting_repo.get_usuarios_by_ids_calls >= 1, "As listagens devem buscar usuários em lote, e não item a item"


@pytest.mark.asyncio
async def test_polo_sem_coordenador_vinculado_expoe_coordenador_nulo(client: AsyncClient, repos):
    admin_token = _token("admin-1")
    _, polos_repo = repos

    polo_id = polos_repo.create_polo({
        "nome": "Polo Legacy",
        "status": "ativo",
    })

    response = await client.get(f"/polos/{polo_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["coordenador_id"] is None
    assert body["coordenador_nome"] is None
    assert body["coordenador_cpf"] is None
    assert body["coordenador_email"] is None


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


def _criar_usuario(auth_repo, user_id, perfil_id, polo_id=None, escola_id=None, nome=None):
    auth_repo.usuarios[user_id] = {
        "id": user_id,
        "nome": nome or user_id,
        "sobrenome": "",
        "email": f"{user_id}@nexus.com.br",
        "cpf": "",
        "status": "ativo",
        "perfil_id": perfil_id,
        "polo_id": polo_id,
        "escola_id": escola_id,
    }


@pytest.fixture
def dois_polos(repos):
    _, polos_repo = repos
    polo_a = polos_repo.create_polo({"nome": "Polo A"})
    polo_b = polos_repo.create_polo({"nome": "Polo B"})
    escola_a = polos_repo.create_escola({"polo_id": polo_a, "nome": "Escola A"})
    escola_b = polos_repo.create_escola({"polo_id": polo_b, "nome": "Escola B"})
    return polo_a, polo_b, escola_a, escola_b


def _bearer(user_id: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id)}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("perfil_id", ["p-polo", "p-coordpolo"])
async def test_coordenador_restrito_ao_proprio_polo(client: AsyncClient, repos, dois_polos, perfil_id):
    auth_repo, _ = repos
    polo_a, polo_b, escola_a, escola_b = dois_polos
    _criar_usuario(auth_repo, "coord", perfil_id, polo_id=polo_a)
    headers = _bearer("coord")

    escolas = await client.get(f"/polos/{polo_a}/escolas", headers=headers)
    assert escolas.status_code == 200, escolas.text
    assert [item["id"] for item in escolas.json()["items"]] == [escola_a]
    assert (await client.get(f"/polos/{polo_b}/escolas", headers=headers)).status_code == 403

    assert (await client.get(f"/escolas/{escola_a}", headers=headers)).status_code == 200
    assert (await client.get(f"/escolas/{escola_b}", headers=headers)).status_code == 403

    gestao = await client.get("/escolas", headers=headers)
    assert [item["id"] for item in gestao.json()["items"]] == [escola_a]

    polos = await client.get("/polos", headers=headers)
    assert polos.status_code == 200, polos.text
    assert [item["id"] for item in polos.json()["items"]] == [polo_a]


@pytest.mark.asyncio
async def test_coordenador_sem_vinculo_nao_lista_polos(client: AsyncClient, repos, dois_polos):
    auth_repo, _ = repos
    _criar_usuario(auth_repo, "coord", "p-polo")
    assert (await client.get("/polos", headers=_bearer("coord"))).status_code == 403


@pytest.mark.asyncio
async def test_admin_continua_vendo_todos_os_polos(client: AsyncClient, dois_polos):
    polos = await client.get("/polos", headers=_bearer("admin-1"))
    assert polos.status_code == 200
    assert polos.json()["total"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("perfil_id", ["p-escola", "p-secescola"])
async def test_secretario_restrito_a_propria_escola(client: AsyncClient, repos, dois_polos, perfil_id):
    auth_repo, _ = repos
    polo_a, _, escola_a, escola_b = dois_polos
    _criar_usuario(auth_repo, "sec", perfil_id, polo_id=polo_a, escola_id=escola_a)
    headers = _bearer("sec")

    assert (await client.get(f"/escolas/{escola_a}", headers=headers)).status_code == 200
    assert (await client.get(f"/escolas/{escola_b}", headers=headers)).status_code == 403
    assert (await client.get("/polos", headers=headers)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("perfil_id", ["p-polo", "p-coordpolo"])
async def test_usuarios_vinculaveis_do_coordenador(client: AsyncClient, repos, dois_polos, perfil_id):
    auth_repo, _ = repos
    polo_a, polo_b, _, _ = dois_polos
    _criar_usuario(auth_repo, "coord", perfil_id, polo_id=polo_a)
    _criar_usuario(auth_repo, "do-polo", "p-professor", polo_id=polo_a)
    _criar_usuario(auth_repo, "de-outro", "p-professor", polo_id=polo_b)
    headers = _bearer("coord")

    resposta = await client.get("/usuarios-vinculaveis", headers=headers)
    assert resposta.status_code == 200, resposta.text
    ids = {item["id"] for item in resposta.json()["items"]}
    assert {"coord", "do-polo", "admin-1"} == ids, "próprio polo e usuários sem polo"

    alheio = await client.get("/usuarios-vinculaveis", params={"polo_id": polo_b}, headers=headers)
    assert alheio.status_code == 403


@pytest.mark.asyncio
async def test_usuarios_vinculaveis_admin_sem_restricao(client: AsyncClient, repos, dois_polos):
    auth_repo, _ = repos
    _, polo_b, _, _ = dois_polos
    _criar_usuario(auth_repo, "de-outro", "p-professor", polo_id=polo_b)

    todos = await client.get("/usuarios-vinculaveis", headers=_bearer("admin-1"))
    assert {"admin-1", "de-outro"} <= {item["id"] for item in todos.json()["items"]}

    filtrado = await client.get("/usuarios-vinculaveis", params={"polo_id": polo_b}, headers=_bearer("admin-1"))
    assert [item["id"] for item in filtrado.json()["items"]] == ["de-outro"]


@pytest.mark.asyncio
async def test_filtro_de_perfil_encontra_nomes_equivalentes(client: AsyncClient, repos, dois_polos):
    auth_repo, _ = repos
    polo_a, _, escola_a, _ = dois_polos
    _criar_usuario(auth_repo, "sec-curto", "p-escola", polo_id=polo_a, escola_id=escola_a)
    _criar_usuario(auth_repo, "sec-longo", "p-secescola", polo_id=polo_a, escola_id=escola_a)

    resposta = await client.get(
        "/usuarios-vinculaveis", params={"perfil": "secretario_escola"}, headers=_bearer("admin-1")
    )
    assert {item["id"] for item in resposta.json()["items"]} == {"sec-curto", "sec-longo"}


@pytest.mark.asyncio
async def test_auditoria_postgres_aceita_datas_da_linha_do_banco(monkeypatch):
    executions = []

    class Cursor:
        def execute(self, sql, params=()):
            executions.append(params)

    @contextmanager
    def database_cursor():
        yield Cursor()

    monkeypatch.setattr(polos_repository_module, "get_db_cursor", database_cursor)

    polos_repository_module.PostgresPolosEscolasRepository().record_audit_log(
        usuario_id="admin-1",
        acao="polo_atualizado",
        entidade="polos",
        entidade_id="polo-1",
        dados_antes={"nome": "Polo", "atualizado_em": datetime(2026, 11, 9, 12, 30)},
        dados_depois={"nome": "Polo novo"},
    )

    assert json.loads(executions[0][4]) == {"nome": "Polo", "atualizado_em": "2026-11-09 12:30:00"}
    assert json.loads(executions[0][5]) == {"nome": "Polo novo"}


@pytest.mark.asyncio
async def test_create_polo_usa_perfil_curto_quando_longo_nao_existe(client: AsyncClient, repos):
    auth_repo, polos_repo = repos
    del polos_repo.perfis["coordenador_polo"]

    res = await client.post("/polos", json=_polo_payload(), headers=_bearer("admin-1"))
    assert res.status_code == 201, res.text
    assert auth_repo.get_user_by_email("coordenador@polo.com")["perfil_id"] == "p-polo"


@pytest.mark.asyncio
async def test_escola_management_search_soft_deactivation_and_scope(client: AsyncClient, repos):
    admin_token = _token("admin-1")
    auth_repo, polos_repo = repos

    polo_a = (
        await client.post(
            "/polos",
            json=_polo_payload(nome="Polo A", coordenador_email="gestorA@polo.com", coordenador_cpf="10000000001"),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    polo_b = (
        await client.post(
            "/polos",
            json=_polo_payload(nome="Polo B", coordenador_email="gestorB@polo.com", coordenador_cpf="10000000002"),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    school_a_id = polos_repo.create_escola(
        {"polo_id": polo_a["id"], "nome": "Escola Alfa", "cidade": "Campinas", "status": "ativo"}
    )
    school_b_id = polos_repo.create_escola(
        {"polo_id": polo_b["id"], "nome": "Escola Beta", "cidade": "Santos", "status": "ativo"}
    )

    search = await client.get(
        "/escolas",
        params={"q": "campinas", "status": "ativo"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search.status_code == 200, search.text
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["id"] == school_a_id

    deactivated = await client.put(
        f"/escolas/{school_a_id}",
        json={"status": "inativo"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "inativo"
    assert (await client.get(f"/escolas/{school_a_id}", headers={"Authorization": f"Bearer {admin_token}"})).status_code == 200

    inactive = await client.get(
        "/escolas",
        params={"status": "inativo"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert inactive.status_code == 200
    assert {item["id"] for item in inactive.json()["items"]} == {school_a_id}

    coordinator_id = auth_repo.get_user_by_email("gestorA@polo.com")["id"]
    coordinator_token = _token(coordinator_id)
    scoped_list = await client.get("/escolas", headers={"Authorization": f"Bearer {coordinator_token}"})
    assert scoped_list.status_code == 200
    assert {item["id"] for item in scoped_list.json()["items"]} == {school_a_id}

    wrong_polo = await client.get(
        "/escolas",
        params={"polo_id": polo_b["id"]},
        headers={"Authorization": f"Bearer {coordinator_token}"},
    )
    assert wrong_polo.status_code == 403
    wrong_school = await client.get(
        f"/escolas/{school_b_id}",
        headers={"Authorization": f"Bearer {coordinator_token}"},
    )
    assert wrong_school.status_code == 403
    wrong_school_update = await client.put(
        f"/escolas/{school_b_id}",
        json={"status": "inativo"},
        headers={"Authorization": f"Bearer {coordinator_token}"},
    )
    assert wrong_school_update.status_code == 403
    move_school_outside_scope = await client.put(
        f"/escolas/{school_a_id}",
        json={"polo_id": polo_b["id"]},
        headers={"Authorization": f"Bearer {coordinator_token}"},
    )
    assert move_school_outside_scope.status_code == 403
    wrong_school_licenses = await client.get(
        f"/escolas/{school_b_id}/licencas/movimentacoes",
        headers={"Authorization": f"Bearer {coordinator_token}"},
    )
    assert wrong_school_licenses.status_code == 403


@pytest.mark.asyncio
async def test_school_indicator_and_license_drilldowns_are_filtered_by_school(client: AsyncClient, repos):
    admin_token = _token("admin-1")
    _, repository = repos
    polo_id = repository.create_polo({"nome": "Polo de teste"})
    escola_id = repository.create_escola(
        {"polo_id": polo_id, "nome": "Escola de teste", "status": "ativo"}
    )
    repository.usuarios["teacher-user"] = {"id": "teacher-user", "nome": "Professora Ana"}
    repository.professores["teacher-id"] = {
        "id": "teacher-id",
        "usuario_id": "teacher-user",
        "polo_id": polo_id,
        "escola_id": escola_id,
        "status": "ativo",
        "quantidade_aulas": 4,
        "horas_totais": 4,
    }
    repository.aulas["lesson-id"] = {
        "id": "lesson-id",
        "professor_id": "teacher-id",
        "escola_id": escola_id,
        "data_aula": date.today(),
        "conteudo": "Revisão",
        "total_aulas_previstas": 4,
    }
    repository.create_turma_escola({"escola_id": escola_id, "polo_id": polo_id, "nome": "Turma A"})
    repository.registrar_movimentacao({
        "polo_id": polo_id,
        "escola_id": escola_id,
        "tipo": "devolucao_escola_polo",
        "quantidade": 2,
    })
    headers = {"Authorization": f"Bearer {admin_token}"}

    teachers = await client.get(f"/escolas/{escola_id}/professores", headers=headers)
    lessons = await client.get(f"/escolas/{escola_id}/aulas", headers=headers)
    classes = await client.get(f"/escolas/{escola_id}/turmas", headers=headers)
    movements = await client.get(f"/escolas/{escola_id}/licencas/movimentacoes", headers=headers)

    assert teachers.status_code == 200, teachers.text
    assert [item["nome"] for item in teachers.json()["items"]] == ["Professora Ana"]
    assert lessons.status_code == 200, lessons.text
    assert [item["id"] for item in lessons.json()["items"]] == ["lesson-id"]
    assert classes.status_code == 200, classes.text
    assert [item["nome"] for item in classes.json()["items"]] == ["Turma A"]
    assert movements.status_code == 200, movements.text
    assert [item["escola_id"] for item in movements.json()["items"]] == [escola_id]


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
            "cpf": "529.982.247-25",
            "email": "aluno@nexus.com.br",
            "data_nascimento": "2000-01-01",
            "escola_id": escola["id"],
            "modalidade": "escola",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert aluno_res.status_code == 201, aluno_res.text
    aluno_id = aluno_res.json()["id"]
    assert aluno_res.json()["numero_matricula"].startswith(f"NX-{date.today().year}-")
    assert aluno_res.json()["usuario_id"] and aluno_res.json()["usuario_id"] != aluno_id
    assert aluno_res.json()["cpf"] == "52998224725"

    # CPF duplicado (mesmo número, outra máscara) e CPF inválido
    dup = await client.post(
        f"/polos/{polo['id']}/alunos",
        json={"nome": "X", "cpf": "52998224725", "email": "outro@nexus.com.br", "data_nascimento": "2000-01-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dup.status_code == 400
    invalido = await client.post(
        f"/polos/{polo['id']}/alunos",
        json={"nome": "X", "cpf": "11111111111", "email": "inv@nexus.com.br", "data_nascimento": "2000-01-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert invalido.status_code == 422

    # Modalidade escola exige escola; EAD não admite escola
    sem_escola = await client.post(
        f"/polos/{polo['id']}/alunos",
        json={"nome": "X", "cpf": "39053344705", "email": "se@nexus.com.br", "data_nascimento": "2000-01-01", "modalidade": "escola"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sem_escola.status_code == 400
    ead_escola = await client.post(
        f"/polos/{polo['id']}/alunos",
        json={"nome": "X", "cpf": "39053344705", "email": "ee@nexus.com.br", "data_nascimento": "2000-01-01", "modalidade": "ead", "escola_id": escola["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ead_escola.status_code == 400

    # Turmas da escola
    turma = await client.post(
        f"/escolas/{escola['id']}/turmas",
        json={"nome": "Turma 2026-A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert turma.status_code == 201, turma.text
    turmas = (
        await client.get(f"/escolas/{escola['id']}/turmas", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    assert turmas["total"] == 1 and turmas["items"][0]["escola_id"] == escola["id"]

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


@pytest.mark.asyncio
async def test_resumo_operacional_polo_e_escola(client: AsyncClient, repos):
    admin_token = _token("admin-1")

    polo = (
        await client.post("/polos", json=_polo_payload(), headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    escola = (
        await client.post(
            f"/polos/{polo['id']}/escolas",
            json={
                "nome": "Escola Alfa",
                "endereco": {"logradouro": "Rua B", "numero": "20", "complemento": "Sala 2", "cidade": "Sao Paulo", "estado": "SP"},
                "secretario_nome": "Diretora Ana",
                "secretario_cpf": "22233344455",
                "secretario_email": "secretaria@escola.com",
                "secretario_senha": "senha_segura_456",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    await client.post(
        f"/polos/{polo['id']}/licencas/compra",
        json={"quantidade": 50, "fornecedor": "Editora XPTO", "valor_unitario": 40.0, "data": str(date.today())},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/polos/{polo['id']}/licencas/distribuir",
        json={"escola_id": escola["id"], "quantidade": 20},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    aluno = (
        await client.post(
            f"/polos/{polo['id']}/alunos",
            json={
                "nome": "Joao",
                "cpf": "529.982.247-25",
                "email": "aluno@nexus.com.br",
                "data_nascimento": "2000-01-01",
                "escola_id": escola["id"],
                "modalidade": "escola",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    await client.post(
        f"/escolas/{escola['id']}/licencas/vender",
        json={"aluno_id": aluno["id"], "quantidade": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/escolas/{escola['id']}/turmas",
        json={"nome": "Turma 2026-A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resumo_polo = (
        await client.get(f"/polos/{polo['id']}/dashboard/resumo", headers={"Authorization": f"Bearer {admin_token}"})
    )
    assert resumo_polo.status_code == 200, resumo_polo.text
    rp = resumo_polo.json()
    assert rp["escolas"] == 1
    assert rp["turmas"] == 1
    assert rp["alunos"] == 1
    assert rp["professores"] == 0
    assert rp["aulas"] == 0
    assert rp["licencas_estoque"] == 30  # 50 compradas - 20 distribuidas
    assert rp["licencas_atribuidas"] == 1  # 1 ativa (vendida)
    assert rp["licencas_movimentacoes"] >= 2  # compra + distribuicao + venda
    assert rp["pedidos_licencas"] == 0
    assert rp["pedidos_livros"] == 0

    resumo_escola = (
        await client.get(f"/escolas/{escola['id']}/dashboard/resumo", headers={"Authorization": f"Bearer {admin_token}"})
    )
    assert resumo_escola.status_code == 200, resumo_escola.text
    re = resumo_escola.json()
    assert re["alunos"] == 1
    assert re["turmas"] == 1
    assert re["aulas"] == 0
    assert re["professores"] == 0
    assert re["licencas_estoque"] == 19  # 20 distribuidas - 1 vendida
    assert re["licencas_alunos"] == 1
    assert re["licencas_atribuidas"] == 1
    assert re["licencas_movimentacoes"] >= 2
    assert re["pedidos_licencas"] == 0
    assert re["pedidos_livros"] == 0


@pytest.mark.asyncio
async def test_polo_e_escola_expoe_complemento_e_dados_coordenador(client: AsyncClient, repos):
    admin_token = _token("admin-1")

    polo_payload = _polo_payload()
    polo_payload["endereco"]["complemento"] = "Sala 402"
    polo = (await client.post("/polos", json=polo_payload, headers={"Authorization": f"Bearer {admin_token}"})).json()
    assert polo["endereco"]["complemento"] == "Sala 402"
    assert polo["coordenador_nome"] == "Carlos Coordenador"
    assert polo["coordenador_cpf"] == "12345678900"
    assert polo["coordenador_email"] == "coordenador@polo.com"

    escola = (
        await client.post(
            f"/polos/{polo['id']}/escolas",
            json={
                "nome": "Escola Alfa",
                "endereco": {"logradouro": "Rua B", "numero": "20", "complemento": "Fundos", "cidade": "Sao Paulo", "estado": "SP"},
                "secretario_nome": "Diretora Ana",
                "secretario_cpf": "22233344455",
                "secretario_email": "secretaria@escola.com",
                "secretario_senha": "senha_segura_456",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    assert escola["endereco"]["complemento"] == "Fundos"
    assert escola["secretario_nome"] == "Diretora Ana"
    assert escola["secretario_cpf"] == "22233344455"
    assert escola["secretario_email"] == "secretaria@escola.com"
