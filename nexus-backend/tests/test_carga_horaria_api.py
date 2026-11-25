"""Fluxo de ponta a ponta: Calendário Acadêmico → cronograma → Diário (RN03) → andamento e frequência."""
from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.aulas.repository import InMemoryAulasRepository, set_aulas_repository
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.carga_horaria.repository import InMemoryCargaHorariaRepository, set_carga_horaria_repository

V_ANA = "11111111-1111-1111-1111-111111111111"
TURMA = "33333333-3333-3333-3333-333333333333"
CURSO = "curso-1"
DISC = "disc-1"

CALENDARIO = {
    "nome": "Calendário 2026",
    "data_inicio": "2026-02-01",
    "data_fim": "2026-03-31",
    "dias_semana": [6],
    "meses_recesso": [7, 12],
}


def _usuario(user_id: str, perfil_id: str, polo_id=None) -> dict:
    return {
        "id": user_id, "nome": user_id, "sobrenome": "", "email": f"{user_id}@nexus.com.br",
        "senha_hash": hash_password("senha123"), "senha_algoritmo": "argon2id", "status": "ativo",
        "perfil_id": perfil_id, "polo_id": polo_id, "escola_id": None,
    }


@pytest.fixture
def repos():
    auth = InMemoryAuthRepository()
    auth.perfis = {
        "p-admin": {"id": "p-admin", "nome": "admin", "descricao": "Administrador"},
        "p-professor": {"id": "p-professor", "nome": "professor", "descricao": "Professor"},
        "p-polo": {"id": "p-polo", "nome": "polo", "descricao": "Polo"},
    }
    auth.usuarios["admin-1"] = _usuario("admin-1", "p-admin")
    auth.usuarios["ana"] = _usuario("ana", "p-professor")
    auth.usuarios["polo-outro"] = _usuario("polo-outro", "p-polo", polo_id="polo-9")
    set_auth_repository(auth)

    aulas = InMemoryAulasRepository()
    aulas.vinculos[V_ANA] = {
        "id": V_ANA, "professor_id": "prof-ana", "professor_usuario_id": "ana", "professor_nome": "Ana",
        "disciplina_id": DISC, "disciplina_nome": "Eclesiologia", "curso_nome": "Teologia",
        "turma_id": TURMA, "turma_nome": "Turma A", "polo_id": "polo-1", "polo_nome": "Polo Central", "ativo": True,
    }
    aulas.alunos_turma[TURMA] = [
        {"aluno_id": "a1", "nome": "Aluno 1", "numero_matricula": "M1"},
        {"aluno_id": "a2", "nome": "Aluno 2", "numero_matricula": "M2"},
    ]
    set_aulas_repository(aulas)

    carga = InMemoryCargaHorariaRepository(aulas_repo=aulas)
    carga.turmas[TURMA] = {
        "id": TURMA, "nome": "Turma A", "curso_id": CURSO, "polo_id": "polo-1", "escola_id": None,
        "data_inicio": date(2026, 2, 1), "data_fim": date(2026, 3, 31), "concluida_em": None,
    }
    carga.disciplinas[DISC] = {"nome": "Eclesiologia", "carga_horaria": 40, "qtd_aulas_prevista": 2, "curso_id": CURSO}
    set_carga_horaria_repository(carga)
    yield aulas, carga
    set_aulas_repository(None)
    set_carga_horaria_repository(None)


@pytest_asyncio.fixture
async def client(repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _h(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id, 'tipo': 'access'})}"}


async def _preparar(client, carga, **regras) -> dict:
    """Cria o calendário, vincula ao curso e gera o cronograma da turma."""
    res = await client.post("/calendarios-academicos", json={**CALENDARIO, "regras": regras}, headers=_h("admin-1"))
    assert res.status_code == 201, res.text
    carga.cursos[CURSO] = {"calendario_id": res.json()["id"]}
    res = await client.post(f"/turmas/{TURMA}/cronograma/gerar", headers=_h("admin-1"))
    assert res.status_code == 200, res.text
    return res.json()


async def _ata(client, user="ana", **dados):
    payload = {"professor_disciplina_id": V_ANA, "data_aula": "2026-02-07", "conteudo_ministrado": "Conteúdo", **dados}
    return await client.post("/aulas/me", json=payload, headers=_h(user))


