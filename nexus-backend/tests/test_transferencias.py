from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.modules.admin.repository import InMemoryAdminRepository
from app.modules.admin.service import AdminService
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.auth.schemas import PerfilResponse, UserResponse
from app.modules.transferencias.repository import (
    InMemoryTransferenciasRepository,
    set_transferencias_repository,
)
from app.modules.transferencias.schemas import (
    TransferenciaCreateRequest,
    TransferenciaResolverRequest,
)
from app.modules.transferencias.service import Ator, TransferenciasService, ator_de

POLO_A = str(uuid.UUID(int=1))
POLO_B = str(uuid.UUID(int=2))
ESCOLA_A = str(uuid.UUID(int=11))
ESCOLA_B = str(uuid.UUID(int=12))
ALUNO = str(uuid.UUID(int=21))
ALUNO_EAD = str(uuid.UUID(int=22))
ALUNO_INATIVO_1_ANO = str(uuid.UUID(int=23))
COORDENADOR_ALUNO = str(uuid.UUID(int=24))
ALUNO_OUTRO_POLO = str(uuid.UUID(int=25))

ATOR_POLO = Ator("polo", "u-polo", POLO_A, None)
ATOR_ESCOLA = Ator("escola", "u-escola", POLO_A, ESCOLA_A)
ATOR_ALUNO = Ator("aluno", "u-aluno", POLO_A, None)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _aluno(aluno_id, usuario_id, polo=POLO_A, escola=ESCOLA_A, modalidade="polo", perfil="aluno", ref=None):
    return {
        "id": aluno_id,
        "usuario_id": usuario_id,
        "nome": f"Aluno {usuario_id}",
        "numero_matricula": f"M-{usuario_id}",
        "polo_id": polo,
        "escola_id": escola,
        "modalidade": modalidade,
        "status": "ativo",
        "perfil_nome": perfil,
        "referencia_movimentacao": ref or _agora(),
    }


@pytest.fixture
def repo():
    r = InMemoryTransferenciasRepository()
    r.polos[POLO_A] = {"id": POLO_A, "nome": "Polo A", "status": "ativo"}
    r.polos[POLO_B] = {"id": POLO_B, "nome": "Polo B", "status": "ativo"}
    r.escolas[ESCOLA_A] = {"id": ESCOLA_A, "nome": "Escola A", "polo_id": POLO_A, "status": "ativo"}
    r.escolas[ESCOLA_B] = {"id": ESCOLA_B, "nome": "Escola B", "polo_id": POLO_B, "status": "ativo"}
    r.alunos[ALUNO] = _aluno(ALUNO, "u-aluno")
    r.alunos[ALUNO_EAD] = _aluno(ALUNO_EAD, "u-ead", polo=None, escola=None, modalidade="ead")
    r.alunos[ALUNO_INATIVO_1_ANO] = _aluno(
        ALUNO_INATIVO_1_ANO, "u-parado", ref=_agora() - timedelta(days=400)
    )
    r.alunos[COORDENADOR_ALUNO] = _aluno(COORDENADOR_ALUNO, "u-coord", perfil="polo")
    r.alunos[ALUNO_OUTRO_POLO] = _aluno(ALUNO_OUTRO_POLO, "u-outro", polo=POLO_B, escola=ESCOLA_B)
    r.usuarios["u-aluno"] = {"polo_id": POLO_A, "escola_id": ESCOLA_A}
    r.usuarios["u-coord"] = {"polo_id": POLO_A, "escola_id": None}
    r.turma_alunos.append({"turma_id": "t-1", "aluno_id": ALUNO})
    return r


@pytest.fixture
def service(repo):
    return TransferenciasService(repo)


def _troca(aluno_id=ALUNO, polo=POLO_B, escola=ESCOLA_B):
    return TransferenciaCreateRequest(
        aluno_id=aluno_id, tipo="troca_polo", polo_destino_id=polo, escola_destino_id=escola
    )


def _codigo(func, *args) -> int:
    with pytest.raises(HTTPException) as exc_info:
        func(*args)
    return exc_info.value.status_code


