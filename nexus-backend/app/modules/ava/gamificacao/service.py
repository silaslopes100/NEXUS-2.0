"""Regras da gamificação: crédito de XP, sequência de dias, conquistas e ranking."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.modules.ava.gamificacao import regras
from app.modules.ava.gamificacao.repository import PostgresGamificacaoRepository
from app.modules.ava.gamificacao.schemas import (
    ConquistaOut,
    CursoRankingOut,
    EventoXpOut,
    NivelOut,
    PerfilGamificacaoOut,
    RankingItemOut,
    RankingOut,
    RecompensaOut,
)

# (tipo, referência, xp, descrição)
Evento = Tuple[str, str, int, Optional[str]]

_ESTUDO = {"aula_concluida", "avaliacao_aprovada"}


def _nivel(xp: int) -> NivelOut:
    n, nome, inicio, fim, pct = regras.faixa(xp)
    return NivelOut(nivel=n, nome=nome, xp_total=xp, xp_inicio=inicio, xp_proximo=fim, progresso_pct=pct)


def _evento_out(e: Dict[str, Any]) -> EventoXpOut:
    return EventoXpOut(tipo=e["tipo"], rotulo=regras.ROTULOS.get(e["tipo"], e["tipo"]), xp=int(e["xp"]),
                       descricao=e.get("descricao"), criado_em=e.get("criado_em"))


def _conquista_out(c: Dict[str, Any], obtida_em: Any = None) -> ConquistaOut:
    return ConquistaOut(codigo=c["codigo"], nome=c["nome"], descricao=c["descricao"], icone=c["icone"], cor=c["cor"],
                        xp_bonus=int(c.get("xp_bonus") or 0), obtida_em=obtida_em)


def _nome_publico(nome: Optional[str], sobrenome: Optional[str]) -> str:
    """Privacidade no ranking: primeiro nome + inicial do sobrenome."""
    partes = f"{nome or ''} {sobrenome or ''}".split()
    if not partes:
        return "Aluno"
    return f"{partes[0]} {partes[-1][0].upper()}." if len(partes) > 1 else partes[0]


class GamificacaoService:
    def __init__(self, repo: PostgresGamificacaoRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------ crédito

    def registrar(self, usuario_id: str, curso_id: Optional[str], eventos: Sequence[Evento],
                  nota: Optional[float] = None) -> RecompensaOut:
        """Credita os eventos (idempotente) e avalia sequência, conquistas e nível."""
        xp_antes = self.repo.xp_total(usuario_id)
        lista: List[Evento] = list(eventos)
        streak_atual = 0
        if any(e[0] in _ESTUDO for e in lista):
            atual, _, novo_dia, hoje = self.repo.registrar_dia(usuario_id)
            streak_atual = atual
            if novo_dia:
                lista.append(("streak_dia", hoje.isoformat(), regras.xp_streak(atual),
                              f"{atual} dia(s) seguido(s)"))
        novos = self.repo.inserir_eventos(usuario_id, curso_id, lista)
        conquistas: List[ConquistaOut] = []
        if novos:
            conquistas = self._avaliar_conquistas(usuario_id, curso_id, nota)
        xp_depois = self.repo.xp_total(usuario_id)
        if not streak_atual:
            streak_atual = self.repo.streak(usuario_id)[0]
        todos = novos + [{"tipo": "conquista", "xp": c.xp_bonus, "descricao": c.nome} for c in conquistas if c.xp_bonus]
        return RecompensaOut(
            xp_ganho=xp_depois - xp_antes, eventos=[_evento_out(e) for e in todos], conquistas=conquistas,
            subiu_nivel=regras.nivel_de(xp_depois) > regras.nivel_de(xp_antes), nivel=_nivel(xp_depois),
            streak_atual=streak_atual,
        )

    def _posicao_semanal(self, usuario_id: str, curso_id: Optional[str]) -> Optional[int]:
        if not curso_id:
            return None
        visiveis = [r for r in self.repo.ranking(curso_id, semana=True) if r["visivel"] or r["usuario_id"] == usuario_id]
        return next((i + 1 for i, r in enumerate(visiveis) if r["usuario_id"] == usuario_id), None)

    def _avaliar_conquistas(self, usuario_id: str, curso_id: Optional[str], nota: Optional[float]) -> List[ConquistaOut]:
        obtidas = self.repo.obtidas(usuario_id)
        pendentes = [c for c in self.repo.catalogo() if c["id"] not in obtidas]
        if not pendentes:
            return []
        contadores = self.repo.contadores(usuario_id)
        recorde = max(self.repo.streak(usuario_id)[1], 0)
        posicao: Optional[int] = None
        novas: List[ConquistaOut] = []
        for c in pendentes:
            r = c.get("regra") or {}
            ok = False
            if "contador" in r:
                ok = contadores.get(r["contador"], 0) >= int(r.get("minimo", 1))
            elif "streak" in r:
                ok = recorde >= int(r["streak"])
            elif "nota" in r:
                ok = nota is not None and float(nota) >= float(r["nota"])
            elif "ranking_semanal" in r:
                if posicao is None:
                    posicao = self._posicao_semanal(usuario_id, curso_id) or 0
                ok = 0 < posicao <= int(r["ranking_semanal"])
            if not ok:
                continue
            obtida_em = self.repo.conceder(usuario_id, c["id"])
            if obtida_em is None:
                continue
            if c.get("xp_bonus"):
                self.repo.inserir_eventos(usuario_id, curso_id, [("conquista", c["codigo"], int(c["xp_bonus"]), c["nome"])])
            novas.append(_conquista_out(c, obtida_em))
        return novas

    # ------------------------------------------------------------------ leitura

    def perfil(self, usuario_id: str) -> PerfilGamificacaoOut:
        xp = self.repo.xp_total(usuario_id)
        atual, recorde, ultimo, hoje = self.repo.streak(usuario_id)
        obtidas = self.repo.obtidas(usuario_id)
        conquistas = [_conquista_out(c, obtidas.get(c["id"])) for c in self.repo.catalogo()]
        return PerfilGamificacaoOut(
            nivel=_nivel(xp), xp_semana=self.repo.xp_semana(usuario_id), streak_atual=atual, streak_recorde=recorde,
            estudou_hoje=ultimo == hoje, ultimo_dia=ultimo, ranking_visivel=self.repo.ranking_visivel(usuario_id),
            conquistas=conquistas, historico=[_evento_out(e) for e in self.repo.historico(usuario_id)],
        )

    def ranking(self, usuario_id: str, periodo: str, curso_id: Optional[str], limite: int = 10) -> RankingOut:
        cursos = [CursoRankingOut(id=c["id"], nome=c["nome"]) for c in self.repo.cursos_do_aluno(usuario_id)]
        visivel_eu = self.repo.ranking_visivel(usuario_id)
        curso = next((c for c in cursos if c.id == curso_id), cursos[0] if cursos else None)
        if not curso:
            return RankingOut(periodo=periodo, cursos=cursos, ranking_visivel=visivel_eu)  # type: ignore[arg-type]
        linhas = self.repo.ranking(curso.id, semana=periodo == "semana")
        publicos = [r for r in linhas if r["visivel"]]
        itens = [
            RankingItemOut(posicao=i + 1, usuario_id=r["usuario_id"], nome=_nome_publico(r.get("nome"), r.get("sobrenome")),
                           foto_url=r.get("foto_url"), xp=int(r["xp"]), nivel=regras.nivel_de(int(r["xp_total"])),
                           eu=r["usuario_id"] == usuario_id)
            for i, r in enumerate(publicos)
        ]
        minha = next((i for i in itens if i.eu), None)
        return RankingOut(periodo=periodo, curso=curso, cursos=cursos, itens=itens[:limite], minha_posicao=minha,  # type: ignore[arg-type]
                          total_participantes=len(publicos), ranking_visivel=visivel_eu)

    def definir_ranking_visivel(self, usuario_id: str, visivel: bool) -> None:
        self.repo.definir_ranking_visivel(usuario_id, visivel)
