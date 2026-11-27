"""Fase 3B–3D: regras de pagamento, checkout, logística, baixa manual, vendas e segunda via."""
from __future__ import annotations

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
from app.modules.financeiro.cobranca_service import CobrancaService
from app.modules.financeiro.gateways import fake
from app.modules.financeiro.operacao_service import OperacaoService
from app.modules.financeiro.repository import ESCOPO_GLOBAL as ESCOPO
from app.modules.financeiro.repository import InMemoryFinanceiroRepository, set_financeiro_repository
from app.modules.financeiro.schemas import (
    CheckoutRequest,
    EnderecoEntrega,
    EnvioCreate,
    FiltrosPeriodo,
    PedidoItemIn,
    PedidoUpdate,
    ProdutoCreate,
    RegraPagamentoCreate,
    RegraPagamentoUpdate,
)
from app.modules.financeiro.service import FinanceiroService

POLO = "polo-a"
FISCAL = {
    "nome": "Polo A", "cep": "01001-000", "logradouro": "Praça da Sé", "numero": "1", "bairro": "Sé",
    "cidade": "São Paulo", "uf": "SP", "documento_fiscal": "11222333000181",
    "razao_social": "Polo A Educação LTDA", "email_financeiro": "fin@poloa.com.br", "telefone_financeiro": None,
}


def _user(perfil="polo", uid="u-polo", polo_id=POLO) -> UserResponse:
    return UserResponse(id=uid, nome=uid, perfil=PerfilResponse(id=f"p-{perfil}", nome=perfil), polo_id=polo_id)


ADMIN = _user("admin", "adm", None)


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_SECRETS_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "PAYMENT_ENV", "sandbox")
    monkeypatch.setattr(settings, "PUBLIC_API_URL", "https://api.teste")
    fake.resetar()
    yield
    fake.resetar()


@pytest.fixture
def repo():
    r = InMemoryFinanceiroRepository()
    r.polos[POLO] = dict(FISCAL)
    r.salvar_gateway_config("fake", "sandbox", {"webhook_token_cripto": encrypt_secret("tok"), "ativo": True, "padrao": True})
    r.regras.append({"id": "regra-padrao", "nome": "Padrão", "meios_permitidos": ["BOLETO", "PIX"],
                     "dias_vencimento": 3, "prioridade": 1000, "ativo": True, "valor_minimo": 0})
    return r


@pytest.fixture
def creditos():
    return []


@pytest.fixture
def op(repo, creditos):
    cobranca = CobrancaService(repo, creditar_licencas=lambda pedido, uid: creditos.append(pedido["numero"]))
    return OperacaoService(repo, cobranca)


def _produto(repo, tipo="livro", preco=50.0, peso=300):
    return FinanceiroService(repo).create_produto(ProdutoCreate(
        tipo=tipo, sku=f"SKU-{tipo}-{len(repo.produtos)}", nome=f"P {tipo}", preco=preco, peso_g=peso,
        disciplina_id="disc-1" if tipo == "licenca" else None,
    ))


def _checkout(op, repo, tipo="livro", qtd=2, meio="BOLETO", preco=50.0):
    prod = _produto(repo, tipo, preco)
    return op.checkout(CheckoutRequest(tipo=tipo, itens=[PedidoItemIn(produto_id=prod.id, quantidade=qtd)], meio=meio), _user())


# ---------------------------------------------------------------------------
# Regras de pagamento
# ---------------------------------------------------------------------------

def test_regra_mais_especifica_e_valor_minimo(op, repo):
    op.criar_regra(RegraPagamentoCreate(nome="Licença só PIX", aplica_tipo_pedido="licenca", meios_permitidos=["PIX"]))
    op.criar_regra(RegraPagamentoCreate(nome="Livros grandes", aplica_tipo_pedido="livro", valor_minimo=1000,
                                        meios_permitidos=["BOLETO"], dias_vencimento=10, multa_pct=2, juros_mes_pct=1))
    cob = op.cobranca
    assert cob.opcoes_checkout("licenca", POLO, 100)["meios"] == ["PIX"]
    assert cob.opcoes_checkout("livro", POLO, 50)["regra_nome"] == "Padrão"
    grande = cob.opcoes_checkout("livro", POLO, 1500)
    assert grande["regra_nome"] == "Livros grandes" and grande["dias_vencimento"] == 10 and grande["multa_pct"] == 2