APROVAR = TransferenciaResolverRequest(aprovado=True)


# ---------- Solicitação ----------


def test_polo_solicita_troca_com_dados_de_origem_do_banco(service):
    criada = service.criar(ATOR_POLO, _troca(), "127.0.0.1")

    assert criada.status == "pendente"
    assert criada.polo_origem_id == POLO_A
    assert criada.escola_origem_id == ESCOLA_A
    assert criada.polo_destino_nome == "Polo B"
    assert criada.solicitado_por == "u-polo"


def test_aluno_solicita_para_si_mesmo_ignorando_aluno_informado(service):
    dados = _troca(aluno_id=ALUNO_OUTRO_POLO)

    criada = service.criar(ATOR_ALUNO, dados, None)

    assert criada.aluno_id == ALUNO


def test_escola_so_solicita_alunos_da_propria_escola(service, repo):
    repo.alunos[ALUNO]["escola_id"] = None

    assert _codigo(service.criar, ATOR_ESCOLA, _troca(), None) == 403


def test_polo_nao_solicita_aluno_de_outro_polo(service):
    assert _codigo(service.criar, ATOR_POLO, _troca(ALUNO_OUTRO_POLO, POLO_A, ESCOLA_A), None) == 403


def test_escola_de_destino_e_obrigatoria(service):
    dados = TransferenciaCreateRequest(aluno_id=ALUNO, tipo="troca_polo", polo_destino_id=POLO_B)

    assert _codigo(service.criar, ATOR_POLO, dados, None) == 400


def test_escola_de_destino_deve_ser_do_polo_escolhido(service):
    assert _codigo(service.criar, ATOR_POLO, _troca(escola=ESCOLA_A), None) == 400


def test_destino_deve_ser_diferente_da_origem(service):
    assert _codigo(service.criar, ATOR_POLO, _troca(polo=POLO_A, escola=ESCOLA_A), None) == 400


def test_nao_permite_duas_solicitacoes_pendentes(service):
    service.criar(ATOR_POLO, _troca(), None)

    assert _codigo(service.criar, ATOR_POLO, _troca(), None) == 409


def test_aluno_desistente_nao_solicita(service, repo):
    repo.alunos[ALUNO]["status"] = "desistente"

    assert _codigo(service.criar, ATOR_POLO, _troca(), None) == 400


def test_tipo_precisa_combinar_com_a_modalidade(service):
    troca_de_ead = _troca(aluno_id=ALUNO_EAD)
    ead_de_presencial = TransferenciaCreateRequest(
        aluno_id=ALUNO, tipo="ead_para_polo", polo_destino_id=POLO_B, escola_destino_id=ESCOLA_B
    )

    assert _codigo(service.criar, ATOR_POLO, troca_de_ead, None) == 400
    assert _codigo(service.criar, ATOR_POLO, ead_de_presencial, None) == 400


# ---------- Aprovação ----------


def test_aprovar_troca_move_aluno_e_remove_das_turmas(service, repo):
    criada = service.criar(ATOR_POLO, _troca(), None)

    resolvida = service.resolver(criada.id, APROVAR, "admin-1", None)

    assert resolvida.status == "aprovada"
    assert repo.alunos[ALUNO]["polo_id"] == POLO_B
    assert repo.alunos[ALUNO]["escola_id"] == ESCOLA_B
    assert repo.usuarios["u-aluno"] == {"polo_id": POLO_B, "escola_id": ESCOLA_B}
    assert repo.turma_alunos == []
    assert repo.logs[-1]["acao"] == "transferencia_aprovada"


def test_migrar_para_ead_remove_polo_e_escola(service, repo):
    dados = TransferenciaCreateRequest(aluno_id=ALUNO, tipo="polo_para_ead")
    criada = service.criar(ATOR_POLO, dados, None)

    service.resolver(criada.id, APROVAR, "admin-1", None)

    assert repo.alunos[ALUNO]["modalidade"] == "ead"
    assert repo.alunos[ALUNO]["polo_id"] is None
    assert repo.alunos[ALUNO]["escola_id"] is None


