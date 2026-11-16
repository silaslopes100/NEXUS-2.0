"""Adapter Mercado Pago (Payments API v1).

ATENÇÃO: a documentação oficial não pôde ser verificada em 2026-11-13 (páginas
retornaram 404). Os pontos marcados com `# VERIFICAR NA DOC` seguem o formato
conhecido e devem ser conferidos antes de ativar em produção.

- Auth: `Authorization: Bearer <access_token>` (credenciais TEST- no sandbox).
- Webhook: corpo {type: "payment", data: {id}}; header `x-signature: ts=..,v1=..`
  + `x-request-id`; HMAC-SHA256 (hex) do manifesto
  `id:{data.id};request-id:{x-request-id};ts:{ts};` com o segredo do webhook.
"""
from __future__ import annotations

import hashlib
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

BASE_URL = "https://api.mercadopago.com"  # mesmo host; o ambiente é definido pela credencial

STATUS_MAP = {
    "pending": "pendente",
    "in_process": "pendente",
    "authorized": "pendente",
    "approved": "pago",
    "rejected": "falhou",
    "cancelled": "cancelado",
    "refunded": "estornado",
    "charged_back": "estornado",
}

METODOS = {"PIX": "pix", "BOLETO": "bolbradesco"}  # VERIFICAR NA DOC


def normalizar_status(status: Optional[str]) -> str:
    return STATUS_MAP.get((status or "").lower(), "pendente")


def manifesto(data_id: str, request_id: str, ts: str) -> str:
    return f"id:{data_id};request-id:{request_id};ts:{ts};"  # VERIFICAR NA DOC


def _partes_assinatura(valor: str) -> Dict[str, str]:
    partes: Dict[str, str] = {}
    for item in (valor or "").split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            partes[k.strip()] = v.strip()
    return partes


class MercadoPagoGateway(HttpGatewayBase):
    nome = "mercadopago"

    def __init__(self, ambiente: str, credenciais: Dict[str, str], webhook_token: Optional[str] = None,
                 transport: Optional[httpx.BaseTransport] = None) -> None:
        token = (credenciais or {}).get("access_token")
        if not token:
            raise GatewayError("mercadopago: credencial 'access_token' não configurada")
        super().__init__(ambiente, BASE_URL, {"Authorization": f"Bearer {token}"}, transport)
        self.webhook_secret = webhook_token

    def testar_conexao(self) -> str:
        self._request("GET", "/users/me")
        return "Conexão com o Mercado Pago OK"

    def obter_ou_criar_cliente(self, pagador: Pagador, customer_id_cache: Optional[str] = None) -> str:
        # O pagador vai embutido em cada pagamento.
        return customer_id_cache or pagador.documento

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
        metodo = METODOS.get(meio)
        if not metodo:
            raise GatewayError(f"mercadopago: meio '{meio}' não suportado nesta integração")
        end = pagador.endereco
        tipo_doc = "CPF" if len(pagador.documento) == 11 else "CNPJ"
        corpo: Dict[str, Any] = {
            "transaction_amount": round(float(valor), 2),
            "description": (descricao or referencia)[:255],
            "payment_method_id": metodo,
            "external_reference": referencia,
            "date_of_expiration": f"{vencimento.isoformat()}T23:59:59.000-03:00",
            "payer": {
                "email": pagador.email,
                "first_name": pagador.nome[:60],
                "identification": {"type": tipo_doc, "number": pagador.documento},
                "address": {  # exigido para boleto  # VERIFICAR NA DOC
                    "zip_code": (end.cep or "").replace("-", ""),
                    "street_name": end.logradouro,
                    "street_number": end.numero,
                    "neighborhood": end.bairro,
                    "city": end.cidade,
                    "federal_unit": end.uf,
                },
            },
        }
        if notification_url:
            corpo["notification_url"] = notification_url
        headers = {"X-Idempotency-Key": idempotency_key or referencia}
        pagamento = self._request("POST", "/v1/payments", json=corpo, headers=headers)
        transacao = ((pagamento.get("point_of_interaction") or {}).get("transaction_data")) or {}
        detalhes = pagamento.get("transaction_details") or {}
        barcode = pagamento.get("barcode") or {}
        return CobrancaCriada(
            payment_id=str(pagamento["id"]),
            status=normalizar_status(pagamento.get("status")),
            valor=valor,
            vencimento=vencimento,
            boleto_url=detalhes.get("external_resource_url") if meio == "BOLETO" else None,
            invoice_url=transacao.get("ticket_url"),
            linha_digitavel=detalhes.get("digitable_line") or barcode.get("content"),
            pix_copia_cola=transacao.get("qr_code"),
            pix_qrcode_base64=transacao.get("qr_code_base64"),
            raw=pagamento,
        )

    def consultar(self, payment_id: str) -> Tuple[str, Dict[str, Any]]:
        pagamento = self._request("GET", f"/v1/payments/{payment_id}")
        return normalizar_status(pagamento.get("status")), pagamento

    def cancelar(self, payment_id: str) -> None:
        self._request("PUT", f"/v1/payments/{payment_id}", json={"status": "cancelled"})

    # ------------------------------------------------------------------
    @staticmethod
    def _data_id(corpo: bytes, query: Mapping[str, str]) -> Optional[str]:
        data_id = query.get("data.id") or query.get("id")
        if data_id:
            return str(data_id)
        try:
            dados = json.loads(corpo or b"{}")
        except ValueError:
            return None
        return str((dados.get("data") or {}).get("id") or "") or None

    def validar_webhook(self, headers: Mapping[str, str], corpo: bytes, query: Optional[Mapping[str, str]] = None) -> bool:
        if not self.webhook_secret:
            return False
        partes = _partes_assinatura(header(headers, "x-signature") or "")
        ts, v1 = partes.get("ts"), partes.get("v1")
        request_id = header(headers, "x-request-id") or ""
        data_id = self._data_id(corpo, query or {})
        if not (ts and v1 and data_id):
            return False
        esperado = hmac.new(
            self.webhook_secret.encode(), manifesto(data_id, request_id, ts).encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(esperado, v1)

    def interpretar_webhook(
        self, headers: Mapping[str, str], corpo: bytes, query: Mapping[str, str]
    ) -> EventoPagamento:
        data_id = self._data_id(corpo, query)
        if not data_id:
            raise GatewayError("mercadopago: webhook sem data.id")
        status, pagamento = self.consultar(data_id)
        pago_em = None
        if pagamento.get("date_approved"):
            try:
                pago_em = datetime.fromisoformat(str(pagamento["date_approved"]))
            except ValueError:
                pago_em = None
        return EventoPagamento(
            evento_id=f"{data_id}:{pagamento.get('status')}:{pagamento.get('date_last_updated')}",
            tipo_evento=f"payment.{pagamento.get('status')}",
            payment_id=data_id,
            status=status,
            valor_pago=pagamento.get("transaction_details", {}).get("net_received_amount"),
            pago_em=pago_em,
        )
