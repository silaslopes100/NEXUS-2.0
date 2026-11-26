"""Schemas do módulo `carga_horaria` (Calendário Acadêmico, cronograma, andamento e frequência)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TipoAula = Literal["prevista", "reposicao", "extra", "reforco", "complemento", "revisao"]
TIPOS_QUE_ABATEM: tuple = ("prevista", "reposicao")
TIPOS_COMPLEMENTARES: tuple = ("extra", "reforco", "complemento", "revisao")
ROTULO_TIPO = {
    "prevista": "Aula prevista",
    "reposicao": "Reposição",
    "extra": "Extra",
    "reforco": "Reforço",
    "complemento": "Complemento de aula",
    "revisao": "Revisão de aula",
}


class RegrasCalendario(BaseModel):
    """Regras do calendário. Os pontos em aberto do documento são parâmetros ajustáveis.

    Todo curso segue as regras do calendário a que está vinculado; turmas herdam do curso.
    """

    model_config = ConfigDict(extra="ignore")

    carga_horaria_padrao: int = Field(default=40, gt=0, description="RN01: carga sugerida para novas disciplinas")
    disciplinas_por_mes: int = Field(default=2, ge=1, le=12, description="RN05")
    aulas_por_disciplina_mes: int = Field(default=2, ge=1, le=31, description="Ponto em aberto 1")
    fonte_qtd_aulas: Literal["calendario", "disciplina"] = Field(
        default="calendario",
        description="calendario: nº de aulas sai das datas do mês; disciplina: usa qtd_aulas_prevista",
    )
    duracao_aula: Literal["dividir_carga", "fixa"] = Field(
        default="dividir_carga", description="dividir_carga: carga ÷ nº de aulas; fixa: duracao_aula_horas"
    )
    duracao_aula_horas: float = Field(default=20, gt=0, le=200)
    quinta_semana: Literal["aula_extra", "ignorar"] = Field(
        default="aula_extra", description="5ª ocorrência do dia de aula no mês gera aula a mais (carga redividida)"
    )
    organizacao_disciplinas_mes: Literal["paralelo", "sequencial"] = Field(
        default="paralelo", description="Ponto em aberto 2: paralelo (A,B,A,B) ou sequencial (A,A,B,B)"
    )
    capacidade_insuficiente: Literal["alertar", "bloquear"] = Field(default="alertar", description="RN05")
    frequencia_base: Literal["aulas", "horas"] = Field(default="aulas", description="Ponto em aberto 4")
    frequencia_minima_pct: float = Field(default=75, ge=0, le=100, description="RN07")
    horas_abatidas: Literal["previstas", "registradas"] = Field(
        default="previstas", description="previstas: abate as horas da aula prevista; registradas: a duração da ata"
    )
    excluir_ata_devolve_saldo: bool = Field(
        default=True, description="RN03.5: excluir ata devolve horas; se falso, só admin exclui ata que abate horas"
    )
    perfis_alteram_tipo_aula: List[str] = Field(default_factory=lambda: ["admin", "polo"], description="RN03.5")
    saldo_ao_fim_turma: Literal["alertar", "bloquear_conclusao"] = Field(
        default="alertar", description="Ponto em aberto 5: alertar e o admin decide, ou bloquear a conclusão"
    )
    bloquear_ata_fora_periodo: bool = Field(default=True, description="RN03.5")
    # Turmas EAD: cada disciplina tem N dias depois de liberada (N próprio da disciplina, se houver).
    ead_prazo_dias_padrao: int = Field(default=30, ge=1, le=730, description="Turma EAD: dias para concluir")
    ead_liberacao: Literal["sequencial", "todas_no_inicio"] = Field(
        default="sequencial", description="sequencial: uma disciplina por vez; todas_no_inicio: tudo liberado"
    )
    ead_proxima_libera: Literal["anterior_concluida_ou_vencida", "anterior_vencida", "anterior_concluida"] = Field(
        default="anterior_concluida_ou_vencida", description="Quando a próxima disciplina é liberada (sequencial)"
    )
    ead_ao_vencer: Literal["bloquear", "alertar"] = Field(
        default="bloquear", description="bloquear: o AVA fecha a disciplina vencida; alertar: só avisa"
    )


class Feriado(BaseModel):
    data: date
    descricao: Optional[str] = Field(default=None, max_length=255)


class CalendarioWrite(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    descricao: Optional[str] = None
    data_inicio: date
    data_fim: date
    dias_semana: List[int] = Field(min_length=1, description="0=domingo .. 6=sábado")
    meses_recesso: List[int] = Field(default_factory=lambda: [7, 12])
    feriados: List[Feriado] = Field(default_factory=list)
    datas_excluidas: List[date] = Field(default_factory=list)
    datas_extras: List[date] = Field(default_factory=list)
    regras: RegrasCalendario = Field(default_factory=RegrasCalendario)
    ativo: bool = True

    @field_validator("dias_semana")
    @classmethod
    def _dias(cls, valor: List[int]) -> List[int]:
        if any(d < 0 or d > 6 for d in valor):
            raise ValueError("dias_semana aceita valores de 0 (domingo) a 6 (sábado)")
        return sorted(set(valor))

    @field_validator("meses_recesso")
    @classmethod
    def _meses(cls, valor: List[int]) -> List[int]:
        if any(m < 1 or m > 12 for m in valor):
            raise ValueError("meses_recesso aceita valores de 1 a 12")
        return sorted(set(valor))

    @model_validator(mode="after")
    def _periodo(self) -> "CalendarioWrite":
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim anterior a data_inicio")
        return self


class CalendarioResponse(CalendarioWrite):
    id: str
    total_cursos: int = 0
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class MesLetivo(BaseModel):
    mes: str  # AAAA-MM
    datas: List[date]
    quinta_semana: List[date] = Field(default_factory=list)
    recesso: bool = False


class DatasLetivasResponse(BaseModel):
    inicio: date
    fim: date
    total: int
    meses: List[MesLetivo]


# ---------- Cronograma ----------

StatusAulaPrevista = Literal["pendente", "realizada", "realizada_reposicao"]


class AulaPrevistaResponse(BaseModel):
    id: str
    turma_id: str
    disciplina_id: str
    disciplina_nome: Optional[str] = None
    numero: int
    data_prevista: date
    horas_previstas: float
    status: StatusAulaPrevista = "pendente"
    ata_id: Optional[str] = None
    ata_data: Optional[date] = None


class DisciplinaCronograma(BaseModel):
    disciplina_id: str
    nome: str
    carga_horaria: int
    aulas: List[AulaPrevistaResponse]


class CronogramaResponse(BaseModel):
    turma_id: str
    calendario_id: Optional[str] = None
    calendario_nome: Optional[str] = None
    gerado: bool
    alertas: List[str] = Field(default_factory=list)
    disciplinas: List[DisciplinaCronograma] = Field(default_factory=list)


# ---------- Andamento (RN04 / RN06) ----------

Situacao = Literal["em_dia", "atrasado", "nao_iniciada", "concluida"]


class AndamentoDisciplina(BaseModel):
    disciplina_id: str
    nome: str
    carga_horaria: float
    horas_abatidas: float
    saldo: float
    progresso_pct: float
    horas_complementares: float
    concluida: bool
    aulas_previstas: int
    aulas_realizadas: int
    previsto_ate_hoje_horas: float
    situacao: Situacao
    atraso_horas: float = 0
    atraso_aulas: int = 0


class AndamentoResponse(BaseModel):
    turma_id: str
    data_referencia: date
    cronograma_gerado: bool
    carga_total: float
    horas_abatidas: float
    saldo: float
    progresso_pct: float
    horas_complementares: float
    previsto_ate_hoje_horas: float
    situacao: Situacao
    atraso_horas: float = 0
    atraso_aulas: int = 0
    turma_encerrada: bool = False
    alertas: List[str] = Field(default_factory=list)
    concluida_em: Optional[datetime] = None
    pode_concluir: bool = True
    disciplinas: List[AndamentoDisciplina] = Field(default_factory=list)


# ---------- Frequência (RN07) ----------


class FrequenciaDisciplina(BaseModel):
    disciplina_id: str
    nome: str
    presencas: float
    registros: float
    frequencia_pct: Optional[float] = None


class FrequenciaAluno(BaseModel):
    aluno_id: str
    nome: str
    numero_matricula: Optional[str] = None
    frequencia_pct: Optional[float] = None
    em_risco: bool = False
    disciplinas: List[FrequenciaDisciplina] = Field(default_factory=list)


class FrequenciaResponse(BaseModel):
    turma_id: str
    base: Literal["aulas", "horas"]
    minimo_pct: float
    alunos_em_risco: int
    alunos: List[FrequenciaAluno]


class ConclusaoResponse(BaseModel):
    turma_id: str
    concluida_em: datetime
    saldo_pendente: float
    message: str


# ---------- Turmas EAD: prazos por disciplina ----------

class PrazoDisciplinaEad(BaseModel):
    disciplina_id: str
    nome: Optional[str] = None
    ordem: int
    prazo_dias: int
    liberada_em: Optional[date] = None
    data_limite: Optional[date] = None
    concluida_em: Optional[date] = None
    situacao: Literal["aguardando", "liberada", "concluida", "vencida"]


class PrazosAlunoEad(BaseModel):
    aluno_id: str
    nome: Optional[str] = None
    numero_matricula: Optional[str] = None
    inicio: date
    vencidas: int = 0
    disciplinas: List[PrazoDisciplinaEad] = Field(default_factory=list)


class PrazosEadResponse(BaseModel):
    turma_id: str
    regras: Dict[str, Any]
    disciplinas: List[Dict[str, Any]] = Field(default_factory=list)  # ordem e prazo de cada disciplina
    alunos: List[PrazosAlunoEad] = Field(default_factory=list)


# ---------- Histórico (desempenho) da turma ----------


class HistoricoResumo(BaseModel):
    alunos: int = 0
    media_geral: Optional[float] = None  # 0–10 (nota final = maior nota por aluno e disciplina)
    aprovacao_pct: Optional[float] = None  # notas finais >= nota mínima
    notas_lancadas: int = 0  # pares aluno × disciplina com nota final
    frequencia_media: Optional[float] = None
    abaixo_minimo: int = 0
    minimo_pct: float = 75.0
    indice: Optional[float] = None  # 0–100


class HistoricoDisciplina(BaseModel):
    disciplina_id: str
    nome: str
    semestre: Optional[int] = None
    media: Optional[float] = None
    aprovados: int = 0
    reprovados: int = 0
    sem_nota: int = 0
    frequencia_media: Optional[float] = None


class HistoricoAluno(BaseModel):
    aluno_id: str
    nome: str
    numero_matricula: Optional[str] = None
    media: Optional[float] = None
    aprovadas: int = 0
    reprovadas: int = 0
    frequencia_pct: Optional[float] = None
    em_risco: bool = False
    situacao: Literal["bom", "atencao", "sem_dados"] = "sem_dados"


class HistoricoMes(BaseModel):
    mes: str  # AAAA-MM
    media: float
    notas: int


class HistoricoTurmaResponse(BaseModel):
    turma_id: str
    modalidade: str = "presencial"
    frequencia_aplica: bool = True
    peso_notas: float
    peso_frequencia: float
    resumo: HistoricoResumo
    disciplinas: List[HistoricoDisciplina] = Field(default_factory=list)
    alunos: List[HistoricoAluno] = Field(default_factory=list)
    evolucao: List[HistoricoMes] = Field(default_factory=list)
