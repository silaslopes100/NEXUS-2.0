from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.modules import ead as ead_module
from app.modules import turmas as turmas_module
from app.modules.alunos_gestao.repository import (
    InMemoryAlunosGestaoRepository,
    set_alunos_gestao_repository,
)
from app.modules.alunos_gestao.schemas import ReingressoRequest
from app.modules.alunos_gestao.service import AlunosGestaoService
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.transferencias.repository import InMemoryTransferenciasRepository
from app.modules.transferencias.schemas import (
    TransferenciaCreateRequest,
    TransferenciaResolverRequest,
)
from app.modules.transferencias.service import Ator, TransferenciasService

POLO = str(uuid.UUID(int=1))
OUTRO_POLO = str(uuid.UUID(int=2))
ESCOLA = str(uuid.UUID(int=11))
ATIVO = str(uuid.UUID(int=21))
PARADO = str(uuid.UUID(int=22))
CHURN = str(uuid.UUID(int=23))
CHURN_EAD = str(uuid.UUID(int=24))
CONTEUDO = str(uuid.UUID(int=31))

ADMIN = Ator("admin", "admin-1", None, None)
COORDENADOR = Ator("polo", "u-polo", POLO, None)
SECRETARIO = Ator("escola", "u-escola", POLO, ESCOLA)
OUTRO_COORDENADOR = Ator("polo", "u-outro", OUTRO_POLO, None)


def _aluno(aluno_id, usuario, polo=POLO, escola=ESCOLA, status="ativo", modalidade="polo", **extra):
    return {
        "id": aluno_id,
        "usuario_id": usuario,
        "nome": f"Aluno {usuario}",
        "numero_matricula": f"M-{usuario}",
        "polo_id": polo,
        "escola_id": escola,
        "modalidade": modalidade,
        "status": status,
        "referencia_movimentacao": datetime.now(timezone.utc),
        **extra,
    }


@pytest.fixture
def repo():
    r = InMemoryAlunosGestaoRepository()
    r.polos[POLO] = {"id": POLO, "nome": "Polo", "status": "ativo"}
    r.escolas[ESCOLA] = {"id": ESCOLA, "nome": "Escola", "polo_id": POLO, "status": "ativo"}
    r.estoque_polo[POLO] = 5
    r.alunos[ATIVO] = _aluno(ATIVO, "ativo", tem_certificado=True, turmas=["Turma 1"], presentes=3, total_aulas=4)
    r.alunos[PARADO] = _aluno(
        PARADO,
        "parado",
        parado=True,
        referencia_movimentacao=datetime.now(timezone.utc) - timedelta(days=400),
    )
    r.alunos[CHURN] = _aluno(CHURN, "churn", polo=None, escola=None, status="desistente")
    r.alunos[CHURN_EAD] = _aluno(
        CHURN_EAD, "churnead", polo=None, escola=None, status="desistente", modalidade="ead"
    )
    return r


@pytest.fixture
def service(repo):
    return AlunosGestaoService(repo)


def _codigo(func, *args) -> int:
    with pytest.raises(HTTPException) as exc_info:
        func(*args)
    return exc_info.value.status_code


def _listar(service, ator, **filtros):
    args = {"polo_id": None, "escola_id": None, "somente_ead": False, "observacao": None, "q": None}
    args.update(filtros)
    return service.listar(ator, *args.values(), 20, 0)


def _reingresso(modalidade="polo", polo=POLO, escola=ESCOLA, taxa=True):
    return ReingressoRequest(
        modalidade=modalidade, polo_destino_id=polo, escola_destino_id=escola, taxa_confirmada=taxa
    )


# ---------- Listagem ----------


def test_admin_ve_toda_a_base_inclusive_alunos_sem_polo(service):
    assert _listar(service, ADMIN).total == 4


def test_polo_e_escola_ficam_restritos_a_propria_unidade(service):
    assert {a.id for a in _listar(service, COORDENADOR, polo_id=OUTRO_POLO).items} == {ATIVO, PARADO}
    assert {a.id for a in _listar(service, SECRETARIO).items} == {ATIVO, PARADO}


