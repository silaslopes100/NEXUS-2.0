"""Testes das Regras de Negócio de Carga Horária, Progresso e Frequência (RN01–RN07)."""
from __future__ import annotations

from datetime import date

from app.modules.carga_horaria.cronograma import (
    DisciplinaPlano,
    calcular_andamento,
    calcular_frequencia,
    capacidade,
    datas_letivas,
    eh_quinta_ocorrencia,
    gerar_cronograma,
    horas_das_aulas,
    mesclar_com_realizadas,
)
from app.modules.carga_horaria.schemas import RegrasCalendario

SABADO = 6


def _disciplinas(n: int, carga: float = 40, qtd: int = 2) -> list:
    return [DisciplinaPlano(id=f"d{i}", nome=f"Disciplina {i}", carga_horaria=carga, qtd_aulas_prevista=qtd)
            for i in range(1, n + 1)]


# ---------------------------------------------------------------------------
# Datas letivas e recessos (Ponto em aberto 3)
# ---------------------------------------------------------------------------

def test_datas_letivas_respeitam_dia_recesso_feriado_e_extras():
    datas = datas_letivas(
        date(2026, 6, 1), date(2026, 8, 31), [SABADO], meses_recesso=[7],
        feriados=[date(2026, 6, 6)], datas_excluidas=[date(2026, 8, 1)], datas_extras=[date(2026, 7, 15)],
    )
    assert all(d.weekday() == 5 for d in datas if d != date(2026, 7, 15))
    assert date(2026, 6, 6) not in datas and date(2026, 8, 1) not in datas
    assert [d for d in datas if d.month == 7] == [date(2026, 7, 15)]  # recesso, só a data extra
    assert datas[:3] == [date(2026, 6, 13), date(2026, 6, 20), date(2026, 6, 27)]


def test_quinta_ocorrencia_identifica_mes_de_cinco_semanas():
    assert eh_quinta_ocorrencia(date(2026, 8, 29))  # 5º sábado de agosto/2026
    assert not eh_quinta_ocorrencia(date(2026, 8, 22))


# ---------------------------------------------------------------------------
# Horas por aula (Ponto em aberto 1)
# ---------------------------------------------------------------------------

def test_dividir_carga_fecha_exatamente_a_carga():
    regras = RegrasCalendario()
    assert horas_das_aulas(40, 2, regras) == [20, 20]
    tres = horas_das_aulas(40, 3, regras)
    assert tres == [13.33, 13.33, 13.34] and round(sum(tres), 2) == 40
    assert horas_das_aulas(40, 3, RegrasCalendario(duracao_aula="fixa", duracao_aula_horas=20)) == [20, 20, 20]


# ---------------------------------------------------------------------------
# Cronograma (RN05)
# ---------------------------------------------------------------------------

def test_cronograma_paralelo_quatro_sabados_duas_disciplinas():
    datas = datas_letivas(date(2026, 2, 1), date(2026, 2, 28), [SABADO])  # 4 sábados
    res = gerar_cronograma(_disciplinas(2), datas, RegrasCalendario())
    por = {d: [(a.numero, a.data.day, a.horas) for a in res.aulas if a.disciplina_id == d] for d in ("d1", "d2")}
    assert por["d1"] == [(1, 7, 20), (2, 21, 20)]
    assert por["d2"] == [(1, 14, 20), (2, 28, 20)]
    assert res.alertas == []


def test_cronograma_sequencial_usa_blocos():
    datas = datas_letivas(date(2026, 2, 1), date(2026, 2, 28), [SABADO])
    res = gerar_cronograma(_disciplinas(2), datas, RegrasCalendario(organizacao_disciplinas_mes="sequencial"))
    assert [a.data.day for a in res.aulas if a.disciplina_id == "d1"] == [7, 14]
    assert [a.data.day for a in res.aulas if a.disciplina_id == "d2"] == [21, 28]


def test_mes_de_cinco_semanas_gera_aula_extra_e_redivide_a_carga():
    datas = datas_letivas(date(2026, 8, 1), date(2026, 8, 31), [SABADO])  # 5 sábados
    com = gerar_cronograma(_disciplinas(2), datas, RegrasCalendario())
    d1 = [a for a in com.aulas if a.disciplina_id == "d1"]
    assert len(d1) == 3 and round(sum(a.horas for a in d1), 2) == 40
    sem = gerar_cronograma(_disciplinas(2), datas, RegrasCalendario(quinta_semana="ignorar"))
    assert len([a for a in sem.aulas if a.disciplina_id == "d1"]) == 2
    assert all(a.data.day != 29 for a in sem.aulas)


