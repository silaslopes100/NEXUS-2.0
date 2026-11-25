"""Cadastro de turmas: situação, código, vagas, responsável, cancelar/reabrir, prazos EAD e AVA."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.modules.carga_horaria.cronograma import cronograma_ead
from app.modules.carga_horaria.schemas import RegrasCalendario
from app.modules.turmas import regras
from test_modules_all import (  # noqa: F401
    ADMIN, CURSO_T, ESCOLA_A, POLO_A, POLO_CURTO, _auth, auth_setup, calendario_em_memoria, client, turmas_setup,
)

HOJE = date(2026, 6, 15)


# ---------- Regras puras ----------

def test_situacao_derivada():
    assert regras.situacao({"cancelada_em": "x", "concluida_em": "y"}) == "cancelada"
    assert regras.situacao({"concluida_em": "y"}) == "concluida"
    assert regras.situacao({"data_inicio": date(2026, 7, 1)}, HOJE) == "planejada"
    assert regras.situacao({"data_inicio": date(2026, 1, 1)}, HOJE) == "em_andamento"
    assert regras.periodo_encerrado({"data_inicio": date(2026, 1, 1), "data_fim": date(2026, 5, 1)}, HOJE)
    assert not regras.periodo_encerrado({"data_inicio": date(2026, 1, 1), "data_fim": date(2026, 12, 1)}, HOJE)
    with pytest.raises(Exception) as exc:
        regras.exigir_turma_editavel({"cancelada_em": "x"})
    assert exc.value.status_code == 409


def test_codigo_e_nome_sugerido():
    assert regras.sigla_curso("CURSO DE FOMAÇÃO TEOLÓGICA") == "CFT"
    assert regras.sigla_curso("Ética e Liderança Pastoral Avançada Plus") == "ELPA"
    assert regras.sigla_curso("") == "TUR"
    assert regras.proximo_codigo("CFT", 2026, []) == "CFT-2026-001"
    assert regras.proximo_codigo("CFT", 2026, ["CFT-2026-001", "CFT-2026-009", "CFT-2025-030", "X"]) == "CFT-2026-010"
    assert regras.nome_sugerido("CFT-2026-003", "Escola A", "presencial") == "Turma 03 — Escola A"
    assert regras.nome_sugerido("CFT-2026-012", None, "ead") == "Turma 12 — EAD"


# ---------- Prazos EAD (função pura) ----------

DISCIPLINAS = [
    {"id": "d1", "nome": "A", "ead_prazo_dias": None},
    {"id": "d2", "nome": "B", "ead_prazo_dias": 10},
    {"id": "d3", "nome": "C", "ead_prazo_dias": None},
]


def _sit(linhas):
    return [(l["disciplina_id"], l["situacao"], l["liberada_em"], l["data_limite"]) for l in linhas]


def test_ead_sequencial_libera_quando_conclui_ou_vence():
    r = RegrasCalendario(ead_prazo_dias_padrao=30)
    inicio = date(2026, 5, 1)
    # A concluída em 10/05 → B libera em 10/05 (prazo próprio de 10 dias) → vence em 20/05 → C libera em 21/05.
    linhas = cronograma_ead(DISCIPLINAS, inicio, r, {"d1": date(2026, 5, 10)}, HOJE)
    assert _sit(linhas) == [
        ("d1", "concluida", date(2026, 5, 1), date(2026, 5, 31)),
        ("d2", "vencida", date(2026, 5, 10), date(2026, 5, 20)),
        ("d3", "liberada", date(2026, 5, 21), date(2026, 6, 20)),
    ]


def test_ead_anterior_vencida_ignora_conclusao_antecipada():
    r = RegrasCalendario(ead_prazo_dias_padrao=30, ead_proxima_libera="anterior_vencida")
    linhas = cronograma_ead(DISCIPLINAS, date(2026, 5, 1), r, {"d1": date(2026, 5, 10)}, HOJE)
    # A conclusão antecipada de A (10/05) não adianta B: B só libera depois de A vencer (31/05).
    assert (linhas[1]["liberada_em"], linhas[1]["data_limite"], linhas[1]["situacao"]) == (
        date(2026, 6, 1), date(2026, 6, 11), "vencida")
    assert (linhas[2]["liberada_em"], linhas[2]["situacao"]) == (date(2026, 6, 12), "liberada")


def test_ead_anterior_concluida_trava_a_sequencia():
    r = RegrasCalendario(ead_proxima_libera="anterior_concluida")
    linhas = cronograma_ead(DISCIPLINAS, date(2026, 5, 1), r, {}, HOJE)
    assert linhas[0]["situacao"] == "vencida"
    assert [(l["liberada_em"], l["situacao"]) for l in linhas[1:]] == [(None, "aguardando"), (None, "aguardando")]


def test_ead_todas_no_inicio():
    r = RegrasCalendario(ead_liberacao="todas_no_inicio", ead_prazo_dias_padrao=60)
    linhas = cronograma_ead(DISCIPLINAS, date(2026, 5, 1), r, {}, HOJE)
    assert {l["liberada_em"] for l in linhas} == {date(2026, 5, 1)}
    assert [l["data_limite"] for l in linhas] == [date(2026, 6, 30), date(2026, 5, 11), date(2026, 6, 30)]
    assert [l["situacao"] for l in linhas] == ["liberada", "vencida", "liberada"]


# ---------- API: cadastro ----------

def _turma(**extra):
    return {"curso_id": CURSO_T, "nome": "Turma", **extra}


@pytest.mark.asyncio
async def test_presencial_exige_polo_e_gera_codigo(client, turmas_setup):
    admin = _auth(*ADMIN)
    sem_polo = await client.post("/turmas", json=_turma(), headers=admin)
    assert sem_polo.status_code == 422 and "polo" in sem_polo.json()["detail"]

    sugestao = (await client.get("/turmas/sugestao", params={"curso_id": CURSO_T, "escola_id": ESCOLA_A},
                                 headers=admin)).json()
    assert sugestao["codigo"] == "CFT-2026-001"
    assert sugestao["nome"] == "Turma 01 — Escola A"
    assert (sugestao["data_inicio"], sugestao["data_fim"]) == ("2026-01-01", "2026-12-31")

    t1 = (await client.post("/turmas", json=_turma(escola_id=ESCOLA_A, turno="noite",
                                                    horario_inicio="19:00", horario_fim="22:00"), headers=admin)).json()
    t2 = (await client.post("/turmas", json=_turma(modalidade="ead"), headers=admin)).json()
    assert (t1["codigo"], t2["codigo"]) == ("CFT-2026-001", "CFT-2026-002")
    assert t1["polo_id"] == POLO_A and t1["turno"] == "noite" and t1["situacao"] in ("planejada", "em_andamento")
    assert t2["modalidade"] == "ead" and t2["polo_id"] is None

    horario = await client.post("/turmas", json=_turma(modalidade="ead", horario_inicio="22:00",
                                                       horario_fim="19:00"), headers=admin)
    assert horario.status_code == 422


@pytest.mark.asyncio
async def test_responsavel_da_unidade(client, turmas_setup):
    admin = _auth(*ADMIN)
    invalido = await client.post("/turmas", json=_turma(polo_id=POLO_A, responsavel_id=str(_uuid("admin"))),
                                 headers=admin)
    assert invalido.status_code in (404, 422)

    possiveis = (await client.get("/turmas/responsaveis-possiveis", params={"polo_id": POLO_A}, headers=admin)).json()
    ids = {r["id"] for r in possiveis}
    assert {"polo-1", "coord-1"} <= ids
    assert all(r["perfil"] == "polo" for r in possiveis)


def _uuid(seed: str):
    import uuid

    return uuid.uuid5(uuid.NAMESPACE_DNS, seed)


@pytest.mark.asyncio
async def test_vagas_lotacao_e_reducao(client, turmas_setup):
    admin = _auth(*ADMIN)
    t = (await client.post("/turmas", json=_turma(modalidade="ead", vagas=2), headers=admin)).json()
    for aluno in ("a1", "a2"):
        assert (await client.post(f"/turmas/{t['id']}/matricular-aluno", params={"aluno_id": aluno},
                                  headers=admin)).status_code == 200
    lotada = await client.post(f"/turmas/{t['id']}/matricular-aluno", params={"aluno_id": "a3"}, headers=admin)
    assert lotada.status_code == 409 and "lotada" in lotada.json()["detail"]
    reduz = await client.put(f"/turmas/{t['id']}", json=_turma(modalidade="ead", vagas=1), headers=admin)
    assert reduz.status_code == 422
    sem_limite = await client.put(f"/turmas/{t['id']}", json=_turma(modalidade="ead"), headers=admin)
    assert sem_limite.status_code == 200 and sem_limite.json()["vagas"] is None


@pytest.mark.asyncio
async def test_cancelar_deixa_so_leitura_e_admin_reabre(client, turmas_setup):
    admin, polo = _auth(*ADMIN), _auth(*POLO_CURTO)
    t = (await client.post("/turmas", json=_turma(), headers=polo)).json()
    assert (await client.post(f"/turmas/{t['id']}/matricular-aluno", params={"aluno_id": "a1"},
                              headers=polo)).status_code == 200

    assert (await client.post(f"/turmas/{t['id']}/cancelar", json={"motivo": ""}, headers=polo)).status_code == 422
    cancelada = await client.post(f"/turmas/{t['id']}/cancelar", json={"motivo": "Sem quórum"}, headers=polo)
    assert cancelada.status_code == 200
    assert cancelada.json()["situacao"] == "cancelada" and cancelada.json()["motivo_cancelamento"] == "Sem quórum"

    for resposta in (
        await client.put(f"/turmas/{t['id']}", json=_turma(nome="Outra"), headers=polo),
        await client.post(f"/turmas/{t['id']}/matricular-aluno", params={"aluno_id": "a2"}, headers=polo),
        await client.delete(f"/turmas/{t['id']}/alunos/a1", headers=polo),
        await client.post(f"/turmas/{t['id']}/cancelar", json={"motivo": "De novo"}, headers=polo),
    ):
        assert resposta.status_code == 409 and "somente leitura" in resposta.json()["detail"]

    filtradas = (await client.get("/turmas/paginadas", params={"situacao": "cancelada"}, headers=admin)).json()
    assert [i["id"] for i in filtradas["items"]] == [t["id"]]

    assert (await client.post(f"/turmas/{t['id']}/reabrir", headers=polo)).status_code == 403
    reaberta = await client.post(f"/turmas/{t['id']}/reabrir", headers=admin)
    assert reaberta.status_code == 200 and reaberta.json()["situacao"] != "cancelada"
    assert (await client.post(f"/turmas/{t['id']}/reabrir", headers=admin)).status_code == 409


# ---------- API: prazos EAD ----------

TURMA_EAD = "66666666-6666-6666-6666-666666666666"


def _turma_ead(carga, modalidade="ead"):
    carga.turmas[TURMA_EAD] = {
        "id": TURMA_EAD, "nome": "EAD", "curso_id": CURSO_T, "polo_id": None, "escola_id": None,
        "data_inicio": date(2026, 1, 1), "data_fim": date(2026, 12, 31), "modalidade": modalidade,
    }
    carga.disciplinas["d1"] = {"nome": "A", "carga_horaria": 40, "qtd_aulas_prevista": 2, "curso_id": CURSO_T,
                               "ordem": 1}
    carga.disciplinas["d2"] = {"nome": "B", "carga_horaria": 40, "qtd_aulas_prevista": 2, "curso_id": CURSO_T,
                               "ordem": 2, "ead_prazo_dias": 15}
    carga.alunos[TURMA_EAD] = [{"aluno_id": "al-1", "nome": "Ana", "numero_matricula": "M1",
                                "data_matricula": datetime(2026, 3, 1, tzinfo=timezone.utc)}]


@pytest.mark.asyncio
async def test_prazos_ead_da_turma(client, turmas_setup, calendario_em_memoria):
    carga = calendario_em_memoria
    _turma_ead(carga)
    carga.conclusoes = {("al-1", "d1"): date(2026, 3, 10)}
    res = await client.get(f"/turmas/{TURMA_EAD}/prazos-ead", headers=_auth(*ADMIN))
    assert res.status_code == 200
    corpo = res.json()
    assert corpo["regras"]["ead_prazo_dias_padrao"] == 30
    aluno = corpo["alunos"][0]
    assert aluno["inicio"] == "2026-03-01"  # matrícula depois do início da turma
    assert [(d["nome"], d["liberada_em"], d["data_limite"]) for d in aluno["disciplinas"]] == [
        ("A", "2026-03-01", "2026-03-31"), ("B", "2026-03-10", "2026-03-25"),
    ]

    _turma_ead(carga, modalidade="presencial")
    assert (await client.get(f"/turmas/{TURMA_EAD}/prazos-ead", headers=_auth(*ADMIN))).status_code == 422


# ---------- AVA ----------

class _AvaRepoFalso:
    def __init__(self, linhas):
        self.linhas = linhas

    def disciplinas_do_aluno(self, aluno_id, usuario_id):
        return [dict(l) for l in self.linhas]


def _linha(id_, **extra):
    return {"id": id_, "nome": id_, "liberada_em": datetime(2026, 1, 1, tzinfo=timezone.utc), "publicado": True,
            "total_aulas": 2, "aulas_concluidas": 0, **extra}


def test_ava_segue_a_turma_ead(calendario_em_memoria):
    from app.modules.ava.aluno_service import AvaAlunoService

    carga = calendario_em_memoria
    _turma_ead(carga)
    hoje = date.today()
    carga.turmas[TURMA_EAD]["data_inicio"] = hoje - timedelta(days=40)
    carga.alunos[TURMA_EAD][0]["data_matricula"] = None
    servico = AvaAlunoService(_AvaRepoFalso([_linha("d1"), _linha("d2"), _linha("avulsa")]), None, None)

    situacoes = {d["id"]: servico._situacao(d) for d in servico._disciplinas("al-1", "u-1")}
    # d1: 30 dias desde 40 dias atrás → vencida (bloqueia); d2 libera após o vencimento de d1 → liberada.
    assert situacoes == {"d1": "prazo_expirado", "d2": "liberada", "avulsa": "liberada"}

    carga.calendarios["00000000-0000-0000-0000-0000000000ca"]["regras"] = {"ead_ao_vencer": "alertar"}
    situacoes = {d["id"]: servico._situacao(d) for d in servico._disciplinas("al-1", "u-1")}
    assert situacoes["d1"] == "liberada"  # só avisa

    carga.turmas[TURMA_EAD]["data_inicio"] = hoje
    linhas = {d["id"]: d for d in servico._disciplinas("al-1", "u-1")}
    assert servico._situacao(linhas["d2"]) == "bloqueada"  # ainda não liberada pela sequência
    assert linhas["d1"]["prazo_conclusao"].date() == hoje + timedelta(days=31)

    carga.turmas[TURMA_EAD]["cancelada_em"] = datetime.now(timezone.utc)
    sem_turma = {d["id"]: servico._situacao(d) for d in servico._disciplinas("al-1", "u-1")}
    assert sem_turma == {"d1": "liberada", "d2": "liberada", "avulsa": "liberada"}
