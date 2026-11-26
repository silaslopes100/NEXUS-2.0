"""Regras da Sala de Aula Virtual do aluno EAD.

Liberação da disciplina: o aluno vê as disciplinas dos cursos EAD em que está matriculado
(``matriculas_ead``) e as compradas avulsas. Abre a disciplina quando a compra está paga/liberada
(``compras_disciplina_ead``) ou quando há licença ativa para ela; as demais aparecem com cadeado.
O prazo de conclusão da compra, quando vencido, bloqueia o acesso.

Turma EAD: quando o aluno está numa turma EAD aberta do curso, as disciplinas seguem o
cronograma da turma (Calendário Acadêmico): a ainda não liberada aparece bloqueada e a data
limite da turma vira o prazo de conclusão (vencida bloqueia, ou só avisa, conforme a regra).

Travas por aula (na ordem da disciplina):
- ``drip``: ``liberar_apos_dias`` contados do início do acesso à disciplina;
- ``sequencial``: com a ordem obrigatória ligada, só depois de concluir as obrigatórias anteriores;
- ``pre_requisito``: a aula de avaliação exige as aulas obrigatórias anteriores concluídas.

Pré-visualização (admin): mostra a disciplina inteira, sem travas e sem gravar progresso.
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.modules.ava.aluno_repository import PostgresAvaAlunoRepository
from app.modules.ava.aluno_schemas import (
    AnotacaoIn,
    AnotacaoOut,
    AulaAlunoOut,
    AulaResumoAlunoOut,
    AvaliacaoAulaOut,
    CapituloAlunoOut,
    ConclusaoOut,
    ContinuarOut,
    DisciplinaAlunoOut,
    DisciplinaPlayerOut,
    HomeOut,
    ProgressoIn,
    ResumoAlunoOut,
)
from app.modules.ava.gamificacao import regras as gam
from app.modules.ava.gamificacao.schemas import RecompensaOut
from app.modules.ava.gamificacao.service import GamificacaoService
from app.modules.ava.repository import PostgresAvaRepository
from app.modules.ava.schemas import ItemOut
from app.modules.avaliacoes.schemas import TentativaOut
from app.modules.avaliacoes.service import AvaliacoesService

# Valores de status_pagamento que liberam a disciplina (legado e gateways).
_PAGOS = {"pago", "paga", "aprovado", "aprovada", "confirmado", "confirmada", "liberado", "liberada", "concluido",
          "paid", "received", "confirmed", "received_in_cash"}
_PERCENTUAL_CONCLUSAO = 90

logger = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _dt(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    return None


def _pct(feitas: int, total: int) -> int:
    return int(round(feitas * 100 / total)) if total else 0


def _item_publico(r: Dict[str, Any]) -> ItemOut:
    return ItemOut(**{k: r.get(k) for k in ItemOut.model_fields if k in r})


class AvaAlunoService:
    # Dono do conteúdo (a subclasse dos treinamentos troca por "treinamento_id").
    _DONO = "disciplina_id"

    def __init__(self, repo: PostgresAvaAlunoRepository, conteudo: PostgresAvaRepository,
                 avaliacoes: AvaliacoesService, gamificacao: Optional[GamificacaoService] = None) -> None:
        self.repo = repo
        self.conteudo = conteudo
        self.avaliacoes = avaliacoes
        self.gamificacao = gamificacao

    # ------------------------------------------------------------------ disciplinas

    @staticmethod
    def _concluiu(d: Dict[str, Any]) -> bool:
        base = int(d.get("total_obrigatorias") or 0) or int(d.get("total_aulas") or 0)
        feitas = int(d.get("obrigatorias_concluidas") or 0) if d.get("total_obrigatorias") else int(d.get("aulas_concluidas") or 0)
        return bool(base) and feitas >= base

    @classmethod
    def _situacao(cls, d: Dict[str, Any]) -> str:
        if d.get("ead_aguardando"):  # turma EAD: a disciplina ainda não foi liberada pela sequência
            return "bloqueada"
        pago = bool(d.get("liberada_em") or d.get("licenca_em") or d.get("bolsista")
                    or (d.get("status_pagamento") or "").strip().lower() in _PAGOS)
        prazo = _dt(d.get("prazo_conclusao"))
        vencido = bool(prazo and prazo < _agora()) and not d.get("ead_prazo_alerta")
        expirado = bool(d.get("reprovado_por_prazo")) or vencido
        if expirado:
            return "prazo_expirado"
        if not pago:
            return "pagamento_pendente" if d.get("compra_id") else "bloqueada"
        if not d.get("publicado") or not d.get("total_aulas"):
            return "em_breve"
        return "concluida" if cls._concluiu(d) else "liberada"

    def _disciplinas(self, aluno_id: str, usuario_id: str) -> List[Dict[str, Any]]:
        linhas = self.repo.disciplinas_do_aluno(aluno_id, usuario_id)
        try:
            self._aplicar_turma_ead(aluno_id, linhas)
        except Exception:  # o AVA não pode cair por causa do cronograma da turma
            logger.exception("Falha ao aplicar os prazos da turma EAD do aluno %s", aluno_id)
        return linhas

    def _aplicar_turma_ead(self, aluno_id: str, linhas: List[Dict[str, Any]]) -> None:
        from app.core.config import settings
        from app.modules.carga_horaria.repository import PostgresCargaHorariaRepository, get_carga_horaria_repository
        from app.modules.carga_horaria.service import CargaHorariaService

        repo = get_carga_horaria_repository()
        if not linhas or (not settings.PG_DSN and isinstance(repo, PostgresCargaHorariaRepository)):
            return
        conclusoes = {
            str(d["id"]): (_dt(d.get("ultima_conclusao_em")) or _agora()).date()
            for d in linhas if self._concluiu(d)
        }
        prazos = CargaHorariaService(repo).prazos_ead_do_aluno(str(aluno_id), conclusoes)
        for d in linhas:
            p = prazos.get(str(d["id"]))
            if not p:
                continue
            if p["situacao"] == "aguardando":
                d["ead_aguardando"] = True
            limite = p.get("data_limite")
            liberada = _dt(d.get("liberada_em"))
            if limite and liberada and liberada.date() > limite:
                # Recompra depois do prazo vencido (RN-03): novo pagamento, prazo novo a partir da liberação.
                limite = liberada.date() + timedelta(days=int(p.get("prazo_dias") or 0))
            if limite:
                # Vence ao fim do dia limite.
                d["prazo_conclusao"] = datetime.combine(limite + timedelta(days=1), time.min, tzinfo=timezone.utc)
            if p.get("ao_vencer") == "alertar":
                d["ead_prazo_alerta"] = True

    def _disciplina_out(self, d: Dict[str, Any]) -> DisciplinaAlunoOut:
        total = int(d.get("total_aulas") or 0)
        feitas = int(d.get("aulas_concluidas") or 0)
        return DisciplinaAlunoOut(
            id=d["id"], nome=d["nome"], curso_id=d.get("curso_id"), curso_nome=d.get("curso_nome"),
            semestre=d.get("semestre"), capa_url=d.get("capa_url"), descricao=d.get("descricao_ava"),
            situacao=self._situacao(d), total_aulas=total, aulas_concluidas=feitas, progresso_pct=_pct(feitas, total),
            duracao_min=int(d.get("duracao_min") or 0), prazo_conclusao=d.get("prazo_conclusao"),
            ultimo_acesso_em=d.get("ultimo_acesso_em"),
        )

    def home(self, ctx: Dict[str, Any]) -> HomeOut:
        user, aluno = ctx["user"], ctx["aluno"]
        linhas = self._disciplinas(aluno["id"], str(user.id))
        disciplinas = [self._disciplina_out(d) for d in linhas]
        abertas = {d.id: d for d in disciplinas if d.situacao in ("liberada", "concluida")}
        continuar = None
        ultima = self.repo.ultima_aula(str(user.id), list(abertas))
        if ultima:
            d = abertas[ultima["disciplina_id"]]
            aula_id, aula_titulo, cap_titulo = ultima["aula_id"], ultima["aula_titulo"], ultima["capitulo_titulo"]
            if ultima["status"] == "concluida":  # leva para a próxima aula disponível, quando houver
                proxima = self._proxima_disponivel(ctx, d.id, depois_de=aula_id)
                if proxima:
                    aula_id, aula_titulo, cap_titulo = proxima
            continuar = ContinuarOut(disciplina_id=d.id, disciplina_nome=d.nome, capa_url=d.capa_url, aula_id=aula_id,
                                     aula_titulo=aula_titulo, capitulo_titulo=cap_titulo, progresso_pct=d.progresso_pct,
                                     ultimo_acesso_em=ultima["ultimo_acesso_em"])
        resumo = ResumoAlunoOut(
            aulas_concluidas=sum(d.aulas_concluidas for d in disciplinas),
            disciplinas_concluidas=sum(1 for d in disciplinas if d.situacao == "concluida"),
            disciplinas_liberadas=len(abertas),
            minutos_estudados=self.repo.minutos_estudados(str(user.id)),
        )
        return HomeOut(nome=user.nome, continuar=continuar, disciplinas=disciplinas, resumo=resumo)

    def _linha_disciplina(self, ctx: Dict[str, Any], disciplina_id: str) -> Dict[str, Any]:
        if ctx.get("previa"):
            d = self.repo.disciplina_previa(disciplina_id)
            if not d:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada.")
            return d
        for d in self._disciplinas(ctx["aluno"]["id"], str(ctx["user"].id)):
            if d["id"] == disciplina_id:
                situacao = self._situacao(d)
                if situacao in ("liberada", "concluida"):
                    return d
                mensagens = {
                    "em_breve": "O conteúdo desta disciplina estará disponível em breve.",
                    "prazo_expirado": "O prazo para concluir esta disciplina terminou.",
                    "pagamento_pendente": "O pagamento desta disciplina ainda não foi confirmado.",
                    "bloqueada": "Esta disciplina ainda não foi liberada para você.",
                }
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail=mensagens.get(situacao, "Disciplina indisponível."))
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Disciplina não encontrada.")

    # ------------------------------------------------------------------ estrutura com travas

    def _mapa(self, ctx: Dict[str, Any], d: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """(capítulos, aulas em ordem) com ``status``/``motivo_bloqueio``/``libera_em`` calculados."""
        previa = bool(ctx.get("previa"))
        capitulos = self.conteudo.estrutura((self._DONO, d["id"]), somente_publicados=not previa)
        aulas = [a for c in capitulos for a in c["aulas"]]
        for c in capitulos:
            for a in c["aulas"]:
                a["_capitulo"] = c
        progresso = {} if previa else self.repo.progresso(str(ctx["user"].id), [a["id"] for a in aulas])
        inicio = _dt(d.get("liberada_em")) or _dt(d.get("licenca_em")) or _dt(d.get("matricula_em"))
        sequencial = bool(d.get("sequencial"))
        pendente_obrigatoria = False
        agora = _agora()
        for a in aulas:
            p = progresso.get(a["id"]) or {}
            a["_progresso"] = p
            concluida = p.get("status") == "concluida"
            a["status"], a["motivo_bloqueio"], a["libera_em"] = (
                "concluida" if concluida else "em_andamento" if p else "disponivel", None, None)
            if not previa and not concluida:
                dias = a.get("liberar_apos_dias")
                libera = (inicio + timedelta(days=int(dias))) if dias and inicio else None
                if libera and libera > agora:
                    a.update(status="bloqueada", motivo_bloqueio="drip", libera_em=libera)
                elif pendente_obrigatoria and (sequencial or a["tipo"] == "avaliacao"):
                    a.update(status="bloqueada", motivo_bloqueio="sequencial" if sequencial else "pre_requisito")
            if a.get("obrigatoria") and not concluida:
                pendente_obrigatoria = True
        return capitulos, aulas

    def _proxima_disponivel(self, ctx: Dict[str, Any], disciplina_id: str, depois_de: Optional[str] = None
                            ) -> Optional[Tuple[str, str, str]]:
        d = self._linha_disciplina(ctx, disciplina_id)
        _, aulas = self._mapa(ctx, d)
        idx = next((i for i, a in enumerate(aulas) if a["id"] == depois_de), -1)
        for a in aulas[idx + 1:] + aulas[: idx + 1]:
            if a["status"] in ("disponivel", "em_andamento"):
                return a["id"], a["titulo"], a["_capitulo"]["titulo"]
        return None

    def disciplina(self, ctx: Dict[str, Any], disciplina_id: str) -> DisciplinaPlayerOut:
        d = self._linha_disciplina(ctx, disciplina_id)
        capitulos, aulas = self._mapa(ctx, d)
        if ctx.get("previa"):
            d = {**d, "total_aulas": len(aulas), "aulas_concluidas": 0,
                 "duracao_min": sum(a.get("duracao_min") or 0 for a in aulas), "liberada_em": _agora(),
                 "publicado": True}
        saida_caps = []
        for c in capitulos:
            saida_caps.append(CapituloAlunoOut(
                id=c["id"], titulo=c["titulo"], descricao=c.get("descricao"), total_aulas=len(c["aulas"]),
                aulas_concluidas=sum(1 for a in c["aulas"] if a["status"] == "concluida"),
                aulas=[AulaResumoAlunoOut(
                    id=a["id"], titulo=a["titulo"], tipo=a["tipo"], duracao_min=a.get("duracao_min"),
                    obrigatoria=bool(a.get("obrigatoria")), status=a["status"], motivo_bloqueio=a["motivo_bloqueio"],
                    libera_em=a["libera_em"], tipos_itens=sorted({i["tipo"] for i in a["itens"]}),
                ) for a in c["aulas"]],
            ))
        # Próxima: a em andamento mais recente, senão a primeira disponível.
        em_andamento = sorted((a for a in aulas if a["status"] == "em_andamento"),
                              key=lambda a: _dt(a["_progresso"].get("ultimo_acesso_em")) or _agora(), reverse=True)
        proxima = (em_andamento[0] if em_andamento
                   else next((a for a in aulas if a["status"] == "disponivel"), None))
        return DisciplinaPlayerOut(disciplina=self._disciplina_out(d), sequencial=bool(d.get("sequencial")),
                                   previa=bool(ctx.get("previa")), proxima_aula_id=proxima["id"] if proxima else None,
                                   capitulos=saida_caps)

    # ------------------------------------------------------------------ aula

    def _aula_no_mapa(self, ctx: Dict[str, Any], aula_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], int]:
        base = self.conteudo.get_aula(aula_id)
        if not base or not base.get(self._DONO):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aula não encontrada.")
        d = self._linha_disciplina(ctx, str(base[self._DONO]))
        _, aulas = self._mapa(ctx, d)
        idx = next((i for i, a in enumerate(aulas) if a["id"] == aula_id), None)
        if idx is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aula não encontrada.")
        return d, aulas, idx

    @staticmethod
    def _exigir_liberada(aula: Dict[str, Any]) -> None:
        if aula["status"] != "bloqueada":
            return
        if aula["motivo_bloqueio"] == "drip" and aula.get("libera_em"):
            detalhe = f"Esta aula será liberada em {aula['libera_em']:%d/%m/%Y}."
        elif aula["motivo_bloqueio"] == "pre_requisito":
            detalhe = "Conclua as aulas anteriores para liberar a avaliação."
        else:
            detalhe = "Conclua a aula anterior para liberar esta."
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=detalhe)

    def _estado_avaliacao(self, ctx: Dict[str, Any], aula: Dict[str, Any]) -> Optional[AvaliacaoAulaOut]:
        if aula["tipo"] != "avaliacao" or not aula.get("avaliacao_id"):
            return None
        if ctx.get("previa"):
            av = self.avaliacoes.repo.get_avaliacao(aula["avaliacao_id"])
            if not av:
                return None
            return AvaliacaoAulaOut(avaliacao_id=av["id"], titulo=av["titulo"], instrucoes=av.get("instrucoes"),
                                    ativa=bool(av.get("ativo")), tempo_limite_min=av.get("tempo_limite_min"),
                                    total_questoes=len(av.get("questoes") or []),
                                    tentativas_max=int(av.get("tentativas_max") or 2),
                                    tentativas_restantes=int(av.get("tentativas_max") or 2),
                                    nota_minima=float(av.get("nota_minima") or 6))
        e = self.avaliacoes.estado_ava(aula["avaliacao_id"], ctx["aluno"]["id"])
        return AvaliacaoAulaOut(**e) if e else None

    def aula(self, ctx: Dict[str, Any], aula_id: str) -> AulaAlunoOut:
        d, aulas, idx = self._aula_no_mapa(ctx, aula_id)
        aula = aulas[idx]
        self._exigir_liberada(aula)
        previa = bool(ctx.get("previa"))
        usuario = str(ctx["user"].id)
        avaliacao = self._estado_avaliacao(ctx, aula)
        if not previa:
            if avaliacao and avaliacao.aprovado and aula["status"] != "concluida":
                self.repo.concluir(usuario, aula_id)  # aprovada fora do fluxo (ex.: outra aba)
                aula["status"] = "concluida"
                self._creditar(ctx, d, aula, aulas, avaliacao)
            else:
                self.repo.registrar_acesso(usuario, aula_id)
                if aula["status"] == "disponivel":
                    aula["status"] = "em_andamento"
        p = aula["_progresso"]
        anterior = next((a for a in reversed(aulas[:idx]) if a["status"] != "bloqueada"), None)
        proxima = aulas[idx + 1] if idx + 1 < len(aulas) else None
        return AulaAlunoOut(
            id=aula["id"], disciplina_id=d["id"], capitulo_id=aula["capitulo_id"],
            capitulo_titulo=aula["_capitulo"]["titulo"], titulo=aula["titulo"], descricao=aula.get("descricao"),
            tipo=aula["tipo"], duracao_min=aula.get("duracao_min"), status=aula["status"],
            percentual=100 if aula["status"] == "concluida" else int(p.get("percentual") or 0),
            posicao_seg=p.get("posicao_seg"), itens=[_item_publico(i) for i in aula["itens"]], avaliacao=avaliacao,
            anotacoes=[] if previa else [AnotacaoOut(**x) for x in self.repo.anotacoes(usuario, aula_id)],
            minha_nota=None if previa else self.repo.nota_da_aula(usuario, aula_id),
            anterior_id=anterior["id"] if anterior else None, proxima_id=proxima["id"] if proxima else None,
            numero=idx + 1, total_aulas=len(aulas),
        )

    def progresso(self, ctx: Dict[str, Any], aula_id: str, dados: ProgressoIn) -> Optional[ConclusaoOut]:
        """Grava o andamento do vídeo; aos 90% conclui a aula automaticamente."""
        _, aulas, idx = self._aula_no_mapa(ctx, aula_id)
        aula = aulas[idx]
        self._exigir_liberada(aula)
        if aula["tipo"] == "avaliacao" or aula["status"] == "concluida":
            return None
        self.repo.registrar_acesso(str(ctx["user"].id), aula_id, dados.percentual, dados.posicao_seg)
        return self.concluir(ctx, aula_id) if dados.percentual >= _PERCENTUAL_CONCLUSAO else None

    def concluir(self, ctx: Dict[str, Any], aula_id: str) -> ConclusaoOut:
        d, aulas, idx = self._aula_no_mapa(ctx, aula_id)
        aula = aulas[idx]
        self._exigir_liberada(aula)
        e = None
        if aula["tipo"] == "avaliacao":
            e = self._estado_avaliacao(ctx, aula)
            if not e or not e.aprovado:
                raise HTTPException(status.HTTP_409_CONFLICT, detail="A aula de avaliação é concluída com a aprovação.")
        ja = self.repo.concluir(str(ctx["user"].id), aula_id)
        aula["status"] = "concluida"
        recompensa = self._creditar(ctx, d, aula, aulas, e)
        cap = aula["_capitulo"]
        cap_ok = all(a["status"] == "concluida" for a in cap["aulas"])
        obrigatorias = [a for a in aulas if a.get("obrigatoria")] or aulas
        disc_ok = all(a["status"] == "concluida" for a in obrigatorias)
        feitas = sum(1 for a in aulas if a["status"] == "concluida")
        # Próxima ainda não concluída depois desta (recalcula travas com a conclusão gravada).
        _, novas = self._mapa(ctx, d)
        proxima = next((a for a in novas[idx + 1:] if a["status"] != "concluida"), None)
        return ConclusaoOut(aula_id=aula_id, ja_estava_concluida=ja, capitulo_concluido=cap_ok and not ja,
                            disciplina_concluida=disc_ok and not ja, progresso_pct=_pct(feitas, len(aulas)),
                            proxima_aula_id=proxima["id"] if proxima else None, recompensa=recompensa)

    def _creditar(self, ctx: Dict[str, Any], d: Dict[str, Any], aula: Dict[str, Any], aulas: List[Dict[str, Any]],
                  avaliacao: Optional[AvaliacaoAulaOut]) -> Optional[RecompensaOut]:
        """XP da conclusão (idempotente: repetir não credita de novo)."""
        if not self.gamificacao or ctx.get("previa"):
            return None
        cap = aula["_capitulo"]
        eventos = [("aula_concluida", aula["id"], gam.XP_AULA, aula["titulo"])]
        if all(a["status"] == "concluida" for a in cap["aulas"]):
            eventos.append(("capitulo_concluido", cap["id"], gam.XP_CAPITULO, cap["titulo"]))
        obrigatorias = [a for a in aulas if a.get("obrigatoria")] or aulas
        if all(a["status"] == "concluida" for a in obrigatorias):
            eventos.append(("disciplina_concluida", d["id"], gam.XP_DISCIPLINA, d.get("nome")))
        nota = None
        if avaliacao and avaliacao.aprovado:
            nota = avaliacao.melhor_nota
            eventos.append(("avaliacao_aprovada", avaliacao.avaliacao_id, gam.XP_AVALIACAO, avaliacao.titulo))
            if nota is not None and nota >= gam.NOTA_EXCELENTE:
                eventos.append(("avaliacao_excelente", avaliacao.avaliacao_id, gam.XP_AVALIACAO_EXCELENTE, avaliacao.titulo))
        try:
            return self.gamificacao.registrar(str(ctx["user"].id), d.get("curso_id"), eventos, nota)
        except Exception:  # noqa: BLE001 — a gamificação nunca impede a conclusão da aula
            logger.exception("Falha ao creditar XP da aula %s", aula["id"])
            return None

    def iniciar_avaliacao(self, ctx: Dict[str, Any], aula_id: str) -> TentativaOut:
        _, aulas, idx = self._aula_no_mapa(ctx, aula_id)
        aula = aulas[idx]
        self._exigir_liberada(aula)
        if aula["tipo"] != "avaliacao" or not aula.get("avaliacao_id"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Esta aula não tem avaliação.")
        self.repo.registrar_acesso(str(ctx["user"].id), aula_id)
        return self.avaliacoes.iniciar_ava(aula["avaliacao_id"], str(ctx["user"].id))

    # ------------------------------------------------------------------ anotações / nota

    def _aula_acessivel(self, ctx: Dict[str, Any], aula_id: str) -> None:
        _, aulas, idx = self._aula_no_mapa(ctx, aula_id)
        self._exigir_liberada(aulas[idx])

    def criar_anotacao(self, ctx: Dict[str, Any], aula_id: str, dados: AnotacaoIn) -> AnotacaoOut:
        self._aula_acessivel(ctx, aula_id)
        return AnotacaoOut(**self.repo.criar_anotacao(str(ctx["user"].id), aula_id, dados.texto.strip(),
                                                      dados.posicao_seg))

    def atualizar_anotacao(self, ctx: Dict[str, Any], anotacao_id: str, dados: AnotacaoIn) -> AnotacaoOut:
        r = self.repo.atualizar_anotacao(str(ctx["user"].id), anotacao_id, dados.texto.strip())
        if not r:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Anotação não encontrada.")
        return AnotacaoOut(**r)

    def excluir_anotacao(self, ctx: Dict[str, Any], anotacao_id: str) -> None:
        if not self.repo.excluir_anotacao(str(ctx["user"].id), anotacao_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Anotação não encontrada.")

    def avaliar_aula(self, ctx: Dict[str, Any], aula_id: str, nota: int) -> None:
        self._aula_acessivel(ctx, aula_id)
        self.repo.avaliar_aula(str(ctx["user"].id), aula_id, nota)