def test_migrar_de_ead_para_polo_define_destino(service, repo):
    dados = TransferenciaCreateRequest(
        aluno_id=ALUNO_EAD, tipo="ead_para_polo", polo_destino_id=POLO_B, escola_destino_id=ESCOLA_B
    )
    criada = service.criar(ATOR_POLO, dados, None)

    service.resolver(criada.id, APROVAR, "admin-1", None)

    assert repo.alunos[ALUNO_EAD]["modalidade"] == "polo"
    assert repo.alunos[ALUNO_EAD]["polo_id"] == POLO_B
    assert repo.alunos[ALUNO_EAD]["escola_id"] == ESCOLA_B


def test_rejeitar_nao_altera_aluno(service, repo):
    criada = service.criar(ATOR_POLO, _troca(), None)

    resolvida = service.resolver(
        criada.id, TransferenciaResolverRequest(aprovado=False, motivo="Sem vaga"), "admin-1", None
    )

    assert resolvida.status == "rejeitada"
    assert resolvida.motivo_rejeicao == "Sem vaga"
    assert repo.alunos[ALUNO]["polo_id"] == POLO_A
    assert len(repo.turma_alunos) == 1


def test_nao_resolve_solicitacao_ja_resolvida(service):
    criada = service.criar(ATOR_POLO, _troca(), None)
    service.resolver(criada.id, APROVAR, "admin-1", None)

    assert _codigo(service.resolver, criada.id, APROVAR, "admin-1", None) == 409


def test_solicitacao_inexistente_retorna_404(service):
    assert _codigo(service.resolver, str(uuid.uuid4()), APROVAR, "admin-1", None) == 404


def test_destino_inativado_impede_aprovacao(service, repo):
    criada = service.criar(ATOR_POLO, _troca(), None)
    repo.escolas[ESCOLA_B]["status"] = "inativo"

    assert _codigo(service.resolver, criada.id, APROVAR, "admin-1", None) == 409
    assert repo.alunos[ALUNO]["polo_id"] == POLO_A


def test_coordenador_que_e_aluno_mantem_o_polo_que_gerencia(service, repo):
    criada = service.criar(ATOR_POLO, _troca(aluno_id=COORDENADOR_ALUNO), None)

    service.resolver(criada.id, APROVAR, "admin-1", None)

    assert repo.alunos[COORDENADOR_ALUNO]["polo_id"] == POLO_B
    assert repo.usuarios["u-coord"] == {"polo_id": POLO_A, "escola_id": None}


# ---------- Churn ----------


def test_solicitacao_de_aluno_parado_ha_mais_de_um_ano_recebe_alerta(service):
    criada = service.criar(ATOR_POLO, _troca(aluno_id=ALUNO_INATIVO_1_ANO), None)

    assert criada.alerta_churn is True


def test_churn_exige_confirmacao(service, repo):
    criada = service.criar(ATOR_POLO, _troca(aluno_id=ALUNO_INATIVO_1_ANO), None)

    assert _codigo(service.resolver, criada.id, APROVAR, "admin-1", None) == 409
    assert repo.alunos[ALUNO_INATIVO_1_ANO]["status"] == "ativo"


def test_churn_confirmado_desvincula_e_marca_desistente(service, repo):
    criada = service.criar(ATOR_POLO, _troca(aluno_id=ALUNO_INATIVO_1_ANO), None)

    resolvida = service.resolver(
        criada.id, TransferenciaResolverRequest(aprovado=True, confirmar_churn=True), "admin-1", None
    )

    assert resolvida.status == "churn"
    assert resolvida.alerta_churn is False
    aluno = repo.alunos[ALUNO_INATIVO_1_ANO]
    assert aluno["status"] == "desistente"
    assert aluno["polo_id"] is None
    assert aluno["escola_id"] is None
    assert repo.desistentes[0]["aluno_id"] == ALUNO_INATIVO_1_ANO


# ---------- Escopo e consultas ----------


