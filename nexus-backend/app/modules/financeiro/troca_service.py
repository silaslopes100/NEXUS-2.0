"""Troca de licença/livro solicitada pelo Polo ou pela Escola (migração 026).

Fluxo:
- solicitar: cria um pedido tipo "troca" em 'troca_solicitada', RESERVA as licenças a devolver
  (saem do saldo da unidade) e notifica os admins.
- efetuar (Admin): status 'troca', credita as licenças novas na unidade e movimenta o Estoque Central
  (livro devolvido entra, livro novo sai).
- recusar (Admin): status 'cancelado' com motivo e devolve as licenças reservadas.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.schemas import UserResponse
from app.modules.financeiro import pedidos as regras
from app.modules.financeiro.repository import FinanceiroRepositoryInterface
from app.modules.financeiro.schemas import PedidoResponse, TrocaCreate
from app.modules.financeiro.service import FinanceiroService, escopo_do_usuario, pedido_response

logger = logging.getLogger(__name__)

MOTIVO_LABEL = {
    "disciplina_errada": "Disciplina comprada errada",
    "mudanca_turma": "Mudança de turma ou grade",
    "livro_defeito": "Livro com defeito",
    "outro": "Outro",
}


def _licencas_repo_padrao():
    from app.modules.polos_escolas.repository import get_polos_escolas_repository

    return get_polos_escolas_repository()


def _notificar_padrao(**kwargs: Any) -> None:
    from app.modules.notificacoes import notificar

    notificar(**kwargs)


def _notificar_admins_padrao(**kwargs: Any) -> None:
    from app.modules.notificacoes import notificar_perfil

    notificar_perfil("admin", **kwargs)


class TrocaService:
    def __init__(
        self,
        repo: FinanceiroRepositoryInterface,
        licencas_repo: Any = None,
        notificar: Callable[..., None] = _notificar_padrao,
        notificar_admins: Callable[..., None] = _notificar_admins_padrao,
    ) -> None:
        self.repo = repo
        self.pedidos = FinanceiroService(repo)
        self._licencas_repo = licencas_repo
        self.notificar = notificar
        self.notificar_admins = notificar_admins

    @property
    def licencas(self) -> Any:
        if self._licencas_repo is None:
            self._licencas_repo = _licencas_repo_padrao()
        return self._licencas_repo

    # ------------------------------------------------------------------
    # Apoio
    # ------------------------------------------------------------------

    @staticmethod
    def _unidade(user: UserResponse) -> tuple[str, Optional[str]]:
        """Polo usa o próprio Polo; Escola usa a própria Escola (e o Polo dela)."""
        escopo = escopo_do_usuario(user)
        if escopo.escola_id:
            if not user.polo_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Escola sem Polo vinculado")
            return str(user.polo_id), str(escopo.escola_id)
        if escopo.polo_id:
            return str(escopo.polo_id), None
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Somente Polo ou Escola solicitam troca de licença")

    def _saldo(self, polo_id: str, escola_id: Optional[str], disciplina_id: str) -> int:
        estoque = self.licencas.get_estoque(polo_id=None if escola_id else polo_id, escola_id=escola_id,
                                            materia_id=disciplina_id)
        return int(estoque["quantidade_disponivel"])

    def _mover_licencas(self, pedido: Dict[str, Any], disciplina_id: str, delta: int, tipo_mov: str,
                        status_mov: str, usuario_id: Optional[str], observacao: str) -> None:
        escola_id = pedido.get("escola_id")
        polo_id = pedido.get("polo_id")
        self.licencas.ajustar_estoque(polo_id=None if escola_id else polo_id, escola_id=escola_id,
                                      delta_disponivel=delta, materia_id=disciplina_id)
        self.licencas.registrar_movimentacao({
            "tipo": tipo_mov,
            "polo_id": polo_id,
            "escola_id": escola_id,
            "materia_id": disciplina_id,
            "quantidade": abs(delta),
            "valor_unitario": 0,
            "status": status_mov,
            "actor_id": usuario_id,
            "observacao": observacao,
        })

    def _get_troca(self, pedido_id: str, status_esperado: str = "troca_solicitada") -> Dict[str, Any]:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido or not regras.eh_troca(pedido.get("tipo")):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Troca não encontrada")
        if pedido.get("status") != status_esperado:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Esta troca já foi concluída ou recusada")
        return pedido

    def _notificar_unidade(self, pedido: Dict[str, Any], titulo: str, mensagem: Optional[str]) -> None:
        destino = ({"destino_escola_id": pedido["escola_id"]} if pedido.get("escola_id")
                   else {"destino_polo_id": pedido.get("polo_id")})
        base = "/escola/livros" if pedido.get("escola_id") else "/polo/livros"
        self.notificar(titulo=titulo, mensagem=mensagem, link=base, **destino)

    # ------------------------------------------------------------------
    # Fluxo
    # ------------------------------------------------------------------

    def solicitar(self, payload: TrocaCreate, user: UserResponse) -> PedidoResponse:
        polo_id, escola_id = self._unidade(user)

        ids = {i.disciplina_devolver_id for i in payload.itens} | {i.disciplina_receber_id for i in payload.itens}
        disciplinas = self.repo.get_disciplinas(list(ids))
        faltando = [i for i in ids if i not in disciplinas]
        if faltando:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Disciplina não encontrada")
        for item in payload.itens:
            if not disciplinas[item.disciplina_receber_id].get("ativo", True):
                nome = disciplinas[item.disciplina_receber_id].get("nome")
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"'{nome}' está inativa e não pode ser recebida na troca")

        # Saldo: a soma a devolver por disciplina precisa caber no disponível da unidade.
        a_devolver: Dict[str, int] = {}
        for item in payload.itens:
            a_devolver[item.disciplina_devolver_id] = a_devolver.get(item.disciplina_devolver_id, 0) + item.quantidade
        for disciplina_id, qtd in a_devolver.items():
            saldo = self._saldo(polo_id, escola_id, disciplina_id)
            if qtd > saldo:
                nome = disciplinas[disciplina_id].get("nome")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Saldo insuficiente de '{nome}': disponível {saldo}, solicitado {qtd}")

        endereco = self.pedidos._endereco(SimpleNamespace(endereco=payload.endereco, tipo="troca"), polo_id)
        itens = [{
            "produto_id": None,
            "disciplina_id": item.disciplina_receber_id,
            "descricao": f"{disciplinas[item.disciplina_receber_id].get('nome')} (troca)",
            "quantidade": item.quantidade,
            "valor_unitario": 0,
            "valor_total": 0,
        } for item in payload.itens]
        troca_itens = [item.model_dump() for item in payload.itens]
        dados = {
            "tipo": "troca",
            "polo_id": polo_id,
            "escola_id": escola_id,
            "solicitante_id": user.id,
            "status": "troca_solicitada",
            "valor_bruto": 0,
            "desconto": 0,
            "valor_total": 0,
            "troca_motivo": payload.motivo,
            "troca_descricao": (payload.descricao or "").strip() or None,
            **endereco,
        }
        pedido_id = self.repo.create_pedido(dados, itens, user.id, troca_itens=troca_itens)
        pedido = self.repo.get_pedido(pedido_id)

        # Reserva: as licenças a devolver saem do saldo agora (voltam se a troca for recusada).
        for disciplina_id, qtd in a_devolver.items():
            self._mover_licencas(pedido, disciplina_id, -qtd, "troca_reserva", "em_troca", user.id,
                                 f"Reservada para a troca {pedido['numero']}")

        unidade = pedido.get("escola_nome") or pedido.get("polo_nome") or "Unidade"
        resumo = "; ".join(
            f"{disciplinas[i.disciplina_devolver_id].get('nome')} → {disciplinas[i.disciplina_receber_id].get('nome')}"
            f" ({i.quantidade})" for i in payload.itens
        )
        self.notificar_admins(
            titulo=f"Troca de livro solicitada: {pedido['numero']}",
            mensagem=f"{unidade} · {MOTIVO_LABEL.get(payload.motivo, payload.motivo)} · {resumo}",
            link=f"/admin/logistica/pendentes?pedido={pedido_id}",
        )
        return pedido_response(self.repo.get_pedido(pedido_id))

    def efetuar(self, pedido_id: str, user: UserResponse) -> PedidoResponse:
        pedido = self._get_troca(pedido_id)
        # Status primeiro: se dois admins clicarem juntos, só um passa (o outro recebe 409).
        self.pedidos.alterar_status(pedido["id"], "troca", user.id, observacao="Troca efetuada")
        linhas: List[Dict[str, Any]] = pedido.get("troca_itens") or []
        a_receber: Dict[str, int] = {}
        for linha in linhas:
            disciplina_id = str(linha["disciplina_receber_id"])
            a_receber[disciplina_id] = a_receber.get(disciplina_id, 0) + int(linha["quantidade"])
        status_mov = "disponivel_escola" if pedido.get("escola_id") else "disponivel_polo"
        for disciplina_id, qtd in a_receber.items():
            self._mover_licencas(pedido, disciplina_id, qtd, "troca_recebimento", status_mov, user.id,
                                 f"Recebida na troca {pedido['numero']}")
        try:
            self.repo.movimentar_estoque_troca(pedido["id"], linhas, user.id, f"Troca {pedido['numero']}")
        except Exception:  # noqa: BLE001 — Estoque Central não desfaz a troca; o admin ajusta depois
            logger.exception("Falha ao movimentar o Estoque Central da troca %s", pedido["id"])
        self._notificar_unidade(pedido, f"Troca {pedido['numero']} efetuada",
                                "As licenças novas já estão no seu saldo.")
        return pedido_response(self.repo.get_pedido(pedido["id"]))

    def recusar(self, pedido_id: str, motivo: str, user: UserResponse) -> PedidoResponse:
        pedido = self._get_troca(pedido_id)
        self.pedidos.alterar_status(pedido["id"], "cancelado", user.id, observacao="Troca recusada",
                                    campos={"motivo_cancelamento": motivo.strip()})
        a_devolver: Dict[str, int] = {}
        for linha in pedido.get("troca_itens") or []:
            disciplina_id = str(linha["disciplina_devolver_id"])
            a_devolver[disciplina_id] = a_devolver.get(disciplina_id, 0) + int(linha["quantidade"])
        status_mov = "disponivel_escola" if pedido.get("escola_id") else "disponivel_polo"
        for disciplina_id, qtd in a_devolver.items():
            self._mover_licencas(pedido, disciplina_id, qtd, "troca_estorno", status_mov, user.id,
                                 f"Troca {pedido['numero']} recusada: licença devolvida ao saldo")
        self._notificar_unidade(pedido, f"Troca {pedido['numero']} recusada", f"Motivo: {motivo.strip()}")
        return pedido_response(self.repo.get_pedido(pedido["id"]))
