"""Testes do núcleo Financeiro & Logística (Fase 1): regras, service, escopo, acesso e crypto."""
from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core import crypto
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.auth.schemas import PerfilResponse, UserResponse
from app.modules.financeiro import pedidos as regras
from app.modules.financeiro.repository import InMemoryFinanceiroRepository, set_financeiro_repository
from app.modules.financeiro.schemas import EnderecoEntrega, PedidoCreate, PedidoItemIn, ProdutoCreate
from app.modules.financeiro.service import FinanceiroService

POLO_A, POLO_B = "polo-a", "polo-b"
ENDERECO_POLO = {
    "nome": "Polo A", "cep": "01001-000", "logradouro": "Praça da Sé", "numero": "1",
    "bairro": "Sé", "cidade": "São Paulo", "uf": "SP",
}


def _user(perfil: str, uid: str = "u1", polo_id=None, escola_id=None, permissoes=()) -> UserResponse:
    return UserResponse(
        id=uid, nome=uid, perfil=PerfilResponse(id=f"p-{perfil}", nome=perfil),
        polo_id=polo_id, escola_id=escola_id, permissoes=list(permissoes),
    )


@pytest.fixture
def repo():
    r = InMemoryFinanceiroRepository()
    r.polos[POLO_A] = dict(ENDERECO_POLO)
    r.polos[POLO_B] = {**ENDERECO_POLO, "nome": "Polo B"}
    return r


@pytest.fixture
def service(repo):
    return FinanceiroService(repo)


def _produto(service, tipo="livro", sku="LIV-1", preco=10.0, ativo=True):
    return service.create_produto(ProdutoCreate(tipo=tipo, sku=sku, nome=f"Produto {sku}", preco=preco, ativo=ativo))


# ---------------------------------------------------------------------------
# Regras puras
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("de,para", [
    ("aguardando_pagamento", "pago_aguardando_envio"),
    ("aguardando_pagamento", "concluido"),
    ("aguardando_pagamento", "cancelado"),
    ("pago_aguardando_envio", "enviado"),
    ("pago_aguardando_envio", "cancelado"),
    ("enviado", "entregue"),
])
def test_transicoes_validas(de, para):
    regras.validar_transicao(de, para)


@pytest.mark.parametrize("de,para", [
    ("aguardando_pagamento", "enviado"),
    ("enviado", "cancelado"),
    ("cancelado", "aguardando_pagamento"),
    ("concluido", "cancelado"),
    ("entregue", "enviado"),
])
def test_transicoes_invalidas_geram_409(de, para):
    with pytest.raises(HTTPException) as exc:
        regras.validar_transicao(de, para)
    assert exc.value.status_code == 409


@pytest.mark.parametrize("tipo,para", [
    ("livro", "concluido"),
    ("licenca", "pago_aguardando_envio"),
])
def test_destino_incoerente_com_tipo_gera_409(tipo, para):
    with pytest.raises(HTTPException) as exc:
        regras.validar_transicao_para_tipo(tipo, "aguardando_pagamento", para)
    assert exc.value.status_code == 409
    regras.validar_transicao_para_tipo(tipo, "aguardando_pagamento", "cancelado")


def test_status_pos_pagamento():
    assert regras.status_pos_pagamento("livro") == "pago_aguardando_envio"
    assert regras.status_pos_pagamento("licenca") == "concluido"


def test_calcular_totais_com_desconto_e_arredondamento():
    bruto, desc, total = regras.calcular_totais([(Decimal("10.005"), 3), ("2.10", 1)], desconto="5")
    assert bruto == Decimal("32.13")  # 10.01*3 + 2.10
    assert desc == Decimal("5.00")
    assert total == Decimal("27.13")


def test_desconto_nao_deixa_total_negativo():
    _, desc, total = regras.calcular_totais([(10, 1)], desconto=50)
    assert desc == Decimal("10.00") and total == Decimal("0.00")


# ---------------------------------------------------------------------------
# Service: criação de pedido
# ---------------------------------------------------------------------------

