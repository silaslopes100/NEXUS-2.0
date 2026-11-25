import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { GraficoBarrasMensal, LinhaMensal } from '@/components/charts/GraficoBarrasMensal';
import { PeriodoFiltros, useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { financeiroApi } from '@/features/financeiro/api';
import { BotoesExportar } from '@/features/financeiro/components/BotoesExportar';
import { STATUS_PEDIDO, StatusPedido, TIPO_PEDIDO, VendasKpis, VendasSerieItem, erroApi, formatBRL } from '@/features/financeiro/types';

const TIPO_OPCOES = Object.entries(TIPO_PEDIDO).map(([value, label]) => ({ value, label }));

const Tile: React.FC<{ label: string; valor: string; detalhe?: string }> = ({ label, valor, detalhe }) => (
  <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
    <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
    <strong className="mt-2 block text-2xl font-black text-white">{valor}</strong>
    {detalhe && <p className="mt-1 text-xs text-slate-400">{detalhe}</p>}
  </div>
);

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
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
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

          <GraficoBarrasMensal
            titulo="Receita paga por mês"
            subtitulo="Pelo mês de criação do pedido"
            series={[{ chave: 'receita', rotulo: 'Receita' }]}
            dados={serie as unknown as LinhaMensal[]}
            formatar={formatBRL}
            detalhe={(l) => `${l.pedidos_pagos} pago(s) de ${l.pedidos} pedido(s)`}
            vazio="Sem pedidos no período."
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
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
            <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
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
