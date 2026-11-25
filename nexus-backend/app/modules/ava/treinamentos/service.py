"""Regras dos Treinamentos: gestão (admin) e trilha do usuário (Polo, Escola, Professor)."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.ava.aluno_repository import PostgresAvaAlunoRepository
from app.modules.ava.aluno_schemas import AvaliacaoAulaOut, DisciplinaAlunoOut, DisciplinaPlayerOut
from app.modules.ava.aluno_service import AvaAlunoService
from app.modules.ava.gamificacao.schemas import RecompensaOut
from app.modules.ava.repository import PostgresAvaRepository, uuid_valido
from app.modules.ava.schemas import CapituloIn, CapituloOut, ReordenarIn
from app.modules.ava.service import AvaAdminService
from app.modules.ava.treinamentos import pdf as pdf_mod
from app.modules.ava.treinamentos.repository import PostgresTreinamentosRepository
from app.modules.ava.treinamentos.schemas import (
    ROTULO_CATEGORIA,
    CertificadoValidacaoOut,
    EstruturaTreinamentoOut,
    ParticipanteOut,
    TreinamentoCatalogoOut,
    TreinamentoIn,
    TreinamentoOut,
    TreinamentosPage,
    UnidadeOut,
    UnidadesOut,
)

PERFIS_PUBLICO = ("polo", "escola", "professor")


def _texto(valor: Optional[str]) -> Optional[str]:
    limpo = (valor or "").strip()
    return limpo or None


def _pct(feitas: int, total: int) -> int:
    return int(round(feitas * 100 / total)) if total else 0


def _inicio_dt(d: Optional[date]) -> Optional[datetime]:
    return datetime.combine(d, time.min, tzinfo=timezone.utc) if d else None


def _concluiu(t: Dict[str, Any]) -> bool:
    base = int(t.get("total_obrigatorias") or 0) or int(t.get("total_aulas") or 0)
    return bool(t.get("concluido_em")) or (base > 0 and int(t.get("aulas_concluidas") or 0) >= base)


# ===========================================================================
# Admin
# ===========================================================================

class TreinamentosAdminService:
    def __init__(self, repo: PostgresTreinamentosRepository, conteudo: AvaAdminService) -> None:
        self.repo = repo
        self.conteudo = conteudo

    def _out(self, t: Dict[str, Any], unidades: Optional[Dict[str, Any]] = None) -> TreinamentoOut:
        u = (unidades or {}).get(t["id"], {"polos": [], "escolas": []})
        return TreinamentoOut(
            **{k: t.get(k) for k in TreinamentoOut.model_fields if k in t and k not in ("polos", "escolas")},
            polos=[UnidadeOut(**p) for p in u["polos"]], escolas=[UnidadeOut(**e) for e in u["escolas"]],
        )

    def _existente(self, treinamento_id: str) -> Dict[str, Any]:
        t = self.repo.obter(treinamento_id)
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
        return t

    def listar(self, q: Optional[str], situacao: str, limite: int, offset: int) -> TreinamentosPage:
        total, linhas = self.repo.listar(_texto(q), situacao, limite, offset)
        unidades = self.repo.unidades([t["id"] for t in linhas])
        return TreinamentosPage(items=[self._out(t, unidades) for t in linhas], total=total)

    def obter(self, treinamento_id: str) -> TreinamentoOut:
        t = self._existente(treinamento_id)
        return self._out(t, self.repo.unidades([t["id"]]))

    def salvar(self, treinamento_id: Optional[str], dados: TreinamentoIn, user: UserResponse) -> TreinamentoOut:
        if treinamento_id:
            self._existente(treinamento_id)
        polos = sorted(set(dados.polo_ids))
        escolas = sorted(set(dados.escola_ids))
        if any(not uuid_valido(x) for x in polos + escolas) or not self.repo.unidades_existem(polos, escolas):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Polo ou escola inválido.")
        registro = dados.model_dump(exclude={"polo_ids", "escola_ids"})
        registro.update(titulo=dados.titulo.strip(), descricao=_texto(dados.descricao), capa_url=_texto(dados.capa_url),
                        perfis_alvo=sorted(set(dados.perfis_alvo)))
        novo = self.repo.salvar(treinamento_id, registro, polos, escolas, str(user.id))
        return self.obter(novo)

    def alternar(self, treinamento_id: str) -> TreinamentoOut:
        self._existente(treinamento_id)
        self.repo.alternar_publicado(treinamento_id)
        return self.obter(treinamento_id)

    def duplicar(self, treinamento_id: str, user: UserResponse) -> TreinamentoOut:
        self._existente(treinamento_id)
        return self.obter(self.repo.duplicar(treinamento_id, str(user.id)))

    async def excluir(self, treinamento_id: str) -> None:
        self._existente(treinamento_id)
        await self.conteudo._limpar_arquivos(self.repo.excluir(treinamento_id))

    def unidades(self) -> UnidadesOut:
        polos, escolas = self.repo.todas_unidades()
        return UnidadesOut(polos=[UnidadeOut(**p) for p in polos], escolas=[UnidadeOut(**e) for e in escolas])

    def estrutura(self, treinamento_id: str) -> EstruturaTreinamentoOut:
        t = self.obter(treinamento_id)
        return EstruturaTreinamentoOut(treinamento=t, capitulos=self.conteudo.capitulos(("treinamento_id", treinamento_id)))

    def criar_capitulo(self, treinamento_id: str, dados: CapituloIn) -> CapituloOut:
        self._existente(treinamento_id)
        return self.conteudo.criar_capitulo(("treinamento_id", treinamento_id), dados)

    def reordenar(self, treinamento_id: str, dados: ReordenarIn) -> EstruturaTreinamentoOut:
        self._existente(treinamento_id)
        self.conteudo.reordenar(("treinamento_id", treinamento_id), dados)
        return self.estrutura(treinamento_id)

    def participantes(self, treinamento_id: str) -> List[ParticipanteOut]:
        self._existente(treinamento_id)
        return [ParticipanteOut(**r, progresso_pct=_pct(int(r["aulas_concluidas"]), int(r["total_aulas"])))
                for r in self.repo.participantes(treinamento_id)]


# ===========================================================================
# Usuário (Polo, Escola, Professor) — mesmo player do AVA
# ===========================================================================

class TreinamentoUsuarioService(AvaAlunoService):
    """Reaproveita a trilha do AVA (travas, progresso, anotações) com o dono ``treinamento_id``.

    Sem gamificação e sem aulas de avaliação. Ao concluir as aulas obrigatórias, registra a
    conclusão (código de validação do certificado).
    """

    _DONO = "treinamento_id"

    def __init__(self, repo: PostgresAvaAlunoRepository, conteudo: PostgresAvaRepository,
                 treinamentos: PostgresTreinamentosRepository) -> None:
        super().__init__(repo, conteudo, avaliacoes=None)  # type: ignore[arg-type]
        self.treinamentos = treinamentos

    # ------------------------------------------------------------------ público

    def _visiveis(self, user: UserResponse, somente: Optional[str] = None) -> List[Dict[str, Any]]:
        perfil = perfil_do_usuario(user)
        if perfil not in PERFIS_PUBLICO:
            return []
        polos, escolas = self.treinamentos.unidades_do_usuario(str(user.id))
        return self.treinamentos.catalogo(str(user.id), perfil, polos, escolas, somente)

    def catalogo(self, user: UserResponse) -> List[TreinamentoCatalogoOut]:
        hoje = date.today()
        saida = []
        for t in self._visiveis(user):
            total, feitas = int(t["total_aulas"] or 0), int(t["aulas_concluidas"] or 0)
            saida.append(TreinamentoCatalogoOut(
                **{k: t.get(k) for k in TreinamentoCatalogoOut.model_fields if k in t},
                progresso_pct=100 if t.get("concluido_em") else _pct(feitas, total),
                disponivel=total > 0 and not (t.get("data_inicio") and t["data_inicio"] > hoje),
            ))
        return saida

    def _linha_disciplina(self, ctx: Dict[str, Any], disciplina_id: str) -> Dict[str, Any]:
        """O "dono" aqui é o treinamento (mantém a assinatura do AVA)."""
        if ctx.get("previa"):
            t = self.treinamentos.obter(disciplina_id)
            if not t:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
        else:
            achados = self._visiveis(ctx["user"], disciplina_id) if uuid_valido(disciplina_id) else []
            if not achados:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
            t = achados[0]
            if t.get("data_inicio") and t["data_inicio"] > date.today():
                raise HTTPException(status.HTTP_403_FORBIDDEN,
                                    detail=f"Este treinamento começa em {t['data_inicio']:%d/%m/%Y}.")
        return {**t, "nome": t["titulo"], "curso_nome": ROTULO_CATEGORIA.get(t.get("categoria"), "Treinamento"),
                "descricao_ava": t.get("descricao"), "liberada_em": _inicio_dt(t.get("data_inicio")),
                "publicado": True}

    def _disciplina_out(self, d: Dict[str, Any]) -> DisciplinaAlunoOut:
        total, feitas = int(d.get("total_aulas") or 0), int(d.get("aulas_concluidas") or 0)
        return DisciplinaAlunoOut(
            id=d["id"], nome=d["nome"], curso_nome=d.get("curso_nome"), capa_url=d.get("capa_url"),
            descricao=d.get("descricao_ava"), situacao="concluida" if _concluiu(d) else "liberada",
            total_aulas=total, aulas_concluidas=feitas, progresso_pct=_pct(feitas, total),
            duracao_min=int(d.get("duracao_min") or 0), ultimo_acesso_em=d.get("ultimo_acesso_em"),
        )

    def disciplina(self, ctx: Dict[str, Any], disciplina_id: str) -> DisciplinaPlayerOut:
        out = super().disciplina(ctx, disciplina_id)
        if not ctx.get("previa"):
            t = self._linha_disciplina(ctx, disciplina_id)
            out.certificado_disponivel = bool(t.get("certificado_ativo") and t.get("concluido_em"))
        return out

    def _estado_avaliacao(self, ctx: Dict[str, Any], aula: Dict[str, Any]) -> Optional[AvaliacaoAulaOut]:
        return None

    def _creditar(self, ctx: Dict[str, Any], d: Dict[str, Any], aula: Dict[str, Any], aulas: List[Dict[str, Any]],
                  avaliacao: Optional[AvaliacaoAulaOut]) -> Optional[RecompensaOut]:
        """Sem XP; quando todas as obrigatórias estão concluídas, registra a conclusão do treinamento."""
        if ctx.get("previa"):
            return None
        obrigatorias = [a for a in aulas if a.get("obrigatoria")] or aulas
        if all(a["status"] == "concluida" for a in obrigatorias):
            self.treinamentos.concluir(d["id"], str(ctx["user"].id))
        return None

    def iniciar_avaliacao(self, ctx: Dict[str, Any], aula_id: str):  # noqa: ANN201
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Treinamentos não têm avaliações.")

    # ------------------------------------------------------------------ certificado

    def certificado(self, user: UserResponse, treinamento_id: str, url_base: str) -> tuple[bytes, str]:
        achados = self._visiveis(user, treinamento_id) if uuid_valido(treinamento_id) else []
        t = achados[0] if achados else None
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Treinamento não encontrado.")
        if not t.get("certificado_ativo"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Este treinamento não emite certificado.")
        c = self.treinamentos.conclusao(treinamento_id, str(user.id))
        if not c:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Conclua todas as aulas para emitir o certificado.")
        conteudo = pdf_mod.gerar_certificado(
            nome=c["nome"] or user.nome, treinamento=t["titulo"],
            categoria=ROTULO_CATEGORIA.get(t.get("categoria"), "Treinamento"), carga_horaria=t.get("carga_horaria"),
            concluido_em=c["concluido_em"], codigo=c["codigo_validacao"],
            url_validacao=f"{url_base.rstrip('/')}/certificados/validar/{c['codigo_validacao']}",
        )
        return conteudo, f"certificado-{c['codigo_validacao']}.pdf"

    def validar(self, codigo: str) -> CertificadoValidacaoOut:
        r = self.treinamentos.validar(codigo) if codigo and len(codigo) <= 16 else None
        if not r:
            return CertificadoValidacaoOut(valido=False, codigo=codigo.upper())
        return CertificadoValidacaoOut(valido=True, codigo=r["codigo_validacao"], nome=r["nome"], treinamento=r["titulo"],
                                       categoria=ROTULO_CATEGORIA.get(r.get("categoria")), carga_horaria=r.get("carga_horaria"),
                                       concluido_em=r["concluido_em"])