def test_criar_pedido_usa_preco_do_catalogo_e_snapshot_endereco(service):
    prod = _produto(service, preco=59.9)
    pedido = service.criar_pedido(
        PedidoCreate(tipo="livro", itens=[PedidoItemIn(produto_id=prod.id, quantidade=2),
                                          PedidoItemIn(produto_id=prod.id, quantidade=1)]),
        _user("polo", polo_id=POLO_A),
    )
    assert pedido.polo_id == POLO_A
    assert pedido.status == "aguardando_pagamento"
    assert len(pedido.itens) == 1 and pedido.itens[0].quantidade == 3  # itens repetidos somados
    assert pedido.valor_total == pytest.approx(179.7)
    assert pedido.endereco.cep == "01001-000"
    assert pedido.historico[0].status_para == "aguardando_pagamento"


def test_criar_pedido_rejeita_produto_inativo_ou_de_outro_tipo(service):
    inativo = _produto(service, sku="LIV-X", ativo=False)
    licenca = _produto(service, tipo="licenca", sku="LIC-1")
    polo = _user("polo", polo_id=POLO_A)
    for produto_id in (inativo.id, licenca.id, "nao-existe"):
        with pytest.raises(HTTPException) as exc:
            service.criar_pedido(
                PedidoCreate(tipo="livro", itens=[PedidoItemIn(produto_id=produto_id, quantidade=1)]), polo
            )
        assert exc.value.status_code == 422


def test_criar_pedido_livro_exige_endereco_completo(service, repo):
    repo.polos[POLO_A] = {"nome": "Polo A"}  # sem endereço cadastrado
    prod = _produto(service)
    with pytest.raises(HTTPException) as exc:
        service.criar_pedido(
            PedidoCreate(tipo="livro", itens=[PedidoItemIn(produto_id=prod.id, quantidade=1)]),
            _user("polo", polo_id=POLO_A),
        )
    assert exc.value.status_code == 422
    pedido = service.criar_pedido(
        PedidoCreate(
            tipo="livro", itens=[PedidoItemIn(produto_id=prod.id, quantidade=1)],
            endereco=EnderecoEntrega(cep="20000-000", logradouro="Rua X", cidade="Rio", uf="RJ"),
        ),
        _user("polo", polo_id=POLO_A),
    )
    assert pedido.endereco.cidade == "Rio"


def test_polo_nao_cria_pedido_para_outro_polo(service):
    prod = _produto(service)
    with pytest.raises(HTTPException) as exc:
        service.criar_pedido(
            PedidoCreate(tipo="livro", polo_id=POLO_B, itens=[PedidoItemIn(produto_id=prod.id, quantidade=1)]),
            _user("polo", polo_id=POLO_A),
        )
    assert exc.value.status_code == 403


def test_alterar_status_preenche_timestamp_e_trava_otimista(service, repo):
    prod = _produto(service)
    pedido = service.criar_pedido(
        PedidoCreate(tipo="livro", itens=[PedidoItemIn(produto_id=prod.id, quantidade=1)]),
        _user("polo", polo_id=POLO_A),
    )
    pago = service.alterar_status(pedido.id, "pago_aguardando_envio", None, origem="webhook")
    assert pago.pago_em is not None
    assert [h.status_para for h in pago.historico] == ["aguardando_pagamento", "pago_aguardando_envio"]

    # Outra operação lê o status antigo e tenta transicionar: conflito.
    with pytest.raises(HTTPException) as exc:
        repo.alterar_status_pedido(pedido.id, "aguardando_pagamento", "cancelado", None, "usuario")
    assert exc.value.status_code == 409

    cancelado = service.alterar_status(pedido.id, "cancelado", "u1", campos={"motivo_cancelamento": "teste"})
    assert cancelado.motivo_cancelamento == "teste" and cancelado.cancelado_em is not None
    with pytest.raises(HTTPException) as exc:
        service.alterar_status(pedido.id, "cancelado", "u1")
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Escopo de visibilidade
# ---------------------------------------------------------------------------