def test_capacidade_insuficiente_gera_alerta():
    regras = RegrasCalendario()
    assert capacidade(8, 4, regras) == {"meses_necessarios": 4, "meses_disponiveis": 4, "cabe": True}
    datas = datas_letivas(date(2026, 2, 1), date(2026, 3, 31), [SABADO])  # 2 meses
    res = gerar_cronograma(_disciplinas(6), datas, regras)
    assert not res.capacidade["cabe"]
    assert any("precisa de 3 meses" in a for a in res.alertas)
    assert any("Disciplina 5" in a for a in res.alertas)


def test_modo_disciplina_segue_ate_atingir_qtd_aulas_prevista():
    datas = datas_letivas(date(2026, 2, 1), date(2026, 3, 31), [SABADO])
    regras = RegrasCalendario(fonte_qtd_aulas="disciplina", disciplinas_por_mes=1, aulas_por_disciplina_mes=4)
    res = gerar_cronograma(_disciplinas(1, qtd=6), datas, regras)
    aulas = [a for a in res.aulas if a.disciplina_id == "d1"]
    assert len(aulas) == 6 and aulas[0].data == date(2026, 2, 7) and aulas[-1].data.month == 3
    assert round(sum(a.horas for a in aulas), 2) == 40


def test_regerar_mantem_realizadas_e_divide_so_o_que_falta():
    datas = datas_letivas(date(2026, 8, 1), date(2026, 8, 31), [SABADO])
    regras = RegrasCalendario(disciplinas_por_mes=1)
    geradas = gerar_cronograma(_disciplinas(1), datas, regras).aulas  # 5 sábados -> 3 aulas (2 + 5ª semana)
    realizadas = [{"disciplina_id": "d1", "numero": 1, "horas_previstas": 20}]
    novas = mesclar_com_realizadas(geradas, realizadas, {"d1": 40}, regras)
    assert [a.numero for a in novas] == [2, 3]
    assert round(sum(a.horas for a in novas), 2) == 20


# ---------------------------------------------------------------------------
# Exemplo do documento (RN03.3, RN03.4, RN04, RN07)
# ---------------------------------------------------------------------------

def test_exemplo_do_documento_progresso_saldo_e_frequencia():
    # Curso com 8 disciplinas de 40 h = 320 h; turma de 01/02 a 31/05 (4 meses) — cabe no calendário.
    assert capacidade(8, 4, RegrasCalendario())["cabe"] and 8 * 40 == 320

    # Disciplina A com 4 aulas previstas de 10 h (no exemplo, 3 aulas = 30 h).
    regras = RegrasCalendario()
    disc = [DisciplinaPlano(id="A", nome="Disciplina A", carga_horaria=40, qtd_aulas_prevista=4)]
    previstas = [
        {"id": f"p{n}", "disciplina_id": "A", "numero": n, "data_prevista": date(2026, 2, 7 * n), "horas_previstas": 10}
        for n in range(1, 5)
    ]
    atas = [
        {"id": "a1", "disciplina_id": "A", "tipo": "prevista", "horas": 2, "aula_prevista_id": "p1", "chave": "k1"},
        {"id": "a2", "disciplina_id": "A", "tipo": "prevista", "horas": 2, "aula_prevista_id": "p2", "chave": "k2"},
        # A aula 3 não aconteceu; reposição registrada depois.
        {"id": "a3", "disciplina_id": "A", "tipo": "reposicao", "horas": 2, "aula_prevista_id": "p3", "chave": "k3"},
        # Reforço de 2 h: horas complementares, não abate.
        {"id": "a4", "disciplina_id": "A", "tipo": "reforco", "horas": 2, "aula_prevista_id": "p2", "chave": "k4"},
    ]
    andamento = calcular_andamento(disc, previstas, atas, regras, hoje=date(2026, 3, 31))
    linha = andamento["disciplinas"][0]
    assert (linha["horas_abatidas"], linha["saldo"], linha["progresso_pct"]) == (30, 10, 75)
    assert linha["horas_complementares"] == 2
    # Previsto até 31/03: 4 aulas (40 h) e realizado 30 h -> atrasado em 1 aula (10 h).
    assert (linha["situacao"], linha["atraso_horas"], linha["atraso_aulas"]) == ("atrasado", 10, 1)

    # Aluno presente nas aulas 1 e 3 (reposição), ausente na 2, e foi ao Reforço: 66,7%.
    presencas = [
        {"aluno_id": "x", "chave": "k1", "presente": True},
        {"aluno_id": "x", "chave": "k2", "presente": False},
        {"aluno_id": "x", "chave": "k3", "presente": True},
        {"aluno_id": "x", "chave": "k4", "presente": True},
    ]
    freq = calcular_frequencia([{"aluno_id": "x", "nome": "Aluno"}], disc, atas, presencas, previstas, regras)
    assert freq[0]["frequencia_pct"] == 66.67
    assert freq[0]["em_risco"]  # abaixo de 75%
    assert freq[0]["disciplinas"][0]["registros"] == 3  # o Reforço não entra


