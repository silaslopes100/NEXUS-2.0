"""Regras de negócio do módulo `carga_horaria`.

Todo curso segue o Calendário Acadêmico a que está vinculado; as turmas herdam do curso.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from app.modules.auth.roles import perfil_do_usuario
from app.modules.auth.schemas import UserResponse
from app.modules.carga_horaria import cronograma as cr
from app.modules.carga_horaria.repository import (
    CargaHorariaRepositoryInterface,
    get_carga_horaria_repository,
)
from app.modules.carga_horaria.schemas import (
    AndamentoResponse,
    AulaPrevistaResponse,
    CalendarioResponse,
    CalendarioWrite,
    ConclusaoResponse,
    CronogramaResponse,
    DatasLetivasResponse,
    DisciplinaCronograma,
    FrequenciaResponse,
    HistoricoAluno,
    HistoricoDisciplina,
    HistoricoMes,
    HistoricoResumo,
    HistoricoTurmaResponse,
    MesLetivo,
    PrazoDisciplinaEad,
    PrazosAlunoEad,
    PrazosEadResponse,
    RegrasCalendario,
)
from app.modules.turmas.regras import exigir_turma_editavel


def regras_do_calendario(calendario: Optional[Dict[str, Any]]) -> RegrasCalendario:
    return RegrasCalendario(**((calendario or {}).get("regras") or {}))


def datas_do_calendario(calendario: Dict[str, Any], inicio: date, fim: date) -> List[date]:
    """Datas letivas do calendário dentro de [inicio, fim] ∩ vigência do calendário."""
    ini = max(inicio, calendario["data_inicio"])
    end = min(fim, calendario["data_fim"])
    feriados = [date.fromisoformat(str(f["data"])[:10]) if not isinstance(f["data"], date) else f["data"]
                for f in (calendario.get("feriados") or [])]
    return cr.datas_letivas(
        ini, end, calendario["dias_semana"], calendario.get("meses_recesso") or [], feriados,
        calendario.get("datas_excluidas") or [], calendario.get("datas_extras") or [],
    )


def _planos(disciplinas: List[Dict[str, Any]]) -> List[cr.DisciplinaPlano]:
    return [
        cr.DisciplinaPlano(
            id=str(d["id"]), nome=d.get("nome") or "Disciplina",
            carga_horaria=float(d.get("carga_horaria") or 0), qtd_aulas_prevista=int(d.get("qtd_aulas_prevista") or 0),
        )
        for d in disciplinas
    ]


def chave_aula(professor_disciplina_id: Any, data_aula: Any, numero_aula: Any) -> str:
    """Liga presença e ata: mesmo vínculo docente, data e número da aula."""
    return f"{professor_disciplina_id}|{data_aula}|{numero_aula}"


class CargaHorariaService:
    def __init__(self, repo: Optional[CargaHorariaRepositoryInterface] = None) -> None:
        self._repo = repo

    @property
    def repo(self) -> CargaHorariaRepositoryInterface:
        return self._repo or get_carga_horaria_repository()

    # ---------- Calendários ----------

    def listar_calendarios(self) -> List[CalendarioResponse]:
        return [CalendarioResponse(**c) for c in self.repo.listar_calendarios()]

    def obter_calendario(self, calendario_id: str) -> CalendarioResponse:
        cal = self.repo.obter_calendario(calendario_id)
        if not cal:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")
        return CalendarioResponse(**cal)

    def criar_calendario(self, user: UserResponse, dados: CalendarioWrite, ip: Optional[str]) -> CalendarioResponse:
        valores = dados.model_dump(mode="json")
        valores.update(data_inicio=dados.data_inicio, data_fim=dados.data_fim,
                       datas_excluidas=dados.datas_excluidas, datas_extras=dados.datas_extras)
        novo_id = self.repo.criar_calendario(valores)
        depois = self.obter_calendario(novo_id)
        self.repo.auditar(user.id, "calendario_academico_criado", "calendarios_academicos", novo_id,
                          depois=depois.model_dump(mode="json"), ip=ip)
        return depois

    def atualizar_calendario(
        self, user: UserResponse, calendario_id: str, dados: CalendarioWrite, ip: Optional[str]
    ) -> CalendarioResponse:
        antes = self.obter_calendario(calendario_id)
        valores = dados.model_dump(mode="json")
        valores.update(data_inicio=dados.data_inicio, data_fim=dados.data_fim,
                       datas_excluidas=dados.datas_excluidas, datas_extras=dados.datas_extras)
        self.repo.atualizar_calendario(calendario_id, valores)
        depois = self.obter_calendario(calendario_id)
        self.repo.auditar(user.id, "calendario_academico_atualizado", "calendarios_academicos", calendario_id,
                          antes=antes.model_dump(mode="json"), depois=depois.model_dump(mode="json"), ip=ip)
        self.sincronizar_turmas(user, ip, calendario_id=calendario_id)
        return depois

    def sincronizar_turmas(
        self, user: Optional[UserResponse], ip: Optional[str],
        calendario_id: Optional[str] = None, curso_id: Optional[str] = None,
    ) -> int:
        """Início e fim das turmas abertas = vigência do calendário do curso (auditado por turma)."""
        alteradas = self.repo.sincronizar_datas_turmas(calendario_id=calendario_id, curso_id=curso_id)
        for t in alteradas:
            self.repo.auditar(
                user.id if user else None, "turma_datas_sincronizadas", "turmas", t["id"],
                antes={"data_inicio": str(t.get("inicio_antes")), "data_fim": str(t.get("fim_antes"))},
                depois={"data_inicio": str(t.get("data_inicio")), "data_fim": str(t.get("data_fim")),
                        "origem": "calendario_academico"},
                ip=ip,
            )
        return len(alteradas)

    def turmas_afetadas(self, calendario_id: str) -> int:
        return self.repo.contar_turmas_abertas_do_calendario(calendario_id)

    def excluir_calendario(self, user: UserResponse, calendario_id: str, ip: Optional[str]) -> None:
        antes = self.obter_calendario(calendario_id)
        if self.repo.contar_cursos_do_calendario(calendario_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Há cursos vinculados a este calendário. Vincule-os a outro calendário antes de excluir.",
            )
        self.repo.excluir_calendario(calendario_id)
        self.repo.auditar(user.id, "calendario_academico_excluido", "calendarios_academicos", calendario_id,
                          antes=antes.model_dump(mode="json"), ip=ip)

    def datas_letivas(self, calendario_id: str, inicio: Optional[date], fim: Optional[date]) -> DatasLetivasResponse:
        cal = self.obter_calendario(calendario_id).model_dump()
        ini = inicio or cal["data_inicio"]
        end = fim or cal["data_fim"]
        datas = datas_do_calendario(cal, ini, end)
        por_mes = cr.agrupar_por_mes(datas)
        meses = [
            MesLetivo(
                mes=m,
                datas=por_mes.get(m, []),
                quinta_semana=[d for d in por_mes.get(m, []) if cr.eh_quinta_ocorrencia(d)],
                recesso=int(m[5:7]) in (cal.get("meses_recesso") or []),
            )
            for m in cr.meses_no_intervalo(max(ini, cal["data_inicio"]), min(end, cal["data_fim"]))
        ]
        return DatasLetivasResponse(inicio=ini, fim=end, total=len(datas), meses=meses)

    # ---------- Turma: acesso e contexto ----------

    def contexto(self, user: Optional[UserResponse], turma_id: str) -> Dict[str, Any]:
        turma = self.repo.contexto_turma(turma_id)
        if not turma:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")
        if user is not None:
            perfil = perfil_do_usuario(user)
            if perfil == "polo" and str(turma.get("polo_id")) != str(user.polo_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Turma")
            if perfil == "escola" and str(turma.get("escola_id")) != str(user.escola_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado a esta Turma")
        return turma

    @staticmethod
    def _exigir_calendario(turma: Dict[str, Any]) -> Dict[str, Any]:
        if not turma.get("curso_id"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A turma não tem curso vinculado.")
        if not turma.get("calendario"):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O curso da turma não está vinculado a um Calendário Acadêmico.",
            )
        if not turma.get("data_inicio") or not turma.get("data_fim"):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A turma precisa ter data de início e de término."
            )
        return turma["calendario"]

    # ---------- Cronograma (RN05) ----------

    def _montar_cronograma(self, turma: Dict[str, Any], alertas: List[str]) -> CronogramaResponse:
        previstas = self.repo.listar_aulas_previstas(turma["id"])
        disciplinas = self.repo.disciplinas_do_curso(turma["curso_id"]) if turma.get("curso_id") else []
        grupos: "OrderedDict[str, List[AulaPrevistaResponse]]" = OrderedDict((d["id"], []) for d in disciplinas)
        for a in previstas:
            grupos.setdefault(a["disciplina_id"], []).append(AulaPrevistaResponse(**a))
        nomes = {d["id"]: d for d in disciplinas}
        cal = turma.get("calendario") or {}
        return CronogramaResponse(
            turma_id=turma["id"],
            calendario_id=cal.get("id"),
            calendario_nome=cal.get("nome"),
            gerado=bool(previstas),
            alertas=alertas,
            disciplinas=[
                DisciplinaCronograma(
                    disciplina_id=disc_id,
                    nome=(nomes.get(disc_id) or {}).get("nome") or (aulas[0].disciplina_nome if aulas else "Disciplina"),
                    carga_horaria=int((nomes.get(disc_id) or {}).get("carga_horaria") or 0),
                    aulas=sorted(aulas, key=lambda a: a.numero),
                )
                for disc_id, aulas in grupos.items()
            ],
        )

    def cronograma(self, user: UserResponse, turma_id: str) -> CronogramaResponse:
        return self._montar_cronograma(self.contexto(user, turma_id), [])

    def gerar_cronograma(self, user: UserResponse, turma_id: str, ip: Optional[str]) -> CronogramaResponse:
        turma = self.contexto(user, turma_id)
        exigir_turma_editavel(turma)
        calendario = self._exigir_calendario(turma)
        regras = regras_do_calendario(calendario)
        disciplinas = self.repo.disciplinas_do_curso(turma["curso_id"])
        invalidas = [d["nome"] for d in disciplinas
                     if not d.get("carga_horaria") or (regras.fonte_qtd_aulas == "disciplina"
                                                       and not d.get("qtd_aulas_prevista"))]
        if invalidas:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Disciplinas sem carga horária ou quantidade de aulas (RN01): {', '.join(invalidas)}",
            )
        if not disciplinas:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O curso da turma não tem disciplinas ativas.")

        datas = datas_do_calendario(calendario, turma["data_inicio"], turma["data_fim"])
        resultado = cr.gerar_cronograma(_planos(disciplinas), datas, regras)
        if not resultado.capacidade["cabe"] and regras.capacidade_insuficiente == "bloquear":
            raise HTTPException(status.HTTP_409_CONFLICT, detail=resultado.alertas[0])

        realizadas = [a for a in self.repo.listar_aulas_previstas(turma_id) if a["status"] != "pendente"]
        cargas = {str(d["id"]): float(d["carga_horaria"]) for d in disciplinas}
        novas = cr.mesclar_com_realizadas(resultado.aulas, realizadas, cargas, regras)
        self.repo.substituir_pendentes(turma_id, novas)
        self.repo.auditar(user.id, "cronograma_gerado", "turmas", turma_id,
                          depois={"aulas_pendentes": len(novas), "aulas_realizadas": len(realizadas),
                                  "alertas": resultado.alertas}, ip=ip)
        return self._montar_cronograma(turma, resultado.alertas)

    # ---------- Andamento (RN04 / RN06) ----------

    def _dados_calculo(self, turma: Dict[str, Any]) -> Tuple[RegrasCalendario, List[cr.DisciplinaPlano],
                                                              List[Dict[str, Any]], List[Dict[str, Any]]]:
        regras = regras_do_calendario(turma.get("calendario"))
        disciplinas = _planos(self.repo.disciplinas_do_curso(turma["curso_id"])) if turma.get("curso_id") else []
        previstas = self.repo.listar_aulas_previstas(turma["id"])
        atas = []
        for ata in self.repo.listar_atas_turma(turma["id"]):
            atas.append({
                **ata,
                "tipo": ata.get("tipo") or "prevista",
                "chave": chave_aula(ata["professor_disciplina_id"], ata["data_aula"], ata["numero_aula"]),
            })
        return regras, disciplinas, previstas, atas

    def andamento(self, user: Optional[UserResponse], turma_id: str, hoje: Optional[date] = None) -> AndamentoResponse:
        turma = self.contexto(user, turma_id)
        regras, disciplinas, previstas, atas = self._dados_calculo(turma)
        hoje = hoje or date.today()
        dados = cr.calcular_andamento(disciplinas, previstas, atas, regras, hoje, turma.get("data_fim"))
        if not previstas:
            dados["alertas"].insert(0, "Cronograma ainda não gerado: gere o cronograma para acompanhar o andamento.")
        sem_ref = sum(1 for a in atas if a["tipo"] == "prevista" and not a.get("aula_prevista_id"))
        if sem_ref:
            dados["alertas"].append(f"{sem_ref} ata(s) sem aula prevista vinculada não abatem horas.")
        return AndamentoResponse(
            turma_id=turma_id, data_referencia=hoje, cronograma_gerado=bool(previstas),
            concluida_em=turma.get("concluida_em"), **dados,
        )

    # ---------- Frequência (RN07) ----------

    def frequencia(self, user: Optional[UserResponse], turma_id: str) -> FrequenciaResponse:
        turma = self.contexto(user, turma_id)
        regras, disciplinas, previstas, atas = self._dados_calculo(turma)
        presencas = [
            {**p, "chave": chave_aula(p["professor_disciplina_id"], p["data_aula"], p["numero_aula"])}
            for p in self.repo.listar_presencas_turma(turma_id)
        ]
        alunos = cr.calcular_frequencia(self.repo.alunos_turma(turma_id), disciplinas, atas, presencas, previstas, regras)
        return FrequenciaResponse(
            turma_id=turma_id, base=regras.frequencia_base, minimo_pct=regras.frequencia_minima_pct,
            alunos_em_risco=sum(1 for a in alunos if a["em_risco"]), alunos=alunos,
        )

    # ---------- Histórico (desempenho) da turma ----------

    def historico(self, user: Optional[UserResponse], turma_id: str) -> HistoricoTurmaResponse:
        """Desempenho da turma: notas finais (maior nota por aluno e disciplina) + frequência + índice 0–100."""
        from app.modules.admin.ranking_config import indice, obter_pesos

        turma = self.contexto(user, turma_id)
        ead = turma.get("modalidade") == "ead"
        pesos = obter_pesos()
        nota_minima = 6.0
        disciplinas = sorted(self.repo.disciplinas_do_curso(turma["curso_id"]) if turma.get("curso_id") else [],
                             key=lambda d: (d.get("semestre") or 0, d.get("ordem") or 0, d.get("nome") or ""))
        alunos = self.repo.alunos_turma(turma_id)
        ids_alunos = [a["aluno_id"] for a in alunos]
        notas = self.repo.notas_turma(ids_alunos, [d["id"] for d in disciplinas])

        finais: Dict[Tuple[str, str], float] = {}
        meses: Dict[str, List[float]] = {}
        for n in notas:
            chave = (n["aluno_id"], n["disciplina_id"])
            valor = float(n["valor"])
            finais[chave] = max(finais.get(chave, valor), valor)
            quando = n.get("lancado_em")
            if quando:
                meses.setdefault(f"{quando.year:04d}-{quando.month:02d}", []).append(valor)

        freq_alunos: Dict[str, Dict[str, Any]] = {}
        minimo = 75.0
        if not ead:
            try:
                f = self.frequencia(user, turma_id)
                minimo = f.minimo_pct
                freq_alunos = {a.aluno_id: a.model_dump() for a in f.alunos}
            except HTTPException:
                freq_alunos = {}

        def _media(vals: List[float]) -> Optional[float]:
            return round(sum(vals) / len(vals), 2) if vals else None

        linhas_disc = []
        for d in disciplinas:
            vals = [finais[(a, d["id"])] for a in ids_alunos if (a, d["id"]) in finais]
            freqs = [fd["frequencia_pct"] for fa in freq_alunos.values() for fd in fa.get("disciplinas", [])
                     if fd["disciplina_id"] == d["id"] and fd.get("frequencia_pct") is not None]
            linhas_disc.append(HistoricoDisciplina(
                disciplina_id=d["id"], nome=d.get("nome") or "", semestre=d.get("semestre"), media=_media(vals),
                aprovados=sum(1 for v in vals if v >= nota_minima), reprovados=sum(1 for v in vals if v < nota_minima),
                sem_nota=len(ids_alunos) - len(vals), frequencia_media=_media(freqs),
            ))

        linhas_alunos = []
        for a in alunos:
            vals = [v for (al, _), v in finais.items() if al == a["aluno_id"]]
            fa = freq_alunos.get(a["aluno_id"]) or {}
            freq = fa.get("frequencia_pct")
            media = _media(vals)
            if media is None and freq is None:
                situacao = "sem_dados"
            elif (media is not None and media < nota_minima) or fa.get("em_risco"):
                situacao = "atencao"
            else:
                situacao = "bom"
            linhas_alunos.append(HistoricoAluno(
                aluno_id=a["aluno_id"], nome=a.get("nome") or "", numero_matricula=a.get("numero_matricula"), media=media,
                aprovadas=sum(1 for v in vals if v >= nota_minima), reprovadas=sum(1 for v in vals if v < nota_minima),
                frequencia_pct=freq, em_risco=bool(fa.get("em_risco")), situacao=situacao,
            ))

        todas = list(finais.values())
        media_geral = _media(todas)
        freqs_alunos = [x["frequencia_pct"] for x in freq_alunos.values() if x.get("frequencia_pct") is not None]
        freq_media = round(sum(freqs_alunos) / len(freqs_alunos), 1) if freqs_alunos else None
        componentes: Dict[str, Optional[float]] = {"notas": media_geral * 10 if media_geral is not None else None}
        if not ead:
            componentes["frequencia"] = freq_media
        resumo = HistoricoResumo(
            alunos=len(alunos), media_geral=media_geral,
            aprovacao_pct=round(sum(1 for v in todas if v >= nota_minima) * 100 / len(todas), 1) if todas else None,
            notas_lancadas=len(todas), frequencia_media=freq_media,
            abaixo_minimo=sum(1 for x in freq_alunos.values() if x.get("em_risco")), minimo_pct=minimo,
            indice=indice(componentes, pesos),
        )
        return HistoricoTurmaResponse(
            turma_id=turma_id, modalidade=turma.get("modalidade") or "presencial", frequencia_aplica=not ead,
            peso_notas=pesos["peso_notas"], peso_frequencia=pesos["peso_frequencia"], resumo=resumo,
            disciplinas=linhas_disc, alunos=sorted(linhas_alunos, key=lambda x: (x.situacao != "atencao", x.nome.lower())),
            evolucao=[HistoricoMes(mes=m, media=round(sum(v) / len(v), 2), notas=len(v)) for m, v in sorted(meses.items())],
        )

    # ---------- Conclusão (Ponto em aberto 5) ----------

    def concluir(self, user: UserResponse, turma_id: str, ip: Optional[str]) -> ConclusaoResponse:
        turma = self.contexto(user, turma_id)
        if turma.get("concluida_em"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="A turma já está concluída.")
        if turma.get("cancelada_em"):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Turma cancelada: reabra antes de concluir.")
        andamento = self.andamento(user, turma_id)
        if not andamento.pode_concluir:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Saldo pendente de {andamento.saldo:g} h: o calendário bloqueia a conclusão até zerar o saldo.",
            )
        quando = self.repo.concluir_turma(turma_id, str(user.id))
        self.repo.auditar(user.id, "turma_concluida", "turmas", turma_id,
                          depois={"saldo_pendente": andamento.saldo, "progresso_pct": andamento.progresso_pct}, ip=ip)
        msg = "Turma concluída." if not andamento.saldo else f"Turma concluída com saldo de {andamento.saldo:g} h."
        return ConclusaoResponse(turma_id=turma_id, concluida_em=quando, saldo_pendente=andamento.saldo, message=msg)

    # ---------- Turmas EAD: prazo de cada disciplina ----------

    @staticmethod
    def _inicio_aluno(turma_inicio: Any, data_matricula: Any) -> date:
        datas = [d.date() if isinstance(d, datetime) else d for d in (turma_inicio, data_matricula) if d]
        return max(datas) if datas else date.today()

    def _disciplinas_ead(self, curso_id: Optional[str]) -> List[Dict[str, Any]]:
        if not curso_id:
            return []
        disciplinas = self.repo.disciplinas_do_curso(curso_id)
        return sorted(disciplinas, key=lambda d: (d.get("semestre") or 0, d.get("ordem") or 0, d.get("nome") or ""))

    def prazos_ead(self, user: Optional[UserResponse], turma_id: str, hoje: Optional[date] = None) -> PrazosEadResponse:
        turma = self.contexto(user, turma_id)
        if turma.get("modalidade") != "ead":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prazos por disciplina valem só para turma EAD.")
        regras = regras_do_calendario(turma.get("calendario"))
        disciplinas = self._disciplinas_ead(turma.get("curso_id"))
        alunos = self.repo.alunos_turma(turma_id)
        conclusoes = self.repo.conclusoes_ava([a["aluno_id"] for a in alunos], [d["id"] for d in disciplinas])
        saida = []
        for a in alunos:
            inicio = self._inicio_aluno(turma.get("data_inicio"), a.get("data_matricula"))
            minhas = {d_id: dt for (al, d_id), dt in conclusoes.items() if al == a["aluno_id"]}
            linhas = cr.cronograma_ead(disciplinas, inicio, regras, minhas, hoje)
            saida.append(PrazosAlunoEad(
                aluno_id=a["aluno_id"], nome=a.get("nome"), numero_matricula=a.get("numero_matricula"), inicio=inicio,
                vencidas=sum(1 for l in linhas if l["situacao"] == "vencida"),
                disciplinas=[PrazoDisciplinaEad(**l) for l in linhas],
            ))
        return PrazosEadResponse(
            turma_id=turma_id,
            regras={k: v for k, v in regras.model_dump().items() if k.startswith("ead_")},
            disciplinas=[{"disciplina_id": d["id"], "nome": d.get("nome"),
                          "prazo_dias": int(d.get("ead_prazo_dias") or regras.ead_prazo_dias_padrao)}
                         for d in disciplinas],
            alunos=saida,
        )

    def prazos_ead_do_aluno(
        self, aluno_id: str, conclusoes: Dict[str, date], hoje: Optional[date] = None
    ) -> Dict[str, Dict[str, Any]]:
        """{disciplina_id: {liberada_em, data_limite, situacao, ao_vencer}} das turmas EAD abertas do aluno (AVA)."""
        resultado: Dict[str, Dict[str, Any]] = {}
        for t in self.repo.turmas_ead_do_aluno(aluno_id):
            turma = self.repo.contexto_turma(t["turma_id"])
            if not turma:
                continue
            regras = regras_do_calendario(turma.get("calendario"))
            inicio = self._inicio_aluno(t.get("data_inicio"), t.get("data_matricula"))
            for linha in cr.cronograma_ead(self._disciplinas_ead(t.get("curso_id")), inicio, regras, conclusoes, hoje):
                resultado.setdefault(linha["disciplina_id"], {**linha, "ao_vencer": regras.ead_ao_vencer})
        return resultado