def _dois_pedidos(service):
    prod = _produto(service)
    item = [PedidoItemIn(produto_id=prod.id, quantidade=1)]
    a = service.criar_pedido(PedidoCreate(tipo="livro", itens=item), _user("polo", polo_id=POLO_A))
    b = service.criar_pedido(PedidoCreate(tipo="livro", itens=item), _user("polo", "u2", polo_id=POLO_B))
    return a, b


@pytest.mark.parametrize("perfil", ["admin", "financeiro", "logistica"])
def test_perfis_globais_veem_todos_os_pedidos(service, perfil):
    _dois_pedidos(service)
    from app.modules.financeiro.schemas import FiltrosPeriodo
    assert service.list_pedidos(FiltrosPeriodo(), _user(perfil)).total == 2


def test_polo_so_ve_os_proprios_pedidos(service):
    a, b = _dois_pedidos(service)
    from app.modules.financeiro.schemas import FiltrosPeriodo
    polo_a = _user("polo", polo_id=POLO_A)
    lista = service.list_pedidos(FiltrosPeriodo(), polo_a)
    assert [p.id for p in lista.items] == [a.id]
    # Pedir explicitamente outro polo não fura o escopo.
    assert service.list_pedidos(FiltrosPeriodo(polo_id=POLO_B), polo_a).total == 0
    with pytest.raises(HTTPException) as exc:
        service.get_pedido(b.id, polo_a)
    assert exc.value.status_code == 404


def test_filtros_de_periodo(service):
    _dois_pedidos(service)
    from datetime import date
    from app.modules.financeiro.schemas import FiltrosPeriodo
    hoje = date.today()
    admin = _user("admin")
    assert service.list_pedidos(FiltrosPeriodo(ano=hoje.year, mes=hoje.month), admin).total == 2
    semestre_oposto = 2 if hoje.month <= 6 else 1
    assert service.list_pedidos(FiltrosPeriodo(semestre=semestre_oposto), admin).total == 0
    assert service.list_pedidos(FiltrosPeriodo(status="enviado"), admin).total == 0
    assert service.list_pedidos(FiltrosPeriodo(polo_id=POLO_B), admin).total == 1
    with pytest.raises(ValueError):
        FiltrosPeriodo(data_inicio=hoje, data_fim=date(2000, 1, 1))


# ---------------------------------------------------------------------------
# API: acesso por área
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_repo():
    r = InMemoryAuthRepository()
    r.perfis["p-financeiro"] = {"id": "p-financeiro", "nome": "financeiro", "descricao": "Financeiro"}
    r.perfis["p-logistica"] = {"id": "p-logistica", "nome": "logistica", "descricao": "Logística"}
    usuarios = {
        "admin-1": "p-admin", "fin-1": "p-financeiro", "log-1": "p-logistica",
        "prof-1": "p-prof", "prof-fin": "p-prof", "polo-1": "p-polo",
    }
    for uid, perfil_id in usuarios.items():
        r.usuarios[uid] = {
            "id": uid, "nome": uid, "email": f"{uid}@nexus.com.br", "status": "ativo",
            "perfil_id": perfil_id, "polo_id": POLO_A if uid == "polo-1" else None, "escola_id": None,
        }
    # professor com permissão granular de financeiro
    r.usuario_permissoes.append({"usuario_id": "prof-fin", "permissao_id": "perm-fin"})
    set_auth_repository(r)
    return r


