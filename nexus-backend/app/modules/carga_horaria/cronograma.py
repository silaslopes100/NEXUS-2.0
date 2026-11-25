"""Regras de carga horária, cronograma, andamento e frequência — funções puras (sem banco).

Tudo aqui recebe dicionários/objetos simples e devolve resultados, para que cada regra
(RN04–RN07) e cada parâmetro do calendário seja testável isoladamente.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.modules.carga_horaria.schemas import TIPOS_QUE_ABATEM, RegrasCalendario

DIAS_SEMANA = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]


def _dia_semana(d: date) -> int:
    """0=domingo .. 6=sábado (Python usa 0=segunda)."""
    return (d.weekday() + 1) % 7


def _chave_mes(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def eh_quinta_ocorrencia(d: date) -> bool:
    """A data é a 5ª ocorrência do seu dia da semana no mês ("mês de 5 semanas")."""
    return (d.day - 1) // 7 == 4


def _arred(valor: float) -> float:
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Datas letivas
# ---------------------------------------------------------------------------


def datas_letivas(
    inicio: date,
    fim: date,
    dias_semana: Iterable[int],
    meses_recesso: Iterable[int] = (),
    feriados: Iterable[date] = (),
    datas_excluidas: Iterable[date] = (),
    datas_extras: Iterable[date] = (),
) -> List[date]:
    """Dias de aula entre `inicio` e `fim`: dias da semana do calendário, sem recesso,
    feriados e datas excluídas, mais as datas extras (que valem mesmo em recesso)."""
    if fim < inicio:
        return []
    dias = set(dias_semana)
    recesso = set(meses_recesso)
    fora: Set[date] = set(feriados) | set(datas_excluidas)
    resultado: Set[date] = set()
    atual = inicio
    while atual <= fim:
        if _dia_semana(atual) in dias and atual.month not in recesso and atual not in fora:
            resultado.add(atual)
        atual += timedelta(days=1)
    resultado |= {d for d in datas_extras if inicio <= d <= fim and d not in fora}
    return sorted(resultado)


def agrupar_por_mes(datas: Sequence[date]) -> "OrderedDict[str, List[date]]":
    meses: "OrderedDict[str, List[date]]" = OrderedDict()
    for d in sorted(datas):
        meses.setdefault(_chave_mes(d), []).append(d)
    return meses


def meses_no_intervalo(inicio: date, fim: date) -> List[str]:
    meses, ano, mes = [], inicio.year, inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        meses.append(f"{ano:04d}-{mes:02d}")
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
    return meses


def capacidade(n_disciplinas: int, meses_letivos: int, regras: RegrasCalendario) -> Dict[str, Any]:
    """RN05: meses necessários = nº de disciplinas ÷ disciplinas por mês (arredondado para cima)."""
    necessarios = math.ceil(n_disciplinas / regras.disciplinas_por_mes) if n_disciplinas else 0
    return {"meses_necessarios": necessarios, "meses_disponiveis": meses_letivos, "cabe": necessarios <= meses_letivos}


# ---------------------------------------------------------------------------
# Geração do cronograma (RN05)
# ---------------------------------------------------------------------------


@dataclass
class DisciplinaPlano:
    id: str
    nome: str
    carga_horaria: float
    qtd_aulas_prevista: int = 0


@dataclass
class AulaPlanejada:
    disciplina_id: str
    numero: int
    data: date
    horas: float


@dataclass
class ResultadoCronograma:
    aulas: List[AulaPlanejada] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)
    capacidade: Dict[str, Any] = field(default_factory=dict)


def _distribuir(slots: List[date], grupo: List[DisciplinaPlano], modo: str) -> Dict[str, List[date]]:
    """paralelo: A,B,A,B…; sequencial: blocos contíguos (A,A,B,B)."""
    destino: Dict[str, List[date]] = {d.id: [] for d in grupo}
    if not grupo:
        return destino
    if modo == "sequencial":
        base, sobra = divmod(len(slots), len(grupo))
        pos = 0
        for i, disc in enumerate(grupo):
            qtd = base + (1 if i < sobra else 0)
            destino[disc.id] = slots[pos: pos + qtd]
            pos += qtd
    else:
        for i, d in enumerate(slots):
            destino[grupo[i % len(grupo)].id].append(d)
    return destino


def horas_das_aulas(carga: float, n_aulas: int, regras: RegrasCalendario) -> List[float]:
    """dividir_carga: carga ÷ nº de aulas, com a última aula absorvendo o arredondamento
    (a soma fecha exatamente a carga); fixa: duracao_aula_horas em todas."""
    if n_aulas <= 0:
        return []
    if regras.duracao_aula == "fixa":
        return [float(regras.duracao_aula_horas)] * n_aulas
    unidade = _arred(carga / n_aulas)
    horas = [unidade] * (n_aulas - 1)
    horas.append(_arred(carga - unidade * (n_aulas - 1)))
    return horas


def gerar_cronograma(
    disciplinas: Sequence[DisciplinaPlano], datas: Sequence[date], regras: RegrasCalendario
) -> ResultadoCronograma:
    """Distribui as disciplinas do curso nas datas letivas da turma.

    - Cada mês recebe `disciplinas_por_mes` disciplinas (na ordem recebida).
    - Modo `calendario`: cada disciplina do mês recebe `aulas_por_disciplina_mes` aulas;
      com `quinta_semana=aula_extra`, as 5ªs ocorrências do mês viram aulas a mais.
    - Modo `disciplina`: a disciplina segue nos meses seguintes até `qtd_aulas_prevista`.
    """
    resultado = ResultadoCronograma()
    meses = agrupar_por_mes(datas)
    resultado.capacidade = capacidade(len(disciplinas), len(meses), regras)
    if not resultado.capacidade["cabe"]:
        resultado.alertas.append(
            f"O curso precisa de {resultado.capacidade['meses_necessarios']} meses letivos "
            f"({len(disciplinas)} disciplinas ÷ {regras.disciplinas_por_mes} por mês), "
            f"mas o período da turma tem {resultado.capacidade['meses_disponiveis']}."
        )

    datas_por_disc: Dict[str, List[date]] = {d.id: [] for d in disciplinas}
    fila = list(disciplinas)
    ativos: List[DisciplinaPlano] = []
    modo_disciplina = regras.fonte_qtd_aulas == "disciplina"

    for mes, datas_mes in meses.items():
        if modo_disciplina:
            ativos = [d for d in ativos if len(datas_por_disc[d.id]) < max(d.qtd_aulas_prevista, 1)]
            while len(ativos) < regras.disciplinas_por_mes and fila:
                ativos.append(fila.pop(0))
            grupo = list(ativos)
        else:
            grupo = [fila.pop(0) for _ in range(min(regras.disciplinas_por_mes, len(fila)))]
        if not grupo:
            break

        normais = [d for d in datas_mes if not eh_quinta_ocorrencia(d)]
        quintas = [d for d in datas_mes if eh_quinta_ocorrencia(d)]
        if modo_disciplina:
            faltam = sum(max(d.qtd_aulas_prevista, 1) - len(datas_por_disc[d.id]) for d in grupo)
            necessarias = min(faltam, len(grupo) * regras.aulas_por_disciplina_mes)
        else:
            necessarias = len(grupo) * regras.aulas_por_disciplina_mes
        slots = normais[:necessarias]
        if len(slots) < necessarias:
            resultado.alertas.append(
                f"{mes}: {len(slots)} data(s) letiva(s) para {necessarias} aula(s) previstas no mês."
            )
        if regras.quinta_semana == "aula_extra":
            slots = sorted(slots + quintas)

        destino = _distribuir(slots, grupo, regras.organizacao_disciplinas_mes)
        for disc in grupo:
            novas = destino[disc.id]
            if modo_disciplina:
                restante = max(disc.qtd_aulas_prevista, 1) - len(datas_por_disc[disc.id])
                novas = novas[:max(restante, 0)]
            datas_por_disc[disc.id].extend(novas)

    if modo_disciplina:
        fila = [d for d in ativos if len(datas_por_disc[d.id]) < max(d.qtd_aulas_prevista, 1)] + fila

    for disc in disciplinas:
        datas_disc = sorted(datas_por_disc[disc.id])
        if not datas_disc:
            resultado.alertas.append(f"Disciplina \"{disc.nome}\" ficou sem aulas no período da turma.")
            continue
        if modo_disciplina and len(datas_disc) < max(disc.qtd_aulas_prevista, 1):
            resultado.alertas.append(
                f"Disciplina \"{disc.nome}\": {len(datas_disc)} de {disc.qtd_aulas_prevista} aulas couberam no período."
            )
        for numero, (d, h) in enumerate(zip(datas_disc, horas_das_aulas(disc.carga_horaria, len(datas_disc), regras)), 1):
            resultado.aulas.append(AulaPlanejada(disciplina_id=disc.id, numero=numero, data=d, horas=h))
    return resultado


def mesclar_com_realizadas(
    geradas: Sequence[AulaPlanejada],
    realizadas: Sequence[Dict[str, Any]],
    cargas: Dict[str, float],
    regras: RegrasCalendario,
) -> List[AulaPlanejada]:
    """Ao regerar, as aulas já cumpridas ficam; as novas pendentes continuam a numeração
    e dividem só a carga que ainda falta (a soma continua fechando a carga)."""
    por_disc: Dict[str, List[AulaPlanejada]] = {}
    for a in geradas:
        por_disc.setdefault(a.disciplina_id, []).append(a)
    feitas: Dict[str, List[Dict[str, Any]]] = {}
    for r in realizadas:
        feitas.setdefault(str(r["disciplina_id"]), []).append(r)

    saida: List[AulaPlanejada] = []
    for disc_id, aulas in por_disc.items():
        cumpridas = feitas.get(disc_id, [])
        restantes = aulas[len(cumpridas):]
        if not restantes:
            continue
        proximo = max((int(c["numero"]) for c in cumpridas), default=0) + 1
        carga_restante = max(cargas.get(disc_id, 0) - sum(float(c["horas_previstas"]) for c in cumpridas), 0)
        if regras.duracao_aula == "dividir_carga" and carga_restante > 0:
            horas = horas_das_aulas(carga_restante, len(restantes), regras)
        else:
            horas = [a.horas for a in restantes]
        for i, (a, h) in enumerate(zip(restantes, horas)):
            saida.append(AulaPlanejada(disciplina_id=disc_id, numero=proximo + i, data=a.data, horas=h))
    return saida


# ---------------------------------------------------------------------------
# Andamento (RN04 / RN06) e frequência (RN07)
# ---------------------------------------------------------------------------


def status_aula_prevista(ata_tipo: Optional[str]) -> str:
    if ata_tipo == "prevista":
        return "realizada"
    if ata_tipo == "reposicao":
        return "realizada_reposicao"
    return "pendente"


def horas_abatidas_da_ata(ata: Dict[str, Any], aula_prevista: Optional[Dict[str, Any]], regras: RegrasCalendario) -> float:
    if ata.get("tipo") not in TIPOS_QUE_ABATEM or not aula_prevista:
        return 0.0
    if regras.horas_abatidas == "registradas" and ata.get("horas") is not None:
        return float(ata["horas"])
    return float(aula_prevista["horas_previstas"])


def calcular_andamento(
    disciplinas: Sequence[DisciplinaPlano],
    aulas_previstas: Sequence[Dict[str, Any]],
    atas: Sequence[Dict[str, Any]],
    regras: RegrasCalendario,
    hoje: date,
    data_fim_turma: Optional[date] = None,
) -> Dict[str, Any]:
    """Progresso (RN04) e previsto × realizado (RN06) por disciplina e consolidado.

    `aulas_previstas`: {id, disciplina_id, data_prevista, horas_previstas}
    `atas`: {id, disciplina_id, tipo, horas, aula_prevista_id}
    """
    previstas_por_id = {str(a["id"]): a for a in aulas_previstas}
    cumpridas: Dict[str, Dict[str, Any]] = {}  # aula_prevista_id -> ata que a cumpre
    for ata in atas:
        ref = ata.get("aula_prevista_id")
        if ata.get("tipo") in TIPOS_QUE_ABATEM and ref and str(ref) in previstas_por_id:
            cumpridas.setdefault(str(ref), ata)

    linhas = []
    for disc in disciplinas:
        prevs = [a for a in aulas_previstas if str(a["disciplina_id"]) == disc.id]
        abatidas = sum(
            horas_abatidas_da_ata(cumpridas[str(a["id"])], a, regras) for a in prevs if str(a["id"]) in cumpridas
        )
        complementares = sum(
            float(ata.get("horas") or 0) for ata in atas
            if str(ata.get("disciplina_id")) == disc.id and ata.get("tipo") not in TIPOS_QUE_ABATEM
        )
        ate_hoje = [a for a in prevs if a["data_prevista"] <= hoje]
        previsto = sum(float(a["horas_previstas"]) for a in ate_hoje)
        atraso_aulas = sum(1 for a in ate_hoje if str(a["id"]) not in cumpridas)
        carga = float(disc.carga_horaria)
        saldo = max(_arred(carga - abatidas), 0.0)
        concluida = carga > 0 and saldo <= 0
        if concluida:
            situacao = "concluida"
        elif not ate_hoje:
            situacao = "nao_iniciada"
        elif abatidas + 1e-9 >= previsto:
            situacao = "em_dia"
        else:
            situacao = "atrasado"
        linhas.append({
            "disciplina_id": disc.id,
            "nome": disc.nome,
            "carga_horaria": carga,
            "horas_abatidas": _arred(abatidas),
            "saldo": saldo,
            "progresso_pct": _arred(min(abatidas / carga * 100, 100)) if carga else 0.0,
            "horas_complementares": _arred(complementares),
            "concluida": concluida,
            "aulas_previstas": len(prevs),
            "aulas_realizadas": sum(1 for a in prevs if str(a["id"]) in cumpridas),
            "previsto_ate_hoje_horas": _arred(previsto),
            "situacao": situacao,
            "atraso_horas": _arred(max(previsto - abatidas, 0)) if situacao == "atrasado" else 0.0,
            "atraso_aulas": atraso_aulas if situacao == "atrasado" else 0,
        })

    carga_total = sum(l["carga_horaria"] for l in linhas)
    abatidas_total = sum(l["horas_abatidas"] for l in linhas)
    previsto_total = sum(l["previsto_ate_hoje_horas"] for l in linhas)
    saldo_total = max(_arred(carga_total - abatidas_total), 0.0)
    if carga_total and saldo_total <= 0:
        situacao_total = "concluida"
    elif previsto_total <= 0:
        situacao_total = "nao_iniciada"
    elif abatidas_total + 1e-9 >= previsto_total:
        situacao_total = "em_dia"
    else:
        situacao_total = "atrasado"

    encerrada = bool(data_fim_turma and hoje > data_fim_turma)
    alertas: List[str] = []
    if encerrada and saldo_total > 0:
        alertas.append(
            f"Turma encerrada em {data_fim_turma:%d/%m/%Y} com saldo de {saldo_total:g} h. "
            + ("A Diretoria decide se a turma está concluída." if regras.saldo_ao_fim_turma == "alertar"
               else "A conclusão fica bloqueada até zerar o saldo.")
        )
    return {
        "carga_total": _arred(carga_total),
        "horas_abatidas": _arred(abatidas_total),
        "saldo": saldo_total,
        "progresso_pct": _arred(min(abatidas_total / carga_total * 100, 100)) if carga_total else 0.0,
        "horas_complementares": _arred(sum(l["horas_complementares"] for l in linhas)),
        "previsto_ate_hoje_horas": _arred(previsto_total),
        "situacao": situacao_total,
        "atraso_horas": _arred(max(previsto_total - abatidas_total, 0)) if situacao_total == "atrasado" else 0.0,
        "atraso_aulas": sum(l["atraso_aulas"] for l in linhas),
        "turma_encerrada": encerrada,
        "alertas": alertas,
        "pode_concluir": not (regras.saldo_ao_fim_turma == "bloquear_conclusao" and saldo_total > 0),
        "disciplinas": linhas,
    }


def calcular_frequencia(
    alunos: Sequence[Dict[str, Any]],
    disciplinas: Sequence[DisciplinaPlano],
    atas: Sequence[Dict[str, Any]],
    presencas: Sequence[Dict[str, Any]],
    aulas_previstas: Sequence[Dict[str, Any]],
    regras: RegrasCalendario,
) -> List[Dict[str, Any]]:
    """RN07: frequência só sobre atas de aulas previstas e reposições.

    Presença em Extra/Reforço/Complemento/Revisão não soma nem gera falta.
    `atas`: {id, disciplina_id, tipo, horas, aula_prevista_id, chave}
    `presencas`: {aluno_id, chave, presente} — `chave` liga a presença à ata
    (vínculo docente, data e número da aula).
    """
    previstas_por_id = {str(a["id"]): a for a in aulas_previstas}
    atas_validas = {
        a["chave"]: a for a in atas
        if a.get("tipo") in TIPOS_QUE_ABATEM and a.get("aula_prevista_id")
        and str(a["aula_prevista_id"]) in previstas_por_id
    }
    nomes = {d.id: d.nome for d in disciplinas}

    def peso(ata: Dict[str, Any]) -> float:
        if regras.frequencia_base == "aulas":
            return 1.0
        return horas_abatidas_da_ata(ata, previstas_por_id.get(str(ata["aula_prevista_id"])), regras)

    saida = []
    for aluno in alunos:
        por_disc: Dict[str, List[float]] = {}
        for p in presencas:
            if str(p["aluno_id"]) != str(aluno["aluno_id"]):
                continue
            ata = atas_validas.get(p["chave"])
            if not ata or p.get("presente") is None:
                continue
            soma = por_disc.setdefault(str(ata["disciplina_id"]), [0.0, 0.0])
            soma[1] += peso(ata)
            if p["presente"]:
                soma[0] += peso(ata)
        linhas = [
            {
                "disciplina_id": disc_id,
                "nome": nomes.get(disc_id, "Disciplina"),
                "presencas": _arred(pres),
                "registros": _arred(total),
                "frequencia_pct": _arred(pres / total * 100) if total else None,
            }
            for disc_id, (pres, total) in por_disc.items()
        ]
        pres_total = sum(l["presencas"] for l in linhas)
        reg_total = sum(l["registros"] for l in linhas)
        pct = _arred(pres_total / reg_total * 100) if reg_total else None
        saida.append({
            "aluno_id": str(aluno["aluno_id"]),
            "nome": aluno.get("nome") or "Aluno",
            "numero_matricula": aluno.get("numero_matricula"),
            "frequencia_pct": pct,
            "em_risco": pct is not None and pct < regras.frequencia_minima_pct,
            "disciplinas": sorted(linhas, key=lambda l: l["nome"]),
        })
    return sorted(saida, key=lambda a: (not a["em_risco"], (a["nome"] or "").lower()))


# ---------- Turmas EAD: liberação e prazo de cada disciplina ----------

def cronograma_ead(
    disciplinas: Sequence[Dict[str, Any]],
    inicio: date,
    regras: RegrasCalendario,
    conclusoes: Optional[Dict[str, date]] = None,
    hoje: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Liberação e data limite de cada disciplina do aluno na turma EAD.

    `disciplinas` já vem na ordem do curso: {id, nome, ead_prazo_dias}. Cada disciplina tem N dias
    depois de liberada (N próprio da disciplina ou `ead_prazo_dias_padrao`). Na liberação
    sequencial, a próxima libera conforme `ead_proxima_libera`. `conclusoes`: {disciplina_id: data}.
    """
    conclusoes = conclusoes or {}
    hoje = hoje or date.today()
    saida: List[Dict[str, Any]] = []
    liberacao: Optional[date] = inicio
    for ordem, d in enumerate(disciplinas, start=1):
        prazo = int(d.get("ead_prazo_dias") or regras.ead_prazo_dias_padrao)
        if regras.ead_liberacao == "todas_no_inicio":
            liberacao = inicio
        limite = liberacao + timedelta(days=prazo) if liberacao else None
        concluida_em = conclusoes.get(str(d["id"]))
        if concluida_em:
            situacao_d = "concluida"
        elif liberacao is None or liberacao > hoje:
            situacao_d = "aguardando"
        elif limite and hoje > limite:
            situacao_d = "vencida"
        else:
            situacao_d = "liberada"
        saida.append({
            "disciplina_id": str(d["id"]), "nome": d.get("nome"), "ordem": ordem, "prazo_dias": prazo,
            "liberada_em": liberacao, "data_limite": limite, "concluida_em": concluida_em,
            "situacao": situacao_d,
        })
        if regras.ead_liberacao == "todas_no_inicio" or liberacao is None:
            continue
        # Próxima liberação (sequencial).
        vence = limite + timedelta(days=1)
        concluiu_no_prazo = concluida_em if concluida_em and concluida_em <= limite else None
        if regras.ead_proxima_libera == "anterior_vencida":
            liberacao = vence
        elif regras.ead_proxima_libera == "anterior_concluida":
            liberacao = max(concluida_em, liberacao) if concluida_em else None
        else:  # anterior_concluida_ou_vencida
            liberacao = max(concluiu_no_prazo, liberacao) if concluiu_no_prazo else vence
    return saida
