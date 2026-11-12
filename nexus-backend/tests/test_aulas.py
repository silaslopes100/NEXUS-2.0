"""Testes do módulo `aulas` (Diário de Aulas do professor + auditoria do admin)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.aulas.repository import InMemoryAulasRepository, hoje, set_aulas_repository
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository

_PERFIS = {
    "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador"},
    "p-professor": {"id": "p-professor", "nome": "professor", "descricao": "Professor"},
}

V_ANA = "11111111-1111-1111-1111-111111111111"
V_BRUNO = "22222222-2222-2222-2222-222222222222"
DATA = date(2026, 11, 10)


def _usuario(user_id: str, perfil_id: str) -> dict:
    return {
        "id": user_id,
        "nome": user_id,
        "sobrenome": "",
        "email": f"{user_id}@nexus.com.br",
        "senha_hash": hash_password("senha123"),
        "senha_algoritmo": "argon2id",
        "status": "ativo",
        "perfil_id": perfil_id,
        "polo_id": None,
        "escola_id": None,
    }


@pytest.fixture
def repo():
    auth = InMemoryAuthRepository()
    auth.perfis = dict(_PERFIS)
    auth.usuarios["admin-1"] = _usuario("admin-1", "p-admin")
    auth.usuarios["ana"] = _usuario("ana", "p-professor")
    auth.usuarios["bruno"] = _usuario("bruno", "p-professor")
    set_auth_repository(auth)

    aulas = InMemoryAulasRepository()
    base = {"disciplina_nome": "Eclesiologia", "curso_nome": "Teologia", "ativo": True}
    aulas.vinculos[V_ANA] = {
        **base, "id": V_ANA, "professor_id": "prof-ana", "professor_usuario_id": "ana",
        "professor_nome": "Ana Souza", "disciplina_id": "disc-1", "turma_id": "turma-1",
        "turma_nome": "Turma A", "polo_id": "polo-1", "polo_nome": "Polo Central",
    }
    aulas.vinculos[V_BRUNO] = {
        **base, "id": V_BRUNO, "professor_id": "prof-bruno", "professor_usuario_id": "bruno",
        "professor_nome": "Bruno Lima", "disciplina_id": "disc-1", "turma_id": "turma-2",
        "turma_nome": "Turma B", "polo_id": "polo-2", "polo_nome": "Polo Norte",
    }
    aulas.alunos_turma["turma-1"] = [
        {"aluno_id": "a1", "nome": "Aluno 1", "numero_matricula": "M1"},
        {"aluno_id": "a2", "nome": "Aluno 2", "numero_matricula": "M2"},
    ]
    aulas.polos_ativos = {"polo-1": "Polo Central", "polo-2": "Polo Norte"}
    set_aulas_repository(aulas)
    yield aulas
    set_aulas_repository(None)


@pytest_asyncio.fixture
async def client(repo):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _h(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id, 'tipo': 'access'})}"}


async def _registrar(client, user="ana", vinculo=V_ANA, **extra):
    payload = {
        "professor_disciplina_id": vinculo,
        "data_aula": DATA.isoformat(),
        "numero_aula": 1,
        "conteudo_ministrado": "Introdução à eclesiologia",
        **extra,
    }
    return await client.post("/aulas/me", json=payload, headers=_h(user))


@pytest.mark.asyncio
async def test_professor_registra_aula_com_ata_material_e_chamada(client, repo):
    res = await _registrar(client)
    assert res.status_code == 201, res.text
    aula = res.json()
    assert aula["conteudo_ministrado"] == "Introdução à eclesiologia"
    assert aula["polo_nome"] == "Polo Central"
    assert [a["presente"] for a in aula["chamada"]] == [None, None]

    # Material e chamada gravados pelos endpoints existentes aparecem na aula.
    repo.materiais["m1"] = {"id": "m1", "aula_id": aula["id"], "descricao": "Slides", "arquivo_url": "https://x.y/s"}
    repo.presencas += [
        {"professor_disciplina_id": V_ANA, "data_aula": DATA, "numero_aula": 1, "aluno_id": "a1", "presente": True},
        {"professor_disciplina_id": V_ANA, "data_aula": DATA, "numero_aula": 1, "aluno_id": "a2", "presente": False},
    ]
    detalhe = (await client.get(f"/aulas/me/{aula['id']}", headers=_h("ana"))).json()
    assert detalhe["total_materiais"] == 1
    assert (detalhe["presentes"], detalhe["total_chamada"]) == (1, 2)
    assert detalhe["materiais"][0]["descricao"] == "Slides"

    duplicada = await _registrar(client)
    assert duplicada.status_code == 409


@pytest.mark.asyncio
async def test_professor_so_acessa_as_proprias_aulas(client):
    aula = (await _registrar(client)).json()

    assert (await _registrar(client, user="bruno")).status_code == 403
    assert (await client.get(f"/aulas/me/{aula['id']}", headers=_h("bruno"))).status_code == 403
    assert (await client.delete(f"/aulas/me/{aula['id']}", headers=_h("bruno"))).status_code == 403
    lista_bruno = (await client.get("/aulas/me", headers=_h("bruno"))).json()
    assert lista_bruno["total"] == 0
    assert (await client.get("/aulas/auditoria", headers=_h("ana"))).status_code == 403


@pytest.mark.asyncio
async def test_mudar_data_move_a_chamada_e_excluir_limpa_tudo(client, repo):
    aula = (await _registrar(client)).json()
    repo.presencas.append(
        {"professor_disciplina_id": V_ANA, "data_aula": DATA, "numero_aula": 1, "aluno_id": "a1", "presente": True}
    )
    nova = DATA + timedelta(days=1)

    res = await client.put(
        f"/aulas/me/{aula['id']}", json={"data_aula": nova.isoformat()}, headers=_h("ana")
    )
    assert res.status_code == 200, res.text
    assert res.json()["presentes"] == 1
    assert repo.presencas[0]["data_aula"] == nova

    repo.materiais["m1"] = {"id": "m1", "aula_id": aula["id"], "descricao": "PDF"}
    assert (await client.delete(f"/aulas/me/{aula['id']}", headers=_h("ana"))).status_code == 200
    assert repo.aulas == {} and repo.presencas == [] and repo.materiais == {}


@pytest.mark.asyncio
async def test_auditoria_filtra_por_polo_professor_periodo_e_texto(client):
    await _registrar(client)
    await _registrar(client, user="bruno", vinculo=V_BRUNO, conteudo_ministrado="Missões urbanas")
    admin = _h("admin-1")

    todas = (await client.get("/aulas/auditoria", headers=admin)).json()
    assert todas["total"] == 2
    texto = (await client.get("/aulas/auditoria", params={"q": "missões"}, headers=admin)).json()
    assert [i["professor_nome"] for i in texto["items"]] == ["Bruno Lima"]
    futuro = (
        await client.get("/aulas/auditoria", params={"data_inicio": (DATA + timedelta(days=1)).isoformat()}, headers=admin)
    ).json()
    assert futuro["total"] == 0

    filtros = (await client.get("/aulas/auditoria/filtros", headers=admin)).json()
    assert {p["nome"] for p in filtros["polos"]} == {"Polo Central", "Polo Norte"}
    resumo = (await client.get("/aulas/auditoria/disciplinas", headers=admin)).json()
    assert resumo == [{"disciplina_id": "disc-1", "total_aulas": 2, "ultima_aula": DATA.isoformat()}]


def test_filtros_de_polo_e_professor_no_repositorio(repo):
    from app.modules.aulas.service import AulasService

    service = AulasService(repo)
    for vinculo in (V_ANA, V_BRUNO):
        repo.criar({"professor_disciplina_id": vinculo, "data_aula": DATA, "numero_aula": 1})

    assert service.listar(None, {"polo_id": "polo-2"}, 20, 0).items[0].polo_nome == "Polo Norte"
    assert service.listar(None, {"professor_id": "prof-ana"}, 20, 0).total == 1


@pytest.mark.asyncio
async def test_atividade_docente_aponta_polos_sem_registro(client, repo):
    repo.criar({"professor_disciplina_id": V_ANA, "data_aula": hoje(), "numero_aula": 1})

    res = await client.get("/aulas/auditoria/atividade", headers=_h("admin-1"))

    assert res.status_code == 200, res.text
    dados = res.json()
    assert dados["aulas_registradas"] == 1
    assert dados["top_disciplinas"][0] == {"id": "disc-1", "nome": "Eclesiologia", "total_aulas": 1}
    assert [p["nome"] for p in dados["polos_sem_registro"]] == ["Polo Norte"]


def test_material_so_entra_em_aula_da_mesma_turma_e_do_mesmo_professor(repo):
    from fastapi import HTTPException

    from app.modules.auth.repository import get_auth_repository
    from app.modules.aulas.service import AulasService
    from app.modules.auth.schemas import UserResponse

    service = AulasService(repo)
    aula_id = repo.criar({"professor_disciplina_id": V_ANA, "data_aula": DATA, "numero_aula": 1})
    perfis = {"ana": "professor", "bruno": "professor"}

    def usuario(user_id):
        dados = get_auth_repository().usuarios[user_id]
        return UserResponse(
            id=user_id, nome=dados["nome"], email=dados["email"], status="ativo",
            perfil={"id": f"p-{perfis[user_id]}", "nome": perfis[user_id]},
        )

    assert service.aula_do_material(usuario("ana"), aula_id, V_ANA)["data_aula"] == DATA
    with pytest.raises(HTTPException) as outra_turma:
        service.aula_do_material(usuario("ana"), aula_id, V_BRUNO)
    assert outra_turma.value.status_code == 400
    with pytest.raises(HTTPException) as outro_professor:
        service.aula_do_material(usuario("bruno"), aula_id, V_ANA)
    assert outro_professor.value.status_code == 403