def test_lista_monta_turma_presenca_e_observacoes(service):
    aluno = next(a for a in _listar(service, ADMIN).items if a.id == ATIVO)

    assert aluno.turmas == ["Turma 1"]
    assert aluno.percentual_presenca == 75.0
    assert aluno.observacoes == ["formado"]


def test_observacoes_de_churn_e_sem_movimentacao(service):
    itens = {a.id: a.observacoes for a in _listar(service, ADMIN).items}

    assert itens[CHURN] == ["churn"]
    assert itens[PARADO] == ["sem_movimentacao"]


def test_filtro_de_observacao_e_de_ead(service):
    assert {a.id for a in _listar(service, ADMIN, observacao="churn").items} == {CHURN, CHURN_EAD}
    assert [a.id for a in _listar(service, ADMIN, somente_ead=True).items] == [CHURN_EAD]


# ---------- Boletim e progresso ----------


def _linha(disciplina, situacao=None, total=4, concluidos=1, nota=None):
    return {
        "curso_id": "c-1",
        "curso_nome": "Curso",
        "disciplina_id": disciplina,
        "disciplina_nome": disciplina,
        "semestre": 1,
        "carga_horaria": 40,
        "nota": nota,
        "situacao": situacao,
        "total_conteudos": total,
        "conteudos_concluidos": concluidos,
    }


def test_boletim_calcula_progresso_e_separa_disciplinas_em_curso(service, repo):
    repo.linhas_academico[ATIVO] = [
        _linha("Em curso"),
        _linha("Aprovada", situacao="aprovado", nota=9.5),
        _linha("Sem conteudo", total=0, concluidos=0),
    ]

    disciplinas = {d.nome: d for d in service.academico(ADMIN, ATIVO).cursos[0].disciplinas}

    assert disciplinas["Em curso"].progresso == 25
    assert disciplinas["Em curso"].em_curso is True
    assert disciplinas["Aprovada"].em_curso is False
    assert disciplinas["Aprovada"].nota == 9.5
    assert disciplinas["Sem conteudo"].progresso is None


def test_aluno_em_churn_nao_tem_disciplina_em_curso(service, repo):
    repo.linhas_academico[CHURN] = [_linha("Disciplina")]

    assert service.academico(ADMIN, CHURN).cursos[0].disciplinas[0].em_curso is False


def test_boletim_respeita_o_escopo(service):
    assert _codigo(service.academico, OUTRO_COORDENADOR, ATIVO) == 403
    assert service.academico(COORDENADOR, ATIVO).aluno_id == ATIVO
    assert _codigo(service.academico, ADMIN, str(uuid.uuid4())) == 404


# ---------- Churn ----------


def test_confirmar_churn_desvincula_e_cancela_pendencias(service, repo):
    repo.turma_alunos.append({"turma_id": "t", "aluno_id": PARADO})
    repo.solicitacoes.append({"aluno_id": PARADO, "tipo": "troca_polo", "status": "pendente"})

    service.confirmar_churn(PARADO, "admin-1", None)

    aluno = repo.alunos[PARADO]
    assert (aluno["status"], aluno["polo_id"], aluno["escola_id"]) == ("desistente", None, None)
    assert repo.turma_alunos == []
    assert repo.desistentes[0]["aluno_id"] == PARADO
    assert repo.solicitacoes[0]["status"] == "rejeitada"


def test_nao_confirma_churn_de_aluno_com_movimentacao_recente(service, repo):
    assert _codigo(service.confirmar_churn, ATIVO, "admin-1", None) == 409
    assert repo.alunos[ATIVO]["status"] == "ativo"


# ---------- Reingresso ----------


def test_reingresso_no_polo_cobra_licencas_e_revalida(service, repo):
    repo.solicitacoes.append({"aluno_id": CHURN, "tipo": "reingresso", "status": "pendente"})

    resposta = service.reingressar(CHURN, _reingresso(), "admin-1", None)

    aluno = repo.alunos[CHURN]
    assert resposta.licencas_debitadas == 2
    assert repo.estoque_polo[POLO] == 3
    assert repo.movimentacoes[0]["tipo"] == "reingresso_churn"
    assert aluno["status"] == "ativo"
    assert aluno["polo_id"] == POLO
    assert aluno["escola_id"] == ESCOLA
    assert aluno["numero_matricula"] == resposta.numero_matricula != "M-churn"
    assert aluno["revalidado_em"] is not None
    assert repo.desistentes[-1]["matricula_anterior"] == "M-churn"
    assert repo.solicitacoes[0]["status"] == "aprovada"