def test_checkout_respeita_regra_e_envia_encargos(op, repo):
    op.criar_regra(RegraPagamentoCreate(nome="Boleto com multa", aplica_tipo_pedido="livro", meios_permitidos=["BOLETO"],
                                        multa_pct=2, juros_mes_pct=1, desconto_antecipado_pct=5))
    negado = _checkout(op, repo, meio="PIX")
    assert negado.pagamento is None and "não permitido" in negado.erro_cobranca
    assert negado.pedido.status == "aguardando_pagamento"  # pedido fica para tentar de novo

    ok = _checkout(op, repo, meio="BOLETO")
    assert ok.pagamento and ok.pagamento.status == "pendente" and ok.erro_cobranca is None
    enc = fake.COBRANCAS[ok.pagamento.gateway_payment_id]["encargos"]
    assert (enc.multa_pct, enc.juros_mes_pct, enc.desconto_antecipado_pct) == (2, 1, 5)


def test_nao_desativa_ultima_regra_generica(op):
    with pytest.raises(HTTPException) as exc:
        op.desativar_regra("regra-padrao")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException):
        op.atualizar_regra("regra-padrao", RegraPagamentoUpdate(aplica_tipo_pedido="livro"))
    op.criar_regra(RegraPagamentoCreate(nome="Outra genérica"))
    assert op.desativar_regra("regra-padrao").ativo is False
    assert op.listar_regras()[0].generica is True


# ---------------------------------------------------------------------------
# Checkout e baixa manual
# ---------------------------------------------------------------------------

def test_checkout_sem_dados_fiscais_cria_pedido_e_informa(op, repo):
    repo.polos[POLO]["documento_fiscal"] = None
    res = _checkout(op, repo)
    assert res.pagamento is None and "Dados fiscais" in res.erro_cobranca
    assert repo.get_pedido(res.pedido.id)["status"] == "aguardando_pagamento"


def test_baixa_manual_licenca_credita_e_cancela_cobranca(op, repo, creditos):
    res = _checkout(op, repo, tipo="licenca", qtd=5, meio="PIX")
    pedido = op.baixa_manual(res.pedido.id, "concluido", "PIX recebido na conta", ADMIN)
    assert pedido.status == "concluido" and creditos == [res.pedido.numero]
    assert repo.get_pagamento(res.pagamento.id)["status"] == "cancelado"
    with pytest.raises(HTTPException):  # livro não "conclui"
        op.baixa_manual(_checkout(op, repo).pedido.id, "concluido", None, ADMIN)


def test_baixa_manual_com_falha_no_credito_pode_ser_repetida(repo):
    estado = {"falhas": 1, "creditados": []}

    def creditar(pedido, _uid):  # idempotente como o real; falha na primeira vez
        if estado["falhas"]:
            estado["falhas"] -= 1
            raise RuntimeError("estoque fora do ar")
        if pedido["numero"] in estado["creditados"]:
            return False
        estado["creditados"].append(pedido["numero"])
        return True

    op = OperacaoService(repo, CobrancaService(repo, creditar_licencas=creditar))
    res = _checkout(op, repo, tipo="licenca", qtd=5, meio="PIX")
    with pytest.raises(RuntimeError):
        op.baixa_manual(res.pedido.id, "concluido", None, ADMIN)
    assert repo.get_pedido(res.pedido.id)["status"] == "aguardando_pagamento"  # nada concluído sem crédito

    assert op.baixa_manual(res.pedido.id, "concluido", None, ADMIN).status == "concluido"
    assert estado["creditados"] == [res.pedido.numero]


