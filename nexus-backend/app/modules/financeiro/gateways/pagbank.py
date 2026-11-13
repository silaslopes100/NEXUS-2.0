"""Adapter PagBank (Orders API). Docs: https://developer.pagbank.com.br (verificado em 2026-11-13).

- Auth: `Authorization: Bearer <token>`; valores em centavos.
- Webhook: header `x-payload-signature` = assinatura ECDSA (SHA256withECDSA) do
  corpo cru, verificada com a chave pública de `GET /public-keys?type=webhook`.
  O modelo antigo (`x-authenticity-token`, SHA-256) foi descontinuado.
- Corpo do webhook = objeto Order completo (id ORDE_..., charges[]).
"""
from __future__ import annotations

import base64
import json
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Mapping, Optional, Tuple

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.modules.financeiro.gateways.base import (
    CobrancaCriada,
    EventoPagamento,
    GatewayError,
    HttpGatewayBase,
    Pagador,
    header,
)

BASE_URLS = {
    "sandbox": "https://sandbox.api.pagseguro.com",
    "producao": "https://api.pagseguro.com",
}

STATUS_MAP = {
    "WAITING": "pendente",
    "AUTHORIZED": "pendente",
    "IN_ANALYSIS": "pendente",
    "PAID": "pago",
    "DECLINED": "falhou",
    "CANCELED": "cancelado",
}

# Cache da chave pública por ambiente (vale durante a vida do processo).
_CHAVES_PUBLICAS: Dict[str, List[str]] = {}


def normalizar_status(status: Optional[str]) -> str:
    return STATUS_MAP.get((status or "").upper(), "pendente")


def _centavos(valor: float) -> int:
    """Reais -> centavos com arredondamento comercial (evita 100.505 -> 10050 do float)."""
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _link(charge: Dict[str, Any], media: Optional[str] = None, rel: Optional[str] = None) -> Optional[str]:
    for link in charge.get("links") or []:
        if (media and link.get("media") == media) or (rel and link.get("rel") == rel):
            return link.get("href")
    return None


