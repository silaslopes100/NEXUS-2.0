import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronRight, Loader2, RefreshCw, X } from 'lucide-react';
import { GraficoBarrasMensal, LinhaMensal } from '@/components/charts/GraficoBarrasMensal';
import { FILTRO_ALUNOS_EAD, PeriodoFiltros, useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { PedidosTabela } from '@/features/financeiro/components/PedidosTabela';
import { financeiroApi } from '@/features/financeiro/api';
import { BotoesExportar } from '@/features/financeiro/components/BotoesExportar';
import {
  FiltrosPeriodo, STATUS_PEDIDO, StatusPedido, TIPO_PEDIDO, VendasKpis, VendasSerieItem, erroApi, formatBRL,
} from '@/features/financeiro/types';

const TIPO_OPCOES = [
  ...Object.entries(TIPO_PEDIDO).map(([value, label]) => ({ value, label })),
  { value: 'ead_todos', label: 'Todas as vendas EAD' },
];

/** Recorte aberto na listagem ao clicar num indicador (somado aos filtros da tela). */
interface Recorte { titulo: string; filtros: FiltrosPeriodo }

const Tile: React.FC<{ label: string; valor: string; detalhe?: string; destaque?: boolean; onClick?: () => void }> = ({
  label, valor, detalhe, destaque, onClick,
}) => (
  <button type="button" onClick={onClick}
    className={`glass group rounded-2xl border bg-slate-900/80 p-4 text-left transition hover:-translate-y-0.5 hover:border-blue-500/50 ${
      destaque ? 'border-emerald-500/30' : 'border-slate-800'}`}>
    <p className="flex items-center justify-between text-xs font-semibold uppercase text-slate-500">
      {label} <ChevronRight size={14} className="opacity-0 transition group-hover:opacity-100" />
    </p>
    <strong className="mt-2 block text-2xl font-black text-white">{valor}</strong>
    {detalhe && <p className="mt-1 text-xs text-slate-400">{detalhe}</p>}
  </button>
);

/** Dashboard de vendas (Fase 3D): KPIs, receita por mês, status e ranking de Polos, com os filtros padrão. */
export const VendasPage: React.FC = () => {
  const { filtros } = useFiltrosUrl();
  const [kpis, setKpis] = useState<VendasKpis | null>(null);
  const [serie, setSerie] = useState<VendasSerieItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [recorte, setRecorte] = useState<Recorte | null>(null);
  const listagemRef = useRef<HTMLDivElement>(null);

  const abrir = (titulo: string, f: FiltrosPeriodo) => {
    setRecorte({ titulo, filtros: f });
    window.setTimeout(() => listagemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  };

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
          <p className="mt-1 text-sm text-slate-400">
            Licenças e livros vendidos aos Polos e disciplinas vendidas aos alunos EAD. Clique num indicador para ver a listagem.
          </p>
        </div>
        <div className="flex items-start gap-2">
          <BotoesExportar recurso="vendas" />
          <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
        </div>
      </header>

      <PeriodoFiltros tipoOpcoes={TIPO_OPCOES} opcaoAlunosEad />
      {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}

      {loading && !kpis ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : kpis && (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Tile label="Receita paga" valor={formatBRL(kpis.receita_paga)} detalhe={`${kpis.pedidos_pagos} pedido(s) pago(s)`}
              onClick={() => abrir('Vendas pagas', { status: 'pagos' })} />
            <Tile label="A receber" valor={formatBRL(kpis.a_receber)} detalhe={kpis.vencido ? `${formatBRL(kpis.vencido)} vencido` : 'Nada vencido'}
              onClick={() => abrir('Aguardando pagamento', { status: 'aguardando_pagamento' })} />
            <Tile label="Ticket médio" valor={formatBRL(kpis.ticket_medio)} detalhe={`${kpis.pedidos} pedido(s) no período`}
              onClick={() => abrir('Todos os pedidos do período', {})} />
            <Tile label="Licenças · Livros" valor={`${kpis.licencas_vendidas} · ${kpis.livros_vendidos}`} detalhe={`${formatBRL(kpis.receita_licencas + (kpis.receita_kits ?? 0))} · ${formatBRL(kpis.receita_livros)}`}
              onClick={() => abrir('Licenças e livros pagos (Polos)', { status: 'pagos', tipo: 'polos' })} />
            <Tile label="Vendas EAD" valor={formatBRL(kpis.receita_ead)} destaque
              detalhe={`${kpis.vendas_ead} disciplina(s) · ${kpis.vendas_ead_livro} com livro`}
              onClick={() => abrir('Vendas EAD pagas (alunos)', { status: 'pagos', tipo: 'ead_todos' })} />
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
                    <tr key={p.polo_id || i} onClick={() => abrir(`Vendas pagas · ${p.polo_nome || 'Sem Polo'}`, { status: 'pagos', polo_id: p.polo_id || FILTRO_ALUNOS_EAD })}
                      className="cursor-pointer hover:bg-slate-800/50">
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
                    <tr key={s.status} onClick={() => abrir(`Pedidos · ${STATUS_PEDIDO[s.status as StatusPedido]?.label || s.status}`, { status: s.status })}
                      className="cursor-pointer hover:bg-slate-800/50">
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

          {recorte && (
            <div ref={listagemRef} className="scroll-mt-4 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">Listagem do indicador, com os filtros acima aplicados. Clique num pedido para ver os detalhes.</p>
                <button type="button" onClick={() => setRecorte(null)} className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white">
                  <X size={13} /> Fechar listagem
                </button>
              </div>
              <PedidosTabela key={recorte.titulo} titulo={recorte.titulo} filtrosFixos={recorte.filtros} mostrarPolo />
            </div>
          )}
        </>
      )}
    </div>
  );
};
