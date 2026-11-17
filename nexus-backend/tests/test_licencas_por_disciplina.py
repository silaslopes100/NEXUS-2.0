"""Fase 3A: estoque de licenças por disciplina (balde "Sem disciplina", reclassificação, aluno por disciplina)."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.modules.alunos_gestao.repository import DadosReingresso, InMemoryAlunosGestaoRepository
from app.modules.financeiro.cobranca_service import creditar_licencas_padrao
from app.modules.polos_escolas import licencas as lic
from app.modules.polos_escolas.repository import InMemoryPolosEscolasRepository, set_polos_escolas_repository
from app.modules.polos_escolas.schemas import (
    LicencaCompraRequest,
    LicencaDevolverEscolaRequest,
    LicencaDistribuirRequest,
    LicencaReclassificarRequest,
    LicencaVenderRequest,
)

POLO, ESCOLA = "polo-1", "escola-1"
MAT, PORT = "disc-mat", "disc-port"


@pytest.fixture
def repo():
    r = InMemoryPolosEscolasRepository()
    r.disciplinas = {MAT: {"nome": "Matemática"}, PORT: {"nome": "Português"}}
    return r


def _comprar(repo, qtd, disciplina=None):
    lic.comprar_licencas(repo, POLO, LicencaCompraRequest(
        quantidade=qtd, fornecedor="Editora", valor_unitario=10, data=date.today(), disciplina_id=disciplina), "adm")


def _saldo(repo, *, polo=None, escola=None, disciplina="*"):
    return repo.get_estoque(polo_id=polo, escola_id=escola, materia_id=disciplina)["quantidade_disponivel"]


def test_saldos_separados_por_disciplina_e_total(repo):
    _comprar(repo, 10, MAT)
    _comprar(repo, 4, PORT)
    _comprar(repo, 3)  # sem disciplina
    assert _saldo(repo, polo=POLO, disciplina=MAT) == 10
    assert _saldo(repo, polo=POLO, disciplina=PORT) == 4
    assert _saldo(repo, polo=POLO, disciplina=None) == 3
    assert _saldo(repo, polo=POLO) == 17  # KPIs somam tudo
    itens = repo.list_estoque_por_disciplina(polo_id=POLO)
    assert itens[0]["materia_id"] is None  # "Sem disciplina" primeiro
    assert {i["disciplina_nome"] for i in itens[1:]} == {"Matemática", "Português"}


def test_distribuir_respeita_saldo_da_disciplina_e_estoque_da_escola_e_encontrado(repo):
    _comprar(repo, 10, MAT)
    _comprar(repo, 5, PORT)
    with pytest.raises(HTTPException) as exc:  # Português só tem 5
        lic.distribuir_para_escola(repo, POLO, LicencaDistribuirRequest(escola_id=ESCOLA, quantidade=6, disciplina_id=PORT), "adm")
    assert exc.value.status_code == 400
    lic.distribuir_para_escola(repo, POLO, LicencaDistribuirRequest(escola_id=ESCOLA, quantidade=6, disciplina_id=MAT), "adm")
    lic.distribuir_para_escola(repo, POLO, LicencaDistribuirRequest(escola_id=ESCOLA, quantidade=2, disciplina_id=MAT), "adm")
    # Regressão: antes o estoque da escola nunca era encontrado (linha duplicada a cada crédito).
    assert _saldo(repo, escola=ESCOLA, disciplina=MAT) == 8
    assert _saldo(repo, polo=POLO, disciplina=MAT) == 2
    assert len([k for k in repo.estoques if k[1] == ESCOLA]) == 1

    lic.devolver_de_escola_para_polo(repo, ESCOLA, POLO, LicencaDevolverEscolaRequest(quantidade=3, disciplina_id=MAT), "adm")
    assert _saldo(repo, escola=ESCOLA, disciplina=MAT) == 5 and _saldo(repo, polo=POLO, disciplina=MAT) == 5


def test_aluno_uma_licenca_ativa_por_disciplina_e_devolucao(repo):
    _comprar(repo, 5, MAT)
    _comprar(repo, 5, PORT)
    for d in (MAT, PORT):
        lic.distribuir_para_escola(repo, POLO, LicencaDistribuirRequest(escola_id=ESCOLA, quantidade=2, disciplina_id=d), "adm")

    lic.vender_para_aluno(repo, ESCOLA, POLO, LicencaVenderRequest(aluno_id="al-1", quantidade=1, disciplina_id=MAT), "sec")
    lic.vender_para_aluno(repo, ESCOLA, POLO, LicencaVenderRequest(aluno_id="al-1", quantidade=1, disciplina_id=PORT), "sec")
    with pytest.raises(HTTPException) as exc:
        lic.vender_para_aluno(repo, ESCOLA, POLO, LicencaVenderRequest(aluno_id="al-1", quantidade=1, disciplina_id=MAT), "sec")
    assert exc.value.status_code == 400 and "nesta disciplina" in exc.value.detail

    ativas = repo.list_licencas_aluno_ativas("al-1")
    assert {a["disciplina_nome"] for a in ativas} == {"Matemática", "Português"}
    with pytest.raises(HTTPException) as exc:  # duas ativas: precisa dizer qual
        lic.devolver_de_aluno_para_escola(repo, "al-1", "sec")
    assert exc.value.status_code == 409

    mat = next(a for a in ativas if a["materia_id"] == MAT)
    lic.devolver_de_aluno_para_escola(repo, "al-1", "sec", licenca_id=mat["id"])
    assert _saldo(repo, escola=ESCOLA, disciplina=MAT) == 2
    assert repo.get_estoque(escola_id=ESCOLA, materia_id=MAT)["quantidade_vendida"] == 0
    lic.devolver_de_aluno_para_escola(repo, "al-1", "sec")  # sobrou uma: não precisa de id
    assert repo.list_licencas_aluno_ativas("al-1") == []


def test_reclassificar_saldo_sem_disciplina(repo):
    _comprar(repo, 10)
    lic.reclassificar_saldo_polo(repo, POLO, LicencaReclassificarRequest(para_disciplina_id=MAT, quantidade=7), "adm")
    assert _saldo(repo, polo=POLO, disciplina=None) == 3 and _saldo(repo, polo=POLO, disciplina=MAT) == 7
    with pytest.raises(HTTPException):
        lic.reclassificar_saldo_polo(repo, POLO, LicencaReclassificarRequest(para_disciplina_id=MAT, quantidade=4), "adm")
    with pytest.raises(HTTPException) as exc:
        lic.reclassificar_saldo_polo(repo, POLO, LicencaReclassificarRequest(de_disciplina_id=MAT, para_disciplina_id=MAT, quantidade=1), "adm")
    assert exc.value.status_code == 422
    assert any(m["tipo"] == "reclassificacao" for m in repo.movimentacoes.values())


def test_pagamento_de_pedido_credita_por_disciplina(repo):
    set_polos_escolas_repository(repo)
    try:
        creditar_licencas_padrao({
            "numero": "PED-1", "polo_id": POLO, "valor_total": 130,
            "itens": [
                {"disciplina_id": MAT, "quantidade": 5, "valor_total": 50},
                {"disciplina_id": PORT, "quantidade": 4, "valor_total": 80},
            ],
        }, None)
    finally:
        set_polos_escolas_repository(None)
    assert _saldo(repo, polo=POLO, disciplina=MAT) == 5 and _saldo(repo, polo=POLO, disciplina=PORT) == 4
    movs = sorted((m["materia_id"], m["valor_unitario"]) for m in repo.movimentacoes.values())
    assert movs == [(MAT, 10.0), (PORT, 20.0)]


def test_reingresso_debita_da_disciplina_escolhida():
    repo = InMemoryAlunosGestaoRepository()
    repo.alunos["al-1"] = {"id": "al-1", "status": "desistente", "numero_matricula": "NX-1"}
    repo.estoque_polo[(POLO, MAT)] = 2
    repo.estoque_polo[POLO] = 0
    repo.reingressar("al-1", DadosReingresso("polo", POLO, None, 2, MAT), "adm", None)
    assert repo.estoque_polo[(POLO, MAT)] == 0
    assert repo.movimentacoes[-1]["materia_id"] == MAT
