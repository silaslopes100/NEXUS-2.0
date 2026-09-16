"""Cálculos de KPI, agregações e alertas do módulo `polos_escolas` (RN-03, RN-04)."""
from __future__ import annotations

from typing import List

from app.modules.polos_escolas.repository import PolosEscolasRepositoryInterface
from app.modules.polos_escolas.schemas import (
    AlertaResponse,
    DashboardDrilldownResponse,
    DashboardEscolaKpisResponse,
    DashboardFunilResponse,
    DashboardPoloKpisResponse,
    DashboardTreemapResponse,
    DrilldownAluno,
    DrilldownEscola,
    DrilldownPolo,
    FunilSerieItem,
    RelatorioDrilldownLinha,
    RelatorioDrilldownResponse,
    RelatorioDrilldownTotais,
    TreemapNode,
)


def _pct(numerador: float, denominador: float) -> float:
    """Calcula percentual protegido contra divisão por zero."""
    if not denominador:
        return 0.0
    return round((numerador / denominador) * 100, 2)


def calcular_kpis_polo(repo: PolosEscolasRepositoryInterface, polo_id: str) -> DashboardPoloKpisResponse:
    """RN-03: KPIs globais do Polo."""
    compradas = repo.sum_compradas(polo_id)
    vendidas = repo.count_licencas_vendidas_polo(polo_id)
    distribuidas = repo.sum_distribuidas(polo_id)
    estoque_polo = repo.get_estoque(polo_id=polo_id)["quantidade_disponivel"]
    escolas_estoque = repo.list_estoques_escolas_do_polo(polo_id)
    nao_vendidas_escolas = sum(e["disponivel"] for e in escolas_estoque)
    nao_vendidas_polo = estoque_polo

    return DashboardPoloKpisResponse(
        total_licencas_compradas=compradas,
        total_licencas_vendidas_alunos=vendidas,
        total_licencas_nao_vendidas=nao_vendidas_escolas + nao_vendidas_polo,
        total_nao_vendidas_escolas=nao_vendidas_escolas,
        total_nao_vendidas_polo=nao_vendidas_polo,
        taxa_conversao_global=_pct(vendidas, compradas),
        taxa_distribuicao=_pct(distribuidas, compradas),
    )


def calcular_funil(repo: PolosEscolasRepositoryInterface, polo_id: str) -> DashboardFunilResponse:
    """Gráfico de barras empilhadas por Escola (5 séries)."""
    compradas = repo.sum_compradas(polo_id)
    estoque_polo = repo.get_estoque(polo_id=polo_id)["quantidade_disponivel"]
    escolas_estoque = repo.list_estoques_escolas_do_polo(polo_id)

    series: List[FunilSerieItem] = []
    for escola in escolas_estoque:
        vendidas = repo.count_licencas_vendidas_escola(escola["escola_id"])
        series.append(
            FunilSerieItem(
                escola_id=escola["escola_id"],
                escola_nome=escola["nome"],
                compradas=compradas,
                distribuidas_escolas=escola["disponivel"] + vendidas,
                vendidas_alunos=vendidas,
                nao_vendidas_escolas=escola["disponivel"],
                nao_vendidas_polo=estoque_polo,
            )
        )
    return DashboardFunilResponse(polo_id=polo_id, series=series)


def calcular_treemap(repo: PolosEscolasRepositoryInterface, polo_id: str) -> DashboardTreemapResponse:
    """Hierarquia Polo > Escola > Status, tamanho proporcional à quantidade de licenças."""
    polo = repo.get_polo(polo_id)
    nome_polo = polo["nome"] if polo else polo_id
    escolas_estoque = repo.list_estoques_escolas_do_polo(polo_id)
    estoque_polo = repo.get_estoque(polo_id=polo_id)["quantidade_disponivel"]

    filhos_escolas: List[TreemapNode] = []
    for escola in escolas_estoque:
        vendidas = repo.count_licencas_vendidas_escola(escola["escola_id"])
        filhos_escolas.append(
            TreemapNode(
                nome=escola["nome"],
                valor=vendidas + escola["disponivel"],
                tipo="escola",
                filhos=[
                    TreemapNode(nome="Vendidas", valor=vendidas, tipo="status"),
                    TreemapNode(nome="Não Vendidas", valor=escola["disponivel"], tipo="status"),
                ],
            )
        )

    raiz = TreemapNode(
        nome=nome_polo,
        valor=sum(f.valor for f in filhos_escolas) + estoque_polo,
        tipo="polo",
        filhos=filhos_escolas + [TreemapNode(nome="Estoque do Polo", valor=estoque_polo, tipo="status")],
    )
    return DashboardTreemapResponse(polo_id=polo_id, raiz=raiz)


