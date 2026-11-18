"""Escola pede licenças/livros ao Polo → Polo atende (transfere as licenças) e emite a
Nota de Prestação de Contas → Escola repassa o valor → Polo confirma o repasse.

Os livros físicos são entregues pelo Polo fora do sistema; aqui só ficam registrados na Nota.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.modules.notificacoes import notificar
from app.modules.polos_escolas import licencas as lic
from app.modules.polos_escolas.repository import PolosEscolasRepositoryInterface
from app.modules.polos_escolas.schemas import LicencaDistribuirRequest
from app.modules.solicitacoes.repository import SolicitacoesRepositoryInterface

DIAS_VENCIMENTO = 10
STATUS = ("pendente", "atendida", "atendida_parcial", "recusada")


# --- Schemas ----------------------------------------------------------------

class ItemSolicitacaoIn(BaseModel):
    disciplina_id: str
    quantidade: int = Field(gt=0, le=10_000)


class SolicitacaoCriar(BaseModel):
    itens: List[ItemSolicitacaoIn] = Field(min_length=1, max_length=200)
    observacao: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("itens")
    @classmethod
    def _sem_repetir(cls, itens: List[ItemSolicitacaoIn]) -> List[ItemSolicitacaoIn]:
        if len({i.disciplina_id for i in itens}) != len(itens):
            raise ValueError("Cada disciplina deve aparecer uma vez na solicitação")
        return itens


class ItemAtender(BaseModel):
    item_id: str
    quantidade_atendida: int = Field(ge=0)


class SolicitacaoAtender(BaseModel):
    itens: List[ItemAtender] = Field(min_length=1)


class SolicitacaoRecusar(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)


class ItemOut(BaseModel):
    id: str
    disciplina_id: str
    disciplina_nome: Optional[str] = None
    quantidade: int
    quantidade_atendida: int = 0
    valor_unitario: float = 0
    saldo_polo: Optional[int] = None  # preenchido para o Polo decidir quanto atender


class SolicitacaoOut(BaseModel):
    id: str
    numero: str
    escola_id: str
    escola_nome: Optional[str] = None
    polo_id: str
    polo_nome: Optional[str] = None
    status: str
    observacao: Optional[str] = None
    motivo_recusa: Optional[str] = None
    criado_em: Optional[datetime] = None
    resolvido_em: Optional[datetime] = None
    itens: List[ItemOut] = Field(default_factory=list)
    valor_estimado: float = 0
    nota_id: Optional[str] = None
    nota_numero: Optional[str] = None
    nota_status: Optional[str] = None
    nota_valor_total: Optional[float] = None
    nota_vencimento: Optional[date] = None
    nota_repasse_em: Optional[datetime] = None


def _hoje() -> date:
    from app.modules.financeiro.cobranca_service import hoje_brasil

    return hoje_brasil()


def _saida(s: Dict[str, Any], saldos: Optional[Dict[str, int]] = None) -> SolicitacaoOut:
    itens = [ItemOut(**{**i, "saldo_polo": (saldos or {}).get(i["disciplina_id"])}) for i in s.get("itens", [])]
    valor = sum(i.quantidade * i.valor_unitario for i in itens)
    return SolicitacaoOut(**{**s, "itens": itens, "valor_estimado": round(valor, 2)})


class SolicitacoesService:
    def __init__(self, repo: SolicitacoesRepositoryInterface, polos: PolosEscolasRepositoryInterface,
                 notificar_fn: Callable[..., Any] = notificar) -> None:
        self.repo = repo
        self.polos = polos
        self.notificar = notificar_fn

    # --- consulta -----------------------------------------------------------
    def _obter(self, solicitacao_id: str) -> Dict[str, Any]:
        s = self.repo.get(solicitacao_id)
        if not s:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")
        return s

    def checar_escopo(self, solicitacao_id: str, user: Any) -> Dict[str, Any]:
        from app.modules.auth.roles import perfil_do_usuario

        s = self._obter(solicitacao_id)
        perfil = perfil_do_usuario(user)
        if perfil == "polo" and str(s["polo_id"]) != str(user.polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")
        if perfil == "escola" and str(s["escola_id"]) != str(user.escola_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")
        if perfil not in ("admin", "secretario_geral", "polo", "escola"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Perfil não autorizado")
        return s

    def _saldos(self, polo_id: str, disciplinas: List[str]) -> Dict[str, int]:
        return {d: lic._saldo(self.polos, polo_id=polo_id, disciplina_id=d) for d in set(disciplinas)}

    def listar_escola(self, escola_id: str) -> List[SolicitacaoOut]:
        return [_saida(s) for s in self.repo.listar(escola_id=escola_id)]

    def listar_polo(self, polo_id: str, status_filtro: Optional[str] = None) -> List[SolicitacaoOut]:
        if status_filtro and status_filtro not in STATUS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Status inválido")
        linhas = self.repo.listar(polo_id=polo_id, status=status_filtro)
        pendentes = [i["disciplina_id"] for s in linhas if s["status"] == "pendente" for i in s.get("itens", [])]
        saldos = self._saldos(polo_id, pendentes)
        return [_saida(s, saldos if s["status"] == "pendente" else None) for s in linhas]

    def detalhe(self, s: Dict[str, Any]) -> SolicitacaoOut:
        saldos = self._saldos(s["polo_id"], [i["disciplina_id"] for i in s["itens"]]) if s["status"] == "pendente" else None
        return _saida(s, saldos)

    # --- escola -------------------------------------------------------------
    def criar(self, escola_id: str, dados: SolicitacaoCriar, actor_id: Optional[str], ip: Optional[str]) -> SolicitacaoOut:
        escola = self.polos.get_escola(escola_id)
        if not escola:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Escola não encontrada")
        if not escola.get("polo_id"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Escola sem Polo vinculado")
        disciplinas = self.repo.disciplinas([i.disciplina_id for i in dados.itens])
        faltando = [i.disciplina_id for i in dados.itens if i.disciplina_id not in disciplinas]
        if faltando:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Disciplina não encontrada na solicitação")
        fora = [d["nome"] for d in disciplinas.values()
                if not d.get("ativo", True) or not float(d.get("preco") or 0) > 0]
        if fora:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                detail=f"Disciplina sem preço ou inativa: {', '.join(sorted(fora))}")
        itens = [{"disciplina_id": i.disciplina_id, "quantidade": i.quantidade,
                  "valor_unitario": float(disciplinas[i.disciplina_id].get("preco") or 0)} for i in dados.itens]
        polo_id = str(escola["polo_id"])
        sid = self.repo.criar({"escola_id": str(escola_id), "polo_id": polo_id, "solicitante_id": actor_id,
                               "observacao": (dados.observacao or "").strip() or None}, itens)
        s = self._obter(sid)
        total = sum(i["quantidade"] for i in itens)
        self.notificar(
            titulo=f"Nova solicitação {s['numero']}",
            mensagem=f"{escola.get('nome') or 'Uma escola'} pediu {total} licença(s)/livro(s) em {len(itens)} disciplina(s).",
            link="/polo/solicitacoes", destino_polo_id=polo_id,
        )
        self._auditar(actor_id, "solicitacao_criada", sid, {"escola_id": escola_id, "itens": itens}, ip)
        return _saida(s)

    # --- polo ---------------------------------------------------------------
    def atender(self, polo_id: str, solicitacao_id: str, dados: SolicitacaoAtender, actor_id: Optional[str],
                ip: Optional[str]) -> SolicitacaoOut:
        s = self._obter(solicitacao_id)
        if str(s["polo_id"]) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada neste Polo")
        if s["status"] != "pendente":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta solicitação já foi resolvida")
        por_id = {i["id"]: i for i in s["itens"]}
        atendidos: Dict[str, int] = {i["id"]: 0 for i in s["itens"]}
        for item in dados.itens:
            original = por_id.get(item.item_id)
            if not original:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Item não pertence a esta solicitação")
            if item.quantidade_atendida > original["quantidade"]:
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    detail=f"{original.get('disciplina_nome') or 'Item'}: atende no máximo o que foi pedido")
            atendidos[item.item_id] = item.quantidade_atendida
        if not any(atendidos.values()):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Nada a atender. Para negar o pedido, use Recusar.")
        saldos = self._saldos(polo_id, [i["disciplina_id"] for i in s["itens"]])
        for item_id, qtd in atendidos.items():
            d = por_id[item_id]["disciplina_id"]
            if qtd > saldos.get(d, 0):
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    detail=f"Saldo insuficiente no Polo em {por_id[item_id].get('disciplina_nome') or 'disciplina'} "
                                           f"(disponível: {saldos.get(d, 0)})")
        completo = all(atendidos[i["id"]] == i["quantidade"] for i in s["itens"])
        novo_status = "atendida" if completo else "atendida_parcial"
        if not self.repo.resolver(solicitacao_id, status=novo_status, resolvido_por=actor_id, atendidos=atendidos):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta solicitação já foi resolvida")

        for item_id, qtd in atendidos.items():
            if qtd:
                lic.distribuir_para_escola(
                    self.polos, polo_id,
                    LicencaDistribuirRequest(escola_id=s["escola_id"], quantidade=qtd,
                                             disciplina_id=por_id[item_id]["disciplina_id"]),
                    actor_id,
                )
        valor = round(sum(qtd * float(por_id[i]["valor_unitario"] or 0) for i, qtd in atendidos.items()), 2)
        nota_id = self.repo.criar_nota({
            "solicitacao_id": solicitacao_id, "polo_id": polo_id, "escola_id": s["escola_id"], "valor_total": valor,
            "vencimento": _hoje() + timedelta(days=DIAS_VENCIMENTO), "emitida_por": actor_id,
        })
        final = self._obter(solicitacao_id)
        self.notificar(
            titulo=f"Solicitação {s['numero']} {'atendida' if completo else 'atendida em parte'}",
            mensagem=f"As licenças já estão no estoque da Escola. Nota de Prestação de Contas {final.get('nota_numero')} "
                     f"no valor de R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + ".",
            link="/escola/solicitacoes", destino_escola_id=s["escola_id"],
        )
        self._auditar(actor_id, "solicitacao_atendida", solicitacao_id,
                      {"status": novo_status, "atendidos": atendidos, "nota_id": nota_id, "valor_total": valor}, ip)
        return _saida(final)

    def recusar(self, polo_id: str, solicitacao_id: str, dados: SolicitacaoRecusar, actor_id: Optional[str],
                ip: Optional[str]) -> SolicitacaoOut:
        s = self._obter(solicitacao_id)
        if str(s["polo_id"]) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada neste Polo")
        motivo = dados.motivo.strip()
        if not self.repo.resolver(solicitacao_id, status="recusada", resolvido_por=actor_id, motivo_recusa=motivo):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta solicitação já foi resolvida")
        self.notificar(titulo=f"Solicitação {s['numero']} recusada", mensagem=f"Motivo: {motivo}",
                       link="/escola/solicitacoes", destino_escola_id=s["escola_id"])
        self._auditar(actor_id, "solicitacao_recusada", solicitacao_id, {"motivo": motivo}, ip)
        return _saida(self._obter(solicitacao_id))

    def repasse_recebido(self, polo_id: str, nota_id: str, actor_id: Optional[str], ip: Optional[str]) -> SolicitacaoOut:
        nota = self.repo.get_nota(nota_id)
        if not nota or str(nota["polo_id"]) != str(polo_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Nota não encontrada neste Polo")
        if not self.repo.marcar_repasse(nota_id, actor_id):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="O repasse desta Nota já foi registrado")
        s = self._obter(nota["solicitacao_id"])
        self.notificar(titulo=f"Repasse da Nota {nota['numero']} confirmado",
                       mensagem="O Polo confirmou o recebimento do valor.", link="/escola/solicitacoes",
                       destino_escola_id=nota["escola_id"])
        self._auditar(actor_id, "prestacao_repasse_recebido", nota_id, {"solicitacao_id": s["id"]}, ip)
        return _saida(s)

    # --- nota em PDF --------------------------------------------------------
    def nota_pdf(self, s: Dict[str, Any]) -> bytes:
        if not s.get("nota_id"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Esta solicitação ainda não tem Nota de Prestação de Contas")
        from app.modules.solicitacoes.pdf import gerar_nota_prestacao

        nota = self.repo.get_nota(s["nota_id"]) or {}
        return gerar_nota_prestacao(s, nota, self.polos.get_polo(s["polo_id"]) or {},
                                    self.polos.get_escola(s["escola_id"]) or {})

    def _auditar(self, actor_id, acao, entidade_id, dados, ip) -> None:
        try:
            self.polos.record_audit_log(usuario_id=actor_id, acao=acao, entidade="solicitacoes_unidade",
                                        entidade_id=entidade_id, dados_depois=dados, ip=ip)
        except Exception:  # noqa: BLE001
            pass
