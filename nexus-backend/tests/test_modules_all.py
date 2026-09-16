"""Testes automatizados cobrindo os módulos de negócio 03 a 18 do NEXUS 2.0."""
from __future__ import annotations

from datetime import date, datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.admin.repository import InMemoryAdminRepository, set_admin_repository


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
async def test_modulo_cursos_e_disciplinas(client: AsyncClient):
    t_admin = _token("admin-1", "admin@nexus.com.br", "admin")

    c_res = await client.post(
        "/cursos-disciplinas/cursos",
        json={"nome": "Teologia Sistemática", "semestres": 4, "modalidade": "hibrido"},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert c_res.status_code == 201
    curso_id = c_res.json()["id"]

    d_res = await client.post(
        "/cursos-disciplinas/disciplinas",
        json={"curso_id": curso_id, "semestre": 1, "nome": "Bibliologia", "ordem": 1},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert d_res.status_code == 201
    disc_id = d_res.json()["id"]

    cont_res = await client.post(
        f"/cursos-disciplinas/disciplinas/{disc_id}/conteudos",
        json={"disciplina_id": disc_id, "titulo": "Videoaula 1", "tipo_midia": "video", "ordem": 1},
        headers={"Authorization": f"Bearer {t_admin}"},
    )
    assert cont_res.status_code == 201


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