def calcular_drilldown(repo: PolosEscolasRepositoryInterface, polo_id: str) -> DashboardDrilldownResponse:
    """Tabela matriz drill-down: Polo → Escola → Aluno."""
    polo = repo.get_polo(polo_id)
    nome_polo = polo["nome"] if polo else polo_id
    compradas = repo.sum_compradas(polo_id)
    escolas_estoque = repo.list_estoques_escolas_do_polo(polo_id)

    escolas_out: List[DrilldownEscola] = []
    total_vendida_geral = 0
    total_nao_vendida_geral = 0

    for escola in escolas_estoque:
        _, alunos_licenciados = repo.list_alunos_licenciados_escola(escola["escola_id"], limit=1000, offset=0)
        alunos_out = [
            DrilldownAluno(
                aluno_id=str(a["aluno_id"]),
                nome=f"{a.get('nome', '')} {a.get('sobrenome', '')}".strip(),
                qtd_vendida=1 if a.get("status") == "ativa" else 0,
                qtd_nao_vendida=0 if a.get("status") == "ativa" else 1,
                percentual_ociosidade=0.0 if a.get("status") == "ativa" else 100.0,
            )
            for a in alunos_licenciados
        ]
        qtd_vendida_escola = repo.count_licencas_vendidas_escola(escola["escola_id"])
        qtd_recebida = qtd_vendida_escola + escola["disponivel"]
        escolas_out.append(
            DrilldownEscola(
                escola_id=escola["escola_id"],
                nome=escola["nome"],
                qtd_comprada=qtd_recebida,
                qtd_vendida=qtd_vendida_escola,
                qtd_nao_vendida=escola["disponivel"],
                percentual_ociosidade=_pct(escola["disponivel"], qtd_recebida),
                alunos=alunos_out,
            )
        )
        total_vendida_geral += qtd_vendida_escola
        total_nao_vendida_geral += escola["disponivel"]

    estoque_polo = repo.get_estoque(polo_id=polo_id)["quantidade_disponivel"]
    polo_out = DrilldownPolo(
        polo_id=polo_id,
        nome=nome_polo,
        qtd_comprada=compradas,
        qtd_vendida=total_vendida_geral,
        qtd_nao_vendida=total_nao_vendida_geral + estoque_polo,
        percentual_ociosidade=_pct(total_nao_vendida_geral + estoque_polo, compradas),
        escolas=escolas_out,
    )
    return DashboardDrilldownResponse(polo=polo_out)


def calcular_alertas_polo(repo: PolosEscolasRepositoryInterface, polo_id: str) -> List[AlertaResponse]:
    """RN-04: alertas visuais do Polo (amarelo: estoque próprio > 40%)."""
    alertas: List[AlertaResponse] = []
    compradas = repo.sum_compradas(polo_id)
    estoque_polo = repo.get_estoque(polo_id=polo_id)["quantidade_disponivel"]
    if _pct(estoque_polo, compradas) > 40:
        polo = repo.get_polo(polo_id)
        alertas.append(
            AlertaResponse(
                nivel="amarelo",
                escopo="polo",
                referencia_id=polo_id,
                referencia_nome=polo["nome"] if polo else polo_id,
                mensagem="Estoque próprio do Polo ultrapassa 40% das licenças compradas.",
            )
        )
    for escola in repo.list_estoques_escolas_do_polo(polo_id):
        alertas.extend(_alertas_de_escola(repo, escola["escola_id"], escola["nome"]))
    return alertas


