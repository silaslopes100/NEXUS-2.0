"""Testes do módulo `professores` (NEXUS 2.0) — arquitetura em camadas + InMemoryRepository."""
from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core import file_storage as file_storage_module
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.professores import repository as professores_repository_module
from app.modules.professores.repository import (
    InMemoryProfessoresRepository,
    PostgresProfessoresRepository,
    set_professores_repository,
)

_PERFIS = {
    "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador"},
    "p-polo": {"id": "p-polo", "nome": "polo", "descricao": "Gestor de Polo"},
    "p-coordpolo": {"id": "p-coordpolo", "nome": "coordenador_polo", "descricao": "Coordenador de Polo"},
    "p-professor": {"id": "p-professor", "nome": "professor", "descricao": "Professor"},
    "p-aluno": {"id": "p-aluno", "nome": "aluno", "descricao": "Aluno"},
    "p-escola": {"id": "p-escola", "nome": "escola", "descricao": "Gestor de Escola"},
}


@pytest.fixture
def repos():
    auth_repo = InMemoryAuthRepository()
    auth_repo.perfis = dict(_PERFIS)

    professores_repo = InMemoryProfessoresRepository()
    # Em produção os dois repositorios leem a mesma tabela `usuarios`.
    professores_repo.usuarios = auth_repo.usuarios
    professores_repo.perfis = auth_repo.perfis
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


def test_professor_tem_disciplina_nao_filtra_coluna_ativo_no_vinculo_administrativo(
    monkeypatch,
):
    class Cursor:
        query = ""

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, query, params):
            self.query = query

        def fetchone(self):
            return {"vinculado": True}

    cursor = Cursor()
    monkeypatch.setattr(professores_repository_module, "get_db_cursor", lambda: cursor)

    assert PostgresProfessoresRepository().professor_tem_disciplina(
        "professor-1", "disciplina-1"
    )
    assert "FROM professor_disciplinas vinculo" in cursor.query
    assert "vinculo.ativo" not in cursor.query


def test_cadastro_administrativo_preserva_vinculos_de_turma_e_dependencias():
    repo = InMemoryProfessoresRepository()
    repo.professores["p"] = {"id": "p", "usuario_id": "u"}
    repo.disciplinas["d"] = {"id": "d", "nome": "Disciplina", "carga_horaria": 40}
    administrativo = {"id": "admin", "professor_id": "p", "disciplina_id": "d", "turma_id": None, "ativo": False}
    turma = {"id": "turma", "professor_id": "p", "disciplina_id": "d", "turma_id": "t", "ativo": True}
    repo.professor_disciplinas.extend([administrativo, turma])
    repo.professor_materiais.append({"id": "material", "professor_disciplina_id": "admin"})

    assert repo.get_professor("p")["horas_totais"] == 40
    assert repo.professor_tem_disciplina("u", "d")
    assert [v["id"] for v in repo.list_vinculos_academicos_por_usuario("u")] == ["turma"]
    repo._sync_disciplina_ids("p", ["d"])
    assert repo.professor_disciplinas == [administrativo, turma]
    with pytest.raises(HTTPException) as exc:
        repo._sync_disciplina_ids("p", [])
    assert exc.value.status_code == 409
    assert repo.professor_disciplinas == [administrativo, turma]
    repo.professor_materiais.clear()
    repo._sync_disciplina_ids("p", [])
    assert repo.professor_disciplinas == [turma]


def test_auditoria_postgres_serializa_uuid_e_data(monkeypatch):
    class Cursor:
        params = None

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, query, params):
            self.params = params

    cursor = Cursor()
    monkeypatch.setattr(professores_repository_module, "get_db_cursor", lambda: cursor)
    disciplina_id = uuid.uuid4()

    PostgresProfessoresRepository().record_audit_log(
        usuario_id="admin-1",
        acao="professor_atualizado",
        entidade="professores",
        dados_antes={"disciplina_ids": [disciplina_id]},
        dados_depois={"disciplina_ids": [disciplina_id], "data_inicio": date(2026, 2, 1)},
    )

    assert json.loads(cursor.params[4]) == {"disciplina_ids": [str(disciplina_id)]}
    assert json.loads(cursor.params[5]) == {
        "disciplina_ids": [str(disciplina_id)],
        "data_inicio": "2026-02-01",
    }


