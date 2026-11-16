"""Instancia o adapter do gateway a partir de `gateways_config` (credenciais criptografadas)."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.crypto import decrypt_secret
from app.modules.financeiro.gateways.asaas import AsaasGateway
from app.modules.financeiro.gateways.base import GatewayError, PaymentGateway
from app.modules.financeiro.gateways.fake import FakeGateway
from app.modules.financeiro.gateways.mercadopago import MercadoPagoGateway
from app.modules.financeiro.gateways.pagbank import PagBankGateway

ADAPTERS: Dict[str, Any] = {
    "asaas": AsaasGateway,
    "pagbank": PagBankGateway,
    "mercadopago": MercadoPagoGateway,
    "fake": FakeGateway,
}

# Campos de credencial por gateway (exibidos na tela Gateways). `obrigatorio` = exigido para ativar.
CAMPOS_CREDENCIAIS: Dict[str, List[Dict[str, Any]]] = {
    "asaas": [{"campo": "api_key", "label": "API Key ($aact_...)", "obrigatorio": True}],
    "pagbank": [
        {"campo": "token", "label": "Token (Bearer)", "obrigatorio": True},
        {"campo": "webhook_public_key", "label": "Chave pública do webhook (opcional; senão é buscada na API)",
         "obrigatorio": False},
    ],
    "mercadopago": [{"campo": "access_token", "label": "Access Token (TEST-... no sandbox)", "obrigatorio": True}],
}
ROTULO_WEBHOOK_TOKEN = {
    "asaas": "Token de autenticação do webhook (o mesmo cadastrado no painel Asaas)",
    "pagbank": None,  # PagBank assina com ECDSA (chave pública)
    "mercadopago": "Assinatura secreta do webhook (painel Mercado Pago)",
}
GATEWAYS_DISPONIVEIS = ("asaas", "pagbank", "mercadopago")

_override: Optional[Callable[[str, str, Optional[Dict[str, Any]]], PaymentGateway]] = None


def set_gateway_override(fn: Optional[Callable[[str, str, Optional[Dict[str, Any]]], PaymentGateway]]) -> None:
    """Testes: substitui a construção dos adapters (recebe gateway, ambiente, config)."""
    global _override
    _override = fn


def _decifrar(config: Dict[str, Any]) -> tuple[Dict[str, str], Optional[str]]:
    credenciais: Dict[str, str] = {}
    if config.get("credenciais_cripto"):
        credenciais = json.loads(decrypt_secret(config["credenciais_cripto"]))
    token = decrypt_secret(config["webhook_token_cripto"]) if config.get("webhook_token_cripto") else None
    return credenciais, token


def construir(gateway: str, ambiente: str, config: Optional[Dict[str, Any]], exigir_ativo: bool = True) -> PaymentGateway:
    """Cria o adapter. 409 se o gateway não estiver ativo/configurado."""
    if _override is not None:
        return _override(gateway, ambiente, config)
    if gateway not in ADAPTERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Gateway '{gateway}' desconhecido")
    if not config or (exigir_ativo and not config.get("ativo")):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Gateway {gateway} ({ambiente}) não está ativo/configurado",
        )
    try:
        credenciais, token = _decifrar(config)
        return ADAPTERS[gateway](ambiente, credenciais, token)
    except (GatewayError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Gateway {gateway} ({ambiente}) mal configurado: {exc}",
        ) from exc
