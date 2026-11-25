"""Regras das Avaliações (questionário da Disciplina).

Prova online (aluno de Polo/Escola com licença ativa) e contrato para o AVA:
- O AVA lista `GET /avaliacoes?disciplina_id=` para escolher o questionário e usa o mesmo
  fluxo iniciar → respostas → finalizar com `contexto='ava'` (sem licença; matrícula EAD) e
  grava a nota com `origem='ava'` pelo mesmo `registrar_nota`.
- Nota = soma dos pesos certos ÷ soma dos pesos × 10. Histórico: maior nota vale; aprovado >= 6.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.avaliacoes.repository import AvaliacoesRepositoryInterface
from app.modules.avaliacoes.schemas import (
    AlternativaOut,
    AvaliacaoAluno,
    AvaliacaoOut,
    AvaliacaoResumo,
    AvaliacaoSalvar,
    QuestaoOut,
    ResultadoOut,
    TentativaOut,
)

Registrador = Callable[..., str]


def _registrar_padrao(**kwargs: Any) -> str:
    from app.modules.notas_historico import registrar_nota

    return registrar_nota(**kwargs)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _como_dt(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    return None


def _questoes_out(avaliacao: Dict[str, Any], com_gabarito: bool, ordem: Optional[List[str]] = None) -> List[QuestaoOut]:
    questoes = avaliacao.get("questoes") or []
    if ordem:
        por_id = {q["id"]: q for q in questoes}
        questoes = [por_id[i] for i in ordem if i in por_id] + [q for q in questoes if q["id"] not in ordem]
    return [
        QuestaoOut(
            id=q["id"], enunciado=q["enunciado"], peso=float(q.get("peso") or 1), ordem=i,
            alternativas=[AlternativaOut(id=a["id"], texto=a["texto"], correta=a.get("correta") if com_gabarito else None)
                          for a in q.get("alternativas") or []],
        )
        for i, q in enumerate(questoes)
    ]


def _avaliacao_out(a: Dict[str, Any]) -> AvaliacaoOut:
    return AvaliacaoOut(
        id=a["id"], disciplina_id=str(a["disciplina_id"]), disciplina_nome=a.get("disciplina_nome"),
        titulo=a["titulo"], instrucoes=a.get("instrucoes"), tempo_limite_min=a.get("tempo_limite_min"),
        tentativas_max=int(a.get("tentativas_max") or 2), nota_minima=float(a.get("nota_minima") or 6),
        embaralhar=bool(a.get("embaralhar")), ativo=bool(a.get("ativo")), origem=a.get("origem") or "manual",
        questoes=_questoes_out(a, com_gabarito=True), atualizado_em=a.get("atualizado_em"),
    )


def corrigir(avaliacao: Dict[str, Any], respostas: Dict[str, str]) -> tuple[float, int, int]:
    """(nota 0–10 com 1 casa, acertos, total de questões). Correção sempre no servidor."""
    questoes = avaliacao.get("questoes") or []
    peso_total = sum(float(q.get("peso") or 1) for q in questoes) or 1.0
    peso_certo = 0.0
    acertos = 0
    for q in questoes:
        correta = next((a["id"] for a in q.get("alternativas") or [] if a.get("correta")), None)
        if correta and respostas.get(q["id"]) == correta:
            acertos += 1
            peso_certo += float(q.get("peso") or 1)
    return round(peso_certo / peso_total * 10, 1), acertos, len(questoes)


class AvaliacoesService:
    def __init__(self, repo: AvaliacoesRepositoryInterface, registrar: Registrador = _registrar_padrao) -> None:
        self.repo = repo
        self.registrar = registrar

    # ------------------------------------------------------------------
    # Admin / professor
    # ------------------------------------------------------------------

    def listar(self, disciplina_id: Optional[str]) -> List[AvaliacaoResumo]:
        return [AvaliacaoResumo(**{**a, "disciplina_id": str(a["disciplina_id"])}) for a in self.repo.list_avaliacoes(disciplina_id)]

    def da_disciplina(self, disciplina_id: str) -> Optional[AvaliacaoOut]:
        if not self.repo.get_disciplina(disciplina_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        a = self.repo.get_avaliacao_da_disciplina(disciplina_id)
        return _avaliacao_out(a) if a else None

    def salvar(self, disciplina_id: str, payload: AvaliacaoSalvar, usuario_id: Optional[str],
               origem: str = "manual") -> AvaliacaoOut:
        if not self.repo.get_disciplina(disciplina_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada")
        dados = payload.model_dump(exclude={"questoes"})
        questoes = [q.model_dump() for q in payload.questoes]
        avaliacao_id = self.repo.salvar_avaliacao(disciplina_id, dados, questoes, usuario_id, origem)
        return _avaliacao_out(self.repo.get_avaliacao(avaliacao_id))

    def definir_ativo(self, avaliacao_id: str, ativo: bool) -> AvaliacaoOut:
        a = self.repo.get_avaliacao(avaliacao_id)
        if not a:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada")
        if ativo and not a.get("questoes"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cadastre ao menos uma questão antes de ativar")
        self.repo.set_ativo(avaliacao_id, ativo)
        return _avaliacao_out(self.repo.get_avaliacao(avaliacao_id))

    def previa(self, avaliacao_id: str) -> AvaliacaoOut:
        a = self.repo.get_avaliacao(avaliacao_id)
        if not a:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada")
        out = _avaliacao_out(a)
        out.questoes = _questoes_out(a, com_gabarito=False)
        return out

    # ------------------------------------------------------------------
    # Aluno
    # ------------------------------------------------------------------

    def _aluno(self, usuario_id: str) -> Dict[str, Any]:
        aluno = self.repo.get_aluno_por_usuario(usuario_id)
        if not aluno or aluno.get("status", "ativo") != "ativo":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Cadastro de aluno não encontrado ou inativo")
        return aluno

    def _estado(self, avaliacao: Dict[str, Any], aluno_id: str) -> Dict[str, Any]:
        tentativas = self.repo.list_tentativas(avaliacao["id"], aluno_id)
        finalizadas = [t for t in tentativas if t["status"] != "em_andamento"]
        aberta = next((t for t in tentativas if t["status"] == "em_andamento"), None)
        notas = [float(t["nota"]) for t in finalizadas if t.get("nota") is not None]
        maximo = int(avaliacao.get("tentativas_max") or 2)
        return {"tentativas": tentativas, "finalizadas": finalizadas, "aberta": aberta,
                "melhor": max(notas) if notas else None, "restantes": max(maximo - len(finalizadas), 0), "maximo": maximo}

    def minhas(self, usuario_id: str) -> List[AvaliacaoAluno]:
        aluno = self._aluno(usuario_id)
        ead = aluno.get("modalidade") == "ead"
        saida = []
        for d in self.repo.list_disciplinas_licenciadas(aluno["id"]):
            av = self.repo.get_avaliacao_da_disciplina(d["disciplina_id"])
            base = {"disciplina_id": str(d["disciplina_id"]), "disciplina_nome": d.get("disciplina_nome"),
                    "curso_id": d.get("curso_id")}
            if ead:
                saida.append(AvaliacaoAluno(**base, situacao="ava"))
                continue
            if not av or not av.get("ativo"):
                saida.append(AvaliacaoAluno(**base, situacao="sem_avaliacao"))
                continue
            e = self._estado(av, aluno["id"])
            minima = float(av.get("nota_minima") or 6)
            if e["aberta"]:
                situacao = "em_andamento"
            elif e["melhor"] is not None and e["melhor"] >= minima:
                situacao = "aprovado"
            elif e["restantes"] == 0:
                situacao = "sem_tentativas"
            elif e["melhor"] is not None:
                situacao = "reprovado"
            else:
                situacao = "disponivel"
            saida.append(AvaliacaoAluno(
                **base, avaliacao_id=av["id"], titulo=av["titulo"], tempo_limite_min=av.get("tempo_limite_min"),
                tentativas_max=e["maximo"], tentativas_usadas=len(e["finalizadas"]), tentativas_restantes=e["restantes"],
                melhor_nota=e["melhor"], nota_minima=minima, situacao=situacao,
                tentativa_aberta_id=e["aberta"]["id"] if e["aberta"] else None,
                pode_realizar=bool(e["aberta"]) or (e["restantes"] > 0 and situacao != "aprovado"),
            ))
        return saida

    def _tentativa_out(self, avaliacao: Dict[str, Any], tentativa: Dict[str, Any]) -> TentativaOut:
        return TentativaOut(
            tentativa_id=tentativa["id"], avaliacao_id=avaliacao["id"], titulo=avaliacao["titulo"],
            instrucoes=avaliacao.get("instrucoes"), disciplina_nome=avaliacao.get("disciplina_nome"),
            expira_em=tentativa.get("expira_em"),
            questoes=_questoes_out(avaliacao, com_gabarito=False, ordem=tentativa.get("ordem_questoes") or None),
            respostas=dict(tentativa.get("respostas") or {}),
        )

    def iniciar(self, avaliacao_id: str, usuario_id: str) -> TentativaOut:
        """Prova online do aluno de Polo/Escola (exige licença ativa da disciplina)."""
        aluno = self._aluno(usuario_id)
        avaliacao = self._avaliacao_ativa(avaliacao_id)
        if aluno.get("modalidade") == "ead":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Alunos EAD realizam as avaliações pelo AVA")
        licenca = self.repo.get_licenca_ativa(aluno["id"], str(avaliacao["disciplina_id"]))
        if not licenca:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Você não tem licença ativa para esta disciplina")
        return self._abrir_tentativa(avaliacao, aluno, "prova_licenca", licenca.get("id"))

    def iniciar_ava(self, avaliacao_id: str, usuario_id: str) -> TentativaOut:
        """Avaliação dentro do AVA (aluno EAD). A liberação da disciplina é validada pelo módulo AVA."""
        aluno = self._aluno(usuario_id)
        if aluno.get("modalidade") != "ead":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="A Sala de Aula Virtual é exclusiva para alunos EAD.")
        return self._abrir_tentativa(self._avaliacao_ativa(avaliacao_id), aluno, "ava", None)

    def estado_ava(self, avaliacao_id: str, aluno_id: str) -> Optional[Dict[str, Any]]:
        """Situação do aluno numa avaliação (para a aula do tipo avaliação no AVA)."""
        avaliacao = self.repo.get_avaliacao(avaliacao_id)
        if not avaliacao:
            return None
        e = self._estado(avaliacao, aluno_id)
        minima = float(avaliacao.get("nota_minima") or 6)
        aprovado = e["melhor"] is not None and e["melhor"] >= minima
        ativa = bool(avaliacao.get("ativo"))
        return {
            "avaliacao_id": avaliacao["id"], "titulo": avaliacao["titulo"], "instrucoes": avaliacao.get("instrucoes"),
            "ativa": ativa, "tempo_limite_min": avaliacao.get("tempo_limite_min"),
            "total_questoes": len(avaliacao.get("questoes") or []), "tentativas_max": e["maximo"],
            "tentativas_usadas": len(e["finalizadas"]), "tentativas_restantes": e["restantes"],
            "melhor_nota": e["melhor"], "nota_minima": minima, "aprovado": aprovado,
            "tentativa_aberta_id": e["aberta"]["id"] if e["aberta"] else None,
            "pode_realizar": ativa and (bool(e["aberta"]) or (e["restantes"] > 0 and not aprovado)),
        }

    def _avaliacao_ativa(self, avaliacao_id: str) -> Dict[str, Any]:
        avaliacao = self.repo.get_avaliacao(avaliacao_id)
        if not avaliacao or not avaliacao.get("ativo"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Avaliação não disponível")
        return avaliacao

    def _abrir_tentativa(self, avaliacao: Dict[str, Any], aluno: Dict[str, Any], contexto: str,
                         licenca_id: Optional[str]) -> TentativaOut:
        """Retoma a tentativa aberta ou cria uma nova (respeitando aprovação e limite de tentativas)."""
        e = self._estado(avaliacao, aluno["id"])
        if e["aberta"]:
            aberta = e["aberta"]
            expira = _como_dt(aberta.get("expira_em"))
            if expira and expira <= _agora():
                self._fechar(avaliacao, aberta, aluno["id"], "expirada")
                return self._abrir_tentativa(avaliacao, aluno, contexto, licenca_id)
            return self._tentativa_out(avaliacao, aberta)
        if e["melhor"] is not None and e["melhor"] >= float(avaliacao.get("nota_minima") or 6):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Você já foi aprovado nesta avaliação")
        if e["restantes"] <= 0:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Você não tem mais tentativas nesta avaliação")
        ordem = [q["id"] for q in avaliacao.get("questoes") or []]
        if avaliacao.get("embaralhar"):
            random.SystemRandom().shuffle(ordem)
        tempo = avaliacao.get("tempo_limite_min")
        tid = self.repo.criar_tentativa({
            "avaliacao_id": avaliacao["id"], "aluno_id": aluno["id"], "licenca_id": licenca_id,
            "contexto": contexto, "ordem_questoes": ordem,
            "expira_em": _agora() + timedelta(minutes=int(tempo)) if tempo else None,
        })
        return self._tentativa_out(avaliacao, self.repo.get_tentativa(tid))

    def _tentativa_do_aluno(self, tentativa_id: str, usuario_id: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        aluno = self._aluno(usuario_id)
        tentativa = self.repo.get_tentativa(tentativa_id)
        if not tentativa or tentativa["aluno_id"] != aluno["id"]:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tentativa não encontrada")
        avaliacao = self.repo.get_avaliacao(tentativa["avaliacao_id"])
        return aluno, tentativa, avaliacao

    def salvar_respostas(self, tentativa_id: str, respostas: Dict[str, str], usuario_id: str) -> Dict[str, Any]:
        _, tentativa, _ = self._tentativa_do_aluno(tentativa_id, usuario_id)
        if tentativa["status"] != "em_andamento":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta tentativa já foi encerrada")
        self.repo.salvar_respostas(tentativa_id, respostas)
        return {"ok": True}

    def _fechar(self, avaliacao: Dict[str, Any], tentativa: Dict[str, Any], aluno_id: str, status_final: str) -> tuple[float, int, int]:
        nota, acertos, total = corrigir(avaliacao, dict(tentativa.get("respostas") or {}))
        nota_id = self.registrar(
            aluno_id=aluno_id, disciplina_id=str(avaliacao["disciplina_id"]), valor=nota,
            origem="prova" if tentativa.get("contexto", "prova_licenca") == "prova_licenca" else "ava",
            turma_id=self.repo.turma_do_aluno(aluno_id, str(avaliacao["disciplina_id"])), lancado_por=None,
        )
        self.repo.finalizar_tentativa(tentativa["id"], nota, status_final, nota_id)
        return nota, acertos, total

    def finalizar(self, tentativa_id: str, respostas: Optional[Dict[str, str]], usuario_id: str) -> ResultadoOut:
        aluno, tentativa, avaliacao = self._tentativa_do_aluno(tentativa_id, usuario_id)
        if tentativa["status"] != "em_andamento":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta tentativa já foi encerrada")
        expira = _como_dt(tentativa.get("expira_em"))
        vencida = bool(expira and expira <= _agora())
        if respostas is not None and not vencida:  # depois do prazo, valem as respostas salvas até ali
            self.repo.salvar_respostas(tentativa_id, respostas)
            tentativa["respostas"] = respostas
        nota, acertos, total = self._fechar(avaliacao, tentativa, aluno["id"], "expirada" if vencida else "finalizada")
        e = self._estado(avaliacao, aluno["id"])
        minima = float(avaliacao.get("nota_minima") or 6)
        return ResultadoOut(tentativa_id=tentativa_id, nota=nota, aprovado=nota >= minima, nota_minima=minima,
                            acertos=acertos, total_questoes=total, tentativas_restantes=e["restantes"],
                            melhor_nota=e["melhor"])
