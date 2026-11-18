"""Avaliações (questionários) e login por número de licença."""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.avaliacoes.repository import InMemoryAvaliacoesRepository
from app.modules.avaliacoes.schemas import AvaliacaoSalvar
from app.modules.avaliacoes.service import AvaliacoesService, corrigir

DISC = "disc-mat"
USUARIO, ALUNO = "u-aluno", "al-1"


def _questoes(n=4):
    return [{"enunciado": f"Pergunta {i}", "peso": 1,
             "alternativas": [{"texto": "certa", "correta": True}, {"texto": "errada", "correta": False}]}
            for i in range(n)]


@pytest.fixture
def notas():
    return []


@pytest.fixture
def svc(notas):
    repo = InMemoryAvaliacoesRepository()
    repo.disciplinas[DISC] = {"nome": "Matemática", "curso_id": "c1"}
    repo.alunos[USUARIO] = {"id": ALUNO, "modalidade": "polo", "status": "ativo"}
    repo.licencas.append({"id": "lic-1", "aluno_id": ALUNO, "materia_id": DISC, "status": "ativa"})

    def registrar(**kw):
        notas.append(kw)
        return f"nota-{len(notas)}"

    return AvaliacoesService(repo, registrar)


def _salvar(svc, ativo=True, **extra):
    return svc.salvar(DISC, AvaliacaoSalvar(titulo="Prova de Matemática", ativo=ativo, questoes=_questoes(), **extra), "adm")


def test_editor_valida_exatamente_uma_correta():
    with pytest.raises(ValidationError, match="questão 1"):
        AvaliacaoSalvar(titulo="X prova", questoes=[{"enunciado": "Qual?", "alternativas": [
            {"texto": "a", "correta": True}, {"texto": "b", "correta": True}]}])
    with pytest.raises(ValidationError, match="ao menos uma questão"):
        AvaliacaoSalvar(titulo="X prova", ativo=True, questoes=[])


def test_prova_sem_gabarito_nota_no_servidor_e_maior_nota(svc, notas):
    av = _salvar(svc)
    assert all(a.correta is not None for q in av.questoes for a in q.alternativas)  # editor vê o gabarito
    situacao = svc.minhas(USUARIO)[0]
    assert situacao.situacao == "disponivel" and situacao.pode_realizar

    t = svc.iniciar(av.id, USUARIO)
    assert all(a.correta is None for q in t.questoes for a in q.alternativas)  # aluno não vê
    completa = svc.repo.get_avaliacao(av.id)
    certas = {q["id"]: next(a["id"] for a in q["alternativas"] if a["correta"]) for q in completa["questoes"]}
    erradas = {q["id"]: next(a["id"] for a in q["alternativas"] if not a["correta"]) for q in completa["questoes"]}

    # 1ª tentativa: 2 de 4 certas = 5,0 (reprovado)
    respostas = {**erradas, **dict(list(certas.items())[:2])}
    r1 = svc.finalizar(t.tentativa_id, respostas, USUARIO)
    assert (r1.nota, r1.aprovado, r1.acertos, r1.tentativas_restantes) == (5.0, False, 2, 1)
    assert notas[-1]["origem"] == "prova" and notas[-1]["valor"] == 5.0
    assert svc.minhas(USUARIO)[0].situacao == "reprovado"

    # 2ª tentativa: tudo certo = 10,0
    t2 = svc.iniciar(av.id, USUARIO)
    r2 = svc.finalizar(t2.tentativa_id, certas, USUARIO)
    assert r2.aprovado and r2.nota == 10.0 and r2.melhor_nota == 10.0
    assert svc.minhas(USUARIO)[0].situacao == "aprovado"
    with pytest.raises(HTTPException) as exc:  # aprovado não refaz
        svc.iniciar(av.id, USUARIO)
    assert exc.value.status_code == 409


def test_limite_de_tentativas_e_retomada(svc):
    av = _salvar(svc, tentativas_max=1)
    t = svc.iniciar(av.id, USUARIO)
    svc.salvar_respostas(t.tentativa_id, {"x": "y"}, USUARIO)
    retomada = svc.iniciar(av.id, USUARIO)  # mesma tentativa em andamento, com as respostas salvas
    assert retomada.tentativa_id == t.tentativa_id and retomada.respostas == {"x": "y"}
    svc.finalizar(t.tentativa_id, None, USUARIO)
    assert svc.minhas(USUARIO)[0].situacao == "sem_tentativas"
    with pytest.raises(HTTPException) as exc:
        svc.iniciar(av.id, USUARIO)
    assert exc.value.status_code == 409


def test_tempo_esgotado_vale_o_salvo(svc):
    av = _salvar(svc, tempo_limite_min=5)
    t = svc.iniciar(av.id, USUARIO)
    svc.repo.tentativas[t.tentativa_id]["expira_em"] -= timedelta(minutes=10)
    r = svc.finalizar(t.tentativa_id, {"qualquer": "coisa"}, USUARIO)  # respostas após o prazo são ignoradas
    assert r.nota == 0.0 and svc.repo.tentativas[t.tentativa_id]["status"] == "expirada"


