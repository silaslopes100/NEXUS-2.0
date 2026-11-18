"""Catálogo de compra por Curso: disciplinas ativas, à venda (com preço) e preço do Curso = soma."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.modules.cursos_disciplinas import _sincronizar_kit
from app.modules.financeiro.repository import InMemoryFinanceiroRepository


def _repo():
    repo = InMemoryFinanceiroRepository()
    repo.cursos = {
        "c1": {"nome": "Formação Teológica", "status": "ativo"},
        "c2": {"nome": "Curso Cancelado", "status": "cancelado"},
        "c3": {"nome": "Só inativas", "status": "ativo"},
    }
    repo.disciplinas = {
        "d1": {"nome": "Ética Cristã", "curso_id": "c1", "semestre": 1},
        "d2": {"nome": "Hermenêutica", "curso_id": "c1", "semestre": 1},
        "d3": {"nome": "Sem preço", "curso_id": "c1", "semestre": 2},
        "d4": {"nome": "Desativada", "curso_id": "c1", "semestre": 2, "ativo": False},
        "d5": {"nome": "Do cancelado", "curso_id": "c2"},
        "d6": {"nome": "Inativa", "curso_id": "c3", "ativo": False},
    }
    for d, preco in (("d1", 70), ("d2", 70), ("d4", 70), ("d5", 70)):
        repo.produtos[f"k{d}"] = {"id": f"k{d}", "tipo": "kit", "disciplina_id": d, "preco": preco,
                                  "ativo": d != "d4", "nome": f"kit {d}"}
    return repo


def test_catalogo_lista_curso_com_total_das_disciplinas_a_venda():
    cursos = _repo().catalogo_cursos()
    assert [c["id"] for c in cursos] == ["c1"]  # cancelado e só-inativas ficam fora
    c = cursos[0]
    assert (c["disciplinas"], c["disciplinas_a_venda"], c["preco_curso"]) == (3, 2, 140.0)


def test_detalhe_mostra_sem_preco_bloqueada_e_esconde_inativa():
    curso = _repo().catalogo_curso("c1", "polo-1")
    por_nome = {d["nome"]: d for d in curso["disciplinas"]}
    assert set(por_nome) == {"Ética Cristã", "Hermenêutica", "Sem preço"}
    assert por_nome["Sem preço"]["a_venda"] is False and por_nome["Sem preço"]["preco"] is None
    assert por_nome["Ética Cristã"]["a_venda"] is True and por_nome["Ética Cristã"]["preco"] == 70.0


class _Cursor:
    def __init__(self):
        self.params = None

    def execute(self, _sql, params):
        self.params = params


@pytest.mark.parametrize("preco,ativo,esperado", [(70, True, True), (70, False, False), (None, True, False), (0, True, False)])
def test_kit_so_fica_a_venda_com_preco_e_disciplina_ativa(preco, ativo, esperado):
    cur = _Cursor()
    _sincronizar_kit(cur, {"id": "00000000-0000-0000-0000-000000000001", "nome": "X", "preco": preco, "ativo": ativo})
    assert cur.params[-1] is esperado


def test_escola_nao_solicita_disciplina_sem_preco_ou_inativa():
    from app.modules.polos_escolas.repository import InMemoryPolosEscolasRepository
    from app.modules.solicitacoes.repository import InMemorySolicitacoesRepository
    from app.modules.solicitacoes.service import SolicitacaoCriar, SolicitacoesService

    polos = InMemoryPolosEscolasRepository()
    polos.escolas["e1"] = {"id": "e1", "nome": "Escola", "polo_id": "p1"}
    repo = InMemorySolicitacoesRepository()
    repo.disciplinas_db = {"d1": {"nome": "Sem preço", "preco": None}, "d2": {"nome": "Inativa", "preco": 70, "ativo": False}}
    svc = SolicitacoesService(repo, polos, notificar_fn=lambda **_: None)
    for d in ("d1", "d2"):
        with pytest.raises(HTTPException) as exc:
            svc.criar("e1", SolicitacaoCriar(itens=[{"disciplina_id": d, "quantidade": 1}]), "u", None)
        assert "sem preço ou inativa" in exc.value.detail