def test_reingresso_ead_nao_cobra_licencas(service, repo):
    resposta = service.reingressar(CHURN_EAD, _reingresso("ead", None, None), "admin-1", None)

    assert resposta.licencas_debitadas == 0
    assert repo.estoque_polo[POLO] == 5
    assert repo.alunos[CHURN_EAD]["polo_id"] is None
    assert repo.alunos[CHURN_EAD]["modalidade"] == "ead"


def test_reingresso_exige_confirmacao_da_taxa(service, repo):
    assert _codigo(service.reingressar, CHURN, _reingresso(taxa=False), "admin-1", None) == 400
    assert repo.alunos[CHURN]["status"] == "desistente"


def test_reingresso_bloqueia_sem_estoque(service, repo):
    repo.estoque_polo[POLO] = 1

    assert _codigo(service.reingressar, CHURN, _reingresso(), "admin-1", None) == 409
    assert repo.alunos[CHURN]["status"] == "desistente"
    assert repo.estoque_polo[POLO] == 1


def test_reingresso_exige_escola_do_polo(service):
    assert _codigo(service.reingressar, CHURN, _reingresso(escola=None), "admin-1", None) == 400


def test_reingresso_somente_para_aluno_em_churn(service):
    assert _codigo(service.reingressar, ATIVO, _reingresso(), "admin-1", None) == 409


# ---------- Solicitação de reingresso ----------


@pytest.fixture
def transferencias():
    r = InMemoryTransferenciasRepository()
    r.polos[POLO] = {"id": POLO, "nome": "Polo", "status": "ativo"}
    r.escolas[ESCOLA] = {"id": ESCOLA, "nome": "Escola", "polo_id": POLO, "status": "ativo"}
    r.alunos[CHURN] = _aluno(CHURN, "churn", polo=None, escola=None, status="desistente")
    r.alunos[ATIVO] = _aluno(ATIVO, "ativo")
    return TransferenciasService(r)


def _pedido(aluno=CHURN, polo=POLO, escola=ESCOLA):
    return TransferenciaCreateRequest(
        aluno_id=aluno, tipo="reingresso", polo_destino_id=polo, escola_destino_id=escola
    )


def test_coordenador_solicita_reingresso_para_o_proprio_polo(transferencias):
    criada = transferencias.criar(COORDENADOR, _pedido(), None)

    assert criada.status == "pendente"
    assert criada.alerta_churn is False


def test_reingresso_nao_aceita_destino_fora_da_unidade(transferencias):
    assert _codigo(transferencias.criar, OUTRO_COORDENADOR, _pedido(), None) == 400


def test_reingresso_exclusivo_para_churn(transferencias):
    assert _codigo(transferencias.criar, COORDENADOR, _pedido(aluno=ATIVO), None) == 400


def test_busca_de_desistentes_alcanca_alunos_sem_polo(transferencias):
    encontrados = transferencias.buscar_alunos(COORDENADOR, "aluno", desistentes=True)

    assert [a.id for a in encontrados] == [CHURN]


def test_reingresso_nao_e_aprovado_pela_tela_de_transferencias(transferencias):
    criada = transferencias.criar(COORDENADOR, _pedido(), None)

    assert (
        _codigo(
            transferencias.resolver,
            criada.id,
            TransferenciaResolverRequest(aprovado=True),
            "admin-1",
            None,
        )
        == 409
    )
    rejeitada = transferencias.resolver(
        criada.id, TransferenciaResolverRequest(aprovado=False), "admin-1", None
    )
    assert rejeitada.status == "rejeitada"


# ---------- Aprendizado ----------


@pytest.fixture
def com_conteudo(repo):
    repo.linhas_aprendizado[ATIVO] = [
        {
            "curso_id": "c",
            "curso_nome": "Curso",
            "disciplina_id": "d",
            "disciplina_nome": "Disciplina",
            "conteudo_id": CONTEUDO,
            "titulo": "Aula 1",
        }
    ]
    return repo