def test_sem_licenca_ead_e_inativa(svc):
    av = _salvar(svc, ativo=False)
    with pytest.raises(HTTPException) as exc:  # avaliação inativa
        svc.iniciar(av.id, USUARIO)
    assert exc.value.status_code == 404
    svc.definir_ativo(av.id, True)
    svc.repo.licencas[0]["status"] = "devolvida"
    with pytest.raises(HTTPException) as exc:
        svc.iniciar(av.id, USUARIO)
    assert exc.value.status_code == 403
    svc.repo.licencas[0]["status"] = "ativa"
    svc.repo.alunos[USUARIO]["modalidade"] = "ead"
    assert svc.minhas(USUARIO)[0].situacao == "ava"
    with pytest.raises(HTTPException) as exc:
        svc.iniciar(av.id, USUARIO)
    assert exc.value.status_code == 403


def test_correcao_com_peso():
    av = {"questoes": [
        {"id": "q1", "peso": 3, "alternativas": [{"id": "a", "correta": True}, {"id": "b", "correta": False}]},
        {"id": "q2", "peso": 1, "alternativas": [{"id": "c", "correta": True}, {"id": "d", "correta": False}]},
    ]}
    assert corrigir(av, {"q1": "a", "q2": "d"}) == (7.5, 1, 2)


# ---------------------------------------------------------------------------
# Login por número de licença
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_licenca(monkeypatch):
    from app.modules.auth.repository import InMemoryAuthRepository
    from app.modules.auth.service import AuthService
    from app.modules.polos_escolas.repository import InMemoryPolosEscolasRepository, set_polos_escolas_repository

    auth = InMemoryAuthRepository()
    auth.perfis["p-aluno"] = {"id": "p-aluno", "nome": "aluno", "descricao": "Aluno"}
    auth.usuarios[USUARIO] = {"id": USUARIO, "nome": "Aluno", "email": "aluno@nexus.com.br", "status": "ativo",
                              "perfil_id": "p-aluno", "polo_id": None, "escola_id": None}
    polos = InMemoryPolosEscolasRepository()
    polos.usuarios = auth.usuarios
    polos.alunos[ALUNO] = {"id": ALUNO, "usuario_id": USUARIO, "numero_matricula": "M1", "modalidade": "polo",
                           "status": "ativo"}
    lic_id = polos.vincular_licenca_aluno({"aluno_id": ALUNO, "polo_id": "p1", "materia_id": DISC})
    set_polos_escolas_repository(polos)
    yield AuthService(auth), polos, polos.get_licenca_aluno(lic_id)["numero_licenca"]
    set_polos_escolas_repository(None)


def test_login_licenca_valido_e_invalido(auth_licenca, monkeypatch):
    from app.core.security import decode_access_token

    service, polos, numero = auth_licenca
    r = service.login_licenca(numero.lower().replace("-", " "), client_ip="1.2.3.4")
    claims = decode_access_token(r.access_token)
    assert r.via == "licenca" and claims["via"] == "licenca" and r.refresh_token == ""
    assert r.destino["disciplina_id"] == DISC and r.usuario.id == USUARIO
    with pytest.raises(HTTPException) as exc:
        service.login_licenca("NX-2222-3333", client_ip="1.2.3.4")
    assert exc.value.status_code == 401
    polos.alunos[ALUNO]["modalidade"] = "ead"
    with pytest.raises(HTTPException) as exc:
        service.login_licenca(numero, client_ip="1.2.3.4")
    assert exc.value.status_code == 401


def test_login_licenca_bloqueia_por_ip(auth_licenca):
    service, _, numero = auth_licenca
    for _ in range(5):
        with pytest.raises(HTTPException):
            service.login_licenca("NX-2222-3333", client_ip="9.9.9.9")
    with pytest.raises(HTTPException) as exc:
        service.login_licenca(numero, client_ip="9.9.9.9")  # até o número certo fica bloqueado
    assert exc.value.status_code == 429
    assert service.login_licenca(numero, client_ip="8.8.8.8").via == "licenca"  # outro IP segue normal


@pytest.mark.asyncio
async def test_sessao_por_licenca_nao_altera_perfil():
    from fastapi.security import HTTPAuthorizationCredentials

    from app.core.security import create_access_token
    from app.modules.auth.dependencies import exigir_login_completo

    token = create_access_token({"sub": "u", "via": "licenca"})
    with pytest.raises(HTTPException) as exc:
        await exigir_login_completo(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert exc.value.status_code == 403
    await exigir_login_completo(HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_access_token({"sub": "u"})))


# ---------------------------------------------------------------------------
# Script de questionários de demonstração
# ---------------------------------------------------------------------------

def _demo():
    import importlib.util
    from pathlib import Path

    caminho = Path(__file__).resolve().parents[1] / "scripts" / "demo_avaliacoes.py"
    spec = importlib.util.spec_from_file_location("demo_avaliacoes", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_demo_gera_questoes_validas_e_recusa_producao(monkeypatch):
    demo = _demo()
    questoes = demo._questoes("Teologia Sistemática I", 1)
    av = AvaliacaoSalvar(titulo="Avaliação — Teologia", ativo=True, questoes=questoes)
    assert len(av.questoes) == 8 and all(len(q.alternativas) == 4 for q in av.questoes)
    assert len({[a.correta for a in q.alternativas].index(True) for q in av.questoes}) == 4  # correta varia
    assert "Teologia Sistemática I" in av.questoes[0].enunciado

    monkeypatch.setattr(demo.settings, "PAYMENT_ENV", "producao")
    with pytest.raises(SystemExit):
        demo._checar_ambiente(permitir_producao=True)
    monkeypatch.setattr(demo.settings, "PAYMENT_ENV", "sandbox")
    monkeypatch.setattr(demo.settings, "ENVIRONMENT", "production")
    with pytest.raises(SystemExit):
        demo._checar_ambiente(permitir_producao=False)