@pytest.mark.asyncio
async def test_calendario_crud_permissoes_e_previa_de_datas(client, repos):
    _, carga = repos
    assert (await client.post("/calendarios-academicos", json=CALENDARIO, headers=_h("ana"))).status_code == 403
    invalido = await client.post("/calendarios-academicos", json={**CALENDARIO, "dias_semana": [9]}, headers=_h("admin-1"))
    assert invalido.status_code == 422

    res = await client.post("/calendarios-academicos", json={**CALENDARIO, "data_inicio": "2026-01-01", "data_fim": "2026-12-31"}, headers=_h("admin-1"))
    assert res.status_code == 201
    cal = res.json()
    assert cal["regras"]["aulas_por_disciplina_mes"] == 2 and cal["regras"]["frequencia_minima_pct"] == 75

    previa = (await client.get(f"/calendarios-academicos/{cal['id']}/datas-letivas",
                               params={"inicio": "2026-07-01", "fim": "2026-08-31"}, headers=_h("admin-1"))).json()
    julho, agosto = previa["meses"]
    assert julho["recesso"] and julho["datas"] == []
    assert len(agosto["datas"]) == 5 and agosto["quinta_semana"] == ["2026-08-29"]

    carga.cursos[CURSO] = {"calendario_id": cal["id"]}
    res = await client.delete(f"/calendarios-academicos/{cal['id']}", headers=_h("admin-1"))
    assert res.status_code == 409  # curso vinculado
    assert any(a["acao"] == "calendario_academico_criado" for a in carga.auditoria)


@pytest.mark.asyncio
async def test_cronograma_respeita_calendario_e_escopo(client, repos):
    _, carga = repos
    sem_calendario = await client.post(f"/turmas/{TURMA}/cronograma/gerar", headers=_h("admin-1"))
    assert sem_calendario.status_code == 422

    crono = await _preparar(client, carga)
    aulas = crono["disciplinas"][0]["aulas"]
    assert [(a["numero"], a["data_prevista"], a["horas_previstas"], a["status"]) for a in aulas] == [
        (1, "2026-02-07", 20.0, "pendente"), (2, "2026-02-14", 20.0, "pendente"),
    ]
    assert (await client.get(f"/turmas/{TURMA}/cronograma", headers=_h("polo-outro"))).status_code == 403
    assert (await client.post(f"/turmas/{TURMA}/cronograma/gerar", headers=_h("ana"))).status_code == 403


@pytest.mark.asyncio
async def test_diario_registra_prevista_reposicao_e_complementar(client, repos):
    aulas_repo, carga = repos
    crono = await _preparar(client, carga)
    p1, p2 = [a["id"] for a in crono["disciplinas"][0]["aulas"]]

    pend = (await client.get("/aulas/me/pendentes", params={"vinculo_id": V_ANA}, headers=_h("ana"))).json()
    assert pend["cronograma_gerado"] and len(pend["pendentes"]) == 2 and "reposicao" in pend["tipos_permitidos"]

    assert (await _ata(client)).status_code == 422  # prevista sem referência
    assert (await _ata(client, aula_prevista_id=p1, data_aula="2026-05-02")).status_code == 422  # fora do período
    ata1 = await _ata(client, aula_prevista_id=p1)
    assert ata1.status_code == 201, ata1.text
    assert (ata1.json()["tipo"], ata1.json()["horas"], ata1.json()["numero_aula"]) == ("prevista", 20, 1)
    assert (await _ata(client, aula_prevista_id=p1, data_aula="2026-02-08")).status_code == 409  # já realizada

    assert (await _ata(client, tipo="reforco", horas=2, aula_prevista_id=p1)).status_code == 422  # sem justificativa
    reforco = await _ata(client, tipo="reforco", horas=2, aula_prevista_id=p1, justificativa="Dúvidas da turma")
    assert reforco.status_code == 201 and reforco.json()["numero_aula"] == 2  # próximo número livre do dia

    # Aula 2 não aconteceu em 14/02; reposição em 21/02.
    repos_ = await _ata(client, tipo="reposicao", aula_prevista_id=p2, data_aula="2026-02-21", justificativa="Chuva")
    assert repos_.status_code == 201, repos_.text
    pend = (await client.get("/aulas/me/pendentes", params={"vinculo_id": V_ANA}, headers=_h("ana"))).json()
    assert pend["pendentes"] == [] and pend["tipos_permitidos"] == ["extra", "reforco", "complemento", "revisao"]

    # Chamada: a1 presente na 1 e na reposição; a2 ausente na 1, presente só no Reforço.
    aulas_repo.presencas += [
        {"professor_disciplina_id": V_ANA, "data_aula": date(2026, 2, 7), "numero_aula": 1, "aluno_id": "a1", "presente": True},
        {"professor_disciplina_id": V_ANA, "data_aula": date(2026, 2, 7), "numero_aula": 1, "aluno_id": "a2", "presente": False},
        {"professor_disciplina_id": V_ANA, "data_aula": date(2026, 2, 7), "numero_aula": 2, "aluno_id": "a2", "presente": True},
        {"professor_disciplina_id": V_ANA, "data_aula": date(2026, 2, 21), "numero_aula": 2, "aluno_id": "a1", "presente": True},
        {"professor_disciplina_id": V_ANA, "data_aula": date(2026, 2, 21), "numero_aula": 2, "aluno_id": "a2", "presente": False},
    ]
    and_ = (await client.get(f"/turmas/{TURMA}/andamento", params={"data_referencia": "2026-02-28"},
                             headers=_h("admin-1"))).json()
    assert (and_["horas_abatidas"], and_["saldo"], and_["progresso_pct"], and_["situacao"]) == (40, 0, 100, "concluida")
    assert and_["horas_complementares"] == 2

    freq = (await client.get(f"/turmas/{TURMA}/frequencia", headers=_h("admin-1"))).json()
    por_aluno = {a["aluno_id"]: a for a in freq["alunos"]}
    assert por_aluno["a1"]["frequencia_pct"] == 100 and not por_aluno["a1"]["em_risco"]
    assert por_aluno["a2"]["frequencia_pct"] == 0 and por_aluno["a2"]["em_risco"]  # o Reforço não conta
    assert freq["alunos_em_risco"] == 1


