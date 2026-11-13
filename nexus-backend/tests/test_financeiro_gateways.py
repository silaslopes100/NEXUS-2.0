"""Adapters dos gateways (Asaas, PagBank, Mercado Pago) com HTTP simulado e assinaturas reais."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import date

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.modules.financeiro.gateways.asaas import AsaasGateway
from app.modules.financeiro.gateways.base import EnderecoPagador, GatewayError, Pagador
from app.modules.financeiro.gateways.mercadopago import MercadoPagoGateway, manifesto
from app.modules.financeiro.gateways.pagbank import PagBankGateway

PAGADOR = Pagador(
    nome="Polo Centro LTDA", documento="11222333000181", email="fin@polo.com.br", telefone="11999990000",
    endereco=EnderecoPagador(cep="01001-000", logradouro="Praça da Sé", numero="1", bairro="Sé",
                             cidade="São Paulo", uf="SP"),
    referencia="polo-1",
)
VENC = date(2026, 12, 1)


def _transport(rotas, chamadas):
    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(request)
        chave = (request.method, request.url.path)
        resposta = rotas.get(chave)
        if resposta is None:
            return httpx.Response(404, json={"message": f"rota não simulada {chave}"})
        status, corpo = resposta if isinstance(resposta, tuple) else (200, resposta)
        return httpx.Response(status, json=corpo)
    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Asaas
# ---------------------------------------------------------------------------

def test_asaas_boleto_cria_cliente_e_busca_linha_digitavel():
    chamadas = []
    rotas = {
        ("GET", "/v3/customers"): {"data": []},
        ("POST", "/v3/customers"): {"id": "cus_123"},
        ("POST", "/v3/payments"): {"id": "pay_1", "status": "PENDING", "value": 150.5,
                                   "bankSlipUrl": "https://asaas/boleto.pdf", "invoiceUrl": "https://asaas/i/1"},
        ("GET", "/v3/payments/pay_1/identificationField"): {"identificationField": "23793.38128 6000",
                                                            "nossoNumero": "999", "barCode": "237"},
    }
    gw = AsaasGateway("sandbox", {"api_key": "$aact_x"}, "tok", transport=_transport(rotas, chamadas))
    cliente = gw.obter_ou_criar_cliente(PAGADOR)
    cobranca = gw.criar_cobranca(cliente, PAGADOR, 150.5, VENC, "BOLETO", "Pedido PED-1", "PED-1")

    assert cliente == "cus_123"
    assert all(r.headers["access_token"] == "$aact_x" for r in chamadas)
    assert str(chamadas[0].url).startswith("https://api-sandbox.asaas.com/v3/customers")
    corpo = json.loads(chamadas[2].content)
    assert corpo == {"customer": "cus_123", "billingType": "BOLETO", "value": 150.5, "dueDate": "2026-12-01",
                     "description": "Pedido PED-1", "externalReference": "PED-1"}
    assert cobranca.payment_id == "pay_1" and cobranca.status == "pendente"
    assert cobranca.linha_digitavel == "23793.38128 6000" and cobranca.nosso_numero == "999"
    assert cobranca.boleto_url == "https://asaas/boleto.pdf"


def test_asaas_reaproveita_cliente_existente_e_pix():
    chamadas = []
    rotas = {
        ("GET", "/v3/customers"): {"data": [{"id": "cus_existente"}]},
        ("POST", "/v3/payments"): {"id": "pay_2", "status": "PENDING", "value": 10},
        ("GET", "/v3/payments/pay_2/pixQrCode"): {"payload": "000201pix", "encodedImage": "iVBOR"},
    }
    gw = AsaasGateway("producao", {"api_key": "k"}, "tok", transport=_transport(rotas, chamadas))
    assert gw.obter_ou_criar_cliente(PAGADOR) == "cus_existente"
    assert gw.obter_ou_criar_cliente(PAGADOR, "cus_cache") == "cus_cache"
    cobranca = gw.criar_cobranca("cus_existente", PAGADOR, 10, VENC, "PIX", "d", "PED-2")
    assert cobranca.pix_copia_cola == "000201pix" and cobranca.pix_qrcode_base64 == "iVBOR"
    assert str(chamadas[0].url).startswith("https://api.asaas.com/v3/")
    assert not any(r.method == "POST" and r.url.path == "/v3/customers" for r in chamadas)


def test_asaas_erro_http_vira_gateway_error():
    rotas = {("POST", "/v3/payments"): (400, {"errors": [{"code": "invalid", "description": "CPF inválido"}]})}
    gw = AsaasGateway("sandbox", {"api_key": "k"}, "tok", transport=_transport(rotas, []))
    with pytest.raises(GatewayError) as exc:
        gw.criar_cobranca("cus", PAGADOR, 10, VENC, "BOLETO", "d", "r")
    assert exc.value.status_http == 400 and "CPF inválido" in exc.value.mensagem


def test_asaas_sem_api_key():
    with pytest.raises(GatewayError):
        AsaasGateway("sandbox", {}, "tok")


def test_asaas_webhook_token_e_interpretacao():
    gw = AsaasGateway("sandbox", {"api_key": "k"}, "token-secreto")
    corpo = json.dumps({
        "id": "evt_abc", "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_1", "status": "RECEIVED", "netValue": 148.51, "paymentDate": "2026-11-20"},
    }).encode()
    assert gw.validar_webhook({"asaas-access-token": "token-secreto"}, corpo)
    assert gw.validar_webhook({"Asaas-Access-Token": "token-secreto"}, corpo)
    assert not gw.validar_webhook({"asaas-access-token": "errado"}, corpo)
    assert not gw.validar_webhook({}, corpo)
    evento = gw.interpretar_webhook({}, corpo, {})
    assert (evento.evento_id, evento.payment_id, evento.status, evento.valor_pago) == ("evt_abc", "pay_1", "pago", 148.51)

    excluido = gw.interpretar_webhook({}, json.dumps({"event": "PAYMENT_DELETED", "payment": {"id": "pay_9"}}).encode(), {})
    assert excluido.status == "cancelado" and excluido.evento_id == "PAYMENT_DELETED:pay_9"
    vencido = gw.interpretar_webhook({}, json.dumps({"id": "e", "event": "PAYMENT_OVERDUE", "payment": {"id": "p"}}).encode(), {})
    assert vencido.status == "vencido"


# ---------------------------------------------------------------------------
# PagBank
# ---------------------------------------------------------------------------

def test_pagbank_boleto_em_centavos_e_leitura_da_resposta():
    chamadas = []
    rotas = {("POST", "/orders"): {
        "id": "ORDE_1",
        "charges": [{
            "id": "CHAR_1", "status": "WAITING",
            "payment_method": {"boleto": {"id": "BOL_1", "formatted_barcode": "0339 9.1234", "barcode": "0339"}},
            "links": [{"rel": "SELF", "media": "application/pdf", "href": "https://pagbank/boleto.pdf"},
                      {"rel": "SELF", "media": "image/png", "href": "https://pagbank/boleto.png"}],
        }],
    }}
    gw = PagBankGateway("sandbox", {"token": "tk"}, transport=_transport(rotas, chamadas))
    cobranca = gw.criar_cobranca("x", PAGADOR, 100.505, VENC, "BOLETO", "Pedido PED-3", "PED-3",
                                 notification_url="https://api/financeiro/webhooks/pagbank/sandbox")
    corpo = json.loads(chamadas[0].content)
    assert chamadas[0].headers["authorization"] == "Bearer tk"
    assert corpo["charges"][0]["amount"] == {"value": 10051, "currency": "BRL"}
    assert corpo["charges"][0]["payment_method"]["boleto"]["holder"]["tax_id"] == "11222333000181"
    assert corpo["notification_urls"] == ["https://api/financeiro/webhooks/pagbank/sandbox"]
    assert cobranca.payment_id == "CHAR_1" and cobranca.status == "pendente"
    assert cobranca.linha_digitavel == "0339 9.1234" and cobranca.boleto_url == "https://pagbank/boleto.pdf"


def test_pagbank_pix():
    rotas = {("POST", "/orders"): {"id": "ORDE_2", "charges": [{"id": "CHAR_2", "status": "WAITING",
                                                                 "qr_code": {"text": "000201pagbank"}}]}}
    gw = PagBankGateway("sandbox", {"token": "tk"}, transport=_transport(rotas, []))
    assert gw.criar_cobranca("x", PAGADOR, 5, VENC, "PIX", "d", "PED-4").pix_copia_cola == "000201pagbank"


def _par_ecdsa():
    privada = ec.generate_private_key(ec.SECP256R1())
    publica_der = privada.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return privada, base64.b64encode(publica_der).decode()


def test_pagbank_webhook_ecdsa():
    privada, publica = _par_ecdsa()
    gw = PagBankGateway("sandbox", {"token": "tk", "webhook_public_key": publica})
    corpo = json.dumps({"id": "ORDE_1", "charges": [{"id": "CHAR_1", "status": "PAID",
                                                     "paid_at": "2026-11-20T10:00:00-03:00"}]}).encode()
    assinatura = base64.b64encode(privada.sign(corpo, ec.ECDSA(hashes.SHA256()))).decode()

    assert gw.validar_webhook({"x-payload-signature": assinatura}, corpo)
    # várias assinaturas (rotação de chave): basta uma válida
    assert gw.validar_webhook({"x-payload-signature": f"{base64.b64encode(b'lixo').decode()},{assinatura}"}, corpo)
    assert not gw.validar_webhook({"x-payload-signature": assinatura}, corpo + b" ")
    assert not gw.validar_webhook({}, corpo)
    outra_privada, _ = _par_ecdsa()
    falsa = base64.b64encode(outra_privada.sign(corpo, ec.ECDSA(hashes.SHA256()))).decode()
    assert not gw.validar_webhook({"x-payload-signature": falsa}, corpo)

    evento = gw.interpretar_webhook({}, corpo, {})
    assert (evento.payment_id, evento.status, evento.evento_id) == ("CHAR_1", "pago", "ORDE_1:CHAR_1:PAID")


# ---------------------------------------------------------------------------
# Mercado Pago
# ---------------------------------------------------------------------------

def test_mercadopago_pix_com_idempotencia():
    chamadas = []
    rotas = {("POST", "/v1/payments"): {
        "id": 123456, "status": "pending",
        "point_of_interaction": {"transaction_data": {"qr_code": "000201mp", "qr_code_base64": "iVB",
                                                      "ticket_url": "https://mp/ticket"}},
    }}
    gw = MercadoPagoGateway("sandbox", {"access_token": "TEST-1"}, "segredo", transport=_transport(rotas, chamadas))
    cobranca = gw.criar_cobranca("x", PAGADOR, 99.9, VENC, "PIX", "Pedido PED-5", "PED-5", idempotency_key="idem-1")
    corpo = json.loads(chamadas[0].content)
    assert chamadas[0].headers["x-idempotency-key"] == "idem-1"
    assert corpo["payment_method_id"] == "pix" and corpo["external_reference"] == "PED-5"
    assert corpo["payer"]["identification"] == {"type": "CNPJ", "number": "11222333000181"}
    assert cobranca.payment_id == "123456" and cobranca.pix_copia_cola == "000201mp"


def test_mercadopago_webhook_hmac_e_consulta():
    rotas = {("GET", "/v1/payments/777"): {"id": 777, "status": "approved", "date_approved": "2026-11-20T10:00:00",
                                            "date_last_updated": "x"}}
    gw = MercadoPagoGateway("sandbox", {"access_token": "TEST-1"}, "segredo", transport=_transport(rotas, []))
    corpo = json.dumps({"type": "payment", "data": {"id": "777"}}).encode()
    ts, request_id = "1700000000", "req-1"
    v1 = hmac.new(b"segredo", manifesto("777", request_id, ts).encode(), hashlib.sha256).hexdigest()
    headers = {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}

    assert gw.validar_webhook(headers, corpo, {"data.id": "777"})
    assert not gw.validar_webhook({**headers, "x-signature": f"ts={ts},v1=00"}, corpo, {"data.id": "777"})
    evento = gw.interpretar_webhook(headers, corpo, {"data.id": "777"})
    assert evento.payment_id == "777" and evento.status == "pago"