def test_listagem_respeita_o_escopo(service, repo):
    service.criar(ATOR_POLO, _troca(), None)

    assert service.listar(Ator("polo", "x", POLO_B, None), None, None, None, 20, 0).total == 1
    assert service.listar(Ator("polo", "x", str(uuid.uuid4()), None), None, None, None, 20, 0).total == 0
    assert service.listar(ATOR_ALUNO, None, None, None, 20, 0).total == 1
    assert service.listar(Ator("aluno", "u-ead", None, None), None, None, None, 20, 0).total == 0
    assert service.listar(Ator("admin", "a", None, None), None, None, None, 20, 0).total == 1


def test_busca_de_alunos_limita_a_unidade_e_inclui_ead(service):
    encontrados = {aluno.id for aluno in service.buscar_alunos(ATOR_POLO, "aluno")}

    assert ALUNO in encontrados
    assert ALUNO_EAD in encontrados
    assert ALUNO_OUTRO_POLO not in encontrados


def test_resumo_mostra_apenas_pendentes(service):
    criada = service.criar(ATOR_POLO, _troca(), None)
    assert service.resumo_pendentes().total == 1

    service.resolver(criada.id, APROVAR, "admin-1", None)

    assert service.resumo_pendentes().total == 0


def test_escopo_aluno_exige_cadastro_de_aluno():
    usuario = UserResponse(id="u", nome="N", perfil=PerfilResponse(nome="polo"), polo_id=POLO_A)
    duplo = usuario.model_copy(update={"tambem_aluno": True})

    with pytest.raises(HTTPException) as exc_info:
        ator_de(usuario, "aluno")

    assert exc_info.value.status_code == 403
    assert ator_de(duplo, "aluno").perfil == "aluno"
    assert ator_de(duplo).perfil == "polo"


def test_lista_de_usuarios_expoe_a_tag_de_pendencia():
    service = AdminService(repo=InMemoryAdminRepository())

    usuario = service._build_user_response(
        {"id": "u", "nome": "N", "status": "ativo", "transferencia_pendente": True}, []
    )

    assert usuario.transferencia_pendente is True


# ---------- Permissões por rota ----------


@pytest_asyncio.fixture
async def client(repo):
    auth = InMemoryAuthRepository()
    auth.usuarios["admin-1"] = {
        "id": "admin-1", "nome": "Admin", "email": "a@nexus.com.br", "status": "ativo", "perfil_id": "p-admin",
    }
    auth.usuarios["polo-1"] = {
        "id": "polo-1", "nome": "Polo", "email": "p@nexus.com.br", "status": "ativo",
        "perfil_id": "p-polo", "polo_id": POLO_A,
    }
    set_auth_repository(auth)
    set_transferencias_repository(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    set_transferencias_repository(None)


def _headers(user_id: str, perfil: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id, 'perfil': perfil})}"}


@pytest.mark.asyncio
async def test_polo_nao_aprova_e_admin_nao_solicita(client, service):
    criada = service.criar(ATOR_POLO, _troca(), None)

    aprovar = await client.put(
        f"/transferencias/{criada.id}/resolver",
        json={"aprovado": True},
        headers=_headers("polo-1", "polo"),
    )
    solicitar = await client.post(
        "/transferencias",
        json={"aluno_id": ALUNO, "tipo": "polo_para_ead"},
        headers=_headers("admin-1", "admin"),
    )

    assert aprovar.status_code == 403
    assert solicitar.status_code == 403


@pytest.mark.asyncio
async def test_resumo_de_pendencias_e_exclusivo_do_admin(client):
    negado = await client.get("/transferencias/pendentes/resumo", headers=_headers("polo-1", "polo"))
    permitido = await client.get("/transferencias/pendentes/resumo", headers=_headers("admin-1", "admin"))

    assert negado.status_code == 403
    assert permitido.status_code == 200
    assert permitido.json() == {"total": 0, "items": []}


@pytest.mark.asyncio
async def test_busca_exige_tres_caracteres(client):
    resposta = await client.get(
        "/transferencias/alunos", params={"q": "ab"}, headers=_headers("polo-1", "polo")
    )

    assert resposta.status_code == 422