@pytest.mark.asyncio
async def test_troca_de_tipo_exclusao_e_conclusao(client, repos):
    _, carga = repos
    crono = await _preparar(client, carga, excluir_ata_devolve_saldo=False, saldo_ao_fim_turma="bloquear_conclusao")
    p1 = crono["disciplinas"][0]["aulas"][0]["id"]
    ata = (await _ata(client, aula_prevista_id=p1)).json()

    # RN03.5: tipo só muda pela coordenação, com auditoria.
    corpo = {"tipo": "revisao", "aula_prevista_id": p1, "justificativa": "Era revisão"}
    assert (await client.patch(f"/aulas/{ata['id']}/tipo", json=corpo, headers=_h("ana"))).status_code == 403
    res = await client.patch(f"/aulas/{ata['id']}/tipo", json=corpo, headers=_h("admin-1"))
    assert res.status_code == 200 and res.json()["tipo"] == "revisao"
    assert any(a["acao"] == "aula_tipo_alterado" for a in carga.auditoria)
    res = await client.patch(f"/aulas/{ata['id']}/tipo", json={"tipo": "prevista", "aula_prevista_id": p1},
                             headers=_h("admin-1"))
    assert res.status_code == 200 and res.json()["tipo"] == "prevista"

    # Com excluir_ata_devolve_saldo=False, só a Diretoria exclui ata que abate horas.
    assert (await client.delete(f"/aulas/me/{ata['id']}", headers=_h("ana"))).status_code == 403
    assert (await client.delete(f"/aulas/me/{ata['id']}", headers=_h("admin-1"))).status_code == 200
    crono = (await client.get(f"/turmas/{TURMA}/cronograma", headers=_h("admin-1"))).json()
    assert crono["disciplinas"][0]["aulas"][0]["status"] == "pendente"  # voltou a Pendente
    assert any(a["acao"] == "ata_excluida_saldo_devolvido" for a in carga.auditoria)

    # Saldo pendente com bloquear_conclusao: não conclui.
    res = await client.post(f"/turmas/{TURMA}/concluir", headers=_h("admin-1"))
    assert res.status_code == 409 and "Saldo pendente" in res.json()["detail"]


@pytest.mark.asyncio
async def test_regerar_cronograma_mantem_aulas_realizadas(client, repos):
    _, carga = repos
    crono = await _preparar(client, carga)
    p1 = crono["disciplinas"][0]["aulas"][0]["id"]
    assert (await _ata(client, aula_prevista_id=p1)).status_code == 201

    # A coordenação muda a regra para aulas de duração fixa e regera.
    cal_id = carga.cursos[CURSO]["calendario_id"]
    await client.put(f"/calendarios-academicos/{cal_id}",
                     json={**CALENDARIO, "regras": {"aulas_por_disciplina_mes": 4}}, headers=_h("admin-1"))
    crono = (await client.post(f"/turmas/{TURMA}/cronograma/gerar", headers=_h("admin-1"))).json()
    aulas = crono["disciplinas"][0]["aulas"]
    assert aulas[0]["id"] == p1 and aulas[0]["status"] == "realizada"
    assert [a["numero"] for a in aulas] == [1, 2, 3, 4]
    assert round(sum(a["horas_previstas"] for a in aulas), 2) == 40  # só o restante foi redividido