class PagBankGateway(HttpGatewayBase):
    nome = "pagbank"

    def __init__(self, ambiente: str, credenciais: Dict[str, str], webhook_token: Optional[str] = None,
                 transport: Optional[httpx.BaseTransport] = None) -> None:
        token = (credenciais or {}).get("token")
        if not token:
            raise GatewayError("pagbank: credencial 'token' não configurada")
        super().__init__(ambiente, BASE_URLS[ambiente], {"Authorization": f"Bearer {token}"}, transport)
        self._chave_publica_fixa = (credenciais or {}).get("webhook_public_key")

    # ------------------------------------------------------------------
    def testar_conexao(self) -> str:
        self._chaves_publicas(forcar=True)
        return "Conexão com o PagBank OK"

    def obter_ou_criar_cliente(self, pagador: Pagador, customer_id_cache: Optional[str] = None) -> str:
        # No Orders API o cliente vai embutido em cada pedido; usamos o documento como id lógico.
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
        end = pagador.endereco
        centavos = _centavos(valor)
        if meio == "BOLETO":
            metodo: Dict[str, Any] = {
                "type": "BOLETO",
                "boleto": {
                    "due_date": vencimento.isoformat(),
                    "instruction_lines": {"line_1": f"Pedido {referencia}", "line_2": "NEXUS 2.0"},
                    "holder": {
                        "name": pagador.nome,
                        "tax_id": pagador.documento,
                        "email": pagador.email,
                        "address": {
                            "street": end.logradouro, "number": end.numero or "S/N",
                            "complement": end.complemento, "locality": end.bairro,
                            "city": end.cidade, "region_code": end.uf, "country": "BRA",
                            "postal_code": (end.cep or "").replace("-", ""),
                        },
                    },
                },
            }
        elif meio == "PIX":
            metodo = {
                "type": "PIX",
                "pix": {"expiration_date": f"{vencimento.isoformat()}T23:59:59-03:00"},
            }
        else:
            raise GatewayError(f"pagbank: meio '{meio}' não suportado nesta integração")
        corpo: Dict[str, Any] = {
            "reference_id": referencia,
            "customer": {"name": pagador.nome, "email": pagador.email, "tax_id": pagador.documento},
            "items": [{"reference_id": referencia, "name": (descricao or referencia)[:64],
                       "quantity": 1, "unit_amount": centavos}],
            "charges": [{
                "reference_id": referencia,
                "description": (descricao or referencia)[:64],
                "amount": {"value": centavos, "currency": "BRL"},
                "payment_method": metodo,
            }],
        }
        if notification_url:
            corpo["notification_urls"] = [notification_url]
        headers = {"x-idempotency-key": idempotency_key} if idempotency_key else None
        pedido = self._request("POST", "/orders", json=corpo, headers=headers)
        charge = (pedido.get("charges") or [{}])[0]
        boleto = (charge.get("payment_method") or {}).get("boleto") or {}
        qr = charge.get("qr_code") or {}
        return CobrancaCriada(
            payment_id=charge.get("id") or pedido.get("id"),
            status=normalizar_status(charge.get("status")),
            valor=valor,
            vencimento=vencimento,
            boleto_url=_link(charge, media="application/pdf"),
            linha_digitavel=boleto.get("formatted_barcode") or boleto.get("barcode"),
            nosso_numero=boleto.get("id"),
            pix_copia_cola=qr.get("text"),
            invoice_url=_link(charge, rel="QRCODE.PNG"),
            raw=pedido,
        )

    def consultar(self, payment_id: str) -> Tuple[str, Dict[str, Any]]:
        charge = self._request("GET", f"/charges/{payment_id}")
        return normalizar_status(charge.get("status")), charge

    def cancelar(self, payment_id: str) -> None:
        # Documentado para estorno/pré-autorização; boleto WAITING expira sozinho se a API recusar.
        self._request("POST", f"/charges/{payment_id}/cancel", json={})

    # ------------------------------------------------------------------
    def _chaves_publicas(self, forcar: bool = False) -> List[str]:
        if self._chave_publica_fixa:
            return [self._chave_publica_fixa]
        if forcar or self.ambiente not in _CHAVES_PUBLICAS:
            dados = self._request("GET", "/public-keys", params={"type": "webhook"})
            chaves = dados.get("public_keys") or dados.get("public_key") or dados.get("keys") or []
            if isinstance(chaves, str):
                chaves = [chaves]
            if isinstance(chaves, dict):
                chaves = [chaves]
            _CHAVES_PUBLICAS[self.ambiente] = [
                c.get("public_key") or c.get("key") if isinstance(c, dict) else c for c in chaves
            ]
        return [c for c in _CHAVES_PUBLICAS.get(self.ambiente, []) if c]

    @staticmethod
    def _carregar_chave(chave_b64: str):
        der = base64.b64decode(chave_b64)
        return serialization.load_der_public_key(der)

    def validar_webhook(self, headers: Mapping[str, str], corpo: bytes, query: Optional[Mapping[str, str]] = None) -> bool:
        assinatura_header = header(headers, "x-payload-signature") or ""
        assinaturas = [a.strip() for a in assinatura_header.replace(";", ",").split(",") if a.strip()]
        if not assinaturas:
            return False
        try:
            chaves = [self._carregar_chave(c) for c in self._chaves_publicas()]
        except (GatewayError, ValueError):
            return False
        for chave in chaves:
            for assinatura in assinaturas:
                try:
                    chave.verify(base64.b64decode(assinatura), corpo, ec.ECDSA(hashes.SHA256()))
                    return True
                except (InvalidSignature, ValueError):
                    continue
        return False

    def interpretar_webhook(
        self, headers: Mapping[str, str], corpo: bytes, query: Mapping[str, str]
    ) -> EventoPagamento:
        try:
            pedido = json.loads(corpo or b"{}")
        except ValueError as exc:
            raise GatewayError("pagbank: corpo do webhook não é JSON") from exc
        charge = (pedido.get("charges") or [{}])[0]
        status_bruto = charge.get("status")
        pago_em = None
        if charge.get("paid_at"):
            try:
                pago_em = datetime.fromisoformat(str(charge["paid_at"]))
            except ValueError:
                pago_em = None
        valor = (charge.get("amount") or {}).get("summary", {}).get("paid")
        return EventoPagamento(
            evento_id=f"{pedido.get('id')}:{charge.get('id')}:{status_bruto}",
            tipo_evento=f"CHARGE_{status_bruto}",
            payment_id=charge.get("id"),
            status=normalizar_status(status_bruto) if status_bruto else None,
            valor_pago=valor / 100 if isinstance(valor, (int, float)) else None,
            pago_em=pago_em,
        )
