"""Testes automatizados cobrindo os módulos de negócio 03 a 18 do NEXUS 2.0."""
from __future__ import annotations

from datetime import date, datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.admin.repository import InMemoryAdminRepository, set_admin_repository
from app.modules import cursos_disciplinas as cursos_disciplinas_module
from app.modules import turmas as turmas_module
from app.modules.polos_escolas import repository as polos_repository_module
from app.modules.polos_escolas.repository import InMemoryPolosEscolasRepository
from app.modules.transferencias import repository as transferencias_repository_module
from app.modules.transferencias.repository import InMemoryTransferenciasRepository


@pytest.fixture
def auth_setup():
    auth_repo = InMemoryAuthRepository()
    admin_repo = InMemoryAdminRepository()

    # Admin
    auth_repo.usuarios["admin-1"] = {
        "id": "admin-1",
        "nome": "Admin",
        "email": "admin@nexus.com.br",
        "status": "ativo",
        "perfil_id": "p-admin",
        "permissoes": [],
    }
    # Polo
    auth_repo.usuarios["polo-1"] = {
        "id": "polo-1",
        "nome": "Gestor Polo",
        "email": "polo@nexus.com.br",
        "status": "ativo",
        "perfil_id": "p-polo",
        "permissoes": ["p_vendas", "p_matriculas"],
        "polo_id": "polo-1",
        "escola_id": None,
    }
    auth_repo.usuarios["escola-1"] = {
        "id": "escola-1",
        "nome": "Gestor Escola",
        "email": "escola@nexus.com.br",
        "status": "ativo",
        "perfil_id": "p-escola",
        "permissoes": [],
        "polo_id": "polo-1",
        "escola_id": "escola-1",
    }
    # Professor
    auth_repo.usuarios["prof-1"] = {
        "id": "prof-1",
        "nome": "Prof",
        "email": "prof@nexus.com.br",
        "status": "ativo",
        "perfil_id": "p-prof",
        "permissoes": ["p_academico"],
    }
    # Aluno
    auth_repo.usuarios["aluno-1"] = {
        "id": "aluno-1",
        "nome": "Aluno",
        "email": "aluno@nexus.com.br",
        "status": "ativo",
        "perfil_id": "p-aluno",
        "permissoes": [],
    }

    set_auth_repository(auth_repo)
    set_admin_repository(admin_repo)
    return auth_repo


@pytest_asyncio.fixture
async def client(auth_setup):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _token(user_id: str, email: str, role: str) -> str:
    return create_access_token({
        "sub": user_id,
        "email": email,
        "perfil": role,
        "permissoes": [],
    })


# Nota: os testes dos módulos legados `professores`, `alunos`, `presencas`,
# `licencas` e `financeiro`, além do antigo teste de "Polos & Escolas" via
# `/unidades/*`, foram removidos: essas funcionalidades foram absorvidas pelo
# módulo `polos_escolas` (ver tests/test_polos_escolas.py e
# docs/Requisitos_Nexus2.0(Polo_Escola).md).


