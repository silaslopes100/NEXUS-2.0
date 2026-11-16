"""Cobrança, webhooks, reconciliação, cron e configuração dos gateways (Fase 2) com FakeGateway."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.security import create_access_token
from app.main import app
from app.modules.auth.repository import InMemoryAuthRepository, set_auth_repository
from app.modules.auth.schemas import PerfilResponse, UserResponse
from app.modules.financeiro.cobranca_service import CobrancaService, proximo_status
from app.modules.financeiro.gateways import fake
from app.modules.financeiro.repository import InMemoryFinanceiroRepository, set_financeiro_repository
from app.modules.financeiro.schemas import PedidoCreate, PedidoItemIn, ProdutoCreate
from app.modules.financeiro.service import FinanceiroService

POLO = "polo-a"
FISCAL = {
    "nome": "Polo A", "cep": "01001-000", "logradouro": "Praça da Sé", "numero": "1", "bairro": "Sé",
    "cidade": "São Paulo", "uf": "SP", "documento_fiscal": "11222333000181",
    "razao_social": "Polo A Educação LTDA", "email_financeiro": "fin@poloa.com.br", "telefone_financeiro": None,
}
TOKEN = "token-webhook-fake"


def _user(perfil="polo", uid="u-polo", polo_id=POLO) -> UserResponse:
    return UserResponse(id=uid, nome=uid, perfil=PerfilResponse(id=f"p-{perfil}", nome=perfil), polo_id=polo_id)


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_SECRETS_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "PAYMENT_ENV", "sandbox")
    monkeypatch.setattr(settings, "PUBLIC_API_URL", "https://api.teste")
    monkeypatch.setattr(settings, "CRON_SECRET", "cron-secreto")
    fake.resetar()
    yield
    fake.resetar()


@pytest.fixture
def repo():
    r = InMemoryFinanceiroRepository()
    r.polos[POLO] = dict(FISCAL)
    r.salvar_gateway_config("fake", "sandbox", {
        "webhook_token_cripto": encrypt_secret(TOKEN), "ativo": True, "padrao": True,
    })
    return r


@pytest.fixture
def creditos():
    return []


@pytest.fixture
def cobranca(repo, creditos):
    return CobrancaService(repo, creditar_licencas=lambda pedido, uid: creditos.append(pedido["numero"]))


def _pedido(repo, tipo="livro", qtd=2, preco=50.0):
    svc = FinanceiroService(repo)
    prod = svc.create_produto(ProdutoCreate(tipo=tipo, sku=f"SKU-{tipo}-{len(repo.produtos)}", nome=f"P {tipo}", preco=preco))
    return svc.criar_pedido(PedidoCreate(tipo=tipo, itens=[PedidoItemIn(produto_id=prod.id, quantidade=qtd)]), _user())


def _webhook(cobranca, payment_id, status, evento_id="evt-1", token=TOKEN, **extra):
    corpo = json.dumps({"id": evento_id, "payment_id": payment_id, "status": status, **extra}).encode()
    return cobranca.processar_webhook("fake", "sandbox", {"x-fake-token": token}, corpo, {})


# ---------------------------------------------------------------------------
# Regra de não-regressão
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("atual,novo,esperado", [
    ("pendente", "pago", "pago"),
    ("pendente", "vencido", "vencido"),
    ("vencido", "pago", "pago"),
    ("pago", "vencido", None),
    ("pago", "pendente", None),
    ("pago", "cancelado", "estornado"),
    ("pago", "estornado", "estornado"),
    ("cancelado", "pago", None),
    ("pendente", "pendente", None),
    ("pendente", None, None),
])
def test_proximo_status(atual, novo, esperado):
    assert proximo_status(atual, novo) == esperado


# ---------------------------------------------------------------------------
# Geração de cobrança
# ---------------------------------------------------------------------------

def test_gerar_boleto_grava_pagamento_e_reaproveita_cliente(repo, cobranca):
    pedido = _pedido(repo)
    pg = cobranca.gerar_cobranca(pedido.id, "BOLETO", _user())
    assert pg.status == "pendente" and pg.gateway == "fake" and pg.ambiente == "sandbox"
    assert pg.valor == 100.0 and pg.linha_digitavel and pg.boleto_url and pg.pedido_numero == pedido.numero
    assert repo.get_cliente_gateway("fake", "sandbox", POLO)["documento_fiscal"] == FISCAL["documento_fiscal"]

    with pytest.raises(HTTPException) as exc:  # já existe cobrança pendente
        cobranca.gerar_cobranca(pedido.id, "PIX", _user())
    assert exc.value.status_code == 409

    cobranca.cancelar_pagamento(pg.id, _user("admin", "adm", None))
    pix = cobranca.gerar_cobranca(pedido.id, "PIX", _user())
    assert pix.pix_copia_cola and len(fake.CLIENTES) == 1


def test_gerar_cobranca_exige_dados_fiscais(repo, cobranca):
    repo.polos[POLO]["documento_fiscal"] = None
    repo.polos[POLO]["email_financeiro"] = None
    with pytest.raises(HTTPException) as exc:
        cobranca.gerar_cobranca(_pedido(repo).id, "BOLETO", _user())
    assert exc.value.status_code == 422
    assert "CPF/CNPJ" in exc.value.detail and "e-mail financeiro" in exc.value.detail


def test_gerar_cobranca_respeita_regra_e_gateway_padrao(repo, cobranca):
    repo.regras.append({"nome": "Só PIX", "meios_permitidos": ["PIX"], "dias_vencimento": 5, "ativo": True})
    pedido = _pedido(repo)
    with pytest.raises(HTTPException) as exc:
        cobranca.gerar_cobranca(pedido.id, "BOLETO", _user())
    assert exc.value.status_code == 422
    pg = cobranca.gerar_cobranca(pedido.id, "PIX", _user())
    assert (pg.vencimento_em - pg.criado_em.date()).days == 5

    repo.salvar_gateway_config("fake", "sandbox", {"padrao": False})
    with pytest.raises(HTTPException) as exc:
        cobranca.gerar_cobranca(_pedido(repo).id, "PIX", _user())
    assert exc.value.status_code == 409 and "Nenhum gateway" in exc.value.detail


def test_gerar_cobranca_fora_do_escopo_ou_pedido_ja_pago(repo, cobranca):
    pedido = _pedido(repo)
    with pytest.raises(HTTPException) as exc:
        cobranca.gerar_cobranca(pedido.id, "PIX", _user(polo_id="outro-polo"))
    assert exc.value.status_code == 404
    FinanceiroService(repo).alterar_status(pedido.id, "pago_aguardando_envio", None)
    with pytest.raises(HTTPException) as exc:
        cobranca.gerar_cobranca(pedido.id, "PIX", _user())
    assert exc.value.status_code == 409


def test_falha_do_gateway_vira_502(repo, cobranca):
    repo.salvar_gateway_config("fake", "sandbox", {"credenciais_cripto": encrypt_secret(json.dumps({"falhar_em": "cobranca"}))})
    with pytest.raises(HTTPException) as exc:
        cobranca.gerar_cobranca(_pedido(repo).id, "BOLETO", _user())
    assert exc.value.status_code == 502


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

def test_webhook_livro_pago_avanca_pedido_e_e_idempotente(repo, cobranca, creditos):
    pedido = _pedido(repo)
    pg = cobranca.gerar_cobranca(pedido.id, "BOLETO", _user())

    assert _webhook(cobranca, pg.gateway_payment_id, "pago", valor_pago=98.5) == {"status": "processado", "alterado": True}
    p = repo.get_pedido(pedido.id)
    assert p["status"] == "pago_aguardando_envio" and p["pago_em"] is not None
    assert p["historico"][-1]["origem"] == "webhook"
    pago = repo.get_pagamento(pg.id)
    assert pago["status"] == "pago" and pago["valor_liquido"] == 98.5
    assert creditos == []  # livro não credita licença

    assert _webhook(cobranca, pg.gateway_payment_id, "pago")["status"] == "duplicado"
    assert len(repo.webhooks) == 1 and len(repo.get_pedido(pedido.id)["historico"]) == 2

    # evento tardio de vencimento não regride o pagamento
    _webhook(cobranca, pg.gateway_payment_id, "vencido", evento_id="evt-2")
    assert repo.get_pagamento(pg.id)["status"] == "pago"


def test_webhook_licenca_paga_conclui_e_credita_estoque(repo, cobranca, creditos):
    pedido = _pedido(repo, tipo="licenca", qtd=10)
    pg = cobranca.gerar_cobranca(pedido.id, "PIX", _user())
    _webhook(cobranca, pg.gateway_payment_id, "pago")
    assert repo.get_pedido(pedido.id)["status"] == "concluido"
    assert creditos == [pedido.numero]


def test_webhook_token_invalido_nao_grava(repo, cobranca):
    with pytest.raises(HTTPException) as exc:
        _webhook(cobranca, "pay_x", "pago", token="errado")
    assert exc.value.status_code == 401 and repo.webhooks == {}


def test_webhook_de_gateway_inativo_404(repo, cobranca):
    repo.salvar_gateway_config("fake", "sandbox", {"ativo": False})
    with pytest.raises(HTTPException) as exc:
        _webhook(cobranca, "pay_x", "pago")
    assert exc.value.status_code == 404


def test_webhook_pagamento_desconhecido_fica_ignorado(repo, cobranca):
    assert _webhook(cobranca, "pay_legado", "pago")["status"] == "ignorado"
    assert list(repo.webhooks.values())[0]["status"] == "ignorado"


def test_webhook_com_erro_responde_e_cron_reprocessa(repo, cobranca, monkeypatch):
    pedido = _pedido(repo)
    pg = cobranca.gerar_cobranca(pedido.id, "BOLETO", _user())
    original = cobranca.aplicar_status
    monkeypatch.setattr(cobranca, "aplicar_status", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("banco fora")))
    assert _webhook(cobranca, pg.gateway_payment_id, "pago")["status"] == "erro"
    evento = list(repo.webhooks.values())[0]
    assert evento["status"] == "erro" and "banco fora" in evento["erro"]

    monkeypatch.setattr(cobranca, "aplicar_status", original)
    resumo = cobranca.reconciliar()
    assert resumo["webhooks_reprocessados"] == 1
    assert repo.get_pedido(pedido.id)["status"] == "pago_aguardando_envio"
    assert list(repo.webhooks.values())[0]["status"] == "processado"


# ---------------------------------------------------------------------------
# Reconciliação e cancelamento
# ---------------------------------------------------------------------------

def test_reconciliar_consulta_gateway_sem_webhook(repo, cobranca):
    pedido = _pedido(repo)
    pg = cobranca.gerar_cobranca(pedido.id, "BOLETO", _user())
    repo.pagamentos[pg.id]["criado_em"] -= timedelta(hours=1)
    fake.FakeGateway.simular_status(pg.gateway_payment_id, "pago")

    resumo = cobranca.reconciliar()
    assert resumo["pagamentos_consultados"] == 1 and resumo["pagamentos_alterados"] == 1
    assert repo.get_pedido(pedido.id)["historico"][-1]["origem"] == "cron"


def test_cancelar_pagamento(repo, cobranca):
    pg = cobranca.gerar_cobranca(_pedido(repo).id, "BOLETO", _user())
    cancelado = cobranca.cancelar_pagamento(pg.id, _user("admin", "adm", None))
    assert cancelado.status == "cancelado" and fake.COBRANCAS[pg.gateway_payment_id]["status"] == "cancelado"
    with pytest.raises(HTTPException) as exc:
        cobranca.cancelar_pagamento(pg.id, _user("admin", "adm", None))
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# API: configuração, webhook HTTP e cron
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_repo():
    r = InMemoryAuthRepository()
    r.perfis["p-financeiro"] = {"id": "p-financeiro", "nome": "financeiro", "descricao": "Financeiro"}
    for uid, perfil in {"admin-1": "p-admin", "fin-1": "p-financeiro", "polo-1": "p-polo"}.items():
        r.usuarios[uid] = {"id": uid, "nome": uid, "email": f"{uid}@nexus.com.br", "status": "ativo",
                           "perfil_id": perfil, "polo_id": POLO if uid == "polo-1" else None, "escola_id": None}
    set_auth_repository(r)
    return r


@pytest_asyncio.fixture
async def client(auth_repo, repo):
    set_financeiro_repository(repo)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    set_financeiro_repository(None)


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


@pytest.mark.asyncio
async def test_api_config_gateway_mascara_e_permissoes(client):
    url = "/financeiro/gateways/asaas/sandbox"
    sem_credencial = await client.put(url, json={"ativo": True}, headers=_hdr("admin-1"))
    assert sem_credencial.status_code == 422

    body = {"credenciais": {"api_key": "$aact_hmlg_SEGREDO_1234"}, "webhook_token": "tok-webhook-5678",
            "ativo": True, "padrao": True}
    assert (await client.put(url, json=body, headers=_hdr("fin-1"))).status_code == 403
    salvo = await client.put(url, json=body, headers=_hdr("admin-1"))
    assert salvo.status_code == 200
    assert salvo.json()["credenciais"] == {"api_key": "••••1234"} and salvo.json()["webhook_token"] == "••••5678"
    assert salvo.json()["webhook_url"] == "https://api.teste/financeiro/webhooks/asaas/sandbox"

    lista = await client.get("/financeiro/gateways", headers=_hdr("fin-1"))
    texto = lista.text
    assert lista.status_code == 200 and "SEGREDO" not in texto and "tok-webhook" not in texto
    asaas = next(i for i in lista.json()["items"] if i["gateway"] == "asaas" and i["ambiente"] == "sandbox")
    assert asaas["ativo"] and asaas["padrao"] and lista.json()["ambiente_ativo"] == "sandbox"
    assert (await client.get("/financeiro/gateways", headers=_hdr("polo-1"))).status_code == 403

    # alterar só o token mantém a API key
    await client.put(url, json={"webhook_token": "novo-token-9999"}, headers=_hdr("admin-1"))
    asaas = next(i for i in (await client.get("/financeiro/gateways", headers=_hdr("admin-1"))).json()["items"]
                 if i["gateway"] == "asaas" and i["ambiente"] == "sandbox")
    assert asaas["credenciais"] == {"api_key": "••••1234"} and asaas["webhook_token"] == "••••9999"


@pytest.mark.asyncio
async def test_api_cobranca_e_webhook_http(client, repo):
    pedido = _pedido(repo)
    criado = await client.post(f"/financeiro/pedidos/{pedido.id}/cobranca", json={"meio": "BOLETO"}, headers=_hdr("polo-1"))
    assert criado.status_code == 201, criado.text
    payment_id = criado.json()["gateway_payment_id"]

    invalido = await client.post("/financeiro/webhooks/fake/sandbox", content=b'{"id":"e1"}', headers={"x-fake-token": "x"})
    assert invalido.status_code == 401

    corpo = json.dumps({"id": "evt-http", "payment_id": payment_id, "status": "pago"})
    ok = await client.post("/financeiro/webhooks/fake/sandbox", content=corpo, headers={"x-fake-token": TOKEN})
    assert ok.status_code == 200 and ok.json()["status"] == "processado"
    assert repo.get_pedido(pedido.id)["status"] == "pago_aguardando_envio"

    eventos = await client.get("/financeiro/webhooks/eventos", headers=_hdr("fin-1"))
    assert eventos.json()["total"] == 1 and eventos.json()["items"][0]["status"] == "processado"

    filtrado = await client.get(f"/financeiro/pagamentos?pedido_id={pedido.id}", headers=_hdr("polo-1"))
    assert filtrado.json()["total"] == 1 and filtrado.json()["items"][0]["status"] == "pago"


@pytest.mark.asyncio
async def test_api_cron(client, monkeypatch):
    url = "/financeiro/cron/reconciliar"
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers={"Authorization": "Bearer errado"})).status_code == 401
    ok = await client.get(url, headers={"Authorization": "Bearer cron-secreto"})
    assert ok.status_code == 200 and "pagamentos_consultados" in ok.json()
    monkeypatch.setattr(settings, "CRON_SECRET", "")
    assert (await client.get(url, headers={"Authorization": "Bearer "})).status_code == 503
