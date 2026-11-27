"""Cobrança nos gateways, webhooks e reconciliação (Fase 2).

Fluxo: pedido 'aguardando_pagamento' -> gerar_cobranca (gateway) -> webhook/cron
-> aplicar_status -> pedido 'pago_aguardando_envio' (livro) ou 'concluido'
(licença, com crédito no estoque do Polo).
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.crypto import SecretCryptoError, encrypt_secret, decrypt_secret, mask_secret
from app.modules.auth.schemas import UserResponse
from app.modules.financeiro import pedidos as regras
from app.modules.financeiro.gateways import factory
from app.modules.financeiro.gateways.base import Encargos, EnderecoPagador, GatewayError, Pagador, PaymentGateway
from app.modules.financeiro.repository import FinanceiroRepositoryInterface
from app.modules.financeiro.schemas import PagamentoResponse
from app.modules.financeiro.service import FinanceiroService, escopo_do_usuario

logger = logging.getLogger(__name__)

DIAS_VENCIMENTO_PADRAO = 3
MAX_TENTATIVAS_WEBHOOK = 5
# pago só sai para estornado; finais não mudam.
_STATUS_FINAIS = {"cancelado", "estornado", "falhou"}
_CAMPOS_FISCAIS_OBRIGATORIOS = {
    "documento_fiscal": "CPF/CNPJ",
    "razao_social": "razão social",
    "email_financeiro": "e-mail financeiro",
}


# Horário de Brasília (UTC-3, sem horário de verão desde 2019). O servidor (Vercel) roda em UTC:
# sem isso, cobranças geradas após 21h teriam o vencimento contado a partir do "dia seguinte".
FUSO_BRASIL = timezone(timedelta(hours=-3))


def hoje_brasil() -> date:
    return datetime.now(FUSO_BRASIL).date()


def webhook_url(gateway: str, ambiente: str) -> Optional[str]:
    base = settings.PUBLIC_API_URL
    return f"{base}/financeiro/webhooks/{gateway}/{ambiente}" if base else None


def proximo_status(atual: Optional[str], novo: Optional[str]) -> Optional[str]:
    """Regra de não-regressão. Retorna o status a gravar ou None se nada muda."""
    if not novo or novo == atual:
        return None
    if atual in _STATUS_FINAIS:
        return None
    if atual == "pago":
        # pago só muda em caso de estorno/cancelamento (devolução)
        return "estornado" if novo in ("estornado", "cancelado") else None
    return novo


def creditar_licencas_padrao(pedido: Dict[str, Any], usuario_id: Optional[str]) -> bool:
    """Credita o estoque do Polo e o extrato (RN-02.1) quando um pedido de licença é pago.

    Idempotente: cada pedido é creditado uma única vez (ver `creditar_pedido_pago`), então pode ser
    chamado de novo no reprocessamento. Retorna True se creditou agora.
    """
    from app.modules.polos_escolas.repository import get_polos_escolas_repository

    if not pedido.get("polo_id"):
        return False
    # Estoque por disciplina (Fase 3A): um crédito por disciplina dos itens.
    por_disciplina: Dict[Optional[str], Dict[str, float]] = {}
    for item in pedido.get("itens") or []:
        qtd = int(item.get("quantidade") or 0)
        if qtd <= 0:
            continue
        chave = str(item["disciplina_id"]) if item.get("disciplina_id") else None
        acum = por_disciplina.setdefault(chave, {"quantidade": 0, "valor": 0.0})
        acum["quantidade"] += qtd
        acum["valor"] += float(item.get("valor_total") or 0)
    movimentacoes = [
        {
            "tipo": "compra_fornecedor",
            "materia_id": disciplina_id,
            "quantidade": int(acum["quantidade"]),
            "valor_unitario": round(acum["valor"] / acum["quantidade"], 2),
            "status": "disponivel_polo",
            "actor_id": usuario_id,
            "observacao": f"Pedido {pedido.get('numero')} pago via gateway",
        }
        for disciplina_id, acum in por_disciplina.items()
    ]
    # Sem itens a creditar, o pedido é marcado mesmo assim (não volta para a fila de pendências).
    return get_polos_escolas_repository().creditar_pedido_pago(str(pedido["id"]), pedido["polo_id"], movimentacoes)


class CobrancaService:
    def __init__(
        self,
        repo: FinanceiroRepositoryInterface,
        creditar_licencas: Callable[[Dict[str, Any], Optional[str]], Optional[bool]] = creditar_licencas_padrao,
    ) -> None:
        self.repo = repo
        self.pedidos = FinanceiroService(repo)
        self.creditar_licencas = creditar_licencas

    # ------------------------------------------------------------------
    # Configuração dos gateways
    # ------------------------------------------------------------------

    def _adapter(self, gateway: str, ambiente: str, exigir_ativo: bool = True) -> PaymentGateway:
        return factory.construir(gateway, ambiente, self.repo.get_gateway_config(gateway, ambiente), exigir_ativo)

    def gateway_padrao(self, ambiente: str) -> str:
        for c in self.repo.list_gateway_configs():
            if c["ambiente"] == ambiente and c.get("ativo") and c.get("padrao"):
                return c["gateway"]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nenhum gateway ativo e padrão no ambiente '{ambiente}'. Configure em Gateways de Pagamento.",
        )

    def _gateway_da_regra(self, regra: Dict[str, Any], ambiente: str) -> Optional[str]:
        """Gateway preferido da regra, se estiver ativo no ambiente (senão cai no padrão)."""
        preferido = regra.get("gateway_preferido")
        if not preferido:
            return None
        config = self.repo.get_gateway_config(preferido, ambiente) or {}
        return preferido if config.get("ativo") else None

    def opcoes_checkout(self, tipo: str, polo_id: Optional[str], valor: Optional[float]) -> Dict[str, Any]:
        """Meios e vencimento que a regra aplicável oferece (tela de checkout)."""
        regra = self.repo.get_regra_pagamento(tipo, polo_id, valor) or {}
        dias = int(regra.get("dias_vencimento") or DIAS_VENCIMENTO_PADRAO)
        return {
            "regra_id": regra.get("id"),
            "regra_nome": regra.get("nome") or "Padrão",
            "meios": [m for m in (regra.get("meios_permitidos") or ["BOLETO", "PIX"]) if m in ("BOLETO", "PIX")],
            "dias_vencimento": dias,
            "vencimento": hoje_brasil() + timedelta(days=dias),
            "multa_pct": float(regra.get("multa_pct") or 0),
            "juros_mes_pct": float(regra.get("juros_mes_pct") or 0),
            "desconto_antecipado_pct": float(regra.get("desconto_antecipado_pct") or 0),
        }

    @staticmethod
    def _credenciais_mascaradas(config: Dict[str, Any]) -> Dict[str, str]:
        if not config.get("credenciais_cripto"):
            return {}
        try:
            dados = json.loads(decrypt_secret(config["credenciais_cripto"]))
        except RuntimeError:
            return {"_erro": "não foi possível ler (PAYMENT_SECRETS_KEY mudou?)"}
        return {k: mask_secret(v) for k, v in dados.items() if v}

    def listar_gateways(self) -> Dict[str, Any]:
        configs = {(c["gateway"], c["ambiente"]): c for c in self.repo.list_gateway_configs()}
        itens = []
        for gateway in factory.GATEWAYS_DISPONIVEIS:
            for ambiente in factory.AMBIENTES_POR_GATEWAY[gateway]:
                c = configs.get((gateway, ambiente)) or {}
                token_mascarado = ""
                if c.get("webhook_token_cripto"):
                    try:
                        token_mascarado = mask_secret(decrypt_secret(c["webhook_token_cripto"]))
                    except RuntimeError:
                        token_mascarado = "(ilegível)"
                itens.append({
                    "gateway": gateway,
                    "ambiente": ambiente,
                    "ativo": bool(c.get("ativo")),
                    "padrao": bool(c.get("padrao")),
                    "credenciais": self._credenciais_mascaradas(c),
                    "webhook_token": token_mascarado,
                    "campos": factory.CAMPOS_CREDENCIAIS[gateway],
                    "rotulo_webhook_token": factory.ROTULO_WEBHOOK_TOKEN[gateway],
                    "webhook_url": webhook_url(gateway, ambiente),
                    "ultimo_teste_em": c.get("ultimo_teste_em"),
                    "ultimo_teste_ok": c.get("ultimo_teste_ok"),
                })
        return {
            "ambiente_ativo": settings.PAYMENT_ENV,
            "public_api_url_configurada": bool(settings.PUBLIC_API_URL),
            "chave_configurada": bool(settings.PAYMENT_SECRETS_KEY),
            "items": itens,
        }

    def salvar_gateway(self, gateway: str, ambiente: str, dados: Dict[str, Any], usuario_id: str) -> Dict[str, Any]:
        # Falha de criptografia (chave ausente/inválida/trocada) vira HTTPException: um erro não tratado
        # sai como 500 sem cabeçalhos CORS e o navegador só mostra "blocked by CORS policy".
        try:
            return self._salvar_gateway(gateway, ambiente, dados, usuario_id)
        except SecretCryptoError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{exc}. Verifique PAYMENT_SECRETS_KEY nas variáveis de ambiente do backend.",
            ) from exc

    def _salvar_gateway(self, gateway: str, ambiente: str, dados: Dict[str, Any], usuario_id: str) -> Dict[str, Any]:
        if gateway not in factory.GATEWAYS_DISPONIVEIS or ambiente not in factory.AMBIENTES_POR_GATEWAY[gateway]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway/ambiente inválido")
        atual = self.repo.get_gateway_config(gateway, ambiente) or {}
        credenciais: Dict[str, str] = {}
        if atual.get("credenciais_cripto"):
            credenciais = json.loads(decrypt_secret(atual["credenciais_cripto"]))
        permitidos = {c["campo"] for c in factory.CAMPOS_CREDENCIAIS[gateway]}
        for campo, valor in (dados.get("credenciais") or {}).items():
            if campo in permitidos and valor is not None:
                valor = str(valor).strip()
                if valor:
                    credenciais[campo] = valor
                else:
                    credenciais.pop(campo, None)
        campos: Dict[str, Any] = {"atualizado_por": usuario_id}
        if dados.get("credenciais") is not None:
            campos["credenciais_cripto"] = encrypt_secret(json.dumps(credenciais)) if credenciais else None
        token = dados.get("webhook_token")
        if token is not None:
            campos["webhook_token_cripto"] = encrypt_secret(token.strip()) if token.strip() else None
        ativo = dados.get("ativo", atual.get("ativo", False))
        if ativo:
            faltando = [c["label"] for c in factory.CAMPOS_CREDENCIAIS[gateway]
                        if c["obrigatorio"] and not credenciais.get(c["campo"])]
            tem_token = campos.get("webhook_token_cripto", atual.get("webhook_token_cripto"))
            if factory.ROTULO_WEBHOOK_TOKEN[gateway] and not tem_token:
                faltando.append(factory.ROTULO_WEBHOOK_TOKEN[gateway])
            if faltando:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Para ativar, preencha: {', '.join(faltando)}",
                )
        campos["ativo"] = bool(ativo)
        padrao = dados.get("padrao", atual.get("padrao", False))
        campos["padrao"] = bool(padrao and ativo)
        self.repo.salvar_gateway_config(gateway, ambiente, campos)
        return next(i for i in self.listar_gateways()["items"] if i["gateway"] == gateway and i["ambiente"] == ambiente)

    def testar_gateway(self, gateway: str, ambiente: str) -> Dict[str, Any]:
        try:
            mensagem = self._adapter(gateway, ambiente, exigir_ativo=False).testar_conexao()
            ok = True
        except GatewayError as exc:
            mensagem, ok = exc.mensagem, False
        except HTTPException as exc:
            mensagem, ok = str(exc.detail), False
        self.repo.marcar_teste_gateway(gateway, ambiente, ok)
        return {"ok": ok, "mensagem": mensagem}

    # ------------------------------------------------------------------
    # Cobrança
    # ------------------------------------------------------------------

    def _pagador(self, polo_id: str) -> Pagador:
        polo = self.repo.get_dados_cobranca_polo(polo_id)
        if not polo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Polo do pedido não encontrado")
        faltando = [rotulo for campo, rotulo in _CAMPOS_FISCAIS_OBRIGATORIOS.items() if not polo.get(campo)]
        if faltando:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dados fiscais do Polo incompletos ({', '.join(faltando)}). "
                       "Preencha em Polos > Editar > Dados fiscais para cobrança.",
            )
        return Pagador(
            nome=polo["razao_social"],
            documento=polo["documento_fiscal"],
            email=polo.get("email_financeiro"),
            telefone=polo.get("telefone_financeiro"),
            endereco=EnderecoPagador(
                cep=polo.get("cep"), logradouro=polo.get("logradouro"), numero=polo.get("numero"),
                complemento=polo.get("complemento"), bairro=polo.get("bairro"),
                cidade=polo.get("cidade"), uf=polo.get("uf"),
            ),
            referencia=str(polo_id),
        )

    def gerar_cobranca(self, pedido_id: str, meio: str, user: UserResponse, gateway: Optional[str] = None) -> PagamentoResponse:
        pedido = self.pedidos.get_pedido(pedido_id, user)  # valida escopo (404 fora dele)
        polo_id = str(pedido.polo_id)
        return self._emitir(
            pedido, meio, gateway,
            pagador=lambda: self._pagador(polo_id),
            cliente_get=lambda g, a: self.repo.get_cliente_gateway(g, a, polo_id),
            cliente_set=lambda g, a, cid, doc: self.repo.salvar_cliente_gateway(g, a, polo_id, cid, doc),
        )

    def gerar_cobranca_aluno(self, pedido_id: str, meio: str, pagador: Pagador, aluno_id: str,
                             extras_pagamento: Optional[Dict[str, Any]] = None) -> PagamentoResponse:
        """Cobrança de um pedido do próprio aluno EAD (pagador pessoa física, sem Polo)."""
        from app.modules.financeiro.service import pedido_response

        bruto = self.repo.get_pedido(pedido_id)
        if not bruto or str(bruto.get("aluno_id")) != str(aluno_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._emitir(
            pedido_response(bruto), meio, None,
            pagador=lambda: pagador,
            cliente_get=lambda g, a: self.repo.get_cliente_gateway_aluno(g, a, aluno_id),
            cliente_set=lambda g, a, cid, doc: self.repo.salvar_cliente_gateway_aluno(g, a, aluno_id, cid, doc),
            extras_pagamento={"aluno_id": aluno_id, **(extras_pagamento or {})},
        )

    def _emitir(self, pedido, meio: str, gateway: Optional[str], pagador: Callable[[], Pagador],
                cliente_get: Callable[[str, str], Optional[Dict[str, Any]]],
                cliente_set: Callable[[str, str, str, str], None],
                extras_pagamento: Optional[Dict[str, Any]] = None) -> PagamentoResponse:
        if pedido.status != "aguardando_pagamento":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pedido não está aguardando pagamento")
        if self.repo.get_pagamento_pendente_do_pedido(pedido.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe uma cobrança pendente para este pedido. Cancele-a antes de gerar outra.",
            )
        if float(pedido.valor_total) <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pedido sem valor a cobrar")
        ambiente = settings.PAYMENT_ENV
        regra = self.repo.get_regra_pagamento(pedido.tipo, pedido.polo_id, float(pedido.valor_total)) or {}
        meios = regra.get("meios_permitidos") or ["BOLETO", "PIX"]
        if meio not in meios:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Meio '{meio}' não permitido pela regra '{regra.get('nome', 'padrão')}' ({', '.join(meios)})",
            )
        nome_gateway = gateway or self._gateway_da_regra(regra, ambiente) or self.gateway_padrao(ambiente)
        adapter = self._adapter(nome_gateway, ambiente)
        pagador = pagador()
        vencimento = hoje_brasil() + timedelta(days=int(regra.get("dias_vencimento") or DIAS_VENCIMENTO_PADRAO))
        encargos = Encargos(
            multa_pct=float(regra.get("multa_pct") or 0),
            juros_mes_pct=float(regra.get("juros_mes_pct") or 0),
            desconto_antecipado_pct=float(regra.get("desconto_antecipado_pct") or 0),
        )

        try:
            cache = cliente_get(nome_gateway, ambiente)
            usa_cache = cache and cache.get("documento_fiscal") == pagador.documento
            customer_id = adapter.obter_ou_criar_cliente(pagador, cache["customer_id"] if usa_cache else None)
            if not usa_cache:
                cliente_set(nome_gateway, ambiente, customer_id, pagador.documento)
            cobranca = adapter.criar_cobranca(
                customer_id=customer_id,
                pagador=pagador,
                valor=float(pedido.valor_total),
                vencimento=vencimento,
                meio=meio,
                descricao=f"Pedido {pedido.numero} - NEXUS 2.0",
                referencia=pedido.numero,
                notification_url=webhook_url(nome_gateway, ambiente),
                idempotency_key=f"{pedido.id}-{meio}-{int(datetime.now(timezone.utc).timestamp())}",
                encargos=encargos,
            )
        except GatewayError as exc:
            logger.warning("Falha ao gerar cobrança do pedido %s: %s", pedido.numero, exc.mensagem)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.mensagem) from exc

        pagamento_id = self.repo.create_pagamento({
            "pedido_id": pedido.id,
            "polo_id": pedido.polo_id,
            "escola_id": pedido.escola_id,
            "gateway": nome_gateway,
            "ambiente": ambiente,
            "gateway_customer_id": customer_id,
            "gateway_payment_id": cobranca.payment_id,
            "asaas_customer_id": customer_id if nome_gateway == "asaas" else None,
            "asaas_payment_id": cobranca.payment_id if nome_gateway == "asaas" else None,
            "billing_type": meio,
            "valor": cobranca.valor,
            "status": cobranca.status or "pendente",
            "parcelas": 1,
            "boleto_url": cobranca.boleto_url,
            "invoice_url": cobranca.invoice_url,
            "linha_digitavel": cobranca.linha_digitavel,
            "nosso_numero": cobranca.nosso_numero,
            "pix_copia_cola": cobranca.pix_copia_cola,
            "pix_qrcode_base64": cobranca.pix_qrcode_base64,
            "vencimento_em": cobranca.vencimento,
            "descricao": f"Pedido {pedido.numero}",
            **(extras_pagamento or {}),
        })
        return PagamentoResponse(**self.repo.get_pagamento(pagamento_id))

    def get_pagamento(self, pagamento_id: str, user: UserResponse) -> PagamentoResponse:
        pg = self.repo.get_pagamento(pagamento_id)
        escopo = escopo_do_usuario(user)
        if not pg or (escopo.polo_id and pg.get("polo_id") != escopo.polo_id) or (
            escopo.escola_id and pg.get("escola_id") != escopo.escola_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
        return PagamentoResponse(**pg)

    def cancelar_pagamento(self, pagamento_id: str, user: UserResponse) -> PagamentoResponse:
        pg = self.repo.get_pagamento(pagamento_id)
        if not pg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
        if pg.get("status") not in ("pendente", "vencido"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Só cobranças pendentes ou vencidas podem ser canceladas")
        if pg.get("gateway") in factory.ADAPTERS and pg.get("gateway_payment_id") and pg.get("ambiente"):
            try:
                self._adapter(pg["gateway"], pg["ambiente"], exigir_ativo=False).cancelar(pg["gateway_payment_id"])
            except GatewayError as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.mensagem) from exc
        self.repo.update_pagamento(pagamento_id, {"status": "cancelado", "cancelado_em": datetime.now(timezone.utc)})
        return PagamentoResponse(**self.repo.get_pagamento(pagamento_id))

    # ------------------------------------------------------------------
    # Status (webhook e cron)
    # ------------------------------------------------------------------

    def aplicar_status(self, pagamento: Dict[str, Any], novo: Optional[str], origem: str,
                       valor_pago: Optional[float] = None, pago_em: Optional[datetime] = None) -> bool:
        """Aplica o status normalizado ao pagamento e, se pago, conclui o pedido. True se mudou algo.

        Um novo aviso de "pago" para um pagamento que já está pago refaz só o que faltou no pedido:
        se o crédito de licenças falhou na primeira vez, o reprocessamento completa sem duplicar.
        """
        alvo = proximo_status(pagamento.get("status"), novo)
        if not alvo:
            if novo == "pago" and pagamento.get("status") == "pago":
                return self.concluir_pagamento(pagamento, origem)
            return False
        campos: Dict[str, Any] = {"status": alvo}
        if alvo == "pago":
            campos["pago_em"] = pago_em or datetime.now(timezone.utc)
            if valor_pago is not None:
                campos["valor_liquido"] = valor_pago
        if alvo == "cancelado":
            campos["cancelado_em"] = datetime.now(timezone.utc)
        self.repo.update_pagamento(pagamento["id"], campos)

        if alvo == "pago":
            self.concluir_pagamento({**pagamento, **campos}, origem)
        elif alvo == "estornado" and pagamento.get("pedido_id"):
            pedido = self.repo.get_pedido(pagamento["pedido_id"])
            if pedido and pedido["status"] != "cancelado":
                logger.warning("Pagamento estornado no pedido %s (status %s)", pedido.get("numero"), pedido["status"])
        return True

    def concluir_pagamento(self, pagamento: Dict[str, Any], origem: str) -> bool:
        """Efeitos de um pagamento confirmado no pedido. Idempotente: True se fez algo agora.

        Avança o pedido (se ainda aguarda pagamento), credita as licenças (licença/kit) e libera a
        disciplina do aluno EAD. Cada etapa só age se ainda não foi feita, então pode ser repetida
        pelo reprocessamento do webhook e pelo cron até tudo concluir.
        """
        pedido_id = pagamento.get("pedido_id")
        pedido = self.repo.get_pedido(pedido_id) if pedido_id else None
        if not pedido or pedido["status"] == "cancelado":  # cancelado antes de o pagamento chegar
            return False
        fez = False
        if pedido["status"] == "aguardando_pagamento":
            self.pedidos.alterar_status(
                pedido_id, regras.status_pos_pagamento(pedido["tipo"]), None, origem=origem,
                observacao=f"Pagamento confirmado ({pagamento.get('gateway')} {pagamento.get('billing_type') or ''})".strip(),
                campos={"pago_em": pagamento.get("pago_em") or datetime.now(timezone.utc)},
            )
            fez = True
        if regras.credita_licenca(pedido["tipo"]):  # licença avulsa ou kit (livro + licença)
            fez = bool(self.creditar_licencas(pedido, None)) or fez
        if regras.eh_ead(pedido["tipo"]):  # aluno EAD: libera a disciplina no AVA
            from app.modules.ead_vendas.repository import get_vendas_ead_repository

            liberadas = get_vendas_ead_repository().liberar_compra_do_pedido(
                str(pedido_id), pagamento["id"], pagamento.get("valor"))
            fez = bool(liberadas) or fez
        return fez

    def processar_webhook(self, gateway: str, ambiente: str, headers: Mapping[str, str], corpo: bytes,
                          query: Mapping[str, str]) -> Dict[str, Any]:
        if ambiente not in ("sandbox", "producao"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ambiente inválido")
        try:
            adapter = self._adapter(gateway, ambiente)
        except HTTPException as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook não configurado") from exc
        if not adapter.validar_webhook(headers, corpo, query):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura/token do webhook inválido")
        try:
            evento = adapter.interpretar_webhook(headers, corpo, query)
        except Exception as exc:  # noqa: BLE001 - payload inesperado vira 400 sem derrubar a fila
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Webhook ilegível: {exc}") from exc
        try:
            payload = json.loads(corpo or b"{}")
        except ValueError:
            payload = {"raw": corpo.decode("utf-8", "replace")[:5000]}
        webhook_id = self.repo.registrar_webhook(
            gateway, ambiente, evento.evento_id, evento.tipo_evento, evento.payment_id, payload
        )
        if webhook_id is None:
            return {"status": "duplicado", "evento_id": evento.evento_id}
        return self._processar_evento(webhook_id, gateway, evento.payment_id, evento.status,
                                      evento.valor_pago, evento.pago_em, origem="webhook")

    def _processar_evento(self, webhook_id: str, gateway: str, payment_id: Optional[str], novo: Optional[str],
                          valor_pago: Optional[float], pago_em: Optional[datetime], origem: str) -> Dict[str, Any]:
        try:
            pagamento = self.repo.get_pagamento_por_gateway_id(gateway, payment_id) if payment_id else None
            if not pagamento:
                self.repo.finalizar_webhook(webhook_id, "ignorado", "Pagamento não encontrado no NEXUS")
                return {"status": "ignorado"}
            mudou = self.aplicar_status(pagamento, novo, origem, valor_pago, pago_em)
            self.repo.finalizar_webhook(webhook_id, "processado", None if mudou else "Sem mudança de status")
            return {"status": "processado", "alterado": mudou}
        except Exception as exc:  # noqa: BLE001 - devolve 200; o cron reprocessa
            logger.exception("Erro ao processar webhook %s", webhook_id)
            self.repo.finalizar_webhook(webhook_id, "erro", f"{exc.__class__.__name__}: {exc}")
            return {"status": "erro"}

    def simular(self, pagamento_id: str, novo: str, user: UserResponse) -> Dict[str, Any]:
        """Simulador (sandbox): confirma/vence/cancela uma cobrança pelo mesmo caminho do webhook."""
        pg = self.repo.get_pagamento(pagamento_id)
        if not pg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
        if pg.get("gateway") != "fake" or pg.get("ambiente") != "sandbox" or not pg.get("gateway_payment_id"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Só cobranças do Simulador (sandbox) podem ser simuladas",
            )
        from app.modules.financeiro.gateways import fake as fake_gateway

        payment_id = pg["gateway_payment_id"]
        fake_gateway.FakeGateway.simular_status(payment_id, novo)
        evento_id = f"sim:{payment_id}:{novo}:{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        payload = {"id": evento_id, "payment_id": payment_id, "status": novo, "tipo": "SIMULADO",
                   "simulado_por": user.id}
        webhook_id = self.repo.registrar_webhook("fake", "sandbox", evento_id, "SIMULADO", payment_id, payload)
        if webhook_id is None:
            return {"status": "duplicado", "evento_id": evento_id}
        resultado = self._processar_evento(webhook_id, "fake", payment_id, novo, None, None, origem="webhook")
        return {**resultado, "pagamento": PagamentoResponse(**self.repo.get_pagamento(pagamento_id))}

    def reconciliar(self, limite: int = 50) -> Dict[str, int]:
        resumo = {"webhooks_reprocessados": 0, "pagamentos_consultados": 0, "pagamentos_alterados": 0,
                  "pendencias_concluidas": 0, "falhas": 0}
        # Pagamentos já pagos cujo pedido ficou incompleto (ex.: o crédito de licenças falhou).
        for pg in self.repo.list_pagamentos_pagos_pendentes(limite):
            try:
                if self.concluir_pagamento(pg, "cron"):
                    resumo["pendencias_concluidas"] += 1
            except Exception:  # noqa: BLE001
                logger.exception("Conclusão do pagamento %s falhou", pg.get("id"))
                resumo["falhas"] += 1
        for w in self.repo.list_webhooks_com_erro(MAX_TENTATIVAS_WEBHOOK, limite):
            try:
                adapter = self._adapter(w["gateway"], w["ambiente"], exigir_ativo=False)
                corpo = json.dumps(w.get("payload") or {}).encode()
                evento = adapter.interpretar_webhook({}, corpo, {})
            except Exception:  # noqa: BLE001
                self.repo.finalizar_webhook(w["id"], "erro", "Reprocessamento: payload ilegível")
                resumo["falhas"] += 1
                continue
            self._processar_evento(w["id"], w["gateway"], evento.payment_id, evento.status,
                                   evento.valor_pago, evento.pago_em, origem="cron")
            resumo["webhooks_reprocessados"] += 1
        for pg in self.repo.list_pagamentos_para_reconciliar(limite):
            resumo["pagamentos_consultados"] += 1
            try:
                adapter = self._adapter(pg["gateway"], pg["ambiente"], exigir_ativo=False)
                novo, _raw = adapter.consultar(pg["gateway_payment_id"])
                if self.aplicar_status(pg, novo, "cron"):
                    resumo["pagamentos_alterados"] += 1
            except Exception:  # noqa: BLE001
                logger.exception("Reconciliação falhou para pagamento %s", pg.get("id"))
                resumo["falhas"] += 1
        return resumo

    def listar_webhooks(self, gateway: Optional[str], status_filtro: Optional[str], limit: int, offset: int,
                        payment_id: Optional[str] = None) -> Dict[str, Any]:
        total, items = self.repo.list_webhooks(gateway, status_filtro, limit, offset, payment_id)
        return {"total": total, "items": items, "limit": limit, "offset": offset}