@pytest_asyncio.fixture
async def client(auth_repo, repo):
    set_financeiro_repository(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    set_financeiro_repository(None)


def _hdr(uid: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("uid,esperado", [
    ("admin-1", 201), ("fin-1", 201), ("prof-fin", 201),
    ("log-1", 403), ("prof-1", 403), ("polo-1", 403),
])
async def test_require_area_financeiro_para_cadastrar_produto(client, uid, esperado):
    res = await client.post(
        "/financeiro/produtos",
        json={"tipo": "livro", "sku": f"SKU-{uid}", "nome": "Livro", "preco": 10},
        headers=_hdr(uid),
    )
    assert res.status_code == esperado


@pytest.mark.asyncio
async def test_sku_duplicado_gera_409(client):
    body = {"tipo": "livro", "sku": "dup", "nome": "Livro", "preco": 10}
    assert (await client.post("/financeiro/produtos", json=body, headers=_hdr("admin-1"))).status_code == 201
    assert (await client.post("/financeiro/produtos", json=body, headers=_hdr("admin-1"))).status_code == 409


@pytest.mark.asyncio
async def test_listagens_respeitam_perfil(client, service):
    _dois_pedidos(service)
    assert (await client.get("/financeiro/pedidos", headers=_hdr("log-1"))).json()["total"] == 2
    assert (await client.get("/financeiro/pedidos", headers=_hdr("polo-1"))).json()["total"] == 1
    assert (await client.get("/financeiro/pedidos", headers=_hdr("prof-1"))).status_code == 403
    assert (await client.get("/financeiro/pagamentos", headers=_hdr("fin-1"))).status_code == 200
    filtro_invalido = await client.get(
        "/financeiro/pedidos?data_inicio=2026-05-01&data_fim=2026-01-01", headers=_hdr("admin-1")
    )
    assert filtro_invalido.status_code == 422


@pytest.mark.asyncio
async def test_api_criar_pedido_e_alterar_status(client, service):
    prod = _produto(service, preco=25)
    criado = await client.post(
        "/financeiro/pedidos",
        json={"tipo": "livro", "polo_id": POLO_B, "itens": [{"produto_id": prod.id, "quantidade": 4}]},
        headers=_hdr("polo-1"),
    )
    assert criado.status_code == 403  # polo-1 é do Polo A
    criado = await client.post(
        "/financeiro/pedidos",
        json={"tipo": "livro", "itens": [{"produto_id": prod.id, "quantidade": 4}]},
        headers=_hdr("polo-1"),
    )
    assert criado.status_code == 201
    pedido = criado.json()
    assert pedido["polo_id"] == POLO_A and pedido["valor_total"] == 100.0
    url = f"/financeiro/pedidos/{pedido['id']}/status"

    assert (await client.post(url, json={"status": "pago_aguardando_envio"}, headers=_hdr("polo-1"))).status_code == 403
    assert (await client.post(url, json={"status": "cancelado"}, headers=_hdr("fin-1"))).status_code == 422
    assert (await client.post(url, json={"status": "enviado"}, headers=_hdr("fin-1"))).status_code == 422

    pago = await client.post(url, json={"status": "pago_aguardando_envio", "observacao": "PIX manual"}, headers=_hdr("fin-1"))
    assert pago.status_code == 200 and pago.json()["status"] == "pago_aguardando_envio"
    assert (await client.post(url, json={"status": "concluido"}, headers=_hdr("fin-1"))).status_code == 409

    cancelado = await client.post(
        url, json={"status": "cancelado", "motivo_cancelamento": "desistência"}, headers=_hdr("admin-1")
    )
    assert cancelado.status_code == 200
    assert cancelado.json()["motivo_cancelamento"] == "desistência"
    assert [h["status_para"] for h in cancelado.json()["historico"]] == [
        "aguardando_pagamento", "pago_aguardando_envio", "cancelado",
    ]


# ---------------------------------------------------------------------------
# Crypto
# ---------------------------------------------------------------------------

def test_crypto_ida_e_volta_e_mascara(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_SECRETS_KEY", Fernet.generate_key().decode())
    token = crypto.encrypt_secret("$aact_sandbox_123")
    assert token != "$aact_sandbox_123"
    assert crypto.decrypt_secret(token) == "$aact_sandbox_123"
    assert crypto.mask_secret("$aact_sandbox_123") == "••••_123"
    assert crypto.mask_secret("") == ""


def test_crypto_sem_chave_ou_chave_diferente(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_SECRETS_KEY", "")
    with pytest.raises(RuntimeError, match="não configurada"):
        crypto.encrypt_secret("x")
    token = crypto.encrypt_secret("x", key=Fernet.generate_key().decode())
    with pytest.raises(RuntimeError):
        crypto.decrypt_secret(token, key=Fernet.generate_key().decode())
