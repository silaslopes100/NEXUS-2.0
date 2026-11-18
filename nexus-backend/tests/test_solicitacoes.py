"""Solicitações Escola → Polo, Nota de Prestação de Contas e notificações."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.notificacoes import InMemoryNotificacoesRepository, _escopo, set_notificacoes_repository
from app.modules.polos_escolas.repository import InMemoryPolosEscolasRepository
from app.modules.solicitacoes.repository import InMemorySolicitacoesRepository
from app.modules.solicitacoes.service import (
    SolicitacaoAtender,
    SolicitacaoCriar,
    SolicitacaoRecusar,
    SolicitacoesService,
)

POLO, ESCOLA, D1, D2 = "polo-1", "esc-1", "disc-1", "disc-2"


@pytest.fixture
def ctx():
    polos = InMemoryPolosEscolasRepository()
    polos.polos[POLO] = {"id": POLO, "nome": "Polo Centro", "cidade": "São Paulo", "uf": "SP"}
    polos.escolas[ESCOLA] = {"id": ESCOLA, "nome": "Escola Bom Pastor", "polo_id": POLO}
    polos.ajustar_estoque(polo_id=POLO, escola_id=None, delta_disponivel=10, materia_id=D1)
    polos.ajustar_estoque(polo_id=POLO, escola_id=None, delta_disponivel=2, materia_id=D2)
    repo = InMemorySolicitacoesRepository()
    repo.disciplinas_db = {D1: {"nome": "Teologia I", "preco": 50.0}, D2: {"nome": "Hermenêutica", "preco": 40.0}}
    repo.escolas, repo.polos = {ESCOLA: "Escola Bom Pastor"}, {POLO: "Polo Centro"}
    notif = InMemoryNotificacoesRepository()
    set_notificacoes_repository(notif)
    yield SolicitacoesService(repo, polos), polos, notif
    set_notificacoes_repository(None)


def _estoque(polos, **kw):
    return polos.get_estoque(**kw)["quantidade_disponivel"]


def _usuario(perfil, polo_id=None, escola_id=None, uid="u1"):
    return SimpleNamespace(id=uid, perfil=SimpleNamespace(nome=perfil), polo_id=polo_id, escola_id=escola_id)


def test_fluxo_completo_atende_parcial_emite_nota_e_notifica(ctx):
    svc, polos, notif = ctx
    s = svc.criar(ESCOLA, SolicitacaoCriar(itens=[{"disciplina_id": D1, "quantidade": 3},
                                                  {"disciplina_id": D2, "quantidade": 5}]), "u-esc", None)
    assert s.status == "pendente" and s.polo_id == POLO and s.valor_estimado == 3 * 50 + 5 * 40
    polo_user = _usuario("coordenador_polo", polo_id=POLO)
    assert notif.contar_nao_lidas(_escopo(polo_user)) == 1  # Polo avisado

    lista = svc.listar_polo(POLO, "pendente")
    saldo = {i.disciplina_id: i.saldo_polo for i in lista[0].itens}
    assert saldo == {D1: 10, D2: 2}

    item = {i.disciplina_id: i.id for i in s.itens}
    with pytest.raises(HTTPException) as exc:  # mais que o saldo do Polo
        svc.atender(POLO, s.id, SolicitacaoAtender(itens=[{"item_id": item[D2], "quantidade_atendida": 5}]), "u-polo", None)
    assert exc.value.status_code == 400 and "Saldo insuficiente" in exc.value.detail

    r = svc.atender(POLO, s.id, SolicitacaoAtender(itens=[{"item_id": item[D1], "quantidade_atendida": 3},
                                                          {"item_id": item[D2], "quantidade_atendida": 2}]), "u-polo", None)
    assert r.status == "atendida_parcial" and r.nota_numero.startswith("NPC-")
    assert r.nota_valor_total == 3 * 50 + 2 * 40 and r.nota_status == "emitida"
    assert _estoque(polos, polo_id=POLO, materia_id=D1) == 7
    assert _estoque(polos, escola_id=ESCOLA, materia_id=D1) == 3
    assert _estoque(polos, escola_id=ESCOLA, materia_id=D2) == 2
    escola_user = _usuario("secretario_escola", escola_id=ESCOLA)
    assert "atendida em parte" in notif.listar(_escopo(escola_user), 10)[0]["titulo"]

    with pytest.raises(HTTPException) as exc:  # não atende duas vezes
        svc.atender(POLO, s.id, SolicitacaoAtender(itens=[{"item_id": item[D1], "quantidade_atendida": 1}]), "u", None)
    assert exc.value.status_code == 409

    pdf = svc.nota_pdf(svc.checar_escopo(s.id, escola_user))
    assert pdf.startswith(b"%PDF")

    q = svc.repasse_recebido(POLO, r.nota_id, "u-polo", None)
    assert q.nota_status == "repasse_recebido"
    with pytest.raises(HTTPException) as exc:
        svc.repasse_recebido(POLO, r.nota_id, "u-polo", None)
    assert exc.value.status_code == 409


def test_recusar_e_validacoes(ctx):
    svc, polos, notif = ctx
    with pytest.raises(ValidationError):  # disciplina repetida
        SolicitacaoCriar(itens=[{"disciplina_id": D1, "quantidade": 1}, {"disciplina_id": D1, "quantidade": 2}])
    with pytest.raises(HTTPException):
        svc.criar(ESCOLA, SolicitacaoCriar(itens=[{"disciplina_id": "inexistente", "quantidade": 1}]), "u", None)

    s = svc.criar(ESCOLA, SolicitacaoCriar(itens=[{"disciplina_id": D1, "quantidade": 2}]), "u", None)
    with pytest.raises(HTTPException) as exc:  # atender com zero
        svc.atender(POLO, s.id, SolicitacaoAtender(itens=[{"item_id": s.itens[0].id, "quantidade_atendida": 0}]), "u", None)
    assert "Recusar" in exc.value.detail
    with pytest.raises(HTTPException) as exc:  # outro Polo
        svc.recusar("polo-x", s.id, SolicitacaoRecusar(motivo="Sem estoque"), "u", None)
    assert exc.value.status_code == 404

    r = svc.recusar(POLO, s.id, SolicitacaoRecusar(motivo="Sem estoque no momento"), "u", None)
    assert r.status == "recusada" and r.motivo_recusa == "Sem estoque no momento" and r.nota_id is None
    assert _estoque(polos, polo_id=POLO, materia_id=D1) == 10  # nada saiu
    with pytest.raises(HTTPException) as exc:
        svc.nota_pdf(svc.checar_escopo(s.id, _usuario("admin")))
    assert exc.value.status_code == 404


def test_escopo_da_solicitacao(ctx):
    svc, _, _ = ctx
    s = svc.criar(ESCOLA, SolicitacaoCriar(itens=[{"disciplina_id": D1, "quantidade": 1}]), "u", None)
    svc.checar_escopo(s.id, _usuario("coordenador_polo", polo_id=POLO))
    for intruso in (_usuario("coordenador_polo", polo_id="outro"), _usuario("secretario_escola", escola_id="outra")):
        with pytest.raises(HTTPException) as exc:
            svc.checar_escopo(s.id, intruso)
        assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        svc.checar_escopo(s.id, _usuario("aluno"))
    assert exc.value.status_code == 403


def test_notificacoes_por_unidade_e_lidas():
    repo = InMemoryNotificacoesRepository()
    a = repo.criar({"titulo": "Para o polo", "destino_polo_id": POLO})
    repo.criar({"titulo": "Para a escola", "destino_escola_id": ESCOLA})
    repo.criar({"titulo": "Pessoal", "destino_usuario_id": "u9"})
    coord = _escopo(_usuario("coordenador_polo", polo_id=POLO, uid="u9"))
    assert {n["titulo"] for n in repo.listar(coord, 10)} == {"Para o polo", "Pessoal"}
    assert repo.marcar_lida(a, coord) and repo.contar_nao_lidas(coord) == 1
    assert not repo.marcar_lida(a, _escopo(_usuario("secretario_escola", escola_id=ESCOLA)))  # não é dela
    assert repo.marcar_todas(coord) == 1 and repo.contar_nao_lidas(coord) == 0