def test_kit_pago_credita_licencas_e_vai_para_envio(op, repo, creditos):
    kit = FinanceiroService(repo).create_produto(ProdutoCreate(
        tipo="kit", sku="KIT-1", nome="Matemática (livro + licença)", preco=60, disciplina_id="disc-1"))
    res = op.checkout(CheckoutRequest(tipo="kit", itens=[PedidoItemIn(produto_id=kit.id, quantidade=5)],
                                      meio="BOLETO"), _user())
    op.cobranca.simular(res.pagamento.id, "pago", ADMIN)
    pedido = repo.get_pedido(res.pedido.id)
    assert pedido["status"] == "pago_aguardando_envio" and creditos == [res.pedido.numero]
    enviado = op.marcar_enviado(res.pedido.id, EnvioCreate(transportadora="Correios"), ADMIN)
    assert enviado.status == "enviado"
    k = op.kpis_vendas(FiltrosPeriodo(), ADMIN)
    assert k.receita_kits == 300 and k.licencas_vendidas == 5 and k.livros_vendidos == 5
    # filtro da logística: livro + kit
    total, _ = repo.list_pedidos(FiltrosPeriodo(tipo="com_envio"), ESCOPO)
    assert total == 1


def test_cancelar_pedido_cancela_cobranca_pendente(op, repo):
    res = _checkout(op, repo)
    cancelado = op.cancelar_pedido(res.pedido.id, "Desistência", ADMIN)
    assert cancelado.status == "cancelado" and cancelado.motivo_cancelamento == "Desistência"
    assert repo.get_pagamento(res.pagamento.id)["status"] == "cancelado"


def test_cancelar_pedido_pago_registra_estorno_manual(op, repo):
    res = _checkout(op, repo)
    op.cobranca.simular(res.pagamento.id, "pago", ADMIN)
    cancelado = op.cancelar_pedido(res.pedido.id, "Erro no pedido", ADMIN)
    assert "estorno manual" in cancelado.historico[-1].observacao


# ---------------------------------------------------------------------------
# Logística
# ---------------------------------------------------------------------------

def test_envio_e_entrega(op, repo):
    res = _checkout(op, repo, qtd=3)
    with pytest.raises(HTTPException) as exc:  # ainda não pago
        op.marcar_enviado(res.pedido.id, EnvioCreate(transportadora="Correios"), ADMIN)
    assert exc.value.status_code == 409
    op.cobranca.simular(res.pagamento.id, "pago", ADMIN)

    enviado = op.marcar_enviado(res.pedido.id, EnvioCreate(transportadora="Correios", codigo_rastreio="BR123"), ADMIN)
    assert enviado.status == "enviado" and enviado.envios[0].peso_total_g == 900  # 3 × 300 g
    assert "BR123" in enviado.historico[-1].observacao
    entregue = op.marcar_entregue(res.pedido.id, None, ADMIN)
    assert entregue.status == "entregue" and entregue.entregue_em is not None


def test_editar_pedido_itens_so_sem_cobranca(op, repo):
    res = _checkout(op, repo, qtd=2)
    novo = _produto(repo, preco=20)
    with pytest.raises(HTTPException) as exc:
        op.editar_pedido(res.pedido.id, PedidoUpdate(itens=[PedidoItemIn(produto_id=novo.id, quantidade=1)]), ADMIN)
    assert exc.value.status_code == 409 and "cobrança pendente" in exc.value.detail

    op.cobranca.cancelar_pagamento(res.pagamento.id, ADMIN)
    editado = op.editar_pedido(res.pedido.id, PedidoUpdate(
        itens=[PedidoItemIn(produto_id=novo.id, quantidade=4)], observacao="Ajuste do Polo"), ADMIN)
    assert editado.valor_total == 80 and editado.observacao == "Ajuste do Polo"
    assert "itens" in editado.historico[-1].observacao

    with pytest.raises(HTTPException) as exc:  # endereço de livro incompleto
        op.editar_pedido(res.pedido.id, PedidoUpdate(endereco=EnderecoEntrega(cep="01001000")), ADMIN)
    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Vendas e segunda via
# ---------------------------------------------------------------------------