@pytest.mark.asyncio
async def test_atualizar_professor_com_auditoria_postgres(client: AsyncClient, repos, monkeypatch):
    class Cursor:
        params = None

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, query, params):
            self.params = params

    _, repo = repos
    headers = {"Authorization": f"Bearer {_token('admin-1')}"}
    criado = await client.post("/professores/", json=_payload(), headers=headers)
    assert criado.status_code == 201
    cursor = Cursor()
    monkeypatch.setattr(professores_repository_module, "get_db_cursor", lambda: cursor)
    monkeypatch.setattr(repo, "record_audit_log", PostgresProfessoresRepository().record_audit_log)
    disciplina_id = str(uuid.uuid4())

    resposta = await client.put(
        f"/professores/{criado.json()['id']}",
        json={"disciplina_ids": [disciplina_id], "data_inicio": "2026-02-01"},
        headers=headers,
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["disciplina_ids"] == [disciplina_id]
    assert json.loads(cursor.params[5]) == {
        "disciplina_ids": [disciplina_id],
        "data_inicio": "2026-02-01",
    }


@pytest.mark.asyncio
async def test_professor_cria_conteudo_com_link_externo(client: AsyncClient, repos):
    _, professores_repo = repos
    professores_repo.professores["docente-1"] = {
        "id": "docente-1",
        "usuario_id": "prof-1",
    }
    professores_repo._sync_disciplina_ids("docente-1", ["disciplina-1"])
    professores_repo.disciplinas["disciplina-1"] = {
        "id": "disciplina-1",
        "nome": "Matemática",
    }

    resposta = await client.post(
        "/professores/me/conteudos",
        data={
            "disciplina_id": "disciplina-1",
            "titulo": "Aula 01",
            "tipo_midia": "video",
            "ordem": "0",
            "modo": "link",
            "url_arquivo": "https://www.youtube.com/watch?v=abcdefghijk",
        },
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )

    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["tipo_midia"] == "video"
    assert resposta.json()["url_arquivo"] == "https://www.youtube.com/watch?v=abcdefghijk"


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


def _preparar_vinculo_turma(repos, *, polo_id="polo-1", escola_id=None):
    auth_repo, professores_repo = repos
    professor_id = str(uuid.UUID(int=101))
    disciplina_id = str(uuid.UUID(int=102))
    turma_id = str(uuid.UUID(int=103))
    professores_repo.professores[professor_id] = {
        "id": professor_id,
        "usuario_id": "prof-1",
        "status": "ativo",
        "polo_id": polo_id,
        "escola_id": escola_id,
    }
    professores_repo.disciplinas[disciplina_id] = {
        "id": disciplina_id,
        "nome": "História",
        "curso_id": "curso-1",
    }
    professores_repo.turmas[turma_id] = {
        "id": turma_id,
        "nome": "Turma 2026",
        "curso_id": "curso-1",
        "polo_id": polo_id,
        "escola_id": escola_id,
    }
    return auth_repo, professores_repo, professor_id, disciplina_id, turma_id


@pytest.mark.asyncio
@pytest.mark.parametrize(("polo_usuario", "esperados"), [("polo-1", 1), ("polo-2", 0)])
async def test_coordenador_polo_ve_apenas_o_proprio_polo(client: AsyncClient, repos, polo_usuario, esperados):
    auth_repo, _ = repos
    auth_repo.usuarios["coord-1"] = {
        **auth_repo.usuarios["gestor-1"],
        "id": "coord-1",
        "perfil_id": "p-coordpolo",
        "polo_id": polo_usuario,
    }
    criado = await client.post(
        "/professores/", json=_payload(), headers={"Authorization": f"Bearer {_token('admin-1')}"}
    )
    assert criado.status_code == 201

    listagem = await client.get("/professores/", headers={"Authorization": f"Bearer {_token('coord-1')}"})
    assert listagem.status_code == 200, listagem.text
    assert listagem.json()["total"] == esperados


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
    assert criado["horas_totais"] == 0
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
async def test_disciplina_pode_ser_vinculada_a_varios_professores(client: AsyncClient, repos):
    auth_repo, _ = repos
    auth_repo.usuarios["prof-2"] = {
        **auth_repo.usuarios["prof-1"],
        "id": "prof-2",
        "nome": "Bruno",
        "email": "bruno@nexus.com.br",
    }
    disciplina_a, disciplina_b = str(uuid.uuid4()), str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {_token('admin-1')}"}

    primeiro = await client.post(
        "/professores/",
        json=_payload(disciplina_ids=[disciplina_a, disciplina_b]),
        headers=headers,
    )
    segundo = await client.post(
        "/professores/",
        json=_payload(usuario_id="prof-2", disciplina_ids=[disciplina_a]),
        headers=headers,
    )

    assert primeiro.status_code == 201
    assert segundo.status_code == 201
    assert primeiro.json()["disciplina_ids"] == [disciplina_a, disciplina_b]
    assert segundo.json()["disciplina_ids"] == [disciplina_a]

    atualizado = await client.put(
        f"/professores/{primeiro.json()['id']}",
        json={"disciplina_ids": [disciplina_b]},
        headers=headers,
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["disciplina_ids"] == [disciplina_b]

    professor_independente = await client.get(
        f"/professores/{segundo.json()['id']}",
        headers=headers,
    )
    assert professor_independente.json()["disciplina_ids"] == [disciplina_a]


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
    assert atualizado["horas_totais"] == 0
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
async def test_totais_docente_seguem_disciplinas_do_cadastro(client: AsyncClient, repos):
    _, repo = repos
    disciplina_a, disciplina_b = str(uuid.uuid4()), str(uuid.uuid4())
    repo.disciplinas[disciplina_a] = {
        "id": disciplina_a, "nome": "Matemática", "carga_horaria": 40, "qtd_aulas_prevista": 10,
    }
    repo.disciplinas[disciplina_b] = {
        "id": disciplina_b, "nome": "Física", "carga_horaria": None, "qtd_aulas_prevista": 5,
    }
    headers = {"Authorization": f"Bearer {_token('admin-1')}"}
    criado = await client.post(
        "/professores/", json=_payload(disciplina_ids=[disciplina_a, disciplina_a, disciplina_b]),
        headers=headers,
    )
    assert criado.status_code == 201, criado.text
    professor_id = criado.json()["id"]
    assert (criado.json()["horas_totais"], criado.json()["quantidade_aulas"]) == (40, 15)

    repo.disciplinas[disciplina_a].update(carga_horaria=60, qtd_aulas_prevista=12)
    resposta = await client.get(f"/professores/{professor_id}", headers=headers)
    assert (resposta.json()["horas_totais"], resposta.json()["quantidade_aulas"]) == (60, 17)
    lista = await client.get("/professores/", headers=headers)
    assert (lista.json()["items"][0]["horas_totais"], lista.json()["items"][0]["quantidade_aulas"]) == (60, 17)

    atualizado = await client.put(
        f"/professores/{professor_id}",
        json={"disciplina_ids": [], "horas_totais": 999, "quantidade_aulas": 999},
        headers=headers,
    )
    assert atualizado.status_code == 200, atualizado.text
    assert (atualizado.json()["horas_totais"], atualizado.json()["quantidade_aulas"]) == (0, 0)


@pytest.mark.asyncio
async def test_detalhe_docente_alunos_e_escopo(client: AsyncClient, repos):
    auth, repo, professor_id, disciplina_id, turma_id = _preparar_vinculo_turma(
        repos, escola_id="escola-1"
    )
    repo.escolas["escola-1"] = {"id": "escola-1", "nome": "Escola A"}
    repo.cursos["curso-1"] = {"id": "curso-1", "nome": "Curso A"}
    repo.disciplinas[disciplina_id].update(carga_horaria=40, qtd_aulas_prevista=10)
    repo._sync_disciplina_ids(professor_id, [disciplina_id])
    repo.professor_disciplinas.extend([
        {"id": "v-1", "professor_id": professor_id, "disciplina_id": disciplina_id, "turma_id": turma_id, "ativo": True},
        {"id": "v-2", "professor_id": professor_id, "disciplina_id": disciplina_id, "turma_id": "turma-fora", "ativo": True},
        {"id": "v-3", "professor_id": professor_id, "disciplina_id": disciplina_id, "turma_id": "turma-arquivada", "ativo": False},
        {"id": "v-4", "professor_id": professor_id, "disciplina_id": "nao-cadastrada", "turma_id": "turma-sem-disciplina", "ativo": True},
    ])
    repo.turmas.update({
        "turma-fora": {"id": "turma-fora", "nome": "Fora", "polo_id": "polo-2", "escola_id": "escola-2"},
        "turma-arquivada": {"id": "turma-arquivada", "nome": "Arquivada"},
        "turma-sem-disciplina": {"id": "turma-sem-disciplina", "nome": "Sem disciplina"},
    })
    auth.usuarios["aluno-usuario"] = {"id": "aluno-usuario", "nome": "Maria", "sobrenome": "Silva", "email": "maria@example.test"}
    repo.alunos["aluno-1"] = {"id": "aluno-1", "usuario_id": "aluno-usuario", "numero_matricula": "123"}
    repo.turma_alunos.extend([
        {"turma_id": turma_id, "aluno_id": "aluno-1", "status": "ativo"},
        {"turma_id": turma_id, "aluno_id": "aluno-1", "status": "ativo"},
        {"turma_id": turma_id, "aluno_id": "inativo", "status": "inativo"},
        {"turma_id": "turma-fora", "aluno_id": "aluno-1", "status": "ativo"},
    ])
    admin = await client.get(f"/professores/{professor_id}/detalhe", headers={"Authorization": f"Bearer {_token('admin-1')}"})
    assert admin.status_code == 200, admin.text
    body = admin.json()
    assert body["professor"]["horas_totais"] == 40
    assert body["disciplinas"][0]["curso_nome"] == "Curso A"
    assert {t["id"] for t in body["turmas"]} == {turma_id, "turma-fora"}
    turma = next(t for t in body["turmas"] if t["id"] == turma_id)
    assert turma["alunos"] == [{"id": "aluno-1", "nome": "Maria Silva", "numero_matricula": "123", "email": "maria@example.test"}]

    scoped = await client.get(f"/professores/{professor_id}/detalhe", headers={"Authorization": f"Bearer {_token('gestor-1')}"})
    assert scoped.status_code == 200, scoped.text
    assert [t["id"] for t in scoped.json()["turmas"]] == [turma_id]
    auth.usuarios["escola-gestora"] = {
        "id": "escola-gestora", "nome": "Gestora", "status": "ativo", "perfil_id": "p-escola",
        "polo_id": "polo-1", "escola_id": "escola-1",
    }
    escola = await client.get(
        f"/professores/{professor_id}/detalhe",
        headers={"Authorization": f"Bearer {_token('escola-gestora')}"},
    )
    assert escola.status_code == 200, escola.text
    assert [t["id"] for t in escola.json()["turmas"]] == [turma_id]
    auth.usuarios["gestor-1"]["polo_id"] = "polo-2"
    negado = await client.get(f"/professores/{professor_id}/detalhe", headers={"Authorization": f"Bearer {_token('gestor-1')}"})
    assert negado.status_code == 404


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


@pytest.mark.asyncio
async def test_vincular_usuario_aluno_muda_perfil_para_professor(client: AsyncClient, repos):
    auth_repo, professores_repo = repos
    auth_repo.usuarios["aluno-1"] = {
        **auth_repo.usuarios["prof-1"],
        "id": "aluno-1",
        "email": "aluno@nexus.com.br",
        "perfil_id": "p-aluno",
    }

    res = await client.post(
        "/professores/",
        json=_payload(usuario_id="aluno-1"),
        headers={"Authorization": f"Bearer {_token('admin-1')}"},
    )

    assert res.status_code == 201, res.text
    assert auth_repo.usuarios["aluno-1"]["perfil_id"] == "p-professor"
    assert any(
        log["acao"] == "usuario_perfil_alterado" and log["entidade_id"] == "aluno-1"
        for log in professores_repo.logs_auditoria
    )


@pytest.mark.asyncio
async def test_professor_consulta_apenas_suas_disciplinas_e_turmas(client: AsyncClient, repos):
    auth_repo, professores_repo = repos
    auth_repo.usuarios["prof-2"] = {
        **auth_repo.usuarios["prof-1"],
        "id": "prof-2",
        "nome": "Bruno",
        "email": "bruno@nexus.com.br",
    }
    professores_repo.professores.update(
        {
            "docente-1": {"id": "docente-1", "usuario_id": "prof-1"},
            "docente-2": {"id": "docente-2", "usuario_id": "prof-2"},
        }
    )
    professores_repo._sync_disciplina_ids("docente-1", ["disciplina-com-turma", "disciplina-sem-turma"])
    professores_repo._sync_disciplina_ids("docente-2", ["disciplina-de-outro-docente"])
    professores_repo.professor_disciplinas.append(
        {
            "id": "vinculo-1",
            "professor_id": "docente-1",
            "disciplina_id": "disciplina-com-turma",
            "turma_id": "turma-1",
        }
    )
    professores_repo.disciplinas.update(
        {
            "disciplina-com-turma": {
                "id": "disciplina-com-turma",
                "nome": "Matemática",
                "curso_id": "curso-1",
                "semestre": 2,
                "carga_horaria": 60,
                "qtd_aulas_prevista": 15,
            },
            "disciplina-sem-turma": {
                "id": "disciplina-sem-turma",
                "nome": "Física",
            },
            "disciplina-de-outro-docente": {
                "id": "disciplina-de-outro-docente",
                "nome": "Química",
            },
        }
    )
    professores_repo.cursos["curso-1"] = {"id": "curso-1", "nome": "Licenciatura"}
    professores_repo.turmas["turma-1"] = {
        "id": "turma-1",
        "nome": "Turma A",
        "data_inicio": "2026-03-01",
        "data_fim": "2026-12-01",
        "polo_id": "polo-1",
    }

    resposta = await client.get(
        "/professores/me/disciplinas?usuario_id=prof-2",
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert resposta.status_code == 200, resposta.text
    itens = {item["id"]: item for item in resposta.json()["items"]}
    assert set(itens) == {"disciplina-com-turma", "disciplina-sem-turma"}
    assert itens["disciplina-com-turma"]["curso_nome"] == "Licenciatura"
    assert itens["disciplina-com-turma"]["turmas"] == [
        {
            "id": "turma-1",
            "nome": "Turma A",
            "professor_disciplina_id": "vinculo-1",
            "data_inicio": "2026-03-01",
            "data_fim": "2026-12-01",
            "polo_nome": "Polo Central",
            "escola_nome": None,
        }
    ]
    assert itens["disciplina-sem-turma"]["turmas"] == []

    outra_resposta = await client.get(
        "/professores/me/disciplinas",
        headers={"Authorization": f"Bearer {_token('prof-2')}"},
    )
    assert outra_resposta.status_code == 200
    assert [item["id"] for item in outra_resposta.json()["items"]] == [
        "disciplina-de-outro-docente"
    ]


@pytest.mark.asyncio
async def test_professor_consulta_apenas_seus_conteudos_e_materiais(client: AsyncClient, repos):
    auth_repo, professores_repo = repos
    auth_repo.usuarios["prof-2"] = {
        **auth_repo.usuarios["prof-1"],
        "id": "prof-2",
        "nome": "Bruno",
        "email": "bruno@nexus.com.br",
    }
    professores_repo.professores.update(
        {
            "docente-1": {"id": "docente-1", "usuario_id": "prof-1"},
            "docente-2": {"id": "docente-2", "usuario_id": "prof-2"},
        }
    )
    professores_repo._sync_disciplina_ids("docente-1", ["disciplina-1"])
    professores_repo.professor_disciplinas.extend(
        [
            {
                "id": "vinculo-1",
                "professor_id": "docente-1",
                "disciplina_id": "disciplina-1",
                "turma_id": "turma-1",
            },
            {
                "id": "vinculo-2",
                "professor_id": "docente-2",
                "disciplina_id": "disciplina-2",
                "turma_id": "turma-2",
            },
        ]
    )
    professores_repo.disciplinas.update(
        {
            "disciplina-1": {"id": "disciplina-1", "nome": "Matemática"},
            "disciplina-2": {"id": "disciplina-2", "nome": "Física"},
        }
    )
    professores_repo.turmas.update(
        {
            "turma-1": {"id": "turma-1", "nome": "Turma A"},
            "turma-2": {"id": "turma-2", "nome": "Turma B"},
        }
    )
    professores_repo.disciplina_conteudos.extend(
        [
            {
                "id": "conteudo-1",
                "disciplina_id": "disciplina-1",
                "titulo": "Aula de funções",
                "tipo_midia": "video",
                "url_arquivo": "https://example.test/aula",
                "ordem": 1,
            },
            {
                "id": "conteudo-2",
                "disciplina_id": "disciplina-2",
                "titulo": "Conteúdo de outro docente",
            },
        ]
    )
    professores_repo.professor_materiais.extend(
        [
            {
                "id": "material-1",
                "professor_disciplina_id": "vinculo-1",
                "arquivo_url": "https://example.test/material",
                "descricao": "Lista de exercícios",
            },
            {
                "id": "material-2",
                "professor_disciplina_id": "vinculo-2",
                "arquivo_url": "https://example.test/outro-material",
            },
        ]
    )

    resposta = await client.get(
        "/professores/me/conteudos?usuario_id=prof-2",
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )

    assert resposta.status_code == 200, resposta.text
    itens = resposta.json()["items"]
    assert [item["id"] for item in itens] == ["disciplina-1"]
    assert [item["id"] for item in itens[0]["conteudos"]] == ["conteudo-1"]
    assert [item["id"] for item in itens[0]["materiais"]] == ["material-1"]
    assert itens[0]["materiais"][0]["turma_nome"] == "Turma A"


@pytest.mark.asyncio
async def test_professor_cria_edita_e_baixa_arquivo_de_conteudo(
    client: AsyncClient, repos, monkeypatch, tmp_path
):
    auth_repo, professores_repo = repos
    auth_repo.usuarios["prof-2"] = {
        **auth_repo.usuarios["prof-1"],
        "id": "prof-2",
        "nome": "Bruno",
    }
    professores_repo.professores.update(
        {
            "docente-1": {"id": "docente-1", "usuario_id": "prof-1"},
            "docente-2": {"id": "docente-2", "usuario_id": "prof-2"},
        }
    )
    professores_repo._sync_disciplina_ids("docente-1", ["disciplina-1"])
    professores_repo.disciplinas["disciplina-1"] = {"id": "disciplina-1", "nome": "Matemática"}
    monkeypatch.setattr(file_storage_module, "_uses_blob_storage", lambda: False)
    monkeypatch.setattr(file_storage_module, "ACADEMIC_FILES_DIRECTORY", tmp_path)

    criado = await client.post(
        "/professores/me/conteudos",
        data={
            "disciplina_id": "disciplina-1",
            "titulo": "Aula em PDF",
            "tipo_midia": "documento",
            "ordem": "1",
            "modo": "arquivo",
        },
        files={"arquivo": ("aula.pdf", b"%PDF-1.7\nconteudo", "application/pdf")},
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )

    assert criado.status_code == 201, criado.text
    item = criado.json()
    assert item["tem_arquivo"] is True
    assert item["arquivo_nome"] == "aula.pdf"
    assert "arquivo_storage_key" not in item
    stored_path = next(tmp_path.iterdir())
    assert stored_path.read_bytes() == b"%PDF-1.7\nconteudo"

    download = await client.get(
        f"/professores/me/conteudos/{item['id']}/arquivo",
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-1.7\nconteudo"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["cache-control"] == "private, no-store"

    atualizado = await client.put(
        f"/professores/me/conteudos/{item['id']}",
        data={
            "titulo": "Aula revisada",
            "tipo_midia": "link",
            "ordem": "2",
            "modo": "link",
            "url_arquivo": "https://example.test/aula",
        },
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert atualizado.status_code == 200, atualizado.text
    assert atualizado.json()["titulo"] == "Aula revisada"
    assert atualizado.json()["url_arquivo"] == "https://example.test/aula"
    assert atualizado.json()["tem_arquivo"] is False
    assert list(tmp_path.iterdir()) == []

    negado = await client.post(
        "/professores/me/conteudos",
        data={
            "disciplina_id": "disciplina-1",
            "titulo": "Não autorizado",
            "modo": "link",
            "url_arquivo": "https://example.test",
        },
        headers={"Authorization": f"Bearer {_token('prof-2')}"},
    )
    assert negado.status_code == 403

    formato_invalido = await client.post(
        "/professores/me/conteudos",
        data={
            "disciplina_id": "disciplina-1",
            "titulo": "Formato inválido",
            "modo": "arquivo",
        },
        files={"arquivo": ("aula.svg", b"<svg></svg>", "image/svg+xml")},
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert formato_invalido.status_code == 415

    arquivo_grande = await client.post(
        "/professores/me/conteudos",
        data={
            "disciplina_id": "disciplina-1",
            "titulo": "Arquivo grande",
            "modo": "arquivo",
        },
        files={
            "arquivo": (
                "aula.pdf",
                b"%PDF-1.7\n" + b"x" * (4 * 1024 * 1024),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert arquivo_grande.status_code == 413


@pytest.mark.asyncio
async def test_professor_cadastra_material_apenas_em_vinculo_com_turma(
    client: AsyncClient, repos, monkeypatch, tmp_path
):
    auth_repo, professores_repo = repos
    auth_repo.usuarios["prof-2"] = {
        **auth_repo.usuarios["prof-1"],
        "id": "prof-2",
        "nome": "Bruno",
    }
    professores_repo.professores["docente-1"] = {
        "id": "docente-1",
        "usuario_id": "prof-1",
    }
    professores_repo.professor_disciplinas.append(
        {
            "id": "vinculo-1",
            "professor_id": "docente-1",
            "disciplina_id": "disciplina-1",
            "turma_id": "turma-1",
        }
    )
    professores_repo.disciplinas["disciplina-1"] = {"id": "disciplina-1", "nome": "Matemática"}
    professores_repo.turmas["turma-1"] = {"id": "turma-1", "nome": "Turma A"}
    monkeypatch.setattr(file_storage_module, "_uses_blob_storage", lambda: False)
    monkeypatch.setattr(file_storage_module, "ACADEMIC_FILES_DIRECTORY", tmp_path)

    criado = await client.post(
        "/professores/me/materiais",
        data={
            "professor_disciplina_id": "vinculo-1",
            "descricao": "Leitura complementar",
            "modo": "link",
            "url_arquivo": "https://example.test/leitura",
            "data_aula": "2026-03-10",
        },
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )

    assert criado.status_code == 201, criado.text
    assert criado.json()["turma_id"] == "turma-1"
    assert criado.json()["arquivo_url"] == "https://example.test/leitura"

    material_id = criado.json()["id"]
    atualizado = await client.put(
        f"/professores/me/materiais/{material_id}",
        data={
            "descricao": "Material em PDF",
            "modo": "arquivo",
            "data_aula": "2026-03-10",
        },
        files={"arquivo": ("leitura.pdf", b"%PDF-1.7\nconteudo", "application/pdf")},
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert atualizado.status_code == 200, atualizado.text
    assert atualizado.json()["tem_arquivo"] is True
    assert atualizado.json()["arquivo_nome"] == "leitura.pdf"

    download = await client.get(
        f"/professores/me/materiais/{material_id}/arquivo",
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-1.7\nconteudo"

    negado = await client.post(
        "/professores/me/materiais",
        data={
            "professor_disciplina_id": "vinculo-1",
            "descricao": "Material de outra turma",
            "modo": "link",
            "url_arquivo": "https://example.test/outro",
        },
        headers={"Authorization": f"Bearer {_token('prof-2')}"},
    )
    assert negado.status_code == 403


@pytest.mark.asyncio
async def test_gestao_de_vinculos_turma_arquiva_sem_apagar_materiais(client: AsyncClient, repos):
    _, professores_repo, professor_id, disciplina_id, turma_id = _preparar_vinculo_turma(repos)
    headers = {"Authorization": f"Bearer {_token('admin-1')}"}
    payload = {"professor_id": professor_id, "disciplina_id": disciplina_id}

    criado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json=payload,
        headers=headers,
    )
    assert criado.status_code == 201, criado.text
    vinculo = criado.json()
    assert vinculo["professor_id"] == professor_id
    assert vinculo["disciplina_id"] == disciplina_id
    assert vinculo["turma_id"] == turma_id

    professores_repo.professor_materiais.append(
        {
            "id": "material-preservado",
            "professor_disciplina_id": vinculo["id"],
            "arquivo_url": "https://example.test/aula",
            "descricao": "Material existente",
        }
    )
    duplicado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json=payload,
        headers=headers,
    )
    assert duplicado.status_code == 409

    arquivado = await client.delete(
        f"/professores/turmas/{turma_id}/vinculos/{vinculo['id']}",
        headers=headers,
    )
    assert arquivado.status_code == 200
    assert "preservados" in arquivado.json()["message"]
    assert professores_repo.professor_materiais[0]["id"] == "material-preservado"
    assert professores_repo.list_vinculos_ativos_por_turma(turma_id) == []
    professor_conteudos = await client.get(
        "/professores/me/conteudos",
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert professor_conteudos.status_code == 200
    assert professor_conteudos.json()["items"] == []

    reativado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json=payload,
        headers=headers,
    )
    assert reativado.status_code == 201, reativado.text
    assert reativado.json()["id"] == vinculo["id"]
    assert len(professores_repo.professor_disciplinas) == 1


@pytest.mark.asyncio
async def test_gestores_polo_e_escola_so_acessam_vinculos_no_proprio_escopo(
    client: AsyncClient, repos
):
    auth_repo, professores_repo, professor_id, disciplina_id, turma_id = _preparar_vinculo_turma(
        repos, escola_id="escola-1"
    )
    professores_repo.escolas["escola-1"] = {"id": "escola-1", "nome": "Escola"}
    auth_repo.usuarios["escola-1"] = {
        "id": "escola-1",
        "nome": "Gestora",
        "email": "gestora@nexus.com.br",
        "status": "ativo",
        "perfil_id": "p-escola",
        "polo_id": "polo-1",
        "escola_id": "escola-1",
    }
    headers = {"Authorization": f"Bearer {_token('escola-1')}"}
    criado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json={"professor_id": professor_id, "disciplina_id": disciplina_id},
        headers=headers,
    )
    assert criado.status_code == 201, criado.text

    polo_headers = {"Authorization": f"Bearer {_token('gestor-1')}"}
    polo_duplicado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json={"professor_id": professor_id, "disciplina_id": disciplina_id},
        headers=polo_headers,
    )
    assert polo_duplicado.status_code == 409

    professores_repo.turmas[turma_id]["escola_id"] = "outra-escola"
    negado = await client.get(
        f"/professores/turmas/{turma_id}/vinculos",
        headers=headers,
    )
    assert negado.status_code == 403

    professores_repo.turmas[turma_id]["escola_id"] = "escola-1"
    professores_repo.turmas[turma_id]["polo_id"] = "polo-2"
    polo_negado = await client.get(
        f"/professores/turmas/{turma_id}/vinculos",
        headers=polo_headers,
    )
    assert polo_negado.status_code == 403
    professor_negado = await client.get(
        f"/professores/turmas/{turma_id}/vinculos",
        headers={"Authorization": f"Bearer {_token('prof-1')}"},
    )
    assert professor_negado.status_code == 403


@pytest.mark.asyncio
async def test_vinculo_rejeita_disciplina_de_outro_curso(client: AsyncClient, repos):
    _, professores_repo, professor_id, disciplina_id, turma_id = _preparar_vinculo_turma(repos)
    outra_disciplina = str(uuid.UUID(int=104))
    professores_repo.disciplinas[outra_disciplina] = {
        "id": outra_disciplina,
        "nome": "Química",
        "curso_id": "curso-2",
    }

    resposta = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json={"professor_id": professor_id, "disciplina_id": outra_disciplina},
        headers={"Authorization": f"Bearer {_token('admin-1')}"},
    )

    assert resposta.status_code == 400
    assert "curso da turma" in resposta.json()["detail"]


@pytest.mark.asyncio
async def test_consulta_de_disciplinas_exige_perfil_autorizado(client: AsyncClient):
    headers = {"Authorization": f"Bearer {_token('gestor-1')}"}
    resposta = await client.get(
        "/professores/me/disciplinas",
        headers=headers,
    )
    assert resposta.status_code == 403
    conteudos = await client.get("/professores/me/conteudos", headers=headers)
    assert conteudos.status_code == 403


@pytest.mark.asyncio
async def test_cadastro_completa_registro_criado_pelo_perfil(client: AsyncClient, repos):
    _, professores_repo = repos
    professores_repo.professores["auto-1"] = {
        "id": "auto-1",
        "usuario_id": "prof-1",
        "status": "ativo",
        "materias": [],
        "quantidade_aulas": 0,
        "horas_totais": 0,
    }
    headers = {"Authorization": f"Bearer {_token('admin-1')}"}

    res = await client.post("/professores/", json=_payload(), headers=headers)
    duplicado = await client.post("/professores/", json=_payload(), headers=headers)

    assert res.status_code == 201, res.text
    assert res.json()["id"] == "auto-1"
    assert res.json()["materias"] == ["Matemática", "Física"]
    assert len(professores_repo.professores) == 1
    assert duplicado.status_code == 400


# ---------------------------------------------------------------------------
# Lotações: professor em N polos / N escolas
# ---------------------------------------------------------------------------

POLO_A = str(uuid.UUID(int=201))
POLO_B = str(uuid.UUID(int=202))
ESCOLA_A1 = str(uuid.UUID(int=211))
ESCOLA_B1 = str(uuid.UUID(int=221))


def _preparar_lotacoes(repos):
    """Professor lotado no polo A; gestor do polo B; turma no polo B / escola B1."""
    auth_repo, professores_repo, professor_id, disciplina_id, turma_id = _preparar_vinculo_turma(
        repos, polo_id=POLO_A
    )
    professores_repo.polos.update({
        POLO_A: {"id": POLO_A, "nome": "Polo A"},
        POLO_B: {"id": POLO_B, "nome": "Polo B"},
    })
    professores_repo.escolas.update({
        ESCOLA_A1: {"id": ESCOLA_A1, "nome": "Escola A1", "polo_id": POLO_A},
        ESCOLA_B1: {"id": ESCOLA_B1, "nome": "Escola B1", "polo_id": POLO_B},
    })
    professores_repo.turmas[turma_id].update({"polo_id": POLO_B, "escola_id": ESCOLA_B1})
    professores_repo.professores[professor_id].update({"pix": "chave-pix", "valor_hora_aula": 80})
    for user_id, polo_id in (("gestor-a", POLO_A), ("gestor-b", POLO_B)):
        auth_repo.usuarios[user_id] = {
            **auth_repo.usuarios["gestor-1"], "id": user_id, "polo_id": polo_id,
            "email": f"{user_id}@nexus.com.br",
        }
    return professores_repo, professor_id, disciplina_id, turma_id


def _h(user_id: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id)}"}


@pytest.mark.asyncio
async def test_admin_cadastra_professor_com_varias_lotacoes(client: AsyncClient, repos):
    _, professores_repo = repos
    professores_repo.polos.update({POLO_A: {"id": POLO_A, "nome": "Polo A"}, POLO_B: {"id": POLO_B, "nome": "Polo B"}})
    professores_repo.escolas[ESCOLA_A1] = {"id": ESCOLA_A1, "nome": "Escola A1", "polo_id": POLO_A}
    payload = {
        **_payload(),
        "polo_id": None,
        "lotacoes": [
            {"polo_id": POLO_A},
            {"escola_id": ESCOLA_A1},  # polo deduzido da escola
            {"polo_id": POLO_B},
            {"polo_id": POLO_B},  # repetida: ignorada
        ],
    }
    criado = await client.post("/professores/", json=payload, headers=_h("admin-1"))
    assert criado.status_code == 201, criado.text
    lotacoes = criado.json()["lotacoes"]
    assert {(l["polo_id"], l["escola_id"]) for l in lotacoes} == {
        (POLO_A, None), (POLO_A, ESCOLA_A1), (POLO_B, None)
    }
    assert criado.json()["polo_id"] in {POLO_A, POLO_B}

    invalido = await client.put(
        f"/professores/{criado.json()['id']}",
        json={"lotacoes": [{"polo_id": POLO_B, "escola_id": ESCOLA_A1}]},
        headers=_h("admin-1"),
    )
    assert invalido.status_code == 400
    assert "não pertence ao polo" in invalido.json()["detail"]

    substituido = await client.put(
        f"/professores/{criado.json()['id']}",
        json={"lotacoes": [{"polo_id": POLO_B}]},
        headers=_h("admin-1"),
    )
    assert substituido.status_code == 200, substituido.text
    assert [l["polo_id"] for l in substituido.json()["lotacoes"]] == [POLO_B]
    assert substituido.json()["polo_id"] == POLO_B


@pytest.mark.asyncio
async def test_gestor_associa_professor_de_outro_polo_e_passa_a_ve_lo(client: AsyncClient, repos):
    professores_repo, professor_id, disciplina_id, turma_id = _preparar_lotacoes(repos)

    antes = await client.get("/professores/", headers=_h("gestor-b"))
    assert antes.json()["total"] == 0
    assert (await client.get(f"/professores/{professor_id}", headers=_h("gestor-b"))).status_code == 404

    # A busca para associar enxerga professores de qualquer unidade, sem dados sensíveis.
    disponiveis = await client.get("/professores/disponiveis", headers=_h("gestor-b"))
    assert disponiveis.status_code == 200, disponiveis.text
    item = next(i for i in disponiveis.json()["items"] if i["id"] == professor_id)
    assert "pix" not in item and "valor_hora_aula" not in item
    assert item["lotacoes"][0]["polo_id"] == POLO_A

    criado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json={"professor_id": professor_id, "disciplina_id": disciplina_id},
        headers=_h("gestor-b"),
    )
    assert criado.status_code == 201, criado.text

    lotacoes = {(l["polo_id"], l.get("escola_id")) for l in professores_repo.list_lotacoes(professor_id)}
    assert lotacoes == {(POLO_A, None), (POLO_B, ESCOLA_B1)}
    assert any(log["acao"] == "professor_lotacao_incluida" for log in professores_repo.logs_auditoria)

    depois = await client.get("/professores/", headers=_h("gestor-b"))
    assert depois.json()["total"] == 1
    # Cada gestor continua vendo o professor, mas o detalhe só traz as turmas da sua unidade.
    detalhe_b = await client.get(f"/professores/{professor_id}/detalhe", headers=_h("gestor-b"))
    assert detalhe_b.status_code == 200, detalhe_b.text
    detalhe_a = await client.get(f"/professores/{professor_id}/detalhe", headers=_h("gestor-a"))
    assert detalhe_a.status_code == 200
    assert detalhe_a.json()["turmas"] == []


@pytest.mark.asyncio
async def test_gestor_so_altera_lotacao_da_propria_unidade(client: AsyncClient, repos):
    professores_repo, professor_id, _, _ = _preparar_lotacoes(repos)

    negado = await client.post(
        f"/professores/{professor_id}/lotacoes", json={"polo_id": POLO_A}, headers=_h("gestor-b")
    )
    assert negado.status_code == 403

    incluida = await client.post(
        f"/professores/{professor_id}/lotacoes", json={"polo_id": POLO_B}, headers=_h("gestor-b")
    )
    assert incluida.status_code == 200, incluida.text
    lotacoes = {l["polo_id"]: l["id"] for l in incluida.json()["lotacoes"]}
    assert set(lotacoes) == {POLO_A, POLO_B}

    remover_a = await client.delete(
        f"/professores/{professor_id}/lotacoes/{lotacoes[POLO_A]}", headers=_h("gestor-b")
    )
    assert remover_a.status_code == 403

    removida = await client.delete(
        f"/professores/{professor_id}/lotacoes/{lotacoes[POLO_B]}", headers=_h("gestor-b")
    )
    assert removida.status_code == 200, removida.text
    assert [l["polo_id"] for l in removida.json()["lotacoes"]] == [POLO_A]

    ultima = await client.delete(
        f"/professores/{professor_id}/lotacoes/{lotacoes[POLO_A]}", headers=_h("admin-1")
    )
    assert ultima.status_code == 409


@pytest.mark.asyncio
async def test_lotacao_com_turma_ativa_nao_pode_ser_removida(client: AsyncClient, repos):
    professores_repo, professor_id, disciplina_id, turma_id = _preparar_lotacoes(repos)
    criado = await client.post(
        f"/professores/turmas/{turma_id}/vinculos",
        json={"professor_id": professor_id, "disciplina_id": disciplina_id},
        headers=_h("admin-1"),
    )
    assert criado.status_code == 201, criado.text
    lotacao_b = next(l for l in professores_repo.list_lotacoes(professor_id) if l["polo_id"] == POLO_B)

    bloqueada = await client.delete(
        f"/professores/{professor_id}/lotacoes/{lotacao_b['id']}", headers=_h("admin-1")
    )
    assert bloqueada.status_code == 409
    assert "leciona" in bloqueada.json()["detail"]

    await client.delete(f"/professores/turmas/{turma_id}/vinculos/{criado.json()['id']}", headers=_h("admin-1"))
    liberada = await client.delete(
        f"/professores/{professor_id}/lotacoes/{lotacao_b['id']}", headers=_h("admin-1")
    )
    assert liberada.status_code == 200, liberada.text
