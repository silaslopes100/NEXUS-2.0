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
async def test_modulo_turmas_e_calendarios(client: AsyncClient):
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
async def test_modulo_transferencias(client: AsyncClient):
    t_polo = _token("polo-1", "polo@nexus.com.br", "polo")
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    s_res = await client.post(
        "/transferencias",
        json={"aluno_id": "aluno-1", "polo_origem_id": "polo-1", "polo_destino_id": "polo-2"},
        headers={"Authorization": f"Bearer {t_polo}"},
    )
    assert s_res.status_code == 201
    transf_id = s_res.json()["id"]

    r_res = await client.put(
        f"/transferencias/{transf_id}/resolver?aprovado=true",
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