def _alertas_de_escola(repo: PolosEscolasRepositoryInterface, escola_id: str, nome: str) -> List[AlertaResponse]:
    alertas: List[AlertaResponse] = []
    vendidas = repo.count_licencas_vendidas_escola(escola_id)
    estoque = repo.get_estoque(escola_id=escola_id)["quantidade_disponivel"]
    recebidas = vendidas + estoque
    ociosidade = _pct(estoque, recebidas)
    conversao = _pct(vendidas, recebidas)

    if ociosidade > 50:
        alertas.append(
            AlertaResponse(
                nivel="vermelho",
                escopo="escola",
                referencia_id=escola_id,
                referencia_nome=nome,
                mensagem=(
                    "Atenção: Mais da metade das licenças da escola estão paradas. "
                    "Considere devolver ao Polo ou promover uma ação de matrícula."
                ),
            )
        )
    if conversao < 20 and recebidas > 0:
        alertas.append(
            AlertaResponse(
                nivel="laranja",
                escopo="escola",
                referencia_id=escola_id,
                referencia_nome=nome,
                mensagem="Baixa conversão. Verifique se há alunos com matrículas pendentes.",
            )
        )
    return alertas


def calcular_kpis_escola(
    repo: PolosEscolasRepositoryInterface, escola_id: str
) -> DashboardEscolaKpisResponse:
    """RN-03: KPIs do Dashboard da Escola."""
    vendidas = repo.count_licencas_vendidas_escola(escola_id)
    estoque = repo.get_estoque(escola_id=escola_id)["quantidade_disponivel"]
    recebidas = vendidas + estoque
    return DashboardEscolaKpisResponse(
        licencas_recebidas=recebidas,
        licencas_vendidas=vendidas,
        licencas_nao_vendidas=estoque,
        taxa_conversao=_pct(vendidas, recebidas),
        taxa_ociosidade=_pct(estoque, recebidas),
    )


def calcular_alertas_escola(repo: PolosEscolasRepositoryInterface, escola_id: str) -> List[AlertaResponse]:
    escola = repo.get_escola(escola_id)
    nome = escola["nome"] if escola else escola_id
    return _alertas_de_escola(repo, escola_id, nome)


def gerar_relatorio_drilldown(
    repo: PolosEscolasRepositoryInterface, polo_id: str
) -> RelatorioDrilldownResponse:
    """Relatório dinâmico hierárquico com colunas Nível/Campo/Descrição/Fórmula."""
    compradas = repo.sum_compradas(polo_id)
    escolas_estoque = repo.list_estoques_escolas_do_polo(polo_id)

    linhas: List[RelatorioDrilldownLinha] = [
        RelatorioDrilldownLinha(
            nivel="Polo",
            campo="licencas_compradas",
            descricao="Total de licenças compradas pelo Polo",
            formula=str(compradas),
        )
    ]

    total_vendidas_por_escola = 0
    total_nao_vendidas_por_escola = 0

    for escola in escolas_estoque:
        vendidas = repo.count_licencas_vendidas_escola(escola["escola_id"])
        total_vendidas_por_escola += vendidas
        total_nao_vendidas_por_escola += escola["disponivel"]
        linhas.append(
            RelatorioDrilldownLinha(
                nivel="Escola",
                campo=f"escola:{escola['nome']}:vendidas",
                descricao=f"Licenças vendidas pela escola {escola['nome']}",
                formula=str(vendidas),
            )
        )
        linhas.append(
            RelatorioDrilldownLinha(
                nivel="Escola",
                campo=f"escola:{escola['nome']}:nao_vendidas",
                descricao=f"Licenças não vendidas (estoque) da escola {escola['nome']}",
                formula=str(escola["disponivel"]),
            )
        )
        _, alunos = repo.list_alunos_licenciados_escola(escola["escola_id"], limit=1000, offset=0)
        for aluno in alunos:
            linhas.append(
                RelatorioDrilldownLinha(
                    nivel="Aluno",
                    campo=f"aluno:{aluno['aluno_id']}:status",
                    descricao=f"Status da licença de {aluno.get('nome', '')}",
                    formula=aluno.get("status", ""),
                )
            )

    total_nao_vendidas_por_polo = compradas - total_vendidas_por_escola

    totais = RelatorioDrilldownTotais(
        total_vendidas_por_escola=total_vendidas_por_escola,
        total_nao_vendidas_por_escola=total_nao_vendidas_por_escola,
        total_nao_vendidas_por_polo=total_nao_vendidas_por_polo,
    )
    return RelatorioDrilldownResponse(polo_id=polo_id, linhas=linhas, totais=totais)
