"""Adapter Asaas (API v3). Docs: https://docs.asaas.com (verificado em 2026-11-13).

- Auth: header `access_token`.
- Webhook: header `asaas-access-token` com o token configurado no painel;
  corpo {id: "evt_...", event: "PAYMENT_...", payment: {...}}.
"""
from __future__ import annotations

import hmac
import json
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional, Tuple

import httpx

from app.modules.financeiro.gateways.base import (
    CobrancaCriada,
    EventoPagamento,
    GatewayError,
    HttpGatewayBase,
    Pagador,
    header,
)

BASE_URLS = {
    "sandbox": "https://api-sandbox.asaas.com/v3",
    "producao": "https://api.asaas.com/v3",
}

STATUS_MAP = {
    "PENDING": "pendente",
    "AWAITING_RISK_ANALYSIS": "pendente",
    "RECEIVED": "pago",
    "CONFIRMED": "pago",
    "RECEIVED_IN_CASH": "pago",
    "OVERDUE": "vencido",
    "REFUNDED": "estornado",
    "REFUND_REQUESTED": "estornado",
    "REFUND_IN_PROGRESS": "estornado",
    "CHARGEBACK_REQUESTED": "estornado",
    "CHARGEBACK_DISPUTE": "estornado",
    "AWAITING_CHARGEBACK_REVERSAL": "estornado",
}

# Eventos que definem o status independentemente do campo payment.status.
EVENTO_STATUS = {
    "PAYMENT_DELETED": "cancelado",
    "PAYMENT_BANK_SLIP_CANCELLED": "cancelado",
    "PAYMENT_REFUNDED": "estornado",
    "PAYMENT_RECEIVED": "pago",
    "PAYMENT_CONFIRMED": "pago",
    "PAYMENT_OVERDUE": "vencido",
}


def normalizar_status(status: Optional[str]) -> str:
    return STATUS_MAP.get((status or "").upper(), "pendente")


class AsaasGateway(HttpGatewayBase):
    nome = "asaas"

    def __init__(self, ambiente: str, credenciais: Dict[str, str], webhook_token: Optional[str] = None,
                 transport: Optional[httpx.BaseTransport] = None) -> None:
        api_key = (credenciais or {}).get("api_key")
        if not api_key:
            raise GatewayError("asaas: credencial 'api_key' não configurada")
        super().__init__(ambiente, BASE_URLS[ambiente], {"access_token": api_key}, transport)
        self.webhook_token = webhook_token

    # ------------------------------------------------------------------
    def testar_conexao(self) -> str:
        self._request("GET", "/customers", params={"limit": 1})
        return "Conexão com o Asaas OK"

    def obter_ou_criar_cliente(self, pagador: Pagador, customer_id_cache: Optional[str] = None) -> str:
        if customer_id_cache:
            return customer_id_cache
        encontrados = self._request("GET", "/customers", params={"cpfCnpj": pagador.documento, "limit": 1})
        dados = encontrados.get("data") or []
        if dados:
            return dados[0]["id"]
        end = pagador.endereco
        corpo = {
            "name": pagador.nome,
            "cpfCnpj": pagador.documento,
            "email": pagador.email,
            "mobilePhone": pagador.telefone,
            "postalCode": end.cep,
            "address": end.logradouro,
            "addressNumber": end.numero,
            "complement": end.complemento,
            "province": end.bairro,
            "externalReference": pagador.referencia,
            "notificationDisabled": True,  # o NEXUS faz a comunicação com o Polo
        }
        criado = self._request("POST", "/customers", json={k: v for k, v in corpo.items() if v})
        return criado["id"]

    def criar_cobranca(
        self,
        customer_id: str,
        pagador: Pagador,
        valor: float,
        vencimento: date,
        meio: str,
        descricao: str,
        referencia: str,
        notification_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> CobrancaCriada:
        pagamento = self._request("POST", "/payments", json={
            "customer": customer_id,
            "billingType": meio,
            "value": round(float(valor), 2),
            "dueDate": vencimento.isoformat(),
            "description": (descricao or "")[:500],
            "externalReference": referencia,
        })
        cobranca = CobrancaCriada(
            payment_id=pagamento["id"],
            status=normalizar_status(pagamento.get("status")),
            valor=float(pagamento.get("value") or valor),
            vencimento=vencimento,
            boleto_url=pagamento.get("bankSlipUrl"),
            invoice_url=pagamento.get("invoiceUrl"),
            nosso_numero=pagamento.get("nossoNumero"),
            raw=pagamento,
        )
        if meio == "BOLETO":
            linha = self._request("GET", f"/payments/{cobranca.payment_id}/identificationField")
            cobranca.linha_digitavel = linha.get("identificationField")
            cobranca.nosso_numero = linha.get("nossoNumero") or cobranca.nosso_numero
        elif meio == "PIX":
            pix = self._request("GET", f"/payments/{cobranca.payment_id}/pixQrCode")
            cobranca.pix_copia_cola = pix.get("payload")
            cobranca.pix_qrcode_base64 = pix.get("encodedImage")
        return cobranca

    def consultar(self, payment_id: str) -> Tuple[str, Dict[str, Any]]:
        pagamento = self._request("GET", f"/payments/{payment_id}")
        if pagamento.get("deleted"):
            return "cancelado", pagamento
        return normalizar_status(pagamento.get("status")), pagamento

    def cancelar(self, payment_id: str) -> None:
        self._request("DELETE", f"/payments/{payment_id}")

    # ------------------------------------------------------------------
    def validar_webhook(self, headers: Mapping[str, str], corpo: bytes, query: Optional[Mapping[str, str]] = None) -> bool:
        recebido = header(headers, "asaas-access-token") or ""
        if not self.webhook_token or not recebido:
            return False
        return hmac.compare_digest(recebido.encode(), self.webhook_token.encode())

    def interpretar_webhook(
        self, headers: Mapping[str, str], corpo: bytes, query: Mapping[str, str]
    ) -> EventoPagamento:
        try:
            dados = json.loads(corpo or b"{}")
        except ValueError as exc:
            raise GatewayError("asaas: corpo do webhook não é JSON") from exc
        evento = str(dados.get("event") or "")
        pagamento = dados.get("payment") or {}
        payment_id = pagamento.get("id")
        status = EVENTO_STATUS.get(evento)
        if status is None and evento.startswith("PAYMENT_") and pagamento.get("status"):
            status = normalizar_status(pagamento.get("status"))
        pago_em = None
        data_pag = pagamento.get("clientPaymentDate") or pagamento.get("paymentDate") or pagamento.get("confirmedDate")
        if data_pag:
            try:
                pago_em = datetime.fromisoformat(str(data_pag))
            except ValueError:
                pago_em = None
        return EventoPagamento(
            evento_id=str(dados.get("id") or f"{evento}:{payment_id}"),
            tipo_evento=evento,
            payment_id=payment_id,
            status=status,
            valor_pago=float(pagamento["netValue"]) if pagamento.get("netValue") is not None else None,
            pago_em=pago_em,
        )