# 06 & 07. Cursos e Disciplinas (AVA)
@pytest.mark.asyncio
async def test_modulo_cursos_e_disciplinas(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "PG_DSN", "")
    monkeypatch.setattr(cursos_disciplinas_module, "get_db_cursor", lambda: None)
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    c_res = await client.post(
        "/cursos-disciplinas/cursos",
        json={
            "nome": "Teologia Sistemática",
            "descricao": "Formação acadêmica em teologia.",
            "modalidade": "hibrido",
            "carga_horaria_total": 2400,
            "semestres": 4,
            "status": "ativo",
            "nivel_academico": "bacharelado",
        },
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert c_res.status_code == 201
    assert c_res.json()["nivel_academico"] == "bacharelado"
    assert c_res.json()["descricao"] == "Formação acadêmica em teologia."
    assert c_res.json()["carga_horaria_total"] == 2400
    assert c_res.json()["status"] == "ativo"
    acesso_escrita_negado = await client.post(
        "/cursos-disciplinas/cursos",
        json={
            "nome": "Curso por Polo",
            "descricao": "Não deve ser cadastrado pelo Polo.",
            "modalidade": "ead",
            "carga_horaria_total": 100,
            "semestres": 2,
            "status": "ativo",
            "nivel_academico": "bacharelado",
        },
        headers={"Authorization": f"Bearer {_token('polo-1', 'polo@nexus.com.br', 'polo')}"},
    )
    assert acesso_escrita_negado.status_code == 403
    curso_invalido = await client.post(
        "/cursos-disciplinas/cursos",
        json={
            "nome": "Curso inválido",
            "descricao": "Descrição",
            "modalidade": "ead",
            "carga_horaria_total": 100,
            "semestres": 2,
            "status": "ativo",
            "nivel_academico": "doutorado",
        },
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert curso_invalido.status_code == 422
    curso_incompleto = await client.post(
        "/cursos-disciplinas/cursos",
        json={"nome": "Curso incompleto"},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert curso_incompleto.status_code == 422
    curso_id = c_res.json()["id"]

    cursos_res = await client.get(
        "/cursos-disciplinas/cursos",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert cursos_res.status_code == 200
    curso_listado = next(curso for curso in cursos_res.json() if curso["id"] == curso_id)
    assert curso_listado["nome"] == "Teologia Sistemática"
    assert curso_listado["nivel_academico"] == "bacharelado"

    disciplina_ids = []
    for nome, curso_atual in (
        ("Fundamentos", None),
        ("Ética", None),
        ("Introdução", curso_id),
    ):
        disciplina = await client.post(
            "/cursos-disciplinas/disciplinas",
            json={"nome": nome, "curso_id": curso_atual},
            headers={"Authorization": f"Bearer {t_admin}"},
        )
        assert disciplina.status_code == 201
        disciplina_ids.append(disciplina.json()["id"])

    curso_com_disciplinas = await client.post(
        "/cursos-disciplinas/cursos",
        json={
            "nome": "Curso com disciplinas",
            "descricao": "Curso com matriz vinculada",
            "modalidade": "hibrido",
            "carga_horaria_total": 120,
            "semestres": 2,
            "status": "ativo",
            "nivel_academico": "bacharelado",
            "disciplina_ids": disciplina_ids,
        },
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert curso_com_disciplinas.status_code == 201
    novo_curso_id = curso_com_disciplinas.json()["id"]

    cursos_paginados = await client.get(
        "/cursos-disciplinas/cursos/paginados",
        params={"q": "Curso com disciplinas", "limit": 10, "offset": 0},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert cursos_paginados.status_code == 200
    assert cursos_paginados.json()["total"] == 1
    assert [item["id"] for item in cursos_paginados.json()["items"]] == [novo_curso_id]

    disciplinas_vinculadas = await client.get(
        "/cursos-disciplinas/disciplinas",
        params={"curso_id": novo_curso_id},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert {item["id"] for item in disciplinas_vinculadas.json()} == set(disciplina_ids)

    disciplinas_curso_anterior = await client.get(
        "/cursos-disciplinas/disciplinas",
        params={"curso_id": curso_id},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert all(item["id"] != disciplina_ids[-1] for item in disciplinas_curso_anterior.json())

    curso_com_disciplina_inexistente = await client.post(
        "/cursos-disciplinas/cursos",
        json={
            "nome": "Curso sem criação parcial",
            "descricao": "Não deve ser salvo",
            "modalidade": "hibrido",
            "carga_horaria_total": 120,
            "semestres": 2,
            "status": "ativo",
            "nivel_academico": "bacharelado",
            "disciplina_ids": ["00000000-0000-0000-0000-000000000001"],
        },
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert curso_com_disciplina_inexistente.status_code == 404

    cursos_apos_erro = await client.get(
        "/cursos-disciplinas/cursos",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert all(curso["nome"] != "Curso sem criação parcial" for curso in cursos_apos_erro.json())

    for user_id, email, role in (
        ("polo-1", "polo@nexus.com.br", "polo"),
        ("escola-1", "escola@nexus.com.br", "escola"),
    ):
        leitura = await client.get(
            "/cursos-disciplinas/cursos",
            headers={"Authorization": f"Bearer {_token(user_id, email, role)}"},
        )
        assert leitura.status_code == 200

    d_res = await client.post(
        "/cursos-disciplinas/disciplinas",
        json={"curso_id": curso_id, "semestre": 1, "nome": "Bibliologia", "ordem": 1},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert d_res.status_code == 201
    disc_id = d_res.json()["id"]

    disciplinas_curso = await client.get(
        "/cursos-disciplinas/disciplinas",
        params={"curso_id": curso_id},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert disciplinas_curso.status_code == 200
    assert any(disciplina["id"] == disc_id for disciplina in disciplinas_curso.json())

    for user_id, email, role in (
        ("polo-1", "polo@nexus.com.br", "polo"),
        ("escola-1", "escola@nexus.com.br", "escola"),
    ):
        leitura = await client.get(
            "/cursos-disciplinas/disciplinas",
            headers={"Authorization": f"Bearer {_token(user_id, email, role)}"},
        )
        assert leitura.status_code == 200

        atualizacao_negada = await client.put(
            f"/cursos-disciplinas/disciplinas/{disc_id}",
            json={"nome": "Alteração não autorizada"},
            headers={"Authorization": f"Bearer {_token(user_id, email, role)}"},
        )
        assert atualizacao_negada.status_code == 403

        exclusao_negada = await client.delete(
            f"/cursos-disciplinas/disciplinas/{disc_id}",
            headers={"Authorization": f"Bearer {_token(user_id, email, role)}"},
        )
        assert exclusao_negada.status_code == 403

    disciplina_atualizada = await client.put(
        f"/cursos-disciplinas/disciplinas/{disc_id}",
        json={
            "curso_id": curso_id,
            "semestre": 2,
            "nome": "Bibliologia atualizada",
            "ordem": 2,
            "carga_horaria": 50,
            "qtd_aulas_prevista": 12,
            "tipo": "presencial",
            "eh_extra_grade": False,
        },
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert disciplina_atualizada.status_code == 200
    assert disciplina_atualizada.json()["nome"] == "Bibliologia atualizada"
    assert disciplina_atualizada.json()["semestre"] == 2

    disciplina_sem_vinculo = await client.post(
        "/cursos-disciplinas/disciplinas",
        json={"nome": "Optativa sem curso", "curso_id": None, "semestre": None},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert disciplina_sem_vinculo.status_code == 201
    assert disciplina_sem_vinculo.json()["curso_id"] is None
    assert disciplina_sem_vinculo.json()["semestre"] is None

    disciplina_semestre_zero = await client.post(
        "/cursos-disciplinas/disciplinas",
        json={"nome": "Disciplina importada", "semestre": 0},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert disciplina_semestre_zero.status_code == 201
    assert disciplina_semestre_zero.json()["semestre"] == 0

    lista_semestre_zero = await client.get(
        "/cursos-disciplinas/disciplinas",
        params={"semestre": 0},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert lista_semestre_zero.status_code == 200
    assert any(
        item["id"] == disciplina_semestre_zero.json()["id"]
        and item["semestre"] == 0
        for item in lista_semestre_zero.json()
    )

    exclusao_livre = await client.delete(
        f"/cursos-disciplinas/disciplinas/{disciplina_sem_vinculo.json()['id']}",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert exclusao_livre.status_code == 204

    turma_res = await client.post(
        "/turmas",
        json={"nome": "Turma do Curso", "curso_id": curso_id},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert turma_res.status_code == 201
    turmas_curso = await client.get(
        "/turmas",
        params={"curso_id": curso_id},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert turmas_curso.status_code == 200
    assert any(turma["id"] == turma_res.json()["id"] for turma in turmas_curso.json())

    detalhes_curso = await client.get(
        f"/turmas/cursos/{curso_id}/detalhes",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert detalhes_curso.status_code == 200
    assert any(item["id"] == disc_id for item in detalhes_curso.json()["disciplinas"])
    assert any(
        item["id"] == turma_res.json()["id"]
        for item in detalhes_curso.json()["turmas"]
    )

    cont_res = await client.post(
        f"/cursos-disciplinas/disciplinas/{disc_id}/conteudos",
        json={"disciplina_id": disc_id, "titulo": "Videoaula 1", "tipo_midia": "video", "ordem": 1},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert cont_res.status_code == 201
    exclusao_com_conteudo = await client.delete(
        f"/cursos-disciplinas/disciplinas/{disc_id}",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert exclusao_com_conteudo.status_code == 409


# 08. Turmas e Calendários
@pytest.mark.asyncio
async def test_modulo_turmas_e_calendarios(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "PG_DSN", "")
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    t_res = await client.post(
        "/turmas",
        json={"nome": "Turma 2026.1 Noturno"},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert t_res.status_code == 201
    turma_id = t_res.json()["id"]

    m_res = await client.post(
        f"/turmas/{turma_id}/matricular-aluno?aluno_id=aluno-1",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert m_res.status_code == 200


POLO_A = "11111111-1111-1111-1111-111111111111"
POLO_B = "22222222-2222-2222-2222-222222222222"
ESCOLA_A = "33333333-3333-3333-3333-333333333333"
ESCOLA_B = "44444444-4444-4444-4444-444444444444"


@pytest.fixture
def turmas_setup(auth_setup, monkeypatch):
    """Isola o estado em memória de turmas e cria usuários com escopo nos dois nomes de perfil."""
    monkeypatch.setattr(settings, "PG_DSN", "")
    monkeypatch.setattr(turmas_module, "_turmas_db", {})
    monkeypatch.setattr(turmas_module, "_calendarios_db", {})
    monkeypatch.setattr(turmas_module, "_turma_alunos_db", [])

    polos_repo = InMemoryPolosEscolasRepository()
    polos_repo.escolas[ESCOLA_A] = {"id": ESCOLA_A, "polo_id": POLO_A, "nome": "Escola A"}
    polos_repo.escolas[ESCOLA_B] = {"id": ESCOLA_B, "polo_id": POLO_B, "nome": "Escola B"}
    monkeypatch.setattr(polos_repository_module, "_repo_instance", polos_repo)

    auth_setup.perfis["p-coordpolo"] = {"id": "p-coordpolo", "nome": "coordenador_polo", "descricao": "Coordenador"}
    auth_setup.perfis["p-secescola"] = {"id": "p-secescola", "nome": "secretario_escola", "descricao": "Secretário"}
    auth_setup.usuarios["polo-1"].update({"polo_id": POLO_A, "escola_id": None})
    auth_setup.usuarios["escola-1"].update({"polo_id": POLO_A, "escola_id": ESCOLA_A})
    base = {"status": "ativo", "permissoes": []}
    auth_setup.usuarios["coord-1"] = {
        **base, "id": "coord-1", "nome": "Coord", "email": "coord@nexus.com.br",
        "perfil_id": "p-coordpolo", "polo_id": POLO_A, "escola_id": None,
    }
    auth_setup.usuarios["sec-1"] = {
        **base, "id": "sec-1", "nome": "Sec", "email": "sec@nexus.com.br",
        "perfil_id": "p-secescola", "polo_id": POLO_A, "escola_id": ESCOLA_A,
    }
    return auth_setup


def _auth(user_id: str, role: str) -> dict:
    return {"Authorization": f"Bearer {_token(user_id, f'{user_id}@nexus.com.br', role)}"}


ADMIN = ("admin-1", "admin")
POLO_CURTO = ("polo-1", "polo")
POLO_LONGO = ("coord-1", "coordenador_polo")
ESCOLA_CURTO = ("escola-1", "escola")
ESCOLA_LONGO = ("sec-1", "secretario_escola")


@pytest.mark.asyncio
async def test_turmas_crud_paginacao_e_datas(client: AsyncClient, turmas_setup):
    admin = _auth(*ADMIN)

    invalida = await client.post(
        "/turmas",
        json={"nome": "Datas erradas", "data_inicio": "2026-06-01", "data_fim": "2026-01-01"},
        headers=admin,
    )
    assert invalida.status_code == 422

    criada = await client.post(
        "/turmas",
        json={"nome": "Turma Alfa", "escola_id": ESCOLA_A, "polo_id": POLO_B},
        headers=admin,
    )
    assert criada.status_code == 201
    corpo = criada.json()
    assert corpo["polo_id"] == POLO_A, "o polo deve vir da escola, não do payload"
    turma_id = corpo["id"]

    for nome in ("Turma Beta", "Turma Gama"):
        assert (await client.post("/turmas", json={"nome": nome}, headers=admin)).status_code == 201

    pagina = await client.get("/turmas/paginadas", params={"limit": 2, "offset": 0}, headers=admin)
    assert pagina.status_code == 200
    assert pagina.json()["total"] == 3
    assert [item["nome"] for item in pagina.json()["items"]] == ["Turma Alfa", "Turma Beta"]

    busca = await client.get("/turmas/paginadas", params={"q": "gam"}, headers=admin)
    assert [item["nome"] for item in busca.json()["items"]] == ["Turma Gama"]

    detalhe = await client.get(f"/turmas/{turma_id}", headers=admin)
    assert detalhe.status_code == 200
    assert detalhe.json()["total_alunos"] == 0

    editada = await client.put(
        f"/turmas/{turma_id}",
        json={"nome": "Turma Alfa 2", "escola_id": ESCOLA_B, "data_inicio": "2026-02-01"},
        headers=admin,
    )
    assert editada.status_code == 200
    assert editada.json()["nome"] == "Turma Alfa 2"
    assert editada.json()["polo_id"] == POLO_B

    inexistente = await client.put(f"/turmas/{POLO_A}", json={"nome": "Nada"}, headers=admin)
    assert inexistente.status_code == 404

    escola_inexistente = await client.post(
        "/turmas", json={"nome": "Sem escola", "escola_id": POLO_A}, headers=admin
    )
    assert escola_inexistente.status_code == 404


@pytest.mark.asyncio
async def test_turmas_alunos_e_bloqueio_de_exclusao(client: AsyncClient, turmas_setup):
    admin = _auth(*ADMIN)
    turma_id = (await client.post("/turmas", json={"nome": "Turma Alunos"}, headers=admin)).json()["id"]

    for _ in range(2):
        matricula = await client.post(
            f"/turmas/{turma_id}/matricular-aluno", params={"aluno_id": "aluno-1"}, headers=admin
        )
        assert matricula.status_code == 200

    alunos = await client.get(f"/turmas/{turma_id}/alunos", headers=admin)
    assert alunos.status_code == 200
    assert alunos.json()["total"] == 1
    assert alunos.json()["items"][0]["aluno_id"] == "aluno-1"

    assert (await client.delete(f"/turmas/{turma_id}", headers=admin)).status_code == 409

    assert (await client.delete(f"/turmas/{turma_id}/alunos/aluno-1", headers=admin)).status_code == 204
    assert (await client.delete(f"/turmas/{turma_id}/alunos/aluno-1", headers=admin)).status_code == 404

    assert (await client.delete(f"/turmas/{turma_id}", headers=admin)).status_code == 204
    assert (await client.get(f"/turmas/{turma_id}", headers=admin)).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("usuario", [POLO_CURTO, POLO_LONGO])
async def test_turmas_escopo_polo(client: AsyncClient, turmas_setup, usuario):
    admin = _auth(*ADMIN)
    polo = _auth(*usuario)
    outra_id = (
        await client.post("/turmas", json={"nome": "Outro polo", "escola_id": ESCOLA_B}, headers=admin)
    ).json()["id"]

    propria = await client.post("/turmas", json={"nome": "Do polo"}, headers=polo)
    assert propria.status_code == 201
    assert propria.json()["polo_id"] == POLO_A

    negada = await client.post("/turmas", json={"nome": "Invasão", "escola_id": ESCOLA_B}, headers=polo)
    assert negada.status_code == 403

    pagina = await client.get("/turmas/paginadas", params={"polo_id": POLO_B}, headers=polo)
    assert [item["nome"] for item in pagina.json()["items"]] == ["Do polo"]

    assert (await client.get(f"/turmas/{outra_id}", headers=polo)).status_code == 403
    assert (await client.put(f"/turmas/{outra_id}", json={"nome": "X1"}, headers=polo)).status_code == 403
    assert (await client.delete(f"/turmas/{outra_id}", headers=polo)).status_code == 403
    assert (await client.get(f"/turmas/{outra_id}/alunos", headers=polo)).status_code == 403
    assert (await client.get(f"/turmas/{outra_id}/alunos-disponiveis", headers=polo)).status_code == 403
    assert (
        await client.post(f"/turmas/{outra_id}/matricular-aluno", params={"aluno_id": "a"}, headers=polo)
    ).status_code == 403
    assert (await client.delete(f"/turmas/{outra_id}/alunos/a", headers=polo)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("usuario", [ESCOLA_CURTO, ESCOLA_LONGO])
async def test_turmas_escopo_escola(client: AsyncClient, turmas_setup, usuario):
    admin = _auth(*ADMIN)
    escola = _auth(*usuario)
    outra_id = (
        await client.post("/turmas", json={"nome": "Outra escola", "escola_id": ESCOLA_B}, headers=admin)
    ).json()["id"]

    propria = await client.post(
        "/turmas", json={"nome": "Da escola", "escola_id": ESCOLA_B}, headers=escola
    )
    assert propria.status_code == 201
    assert propria.json()["escola_id"] == ESCOLA_A, "a escola do usuário deve prevalecer"
    assert propria.json()["polo_id"] == POLO_A

    listagem = await client.get("/turmas", headers=escola)
    assert [item["nome"] for item in listagem.json()] == ["Da escola"]

    assert (await client.delete(f"/turmas/{outra_id}", headers=escola)).status_code == 403
    assert (await client.delete(f"/turmas/{propria.json()['id']}", headers=escola)).status_code == 204


@pytest.mark.asyncio
async def test_turmas_professor_sem_acesso(client: AsyncClient, turmas_setup):
    resposta = await client.post("/turmas", json={"nome": "Negada"}, headers=_auth("prof-1", "professor"))
    assert resposta.status_code == 403


@pytest.mark.asyncio
async def test_calendarios_crud_e_permissoes(client: AsyncClient, turmas_setup):
    admin = _auth(*ADMIN)
    polo = _auth(*POLO_CURTO)

    sem_token = await client.get("/turmas/calendarios")
    assert sem_token.status_code in (401, 403)

    invalido = await client.post(
        "/turmas/calendarios",
        json={"data_liberacao": "2026-06-01", "data_encerramento": "2026-01-01"},
        headers=admin,
    )
    assert invalido.status_code == 422

    negado = await client.post("/turmas/calendarios", json={}, headers=polo)
    assert negado.status_code == 403

    criado = await client.post(
        "/turmas/calendarios",
        json={"data_liberacao": "2026-01-01", "data_encerramento": "2026-06-01"},
        headers=admin,
    )
    assert criado.status_code == 201
    calendario_id = criado.json()["id"]

    listagem = await client.get("/turmas/calendarios", headers=polo)
    assert [item["id"] for item in listagem.json()] == [calendario_id]

    editado = await client.put(
        f"/turmas/calendarios/{calendario_id}",
        json={"data_liberacao": "2026-02-01", "data_encerramento": "2026-07-01"},
        headers=admin,
    )
    assert editado.status_code == 200
    assert editado.json()["data_liberacao"] == "2026-02-01"

    turma = await client.post(
        "/turmas", json={"nome": "Com calendário", "calendario_oficial_id": calendario_id}, headers=admin
    )
    assert turma.status_code == 201

    assert (await client.delete(f"/turmas/calendarios/{calendario_id}", headers=polo)).status_code == 403
    assert (await client.delete(f"/turmas/calendarios/{calendario_id}", headers=admin)).status_code == 409

    assert (await client.delete(f"/turmas/{turma.json()['id']}", headers=admin)).status_code == 204
    assert (await client.delete(f"/turmas/calendarios/{calendario_id}", headers=admin)).status_code == 204


# 09. EAD
@pytest.mark.asyncio
async def test_modulo_ead(client: AsyncClient):
    t_aluno = _token("aluno-1", "aluno@nexus.com.br", "aluno")

    m_res = await client.post(
        "/ead/matriculas",
        json={"aluno_id": "aluno-1", "ativa_automaticamente": True},
        headers={"Authorization": f"Bearer {t_aluno}"},
    )
    assert m_res.status_code == 201

    c_res = await client.post(
        "/ead/compras",
        json={"aluno_id": "aluno-1", "valor_pago": 120.0, "status_pagamento": "pago"},
        headers={"Authorization": f"Bearer {t_aluno}"},
    )
    assert c_res.status_code == 201


# 10. Notas & Histórico
@pytest.mark.asyncio
async def test_modulo_notas_e_historico(client: AsyncClient):
    t_prof = _token("prof-1", "prof@nexus.com.br", "professor")
    t_aluno = _token("aluno-1", "aluno@nexus.com.br", "aluno")

    n_res = await client.post(
        "/notas-historico/notas",
        json={"aluno_id": "aluno-1", "valor": 9.5, "origem": "ava"},
        headers={"Authorization": f"Bearer {t_prof}"},
    )
    assert n_res.status_code == 201

    h_res = await client.get(
        "/notas-historico/historico/aluno-1",
        headers={"Authorization": f"Bearer {t_aluno}"},
    )
    assert h_res.status_code == 200


# 11. Certificados
@pytest.mark.asyncio
async def test_modulo_certificados(client: AsyncClient):
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")
    t_aluno = _token("aluno-1", "aluno@nexus.com.br", "aluno")

    c_res = await client.post(
        "/certificados/emitir",
        json={"aluno_id": "aluno-1"},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert c_res.status_code == 201
    assert "cdn.nexus.com.br" in c_res.json()["url_arquivo"]

    l_res = await client.get("/certificados?aluno_id=aluno-1", headers={"Authorization": f"Bearer {t_aluno}"})
    assert l_res.status_code == 200


# 15. Cupons
@pytest.mark.asyncio
async def test_modulo_cupons(client: AsyncClient):
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    c_res = await client.post(
        "/cupons",
        json={"codigo": "NEXUS2026", "percentual_desconto": 20.0},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert c_res.status_code == 201

    v_res = await client.get("/cupons/validar/NEXUS2026")
    assert v_res.status_code == 200
    assert v_res.json()["percentual_desconto"] == 20.0


# 16. Pedidos Livros
@pytest.mark.asyncio
async def test_modulo_pedidos_livros(client: AsyncClient):
    t_polo = _token("polo-1", "polo@nexus.com.br", "polo")
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    p_res = await client.post(
        "/pedidos-livros",
        json={"polo_id": "polo-1", "status": "pendente", "itens": [{"disciplina_id": "disc-1", "quantidade": 30}]},
        headers={"Authorization": f"Bearer {t_polo}"},
    )
    assert p_res.status_code == 201
    ped_id = p_res.json()["id"]

    u_res = await client.put(
        f"/pedidos-livros/{ped_id}/status?novo_status=enviado",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert u_res.status_code == 200
    assert u_res.json()["status"] == "enviado"


# 17. Transferências
@pytest.mark.asyncio
async def test_modulo_transferencias(client: AsyncClient, monkeypatch):
    t_polo = _token("polo-1", "polo@nexus.com.br", "polo")
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")
    aluno_id = "00000000-0000-0000-0000-0000000000a1"
    polo_destino = "00000000-0000-0000-0000-0000000000b1"
    escola_destino = "00000000-0000-0000-0000-0000000000c1"

    repo = InMemoryTransferenciasRepository()
    repo.alunos[aluno_id] = {
        "id": aluno_id,
        "usuario_id": "aluno-1",
        "nome": "Aluno",
        "polo_id": "polo-1",
        "escola_id": None,
        "modalidade": "polo",
        "status": "ativo",
        "perfil_nome": "aluno",
        "referencia_movimentacao": datetime.now(timezone.utc),
    }
    repo.polos[polo_destino] = {"id": polo_destino, "nome": "Destino", "status": "ativo"}
    repo.escolas[escola_destino] = {
        "id": escola_destino,
        "nome": "Escola",
        "polo_id": polo_destino,
        "status": "ativo",
    }
    monkeypatch.setattr(transferencias_repository_module, "_repo_instance", repo)

    s_res = await client.post(
        "/transferencias",
        json={
            "aluno_id": aluno_id,
            "tipo": "troca_polo",
            "polo_destino_id": polo_destino,
            "escola_destino_id": escola_destino,
        },
        headers={"Authorization": f"Bearer {t_polo}"},
    )
    assert s_res.status_code == 201
    transf_id = s_res.json()["id"]

    r_res = await client.put(
        f"/transferencias/{transf_id}/resolver",
        json={"aprovado": True},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "aprovada"


# 18. Comunicação (Chat e Feed)
@pytest.mark.asyncio
async def test_modulo_comunicacao(client: AsyncClient):
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    c_res = await client.post(
        "/comunicacao/conversas",
        json={"tipo": "individual"},
    )
    assert c_res.status_code == 201
    conversa_id = c_res.json()["id"]

    m_res = await client.post(
        f"/comunicacao/conversas/{conversa_id}/mensagens?texto=Ola+mundo",
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert m_res.status_code == 201

    f_res = await client.post(
        "/comunicacao/feed",
        json={"titulo": "Aviso Oficial", "conteudo": "Início do semestre letivo 2026.1"},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert f_res.status_code == 201