def test_reposicao_tira_o_atraso_e_extra_nao_compensa():
    regras = RegrasCalendario()
    disc = [DisciplinaPlano(id="A", nome="A", carga_horaria=40)]
    previstas = [
        {"id": "p1", "disciplina_id": "A", "data_prevista": date(2026, 2, 7), "horas_previstas": 20},
        {"id": "p2", "disciplina_id": "A", "data_prevista": date(2026, 2, 21), "horas_previstas": 20},
    ]
    so_extra = [{"id": "e", "disciplina_id": "A", "tipo": "extra", "horas": 20, "aula_prevista_id": None}]
    r = calcular_andamento(disc, previstas, [{"id": "a", "disciplina_id": "A", "tipo": "prevista",
                                               "aula_prevista_id": "p1"}] + so_extra, regras, date(2026, 2, 28))
    assert r["situacao"] == "atrasado" and r["disciplinas"][0]["horas_complementares"] == 20
    reposta = [{"id": "a", "disciplina_id": "A", "tipo": "prevista", "aula_prevista_id": "p1"},
               {"id": "r", "disciplina_id": "A", "tipo": "reposicao", "aula_prevista_id": "p2"}]
    r = calcular_andamento(disc, previstas, reposta, regras, date(2026, 2, 28))
    assert r["situacao"] == "concluida" and r["saldo"] == 0


def test_saldo_no_fim_da_turma_alerta_ou_bloqueia_conclusao():
    disc = [DisciplinaPlano(id="A", nome="A", carga_horaria=40)]
    previstas = [{"id": "p1", "disciplina_id": "A", "data_prevista": date(2026, 2, 7), "horas_previstas": 40}]
    alerta = calcular_andamento(disc, previstas, [], RegrasCalendario(), date(2026, 6, 1), date(2026, 5, 31))
    assert alerta["turma_encerrada"] and alerta["pode_concluir"] and "Diretoria decide" in alerta["alertas"][0]
    bloqueio = calcular_andamento(disc, previstas, [], RegrasCalendario(saldo_ao_fim_turma="bloquear_conclusao"),
                                  date(2026, 6, 1), date(2026, 5, 31))
    assert not bloqueio["pode_concluir"]


def test_frequencia_em_horas_e_horas_registradas():
    regras = RegrasCalendario(frequencia_base="horas", horas_abatidas="registradas")
    disc = [DisciplinaPlano(id="A", nome="A", carga_horaria=40)]
    previstas = [
        {"id": "p1", "disciplina_id": "A", "data_prevista": date(2026, 2, 7), "horas_previstas": 20},
        {"id": "p2", "disciplina_id": "A", "data_prevista": date(2026, 2, 14), "horas_previstas": 20},
    ]
    atas = [
        {"id": "a1", "disciplina_id": "A", "tipo": "prevista", "horas": 3, "aula_prevista_id": "p1", "chave": "k1"},
        {"id": "a2", "disciplina_id": "A", "tipo": "prevista", "horas": 1, "aula_prevista_id": "p2", "chave": "k2"},
    ]
    assert calcular_andamento(disc, previstas, atas, regras, date(2026, 2, 28))["horas_abatidas"] == 4
    presencas = [{"aluno_id": "x", "chave": "k1", "presente": True}, {"aluno_id": "x", "chave": "k2", "presente": False}]
    freq = calcular_frequencia([{"aluno_id": "x"}], disc, atas, presencas, previstas, regras)
    assert freq[0]["frequencia_pct"] == 75.0  # 3 h de 4 h
