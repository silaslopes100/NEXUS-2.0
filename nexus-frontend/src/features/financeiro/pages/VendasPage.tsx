import React, { useCallback, useEffect, useState } from 'react';
import { BarChart3, Loader2, RefreshCw, Table2 } from 'lucide-react';
import { PeriodoFiltros, useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { financeiroApi } from '@/features/financeiro/api';
import { BotoesExportar } from '@/features/financeiro/components/BotoesExportar';
import { STATUS_PEDIDO, StatusPedido, TIPO_PEDIDO, VendasKpis, VendasSerieItem, erroApi, formatBRL } from '@/features/financeiro/types';

const TIPO_OPCOES = Object.entries(TIPO_PEDIDO).map(([value, label]) => ({ value, label }));
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const rotuloMes = (mes: string) => {
  const [ano, m] = mes.split('-');
  return `${MESES[Number(m) - 1]}/${ano.slice(2)}`;
};

const Tile: React.FC<{ label: string; valor: string; detalhe?: string }> = ({ label, valor, detalhe }) => (
  <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
    <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
    <strong className="mt-2 block text-2xl font-black text-white">{valor}</strong>
    {detalhe && <p className="mt-1 text-xs text-slate-400">{detalhe}</p>}
  </div>
);

/** Receita paga por mês: série única, barras finas, tooltip por barra e alternativa em tabela. */
const GraficoReceita: React.FC<{ serie: VendasSerieItem[] }> = ({ serie }) => {
  const [hover, setHover] = useState<number | null>(null);
  const [tabela, setTabela] = useState(false);
  const largura = 720;
  const altura = 220;
  const margem = { top: 16, right: 8, bottom: 28, left: 8 };
  const max = Math.max(...serie.map((s) => s.receita), 1);
  const passo = (largura - margem.left - margem.right) / Math.max(serie.length, 1);
  const barra = Math.min(36, Math.max(6, passo - 2)); // 2px de respiro entre barras
  const plotH = altura - margem.top - margem.bottom;
  const linhas = [0.25, 0.5, 0.75, 1].map((f) => margem.top + plotH * (1 - f));

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="font-bold text-white">Receita paga por mês</h2>
          <p className="text-xs text-slate-500">Pelo mês de criação do pedido · pico {formatBRL(max)}</p>
        </div>
        <button onClick={() => setTabela(!tabela)} className="inline-flex items-center gap-1 rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:text-white">
          {tabela ? <BarChart3 size={14} /> : <Table2 size={14} />} {tabela ? 'Ver gráfico' : 'Ver tabela'}
        </button>
      </div>
      {!serie.length ? (
        <p className="py-12 text-center text-sm text-slate-500">Sem pedidos no período.</p>
      ) : tabela ? (
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr><th className="p-2">Mês</th><th className="p-2 text-right">Pedidos</th><th className="p-2 text-right">Pagos</th><th className="p-2 text-right">Receita</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-300">
            {serie.map((s) => <tr key={s.mes}><td className="p-2">{rotuloMes(s.mes)}</td><td className="p-2 text-right">{s.pedidos}</td><td className="p-2 text-right">{s.pedidos_pagos}</td><td className="p-2 text-right text-white">{formatBRL(s.receita)}</td></tr>)}
          </tbody>
        </table>
      ) : (
        <div className="relative">
          <svg viewBox={`0 0 ${largura} ${altura}`} className="h-56 w-full" role="img" aria-label="Receita paga por mês">
            {linhas.map((y) => <line key={y} x1={margem.left} x2={largura - margem.right} y1={y} y2={y} stroke="currentColor" className="text-slate-800" strokeWidth={1} />)}
            <line x1={margem.left} x2={largura - margem.right} y1={margem.top + plotH} y2={margem.top + plotH} stroke="currentColor" className="text-slate-700" strokeWidth={1} />
            {serie.map((s, i) => {
              const h = (s.receita / max) * plotH;
              const cx = margem.left + passo * i + passo / 2;
              const x = cx - barra / 2;
              const y = margem.top + plotH - h;
              const r = Math.min(4, barra / 2, h);
              // Topo arredondado (4px), base reta no eixo.
              const d = h <= 0 ? '' : `M${x},${margem.top + plotH} V${y + r} Q${x},${y} ${x + r},${y} H${x + barra - r} Q${x + barra},${y} ${x + barra},${y + r} V${margem.top + plotH} Z`;
              const mostrarRotulo = serie.length <= 12 || i % Math.ceil(serie.length / 12) === 0;
              return (
                <g key={s.mes} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
                  <rect x={cx - passo / 2} y={margem.top} width={passo} height={plotH} fill="transparent" />
                  {d && <path d={d} className={hover === i ? 'fill-emerald-300' : 'fill-emerald-500'} />}
                  {mostrarRotulo && <text x={cx} y={altura - 8} textAnchor="middle" className="fill-slate-500 text-[11px]">{rotuloMes(s.mes)}</text>}
                </g>
              );
            })}
          </svg>
          {hover !== null && (
            <div
              className="pointer-events-none absolute top-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs shadow-xl"
              style={{ left: `${Math.min(80, Math.max(0, ((hover + 0.5) / serie.length) * 100 - 10))}%` }}
            >
              <p className="font-semibold text-white">{rotuloMes(serie[hover].mes)}</p>
              <p className="text-slate-300">Receita: {formatBRL(serie[hover].receita)}</p>
              <p className="text-slate-400">{serie[hover].pedidos_pagos} pago(s) de {serie[hover].pedidos} pedido(s)</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

/** Dashboard de vendas (Fase 3D): KPIs, receita por mês, status e ranking de Polos, com os filtros padrão. */
export const VendasPage: React.FC = () => {
  const { filtros } = useFiltrosUrl();
  const [kpis, setKpis] = useState<VendasKpis | null>(null);
  const [serie, setSerie] = useState<VendasSerieItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setErro('');
    try {
      const [k, s] = await Promise.all([financeiroApi.vendasKpis(filtros), financeiroApi.vendasSerie(filtros)]);
      setKpis(k);
      setSerie(s);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar as vendas.'));
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Vendas</h1>
          <p className="mt-1 text-sm text-slate-400">Licenças e livros vendidos aos Polos. A exportação usa os filtros aplicados abaixo.</p>
        </div>
        <div className="flex items-start gap-2">
          <BotoesExportar recurso="vendas" />
          <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
        </div>
      </header>

      <PeriodoFiltros tipoOpcoes={TIPO_OPCOES} />
      {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}

      {loading && !kpis ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : kpis && (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label="Receita paga" valor={formatBRL(kpis.receita_paga)} detalhe={`${kpis.pedidos_pagos} pedido(s) pago(s)`} />
            <Tile label="A receber" valor={formatBRL(kpis.a_receber)} detalhe={kpis.vencido ? `${formatBRL(kpis.vencido)} vencido` : 'Nada vencido'} />
            <Tile label="Ticket médio" valor={formatBRL(kpis.ticket_medio)} detalhe={`${kpis.pedidos} pedido(s) no período`} />
            <Tile label="Licenças · Livros" valor={`${kpis.licencas_vendidas} · ${kpis.livros_vendidos}`} detalhe={`${formatBRL(kpis.receita_licencas)} · ${formatBRL(kpis.receita_livros)}`} />
          </section>

          <GraficoReceita serie={serie} />

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
              <h2 className="border-b border-slate-800 p-4 font-bold text-white">Top Polos (receita paga)</h2>
              <table className="w-full text-left text-sm">
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {kpis.top_polos.map((p, i) => (
                    <tr key={p.polo_id || i}>
                      <td className="w-8 p-3 text-xs text-slate-500">{i + 1}º</td>
                      <td className="p-3 text-white">{p.polo_nome || '—'}</td>
                      <td className="p-3 text-right text-xs">{p.pedidos_pagos} pedido(s)</td>
                      <td className="p-3 text-right font-semibold text-white">{formatBRL(p.receita)}</td>
                    </tr>
                  ))}
                  {!kpis.top_polos.length && <tr><td className="p-8 text-center text-slate-500">Nenhuma venda paga no período.</td></tr>}
                </tbody>
              </table>
            </section>
            <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
              <h2 className="border-b border-slate-800 p-4 font-bold text-white">Pedidos por status</h2>
              <table className="w-full text-left text-sm">
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {kpis.por_status.map((s) => (
                    <tr key={s.status}>
                      <td className="p-3 text-white">{STATUS_PEDIDO[s.status as StatusPedido]?.label || s.status}</td>
                      <td className="p-3 text-right text-xs">{s.pedidos}</td>
                      <td className="p-3 text-right font-semibold text-white">{formatBRL(s.valor)}</td>
                    </tr>
                  ))}
                  {!kpis.por_status.length && <tr><td className="p-8 text-center text-slate-500">Sem pedidos.</td></tr>}
                </tbody>
              </table>
            </section>
          </div>
        </>
      )}
    </div>
  );
};