def test_kpis_e_serie_de_vendas(op, repo):
    pago = _checkout(op, repo, qtd=2, preco=50)  # 100
    op.cobranca.simular(pago.pagamento.id, "pago", ADMIN)
    lic = _checkout(op, repo, tipo="licenca", qtd=10, meio="PIX", preco=10)  # 100
    op.cobranca.simular(lic.pagamento.id, "pago", ADMIN)
    vencido = _checkout(op, repo, qtd=1, preco=30)  # 30 a receber, vencido
    op.cobranca.simular(vencido.pagamento.id, "vencido", ADMIN)
    cancelado = _checkout(op, repo, qtd=1, preco=999)
    op.cancelar_pedido(cancelado.pedido.id, "x", ADMIN)

    k = op.kpis_vendas(FiltrosPeriodo(), ADMIN)
    assert (k.pedidos, k.pedidos_pagos, k.receita_paga) == (3, 2, 200)
    assert (k.a_receber, k.vencido, k.ticket_medio) == (30, 30, 100)
    assert (k.receita_licencas, k.receita_livros, k.licencas_vendidas, k.livros_vendidos) == (100, 100, 10, 2)
    assert k.top_polos[0].receita == 200
    serie = op.serie_vendas(FiltrosPeriodo(), ADMIN)
    assert len(serie) == 1 and serie[0].receita == 200 and serie[0].pedidos == 3


def test_segunda_via_de_boleto_vencido(op, repo):
    res = _checkout(op, repo)
    with pytest.raises(HTTPException):  # não vencido
        op.segunda_via(res.pagamento.id, ADMIN)
    op.cobranca.simular(res.pagamento.id, "vencido", ADMIN)
    nova = op.segunda_via(res.pagamento.id, ADMIN)
    assert nova.id != res.pagamento.id and nova.status == "pendente" and nova.billing_type == "BOLETO"
    assert repo.get_pagamento(res.pagamento.id)["status"] == "cancelado"


# ---------------------------------------------------------------------------
# API: permissões das rotas novas
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(repo):
    auth = InMemoryAuthRepository()
    for nome in ("financeiro", "logistica"):
        auth.perfis[f"p-{nome}"] = {"id": f"p-{nome}", "nome": nome, "descricao": nome}
    for uid, perfil in {"admin-1": "p-admin", "fin-1": "p-financeiro", "log-1": "p-logistica", "polo-1": "p-polo"}.items():
        auth.usuarios[uid] = {"id": uid, "nome": uid, "email": f"{uid}@nexus.com.br", "status": "ativo",
                              "perfil_id": perfil, "polo_id": POLO if uid == "polo-1" else None, "escola_id": None}
    set_auth_repository(auth)
    set_financeiro_repository(repo)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    set_financeiro_repository(None)


def _hdr(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


@pytest.mark.asyncio
async def test_api_checkout_logistica_e_permissoes(client, repo):
    prod = _produto(repo)
    opcoes = await client.get("/financeiro/checkout/opcoes?tipo=livro&valor=100", headers=_hdr("polo-1"))
    assert opcoes.status_code == 200 and opcoes.json()["meios"] == ["BOLETO", "PIX"]

    criado = await client.post("/financeiro/checkout", headers=_hdr("polo-1"), json={
        "tipo": "livro", "itens": [{"produto_id": prod.id, "quantidade": 1}], "meio": "BOLETO"})
    assert criado.status_code == 201, criado.text
    pedido_id, pg_id = criado.json()["pedido"]["id"], criado.json()["pagamento"]["id"]

    await client.post(f"/financeiro/pagamentos/{pg_id}/simular", json={"status": "pago"}, headers=_hdr("admin-1"))
    url_envio = f"/financeiro/pedidos/{pedido_id}/envio"
    assert (await client.post(url_envio, json={"transportadora": "Correios"}, headers=_hdr("fin-1"))).status_code == 403
    assert (await client.post(url_envio, json={"transportadora": "Correios"}, headers=_hdr("polo-1"))).status_code == 403
    enviado = await client.post(url_envio, json={"transportadora": "Correios"}, headers=_hdr("log-1"))
    assert enviado.status_code == 200 and enviado.json()["status"] == "enviado"

    assert (await client.get("/financeiro/regras", headers=_hdr("log-1"))).status_code == 403
    assert (await client.get("/financeiro/regras", headers=_hdr("fin-1"))).status_code == 200
    assert (await client.get("/financeiro/vendas/kpis", headers=_hdr("polo-1"))).status_code == 403
    kpis = await client.get("/financeiro/vendas/kpis?ano=2026", headers=_hdr("fin-1"))
    assert kpis.status_code == 200
    editar = await client.put(f"/financeiro/pedidos/{pedido_id}", json={"observacao": "ok"}, headers=_hdr("log-1"))
    assert editar.status_code == 409  # já enviado
