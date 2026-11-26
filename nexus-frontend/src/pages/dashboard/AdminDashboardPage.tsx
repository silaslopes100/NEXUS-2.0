import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Activity, CalendarRange, KeyRound, Percent, TrendingUp, Users, Wallet } from 'lucide-react';
import { LinhaMensal } from '@/components/charts/GraficoBarrasMensal';
import { PeriodoFiltros, useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { adminApi } from '@/features/admin/api';
import { AtividadeDocente, aulasApi, dataLocalMenosDias } from '@/features/aulas/api';
import { financeiroApi } from '@/features/financeiro/api';
import { VendasKpis, VendasSerieItem, formatBRL } from '@/features/financeiro/types';
import { useAuthStore } from '@/stores/authStore';
import {
  AdminDashboardMetrics, DashboardExecutivo, FiltrosDashboard, OrdenacaoRanking, RankingPolos as Ranking,
} from '@/types/admin';
import { AtividadeDocentePainel, DIAS_ATIVIDADE, DIAS_SEM_REGISTRO } from './admin/AtividadeDocente';
import { BlocoAcademico, BlocoCrescimento, BlocoLicencas, BlocoReceita } from './admin/BlocosIndicadores';
import { CentralPendencias } from './admin/CentralPendencias';
import { KpiVariacao } from './admin/KpiVariacao';
import { RankingPolos } from './admin/RankingPolos';
import { VisualizadoresReais } from './admin/VisualizadoresReais';
import { fmtData, fmtInt, fmtPct, isoLocal, ultimos12Meses, variacaoPct } from './admin/formato';

const CHAVES_PERIODO = ['data_inicio', 'data_fim', 'mes', 'semestre', 'ano'] as const;
const ATALHOS = [
  { rotulo: '30 dias', dias: 30 },
  { rotulo: '90 dias', dias: 90 },
  { rotulo: '12 meses', dias: 365 },
] as const;

/** Receita: mesmo endpoint e critério da tela de Vendas, no período resolvido pelo painel. */
interface Receita {
  atual: VendasKpis;
  anterior: VendasKpis;
  serie: LinhaMensal[];
}

export const AdminDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const { filtros: filtrosUrl } = useFiltrosUrl();
  const [params, setParams] = useSearchParams();

  const filtros: FiltrosDashboard = useMemo(() => ({
    data_inicio: filtrosUrl.data_inicio, data_fim: filtrosUrl.data_fim, mes: filtrosUrl.mes,
    semestre: filtrosUrl.semestre, ano: filtrosUrl.ano, polo_id: filtrosUrl.polo_id, escola_id: filtrosUrl.escola_id,
  }), [filtrosUrl]);
  const chaveFiltros = JSON.stringify(filtros);
  const filtrosPeriodo: FiltrosDashboard = useMemo(() => ({
    data_inicio: filtros.data_inicio, data_fim: filtros.data_fim, mes: filtros.mes, semestre: filtros.semestre, ano: filtros.ano,
  }), [chaveFiltros]); // eslint-disable-line react-hooks/exhaustive-deps

  const [metrics, setMetrics] = useState<AdminDashboardMetrics | null>(null);
  const [executivo, setExecutivo] = useState<DashboardExecutivo | null>(null);
  const [erroExecutivo, setErroExecutivo] = useState(false);
  const [receita, setReceita] = useState<Receita | null>(null);
  const [erroReceita, setErroReceita] = useState(false);
  const [ranking, setRanking] = useState<Ranking | null>(null);
  const [erroRanking, setErroRanking] = useState(false);
  const [carregandoRanking, setCarregandoRanking] = useState(false);
  const [ordenarPor, setOrdenarPor] = useState<OrdenacaoRanking>('indice');
  const [versaoRanking, setVersaoRanking] = useState(0);
  const [atividade, setAtividade] = useState<AtividadeDocente | null>(null);
  const [erroAtividade, setErroAtividade] = useState(false);

  // Totais gerais (cards de consulta) e atividade docente: independem do filtro.
  useEffect(() => {
    let vivo = true;
    adminApi.getDashboardMetrics().then((d) => vivo && setMetrics(d)).catch(() => undefined);
    aulasApi.atividade(DIAS_ATIVIDADE, DIAS_SEM_REGISTRO)
      .then((d) => vivo && setAtividade(d))
      .catch(() => vivo && setErroAtividade(true));
    return () => { vivo = false; };
  }, []);

  // Indicadores do período + receita (precisa do período resolvido pelo backend).
  useEffect(() => {
    let vivo = true;
    setErroExecutivo(false);
    setErroReceita(false);
    adminApi.getDashboardExecutivo(filtros)
      .then(async (exec) => {
        if (!vivo) return;
        setExecutivo(exec);
        const unidade = { polo_id: filtros.polo_id, escola_id: filtros.escola_id };
        const meses = ultimos12Meses(exec.periodo.fim);
        try {
          const [atual, anterior, serie] = await Promise.all([
            financeiroApi.vendasKpis({ ...unidade, data_inicio: exec.periodo.inicio, data_fim: exec.periodo.fim }),
            financeiroApi.vendasKpis({ ...unidade, data_inicio: exec.periodo_anterior.inicio, data_fim: exec.periodo_anterior.fim }),
            financeiroApi.vendasSerie({ ...unidade, data_inicio: `${meses[0]}-01`, data_fim: exec.periodo.fim }),
          ]);
          if (!vivo) return;
          const porMes = new Map<string, VendasSerieItem>(serie.map((s) => [s.mes, s]));
          setReceita({
            atual,
            anterior,
            serie: meses.map((mes) => ({ mes, receita: 0, pedidos: 0, pedidos_pagos: 0, ...porMes.get(mes) })),
          });
        } catch {
          if (vivo) setErroReceita(true);
        }
      })
      .catch(() => { if (vivo) { setErroExecutivo(true); setErroReceita(true); } });
    return () => { vivo = false; };
  }, [chaveFiltros]); // eslint-disable-line react-hooks/exhaustive-deps

  // Ranking: um item por polo, então usa só o período (não a unidade).
  useEffect(() => {
    let vivo = true;
    setCarregandoRanking(true);
    setErroRanking(false);
    adminApi.getRankingPolos(filtrosPeriodo, ordenarPor)
      .then((r) => vivo && setRanking(r))
      .catch(() => vivo && setErroRanking(true))
      .finally(() => vivo && setCarregandoRanking(false));
    return () => { vivo = false; };
  }, [filtrosPeriodo, ordenarPor, versaoRanking]);

  const aplicarAtalho = (dias: number) => {
    const next = new URLSearchParams(params);
    CHAVES_PERIODO.forEach((k) => next.delete(k));
    const hoje = new Date();
    const inicio = new Date(hoje);
    inicio.setDate(hoje.getDate() - (dias - 1));
    next.set('data_inicio', isoLocal(inicio));
    next.set('data_fim', isoLocal(hoje));
    setParams(next);
  };
  const atalhoAtivo = (dias: number) => {
    if (!filtros.data_inicio || !filtros.data_fim || filtros.mes || filtros.semestre || filtros.ano) return false;
    const inicio = new Date(); inicio.setDate(inicio.getDate() - (dias - 1));
    return filtros.data_inicio === isoLocal(inicio) && filtros.data_fim === isoLocal(new Date());
  };
  const semFiltroPeriodo = CHAVES_PERIODO.every((k) => !filtros[k]);

  const cresc = executivo?.crescimento;
  const acad = executivo?.academico;
  const lic = executivo?.licencas;
  const carteira = receita ? receita.atual.receita_paga + receita.atual.a_receber : 0;
  const inadimplencia = receita && carteira ? (receita.atual.vencido / carteira) * 100 : null;
  const carteiraAnt = receita ? receita.anterior.receita_paga + receita.anterior.a_receber : 0;
  const inadimplenciaAnt = receita && carteiraAnt ? (receita.anterior.vencido / carteiraAnt) * 100 : null;
  const deltaPresenca = acad && acad.presenca_media_pct !== null && acad.presenca_media_anterior_pct !== null
    ? Math.round((acad.presenca_media_pct - acad.presenca_media_anterior_pct) * 10) / 10 : null;
  const deltaInadimplencia = inadimplencia !== null && inadimplenciaAnt !== null
    ? Math.round((inadimplencia - inadimplenciaAnt) * 10) / 10 : null;

  return (
    <div className="max-w-7xl space-y-6">
      {/* Banner */}
      <div className="glass relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 p-8 shadow-2xl">
        <div className="relative z-10 flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">Bem-vindo, {user?.nome || 'Administrador'}!</h1>
            <p className="mt-1 max-w-xl text-sm text-slate-400">
              Visão executiva do ecossistema: crescimento, receita, licenças, qualidade acadêmica e o que precisa de ação.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/admin/usuarios" className="flex items-center gap-1.5 rounded-xl bg-nexus-yellow px-4 py-2.5 text-xs font-bold text-ink shadow-lg transition-colors hover:bg-nexus-yellow-hover">
              <Users className="h-4 w-4" /> Gerenciar Usuários
            </Link>
            <Link to="/admin/auditoria" className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-200 transition-colors hover:bg-slate-700">
              <Activity className="h-4 w-4 text-nexus-yellow" /> Logs de Auditoria
            </Link>
          </div>
        </div>
      </div>

      {/* Período */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm text-slate-300">
          <CalendarRange className="h-4 w-4 text-nexus-yellow" />
          {executivo ? (
            <span>
              <strong className="text-white">{fmtData(executivo.periodo.inicio)} a {fmtData(executivo.periodo.fim)}</strong>
              <span className="text-slate-500"> · comparado a {fmtData(executivo.periodo_anterior.inicio)} a {fmtData(executivo.periodo_anterior.fim)}</span>
              {semFiltroPeriodo && <span className="text-slate-500"> (padrão: últimos 30 dias)</span>}
            </span>
          ) : 'Carregando período...'}
        </p>
        <div className="flex gap-2" role="group" aria-label="Atalhos de período">
          {ATALHOS.map((a) => (
            <button
              key={a.dias}
              type="button"
              onClick={() => aplicarAtalho(a.dias)}
              aria-pressed={atalhoAtivo(a.dias)}
              className={`rounded-xl border px-3 py-1.5 text-xs font-semibold ${atalhoAtivo(a.dias) ? 'border-nexus-yellow bg-nexus-yellow/10 text-nexus-yellow' : 'border-slate-700 text-slate-300 hover:bg-slate-800'}`}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>
      <PeriodoFiltros />

      {/* KPIs com tendência */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <KpiVariacao
          rotulo="Novos alunos" icone={TrendingUp} carregando={!cresc && !erroExecutivo}
          valor={erroExecutivo ? '—' : fmtInt(cresc?.novos_alunos)} variacao={cresc?.variacao_novos_alunos_pct}
          detalhe={cresc ? `${fmtInt(cresc.alunos_ativos)} alunos ativos hoje` : undefined} to="/admin/alunos"
        />
        <KpiVariacao
          rotulo="Receita paga" icone={Wallet} carregando={!receita && !erroReceita}
          valor={receita ? formatBRL(receita.atual.receita_paga) : '—'}
          variacao={receita ? variacaoPct(receita.atual.receita_paga, receita.anterior.receita_paga) : undefined}
          detalhe={receita ? `ticket médio ${formatBRL(receita.atual.ticket_medio)}` : undefined} to="/admin/vendas"
        />
        <KpiVariacao
          rotulo="Inadimplência" icone={Percent} carregando={!receita && !erroReceita} subirEhRuim unidadeVariacao="p.p."
          valor={receita ? fmtPct(inadimplencia) : '—'} variacao={receita ? deltaInadimplencia : undefined}
          detalhe={receita ? `${formatBRL(receita.atual.vencido)} vencido` : undefined} to="/admin/financeiro?status=vencido"
        />
        <KpiVariacao
          rotulo="Presença média" icone={Activity} carregando={!acad && !erroExecutivo} unidadeVariacao="p.p."
          valor={erroExecutivo ? '—' : fmtPct(acad?.presenca_media_pct)} variacao={acad ? deltaPresenca : undefined}
          detalhe={acad ? `${fmtInt(acad.registros_presenca)} registro(s) de chamada` : undefined} to="/admin/presencas"
        />
        <KpiVariacao
          rotulo="Licenças consumidas" icone={KeyRound} carregando={!lic && !erroExecutivo}
          valor={erroExecutivo ? '—' : fmtInt(lic?.consumo_periodo)} variacao={lic?.variacao_consumo_pct}
          detalhe={lic ? (lic.cobertura_dias === null ? `${fmtInt(lic.estoque_disponivel)} em estoque` : `estoque para ${fmtInt(lic.cobertura_dias)} dias`) : undefined}
          to="/admin/licencas"
        />
      </div>

      <CentralPendencias pendencias={executivo?.pendencias || null} erro={erroExecutivo} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <BlocoCrescimento dados={cresc || null} erro={erroExecutivo} />
        <BlocoReceita kpis={receita?.atual || null} serie={receita?.serie || []} erro={erroReceita} />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <BlocoLicencas dados={lic || null} erro={erroExecutivo} />
        <BlocoAcademico dados={acad || null} atividade={atividade} erro={erroExecutivo} />
      </div>

      <AtividadeDocentePainel atividade={atividade} erro={erroAtividade} inicioPeriodo={dataLocalMenosDias(DIAS_ATIVIDADE)} />

      <RankingPolos
        ranking={ranking} erro={erroRanking} carregando={carregandoRanking}
        ordenarPor={ordenarPor} onOrdenar={setOrdenarPor} filtros={filtrosPeriodo}
        onPesosSalvos={() => setVersaoRanking((v) => v + 1)}
      />

      <VisualizadoresReais metrics={metrics} executivo={executivo} ranking={ranking} filtros={filtros} />
    </div>
  );
};
