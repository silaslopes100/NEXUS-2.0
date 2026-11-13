"""Contrato comum dos gateways de pagamento (Asaas, PagBank, Mercado Pago, Fake).

Status normalizados internos: pendente | pago | vencido | cancelado | estornado | falhou.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple

import httpx

STATUS_NORMALIZADOS = ("pendente", "pago", "vencido", "cancelado", "estornado", "falhou")
MEIOS = ("BOLETO", "PIX", "CREDIT_CARD")
USER_AGENT = "NEXUS2.0/1.0"
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class GatewayError(Exception):
    """Falha de comunicação ou recusa do gateway."""

    def __init__(self, mensagem: str, status_http: Optional[int] = None, detalhe: Any = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_http = status_http
        self.detalhe = detalhe


@dataclass
class EnderecoPagador:
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None


@dataclass
class Pagador:
    nome: str
    documento: str  # só dígitos (CPF ou CNPJ)
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: EnderecoPagador = field(default_factory=EnderecoPagador)
    referencia: Optional[str] = None  # ex.: id do Polo


@dataclass
class CobrancaCriada:
    payment_id: str
    status: str
    valor: float
    vencimento: Optional[date] = None
    boleto_url: Optional[str] = None
    invoice_url: Optional[str] = None
    linha_digitavel: Optional[str] = None
    nosso_numero: Optional[str] = None
    pix_copia_cola: Optional[str] = None
    pix_qrcode_base64: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventoPagamento:
    evento_id: str
    tipo_evento: str
    payment_id: Optional[str]
    status: Optional[str]  # normalizado; None = evento sem efeito de status
    valor_pago: Optional[float] = None
    pago_em: Optional[datetime] = None


class PaymentGateway(Protocol):
    nome: str
    ambiente: str

    def testar_conexao(self) -> str: ...

    def obter_ou_criar_cliente(self, pagador: Pagador, customer_id_cache: Optional[str] = None) -> str: ...

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
    ) -> CobrancaCriada: ...

    def consultar(self, payment_id: str) -> Tuple[str, Dict[str, Any]]: ...

    def cancelar(self, payment_id: str) -> None: ...

    def validar_webhook(
        self, headers: Mapping[str, str], corpo: bytes, query: Optional[Mapping[str, str]] = None
    ) -> bool: ...

    def interpretar_webhook(
        self, headers: Mapping[str, str], corpo: bytes, query: Mapping[str, str]
    ) -> EventoPagamento: ...


class HttpGatewayBase:
    """Utilitários HTTP comuns (httpx síncrono, timeout curto para serverless)."""

    nome = "base"

    def __init__(self, ambiente: str, base_url: str, headers: Dict[str, str],
                 transport: Optional[httpx.BaseTransport] = None) -> None:
        self.ambiente = ambiente
        self._client = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", **headers},
            timeout=TIMEOUT,
            transport=transport,
        )

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise GatewayError(f"{self.nome}: falha de comunicação ({exc.__class__.__name__})") from exc
        if resp.status_code >= 400:
            try:
                detalhe = resp.json()
            except ValueError:
                detalhe = resp.text[:500]
            raise GatewayError(
                f"{self.nome}: HTTP {resp.status_code} - {self._mensagem_erro(detalhe)}",
                status_http=resp.status_code,
                detalhe=detalhe,
            )
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    @staticmethod
    def _mensagem_erro(detalhe: Any) -> str:
        if isinstance(detalhe, dict):
            erros = detalhe.get("errors") or detalhe.get("error_messages")
            if isinstance(erros, list) and erros:
                primeiro = erros[0]
                if isinstance(primeiro, dict):
                    return str(primeiro.get("description") or primeiro.get("message") or primeiro)
                return str(primeiro)
            return str(detalhe.get("message") or detalhe.get("error") or detalhe)[:300]
        return str(detalhe)[:300]


def header(headers: Mapping[str, str], nome: str) -> Optional[str]:
    """Busca header ignorando maiúsculas/minúsculas."""
    alvo = nome.lower()
    for k, v in headers.items():
        if k.lower() == alvo:
            return v
    return None
