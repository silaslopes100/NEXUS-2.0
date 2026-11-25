"""Consultas da Dashboard Executiva (admin).

Mixins herdados por ``PostgresAdminRepository`` e ``InMemoryAdminRepository``:
mantêm as consultas analíticas fora do repositório principal sem mudar a
injeção de dependência (``get_admin_repository``) nem as fixtures de teste.

O repositório devolve só contagens brutas de um intervalo; período anterior,
variações e cobertura de estoque são calculados no service.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.database import get_db_cursor
from app.modules.financeiro.repository import ESCOPO_GLOBAL, where_periodo
from app.modules.financeiro.schemas import FiltrosPeriodo

# Saídas de licença para alunos (consumo do estoque).
TIPOS_CONSUMO_LICENCA = ("venda_aluno", "reingresso_churn")
# Mesmos predicados da tela de Vendas (financeiro/repository.kpis_vendas), para os números baterem.
PEDIDO_PAGO = "p.pago_em IS NOT NULL AND p.status <> 'cancelado'"
ORDENACOES_RANKING = ("novas_licencas", "receita_paga", "alunos_ativos", "presenca_pct")


def _normalizar(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in dict(row).items()}


def _where_sql(conds: Sequence[str]) -> str:
    return ("WHERE " + " AND ".join(conds)) if conds else ""


def _unidade_aluno(alias: str, polo_id: Optional[str], escola_id: Optional[str]) -> Tuple[str, List[Any]]:
    """Filtro de Polo/Escola pela lotação do aluno."""
    sql, params = "", []
    if polo_id:
        sql += f" AND {alias}.polo_id = %s"
        params.append(polo_id)
    if escola_id:
        sql += f" AND {alias}.escola_id = %s"
        params.append(escola_id)
    return sql, params


def _unidade_local(alias: str, polo_id: Optional[str], escola_id: Optional[str]) -> Tuple[str, List[Any]]:
    """Filtro para tabelas com polo_id OU escola_id (estoque/movimentações de licença)."""
    sql, params = "", []
    if polo_id:
        sql += f" AND ({alias}.polo_id = %s OR {alias}.escola_id IN (SELECT id FROM escolas WHERE polo_id = %s))"
        params.extend([polo_id, polo_id])
    if escola_id:
        sql += f" AND {alias}.escola_id = %s"
        params.append(escola_id)
    return sql, params


class PostgresDashboardMixin:
    def dashboard_contagens_periodo(
        self, inicio: date, fim: date, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]:
        ua, ua_p = _unidade_aluno("a", polo_id, escola_id)
        ul, ul_p = _unidade_local("lm", polo_id, escola_id)
        sql = f"""
            SELECT
                (SELECT COUNT(*) FROM alunos a
                  WHERE a.legacy_id IS NULL AND a.criado_em >= %s AND a.criado_em < %s::date + 1{ua}) AS novos_alunos,
                (SELECT COUNT(*) FROM matriculas_ead m JOIN alunos a ON a.id = m.aluno_id
                  WHERE m.data_matricula >= %s AND m.data_matricula < %s::date + 1{ua}) AS novas_matriculas,
                (SELECT COUNT(*) FROM alunos_desistentes d JOIN alunos a ON a.id = d.aluno_id
                  WHERE d.data_marcacao >= %s AND d.data_marcacao < %s::date + 1{ua}) AS desistencias,
                (SELECT COUNT(*) FROM presencas pr JOIN alunos a ON a.id = pr.aluno_id
                  WHERE COALESCE(pr.data_aula, pr.criado_em::date) BETWEEN %s AND %s{ua}) AS presencas_total,
                (SELECT COUNT(*) FROM presencas pr JOIN alunos a ON a.id = pr.aluno_id
                  WHERE pr.presente AND COALESCE(pr.data_aula, pr.criado_em::date) BETWEEN %s AND %s{ua})
                  AS presencas_positivas,
                (SELECT COUNT(*) FROM certificados ce LEFT JOIN alunos a ON a.id = ce.aluno_id
                  WHERE ce.emitido_em >= %s AND ce.emitido_em < %s::date + 1{ua}) AS certificados,
                (SELECT COALESCE(SUM(lm.quantidade), 0) FROM licencas_movimentacoes lm
                  WHERE lm.tipo IN %s AND lm.criado_em >= %s AND lm.criado_em < %s::date + 1{ul})
                  AS consumo_licencas
        """
        params: List[Any] = []
        for _ in range(6):
            params += [inicio, fim, *ua_p]
        params += [TIPOS_CONSUMO_LICENCA, inicio, fim, *ul_p]
        with get_db_cursor() as cur:
            cur.execute(sql, tuple(params))
            return {k: int(v or 0) for k, v in (cur.fetchone() or {}).items()}

    def dashboard_foto_atual(
        self, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Valores "agora": base ativa, estoque e filas de pendências (globais)."""
        ua, ua_p = _unidade_aluno("a", polo_id, escola_id)
        ul, ul_p = _unidade_local("le", polo_id, escola_id)
        sql = f"""
            SELECT
                (SELECT COUNT(*) FROM alunos a JOIN usuarios u ON u.id = a.usuario_id
                  WHERE a.status = 'ativo' AND u.status = 'ativo'{ua}) AS alunos_ativos,
                (SELECT COALESCE(SUM(le.quantidade_disponivel), 0) FROM licencas_estoque le
                  WHERE TRUE{ul}) AS estoque_disponivel,
                (SELECT COUNT(*) FROM solicitacoes_unidade WHERE status = 'pendente') AS solicitacoes_unidade_pendentes,
                (SELECT COUNT(*) FROM solicitacoes_transferencia WHERE status = 'pendente') AS transferencias_pendentes,
                (SELECT COUNT(*) FROM pedidos WHERE status = 'pago_aguardando_envio') AS pedidos_aguardando_envio,
                (SELECT COUNT(*) FROM pagamentos pg JOIN pedidos p ON p.id = pg.pedido_id
                  WHERE pg.status = 'vencido' AND p.status = 'aguardando_pagamento') AS cobrancas_vencidas_qtd,
                (SELECT COALESCE(SUM(pg.valor), 0) FROM pagamentos pg JOIN pedidos p ON p.id = pg.pedido_id
                  WHERE pg.status = 'vencido' AND p.status = 'aguardando_pagamento') AS cobrancas_vencidas_valor,
                (SELECT COUNT(*) FROM estagio_submissoes WHERE status = 'em_analise') AS estagios_em_analise
        """
        with get_db_cursor() as cur:
            cur.execute(sql, tuple(ua_p + ul_p))
            return _normalizar(cur.fetchone() or {})

    def dashboard_serie_mensal(
        self, fim: date, meses: int = 12, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Matrículas e desistências por mês, terminando no mês de ``fim``."""
        ua, ua_p = _unidade_aluno("a", polo_id, escola_id)
        sql = f"""
            WITH meses AS (
                SELECT generate_series(
                    date_trunc('month', %s::date) - make_interval(months => %s),
                    date_trunc('month', %s::date),
                    interval '1 month'
                )::date AS mes
            )
            SELECT to_char(ms.mes, 'YYYY-MM') AS mes,
                   (SELECT COUNT(*) FROM alunos a
                     WHERE a.legacy_id IS NULL AND a.criado_em >= ms.mes
                       AND a.criado_em < ms.mes + interval '1 month'{ua}) AS novos_alunos,
                   (SELECT COUNT(*) FROM matriculas_ead m JOIN alunos a ON a.id = m.aluno_id
                     WHERE m.data_matricula >= ms.mes
                       AND m.data_matricula < ms.mes + interval '1 month'{ua}) AS matriculas,
                   (SELECT COUNT(*) FROM alunos_desistentes d JOIN alunos a ON a.id = d.aluno_id
                     WHERE d.data_marcacao >= ms.mes
                       AND d.data_marcacao < ms.mes + interval '1 month'{ua}) AS desistencias
              FROM meses ms
             ORDER BY ms.mes
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (fim, meses - 1, fim, *ua_p, *ua_p, *ua_p))
            return [
                {
                    "mes": r["mes"],
                    "novos_alunos": int(r["novos_alunos"] or 0),
                    "matriculas": int(r["matriculas"] or 0),
                    "desistencias": int(r["desistencias"] or 0),
                }
                for r in cur.fetchall()
            ]

    def dashboard_ranking_polos(self, inicio: date, fim: date) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT po.id::text AS polo_id, po.nome AS polo_nome,
                   (SELECT COUNT(*) FROM alunos a JOIN usuarios u ON u.id = a.usuario_id
                     WHERE a.polo_id = po.id AND a.status = 'ativo' AND u.status = 'ativo') AS alunos_ativos,
                   (SELECT COUNT(*) FROM escolas e WHERE e.polo_id = po.id AND e.status = 'ativo') AS escolas_ativas,
                   (SELECT COALESCE(SUM(pi.quantidade), 0) FROM pedidos p JOIN pedidos_itens pi ON pi.pedido_id = p.id
                     WHERE p.polo_id = po.id AND p.tipo IN ('licenca', 'kit') AND {PEDIDO_PAGO}
                       AND p.criado_em >= %s AND p.criado_em < %s::date + 1) AS novas_licencas,
                   (SELECT COALESCE(SUM(p.valor_total), 0) FROM pedidos p
                     WHERE p.polo_id = po.id AND {PEDIDO_PAGO}
                       AND p.criado_em >= %s AND p.criado_em < %s::date + 1) AS receita_paga,
                   pres.total AS presencas_total, pres.positivas AS presencas_positivas
              FROM polos po
              LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE pr.presente) AS positivas
                      FROM presencas pr JOIN alunos a ON a.id = pr.aluno_id
                     WHERE a.polo_id = po.id
                       AND COALESCE(pr.data_aula, pr.criado_em::date) BETWEEN %s AND %s
              ) pres ON TRUE
             WHERE po.status = 'ativo'
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (inicio, fim, inicio, fim, inicio, fim))
            return [_normalizar(r) for r in cur.fetchall()]

    def dashboard_list_matriculas(
        self, filtros: FiltrosPeriodo, q: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds, params = where_periodo(filtros, ESCOPO_GLOBAL, alias="a", coluna_data="m.data_matricula")
        if q:
            conds.append("(lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s OR a.numero_matricula ILIKE %s)")
            params += [f"%{q.strip().lower()}%", f"%{q.strip()}%"]
        base = f"""
              FROM matriculas_ead m
              JOIN alunos a ON a.id = m.aluno_id
              JOIN usuarios u ON u.id = a.usuario_id
              LEFT JOIN cursos c ON c.id = m.curso_id
              LEFT JOIN polos po ON po.id = a.polo_id
              LEFT JOIN escolas e ON e.id = a.escola_id
              {_where_sql(conds)}
        """
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total {base}", tuple(params))
            total = int(cur.fetchone()["total"] or 0)
            cur.execute(
                f"""
                SELECT m.id::text AS id, a.id::text AS aluno_id,
                       concat_ws(' ', u.nome, u.sobrenome) AS aluno_nome, a.numero_matricula,
                       c.nome AS curso_nome, po.nome AS polo_nome, e.nome AS escola_nome, m.data_matricula
                {base}
                ORDER BY m.data_matricula DESC NULLS LAST, aluno_nome
                LIMIT %s OFFSET %s
                """,
                tuple(params + [filtros.limit, filtros.offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]

    def dashboard_list_certificados(
        self, filtros: FiltrosPeriodo, q: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        conds, params = where_periodo(filtros, ESCOPO_GLOBAL, alias="a", coluna_data="ce.emitido_em")
        conds.insert(0, "ce.emitido_em IS NOT NULL")
        if q:
            conds.append("(lower(concat_ws(' ', u.nome, u.sobrenome)) LIKE %s OR a.numero_matricula ILIKE %s)")
            params += [f"%{q.strip().lower()}%", f"%{q.strip()}%"]
        base = f"""
              FROM certificados ce
              LEFT JOIN alunos a ON a.id = ce.aluno_id
              LEFT JOIN usuarios u ON u.id = a.usuario_id
              LEFT JOIN cursos c ON c.id = ce.curso_id
              LEFT JOIN polos po ON po.id = a.polo_id
              {_where_sql(conds)}
        """
        with get_db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total {base}", tuple(params))
            total = int(cur.fetchone()["total"] or 0)
            cur.execute(
                f"""
                SELECT ce.id::text AS id, a.id::text AS aluno_id,
                       COALESCE(NULLIF(concat_ws(' ', u.nome, u.sobrenome), ''), 'Aluno removido') AS aluno_nome,
                       a.numero_matricula, c.nome AS curso_nome, po.nome AS polo_nome, ce.emitido_em,
                       ce.data_estagio_teologia_ministerio, ce.data_estagio_homiletica, ce.url_arquivo
                {base}
                ORDER BY ce.emitido_em DESC, aluno_nome
                LIMIT %s OFFSET %s
                """,
                tuple(params + [filtros.limit, filtros.offset]),
            )
            return total, [dict(r) for r in cur.fetchall()]


def _dia(valor: Any) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        return date.fromisoformat(valor[:10])
    return None


def _no_intervalo(valor: Any, inicio: Optional[date], fim: Optional[date]) -> bool:
    d = _dia(valor)
    if d is None:
        return False
    return (inicio is None or d >= inicio) and (fim is None or d <= fim)


def _bate_periodo(valor: Any, f: FiltrosPeriodo) -> bool:
    d = _dia(valor)
    if d is None:
        return not (f.data_inicio or f.data_fim or f.ano or f.mes or f.semestre)
    if not _no_intervalo(d, f.data_inicio, f.data_fim):
        return False
    if f.ano and d.year != f.ano:
        return False
    if f.mes and d.month != f.mes:
        return False
    if f.semestre and (d.month <= 6) != (f.semestre == 1):
        return False
    return True


class InMemoryDashboardMixin:
    """Versão em memória para os testes. Usa as listas do InMemoryAdminRepository
    (``alunos``, ``matriculas_ead``, ``presencas``, ``certificados``) e as abaixo."""

    alunos: Dict[str, Dict[str, Any]]
    matriculas_ead: List[Dict[str, Any]]
    presencas: List[Dict[str, Any]]
    certificados: List[Dict[str, Any]]

    def _init_dashboard(self) -> None:
        self.desistencias: List[Dict[str, Any]] = []
        self.licencas_movimentacoes: List[Dict[str, Any]] = []
        self.dashboard_foto: Dict[str, Any] = {
            "alunos_ativos": 0,
            "estoque_disponivel": 0,
            "solicitacoes_unidade_pendentes": 0,
            "transferencias_pendentes": 0,
            "pedidos_aguardando_envio": 0,
            "cobrancas_vencidas_qtd": 0,
            "cobrancas_vencidas_valor": 0.0,
            "estagios_em_analise": 0,
        }
        self.ranking_polos_rows: List[Dict[str, Any]] = []

    def _aluno_na_unidade(self, aluno_id: Any, polo_id: Optional[str], escola_id: Optional[str]) -> bool:
        if not polo_id and not escola_id:
            return True
        aluno = self.alunos.get(str(aluno_id)) or {}
        return (not polo_id or str(aluno.get("polo_id")) == polo_id) and (
            not escola_id or str(aluno.get("escola_id")) == escola_id
        )

    def dashboard_contagens_periodo(
        self, inicio: date, fim: date, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]:
        def conta(lista: List[Dict[str, Any]], campo: str) -> List[Dict[str, Any]]:
            return [
                r for r in lista
                if _no_intervalo(r.get(campo), inicio, fim) and self._aluno_na_unidade(r.get("aluno_id"), polo_id, escola_id)
            ]

        presencas = conta(self.presencas, "data_aula")
        consumo = sum(
            int(m.get("quantidade") or 0)
            for m in self.licencas_movimentacoes
            if m.get("tipo") in TIPOS_CONSUMO_LICENCA and _no_intervalo(m.get("criado_em"), inicio, fim)
            and (not polo_id or str(m.get("polo_id")) == polo_id)
            and (not escola_id or str(m.get("escola_id")) == escola_id)
        )
        nativos = [{**a, "aluno_id": aid} for aid, a in self.alunos.items() if not a.get("legacy_id")]
        return {
            "novos_alunos": len(conta(nativos, "criado_em")),
            "novas_matriculas": len(conta(self.matriculas_ead, "data_matricula")),
            "desistencias": len(conta(self.desistencias, "data_marcacao")),
            "presencas_total": len(presencas),
            "presencas_positivas": sum(1 for p in presencas if p.get("presente")),
            "certificados": len(conta(self.certificados, "emitido_em")),
            "consumo_licencas": consumo,
        }

    def dashboard_foto_atual(
        self, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return dict(self.dashboard_foto)

    def dashboard_serie_mensal(
        self, fim: date, meses: int = 12, polo_id: Optional[str] = None, escola_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        ano, mes = fim.year, fim.month
        chaves: List[str] = []
        for _ in range(meses):
            chaves.append(f"{ano:04d}-{mes:02d}")
            mes -= 1
            if mes == 0:
                ano, mes = ano - 1, 12
        chaves.reverse()

        def por_mes(lista: List[Dict[str, Any]], campo: str) -> Dict[str, int]:
            out: Dict[str, int] = {}
            for r in lista:
                d = _dia(r.get(campo))
                if d and self._aluno_na_unidade(r.get("aluno_id"), polo_id, escola_id):
                    k = f"{d.year:04d}-{d.month:02d}"
                    out[k] = out.get(k, 0) + 1
            return out

        nativos = [{**a, "aluno_id": aid} for aid, a in self.alunos.items() if not a.get("legacy_id")]
        nov = por_mes(nativos, "criado_em")
        mat = por_mes(self.matriculas_ead, "data_matricula")
        des = por_mes(self.desistencias, "data_marcacao")
        return [
            {"mes": k, "novos_alunos": nov.get(k, 0), "matriculas": mat.get(k, 0), "desistencias": des.get(k, 0)}
            for k in chaves
        ]

    def dashboard_ranking_polos(self, inicio: date, fim: date) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.ranking_polos_rows]

    def _lista_dashboard(
        self, lista: List[Dict[str, Any]], campo: str, filtros: FiltrosPeriodo, q: Optional[str]
    ) -> Tuple[int, List[Dict[str, Any]]]:
        itens = [
            r for r in lista
            if r.get(campo) is not None and _bate_periodo(r.get(campo), filtros)
            and self._aluno_na_unidade(r.get("aluno_id"), filtros.polo_id, filtros.escola_id)
            and (not q or q.strip().lower() in str(r.get("aluno_nome", "")).lower())
        ]
        itens.sort(key=lambda r: _dia(r.get(campo)) or date.min, reverse=True)
        return len(itens), [dict(r) for r in itens[filtros.offset: filtros.offset + filtros.limit]]

    def dashboard_list_matriculas(
        self, filtros: FiltrosPeriodo, q: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        return self._lista_dashboard(self.matriculas_ead, "data_matricula", filtros, q)

    def dashboard_list_certificados(
        self, filtros: FiltrosPeriodo, q: Optional[str] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        return self._lista_dashboard(self.certificados, "emitido_em", filtros, q)
