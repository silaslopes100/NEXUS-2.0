"""Regras de negócio do núcleo Financeiro & Logística (pedidos, produtos, pagamentos)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.dependencies import PERFIS_ESCOPO_GLOBAL
from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.financeiro import pedidos as regras
from app.modules.financeiro.repository import Escopo, FinanceiroRepositoryInterface
from app.modules.financeiro.schemas import (
    EnderecoEntrega,
    FiltrosPeriodo,
    PagamentoListResponse,
    PagamentoResponse,
    PedidoCreate,
    PedidoListResponse,
    PedidoResponse,
    ProdutoCreate,
    ProdutoListResponse,
    ProdutoResponse,
    ProdutoUpdate,
)

_CAMPOS_ENDERECO = ("nome", "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "telefone")
_ENDERECO_OBRIGATORIO_LIVRO = ("cep", "logradouro", "cidade", "uf")


def escopo_do_usuario(user: UserResponse) -> Escopo:
    """Escopo de visibilidade: global, do Polo ou da Escola."""
    perfil = perfil_do_usuario(user)
    if perfil in PERFIS_ESCOPO_GLOBAL:
        return Escopo()
    if perfil == "polo":
        if not user.polo_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário Polo sem vínculo.")
        return Escopo(polo_id=str(user.polo_id))
    if perfil == "escola":
        if not user.escola_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário Escola sem vínculo.")
        return Escopo(escola_id=str(user.escola_id))
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado.")


def _no_escopo(registro: Dict[str, Any], escopo: Escopo) -> bool:
    if escopo.polo_id and str(registro.get("polo_id")) != escopo.polo_id:
        return False
    if escopo.escola_id and str(registro.get("escola_id")) != escopo.escola_id:
        return False
    return True


def pedido_response(p: Dict[str, Any]) -> PedidoResponse:
    endereco = EnderecoEntrega(**{c: p.get(f"entrega_{c}") for c in _CAMPOS_ENDERECO})
    dados = {k: v for k, v in p.items() if not k.startswith("entrega_")}
    for campo in ("itens", "historico", "envios"):
        dados[campo] = dados.get(campo) or []
    return PedidoResponse(**dados, endereco=endereco)


class FinanceiroService:
    def __init__(self, repo: FinanceiroRepositoryInterface) -> None:
        self.repo = repo

    # ------------------------------------------------------------------
    # Produtos
    # ------------------------------------------------------------------

    def list_produtos(self, tipo: Optional[str] = None, ativo: Optional[bool] = True) -> ProdutoListResponse:
        items = self.repo.list_produtos(tipo=tipo, ativo=ativo)
        return ProdutoListResponse(total=len(items), items=[ProdutoResponse(**p) for p in items])

    def create_produto(self, payload: ProdutoCreate) -> ProdutoResponse:
        dados = payload.model_dump()
        dados["sku"] = dados["sku"].strip().upper()
        return ProdutoResponse(**self.repo.create_produto(dados))

    def update_produto(self, produto_id: str, payload: ProdutoUpdate) -> ProdutoResponse:
        atualizado = self.repo.update_produto(produto_id, payload.model_dump(exclude_unset=True))
        if not atualizado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
        return ProdutoResponse(**atualizado)

    # ------------------------------------------------------------------
    # Pedidos
    # ------------------------------------------------------------------

    def _resolver_unidade(self, payload: PedidoCreate, user: UserResponse) -> tuple[str, Optional[str]]:
        escopo = escopo_do_usuario(user)
        if escopo.escola_id:
            polo_id, escola_id = user.polo_id, escopo.escola_id
            if payload.escola_id and payload.escola_id != escopo.escola_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Escola fora do seu escopo")
        elif escopo.polo_id:
            if payload.polo_id and payload.polo_id != escopo.polo_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Polo fora do seu escopo")
            polo_id, escola_id = escopo.polo_id, payload.escola_id
        else:
            polo_id, escola_id = payload.polo_id, payload.escola_id
        if not polo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o Polo do pedido")
        return str(polo_id), (str(escola_id) if escola_id else None)

    def _montar_itens(self, payload: PedidoCreate) -> List[Dict[str, Any]]:
        quantidades: Dict[str, int] = {}
        for item in payload.itens:
            quantidades[item.produto_id] = quantidades.get(item.produto_id, 0) + item.quantidade
        produtos = self.repo.get_produtos_por_ids(list(quantidades))
        itens: List[Dict[str, Any]] = []
        for produto_id, qtd in quantidades.items():
            produto = produtos.get(produto_id)
            if not produto or not produto.get("ativo"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Produto {produto_id} inexistente ou inativo",
                )
            if produto["tipo"] != payload.tipo:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Produto '{produto['nome']}' não é do tipo '{payload.tipo}'",
                )
            # Preço sempre do catálogo, nunca do cliente.
            unitario = regras.arredondar(produto["preco"])
            itens.append({
                "produto_id": produto_id,
                "disciplina_id": produto.get("disciplina_id"),
                "descricao": produto["nome"],
                "quantidade": qtd,
                "valor_unitario": unitario,
                "valor_total": regras.arredondar(unitario * qtd),
            })
        return itens

    def _endereco(self, payload: PedidoCreate, polo_id: str) -> Dict[str, Any]:
        if payload.endereco:
            base = payload.endereco.model_dump()
        else:
            base = self.repo.get_endereco_polo(polo_id) or {}
        endereco = {f"entrega_{c}": base.get(c) for c in _CAMPOS_ENDERECO}
        if payload.tipo == "livro":
            faltando = [c for c in _ENDERECO_OBRIGATORIO_LIVRO if not endereco.get(f"entrega_{c}")]
            if faltando:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Endereço de entrega incompleto: {', '.join(faltando)}",
                )
        return endereco

    def criar_pedido(self, payload: PedidoCreate, user: UserResponse) -> PedidoResponse:
        """Cria o pedido em 'aguardando_pagamento'. A cobrança é gerada na Fase 3 (checkout)."""
        polo_id, escola_id = self._resolver_unidade(payload, user)
        itens = self._montar_itens(payload)
        bruto, desconto, total = regras.calcular_totais(
            [(i["valor_unitario"], i["quantidade"]) for i in itens]
        )
        dados = {
            "tipo": payload.tipo,
            "polo_id": polo_id,
            "escola_id": escola_id,
            "solicitante_id": user.id,
            "status": "aguardando_pagamento",
            "valor_bruto": bruto,
            "desconto": desconto,
            "valor_total": total,
            "observacao": payload.observacao,
            **self._endereco(payload, polo_id),
        }
        pedido_id = self.repo.create_pedido(dados, itens, user.id)
        return pedido_response(self.repo.get_pedido(pedido_id))

    def alterar_status(
        self,
        pedido_id: str,
        para: str,
        usuario_id: Optional[str],
        origem: str = "usuario",
        observacao: Optional[str] = None,
        campos: Optional[Dict[str, Any]] = None,
    ) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        de = pedido["status"]
        regras.validar_transicao_para_tipo(pedido["tipo"], de, para)
        extras = dict(campos or {})
        coluna_ts = regras.TIMESTAMP_DO_STATUS.get(para)
        if coluna_ts and not extras.get(coluna_ts):
            extras[coluna_ts] = datetime.now(timezone.utc)
        self.repo.alterar_status_pedido(pedido_id, de, para, usuario_id, origem, observacao, extras)
        return pedido_response(self.repo.get_pedido(pedido_id))

    def get_pedido(self, pedido_id: str, user: UserResponse) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido or not _no_escopo(pedido, escopo_do_usuario(user)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return pedido_response(pedido)

    def list_pedidos(self, filtros: FiltrosPeriodo, user: UserResponse) -> PedidoListResponse:
        total, items = self.repo.list_pedidos(filtros, escopo_do_usuario(user))
        return PedidoListResponse(
            total=total, items=[pedido_response(p) for p in items],
            limit=filtros.limit, offset=filtros.offset,
        )

    # ------------------------------------------------------------------
    # Pagamentos
    # ------------------------------------------------------------------

    def list_pagamentos(self, filtros: FiltrosPeriodo, user: UserResponse) -> PagamentoListResponse:
        total, items = self.repo.list_pagamentos(filtros, escopo_do_usuario(user))
        return PagamentoListResponse(
            total=total, items=[PagamentoResponse(**p) for p in items],
            limit=filtros.limit, offset=filtros.offset,
        )