def test_aluno_marca_e_desmarca_conteudo(service, com_conteudo):
    service.marcar_conteudo("ativo", CONTEUDO, True)
    assert service.aprendizado("ativo")[0].disciplinas[0].conteudos[0].concluido is True

    service.marcar_conteudo("ativo", CONTEUDO, False)
    assert service.aprendizado("ativo")[0].disciplinas[0].conteudos[0].concluido is False


def test_aluno_nao_marca_conteudo_fora_dos_seus_cursos(service, com_conteudo):
    assert _codigo(service.marcar_conteudo, "ativo", str(uuid.uuid4()), True) == 404


def test_aluno_em_churn_nao_avanca_no_conteudo(service, com_conteudo):
    assert _codigo(service.marcar_conteudo, "churn", CONTEUDO, True) == 403


# ---------- Regras em módulos vizinhos ----------


@pytest.mark.parametrize(
    ("inicio", "iniciada"),
    [
        (date.today() - timedelta(days=1), True),
        (date.today(), False),
        (date.today() + timedelta(days=5), False),
        (None, True),
    ],
)
def test_turma_ja_iniciada(inicio, iniciada):
    assert turmas_module._turma_ja_iniciada({"data_inicio": inicio}) is iniciada


def _cursor_com_status(monkeypatch, situacao):
    class Cursor:
        def execute(self, sql, params=()):
            pass

        def fetchone(self):
            return {"status": situacao}

    @contextmanager
    def database_cursor():
        yield Cursor()

    monkeypatch.setattr(settings, "PG_DSN", "configured-for-test")
    monkeypatch.setattr(ead_module, "get_db_cursor", database_cursor)


def test_ead_bloqueia_aluno_em_churn_com_a_mensagem_do_whatsapp(monkeypatch):
    _cursor_com_status(monkeypatch, "desistente")

    with pytest.raises(HTTPException) as exc_info:
        ead_module._bloquear_aluno_em_churn("a-1")

    assert exc_info.value.status_code == 409
    assert "WhatsApp (11)1936-6880" in exc_info.value.detail


def test_ead_libera_aluno_ativo(monkeypatch):
    _cursor_com_status(monkeypatch, "ativo")

    ead_module._bloquear_aluno_em_churn("a-1")


# ---------- Permissões por rota ----------


@pytest_asyncio.fixture
async def client(repo):
    auth = InMemoryAuthRepository()
    for usuario, perfil, polo in (("admin-1", "p-admin", None), ("polo-1", "p-polo", POLO)):
        auth.usuarios[usuario] = {
            "id": usuario,
            "nome": usuario,
            "email": f"{usuario}@nexus.com.br",
            "status": "ativo",
            "perfil_id": perfil,
            "polo_id": polo,
        }
    set_auth_repository(auth)
    set_alunos_gestao_repository(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    set_alunos_gestao_repository(None)


def _headers(usuario: str, perfil: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': usuario, 'perfil': perfil})}"}


@pytest.mark.asyncio
async def test_polo_lista_mas_nao_decide_churn_nem_reingresso(client):
    headers = _headers("polo-1", "polo")

    lista = await client.get("/alunos/gestao", headers=headers)
    churn = await client.post(f"/alunos/gestao/{PARADO}/churn", headers=headers)
    reingresso = await client.post(
        f"/alunos/gestao/{CHURN}/reingresso",
        json={"modalidade": "ead", "taxa_confirmada": True},
        headers=headers,
    )

    assert lista.status_code == 200
    assert lista.json()["total"] == 2
    assert churn.status_code == 403
    assert reingresso.status_code == 403


@pytest.mark.asyncio
async def test_admin_gera_nova_matricula_pela_rota(client):
    resposta = await client.post(
        f"/alunos/gestao/{CHURN_EAD}/reingresso",
        json={"modalidade": "ead", "taxa_confirmada": True},
        headers=_headers("admin-1", "admin"),
    )

    assert resposta.status_code == 200
    assert resposta.json()["licencas_debitadas"] == 0
