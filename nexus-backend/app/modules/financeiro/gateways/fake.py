"""Gateway simulado em memória (testes automatizados e uso sem credenciais).

Webhook: header `x-fake-token` = webhook_token; corpo {id, payment_id, status}.
"""
from __future__ import annotations

import hmac
import json
import uuid
from datetime import date
from typing import Any, Dict, List, Mapping, Optional, Tuple

from app.modules.financeiro.gateways.base import CobrancaCriada, EventoPagamento, GatewayError, Pagador, header

# Estado compartilhado entre instâncias (a factory cria uma por requisição).
COBRANCAS: Dict[str, Dict[str, Any]] = {}
CLIENTES: Dict[str, str] = {}
CHAMADAS: List[Tuple[str, Any]] = []


def resetar() -> None:
    COBRANCAS.clear()
    CLIENTES.clear()
    CHAMADAS.clear()


class FakeGateway:
    nome = "fake"

    def __init__(self, ambiente: str = "sandbox", credenciais: Optional[Dict[str, str]] = None,
                 webhook_token: Optional[str] = None, transport: Any = None) -> None:
        self.ambiente = ambiente
        self.webhook_token = webhook_token or "fake-token"
        self.falhar_em: Optional[str] = (credenciais or {}).get("falhar_em")

    def _talvez_falhar(self, operacao: str) -> None:
        if self.falhar_em == operacao:
            raise GatewayError(f"fake: falha simulada em {operacao}", status_http=500)

    def testar_conexao(self) -> str:
        self._talvez_falhar("testar")
        return "Gateway simulado OK"

    def obter_ou_criar_cliente(self, pagador: Pagador, customer_id_cache: Optional[str] = None) -> str:
        CHAMADAS.append(("cliente", pagador.documento))
        if customer_id_cache:
            return customer_id_cache
        return CLIENTES.setdefault(pagador.documento, f"cus_fake_{uuid.uuid4().hex[:8]}")

    def criar_cobranca(self, customer_id: str, pagador: Pagador, valor: float, vencimento: date, meio: str,
                       descricao: str, referencia: str, notification_url: Optional[str] = None,
                       idempotency_key: Optional[str] = None) -> CobrancaCriada:
        self._talvez_falhar("cobranca")
        pid = f"pay_fake_{uuid.uuid4().hex[:10]}"
        COBRANCAS[pid] = {"status": "pendente", "valor": valor, "meio": meio, "referencia": referencia}
        CHAMADAS.append(("cobranca", pid))
        return CobrancaCriada(
            payment_id=pid,
            status="pendente",
            valor=valor,
            vencimento=vencimento,
            boleto_url=f"https://fake.local/boleto/{pid}.pdf" if meio == "BOLETO" else None,
            invoice_url=f"https://fake.local/i/{pid}",
            linha_digitavel="00190.00009 01234.567890 12345.678901 1 99990000010000" if meio == "BOLETO" else None,
            pix_copia_cola="00020126580014br.gov.bcb.pix0136fake" if meio == "PIX" else None,
            pix_qrcode_base64="iVBORw0KGgo=" if meio == "PIX" else None,
        )

    def consultar(self, payment_id: str) -> Tuple[str, Dict[str, Any]]:
        cobranca = COBRANCAS.get(payment_id)
        if not cobranca:
            raise GatewayError("fake: cobrança inexistente", status_http=404)
        return cobranca["status"], dict(cobranca)

    def cancelar(self, payment_id: str) -> None:
        if payment_id in COBRANCAS:
            COBRANCAS[payment_id]["status"] = "cancelado"

    @staticmethod
    def simular_status(payment_id: str, status: str) -> None:
        COBRANCAS[payment_id]["status"] = status

    def validar_webhook(self, headers: Mapping[str, str], corpo: bytes,
                        query: Optional[Mapping[str, str]] = None) -> bool:
        recebido = header(headers, "x-fake-token") or ""
        return bool(recebido) and hmac.compare_digest(recebido, self.webhook_token)

    def interpretar_webhook(self, headers: Mapping[str, str], corpo: bytes,
                            query: Mapping[str, str]) -> EventoPagamento:
        dados = json.loads(corpo or b"{}")
        if dados.get("explodir"):
            raise RuntimeError("falha simulada no processamento")
        return EventoPagamento(
            evento_id=str(dados["id"]),
            tipo_evento=str(dados.get("tipo") or "FAKE"),
            payment_id=dados.get("payment_id"),
            status=dados.get("status"),
            valor_pago=dados.get("valor_pago"),
        )
