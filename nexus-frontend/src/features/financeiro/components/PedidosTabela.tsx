import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Loader2, RefreshCw } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { financeiroApi } from '@/features/financeiro/api';
import { StatusPedidoBadge } from '@/features/financeiro/components/StatusPedidoBadge';
import { PedidoDetalheDrawer } from '@/features/financeiro/components/PedidoDetalheDrawer';
import { SeloDemonstracao } from '@/features/financeiro/components/SimuladorPagamento';
import { FiltrosPeriodo, Pedido, TIPO_PEDIDO, ehDemo, erroApi, formatBRL, formatData } from '@/features/financeiro/types';

const PAGE_SIZE = 20;

interface Props {
  /** Exibe a coluna Polo (oculta para usuários com escopo de um Polo só). */
  mostrarPolo?: boolean;
  /** Permite ações financeiras manuais no detalhe. */
  podeAlterarStatus?: boolean;
  /** Muda para forçar recarga (ex.: após criar um pedido). */
  recarregarChave?: number;
  /** Ações de logística no detalhe (enviar, entregar, editar). */
  podeLogistica?: boolean;
  /** Filtros sempre aplicados (sobrepõem os da URL), ex.: só livros pagos. */
  filtrosFixos?: FiltrosPeriodo;
  titulo?: string;
}

/** Lista paginada de pedidos usando os filtros da URL + drawer de detalhe. */
export const PedidosTabela: React.FC<Props> = ({
  mostrarPolo = true, podeAlterarStatus = false, recarregarChave = 0, podeLogistica = false, filtrosFixos, titulo = 'Pedidos',
}) => {
  const { filtros: filtrosUrl, page, setPage } = useFiltrosUrl();
  const chaveFixos = JSON.stringify(filtrosFixos || {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const filtros = useMemo(() => ({ ...filtrosUrl, ...(filtrosFixos || {}) }), [filtrosUrl, chaveFixos]);
  const [items, setItems] = useState<Pedido[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  // Link de notificação (?pedido=<id>) abre o detalhe direto.
  const [searchParams, setSearchParams] = useSearchParams();
  const [selecionado, setSelecionado] = useState<string | null>(() => searchParams.get('pedido'));
  const fecharDetalhe = () => {
    setSelecionado(null);
    if (searchParams.has('pedido')) {
      const proximo = new URLSearchParams(searchParams);
      proximo.delete('pedido');
      setSearchParams(proximo, { replace: true });
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    setErro('');
    try {
      const res = await financeiroApi.listPedidos({ ...filtros, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
      setItems(res.items);
      setTotal(res.total);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar os pedidos.'));
    } finally {
      setLoading(false);
    }
  }, [filtros, page]);

  useEffect(() => { load(); }, [load, recarregarChave]);

  const paginas = Math.max(Math.ceil(total / PAGE_SIZE), 1);
  const colunas = mostrarPolo ? 7 : 6;

  return (
    <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
      <div className="flex items-center justify-between border-b border-slate-800 p-4">
        <div>
          <h2 className="font-bold text-white">{titulo}</h2>
          <p className="text-xs text-slate-500">{total} pedido(s) encontrado(s)</p>
        </div>
        <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>
      {erro && <p className="border-b border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
      {loading ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="p-4">Número</th>
                <th className="p-4">Data</th>
                {mostrarPolo && <th className="p-4">Polo</th>}
                <th className="p-4">Tipo</th>
                <th className="p-4 text-center">Itens</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {items.map((p) => (
                <tr key={p.id} onClick={() => setSelecionado(p.id)} className="cursor-pointer text-slate-300 hover:bg-slate-800/40">
                  <td className="p-4 font-mono text-xs font-semibold text-white">
                    {p.numero}
                    {ehDemo(p) && <div className="mt-1"><SeloDemonstracao /></div>}
                  </td>
                  <td className="p-4 text-xs">{formatData(p.criado_em)}</td>
                  {mostrarPolo && <td className="p-4 text-xs">{p.polo_nome || '-'}{p.escola_nome ? ` · ${p.escola_nome}` : ''}</td>}
                  <td className="p-4 text-xs">
                    {p.tipo === 'troca' ? (
                      <span className="whitespace-nowrap rounded-full border border-violet-500/40 bg-violet-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-300">
                        Troca de livro
                      </span>
                    ) : TIPO_PEDIDO[p.tipo]}
                  </td>
                  <td className="p-4 text-center text-xs">{p.itens.reduce((s, i) => s + i.quantidade, 0)}</td>
                  <td className="p-4"><StatusPedidoBadge status={p.status} /></td>
                  <td className="p-4 text-right font-semibold text-white">{p.tipo === 'troca' ? '—' : formatBRL(p.valor_total)}</td>
                </tr>
              ))}
              {!items.length && (
                <tr><td colSpan={colunas} className="p-12 text-center text-slate-500">Nenhum pedido encontrado com os filtros atuais.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      {paginas > 1 && (
        <div className="flex items-center justify-between border-t border-slate-800 p-3 text-xs text-slate-400">
          <span>Página {page} de {paginas}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded-lg border border-slate-700 p-1.5 disabled:opacity-40"><ChevronLeft size={14} /></button>
            <button disabled={page >= paginas} onClick={() => setPage(page + 1)} className="rounded-lg border border-slate-700 p-1.5 disabled:opacity-40"><ChevronRight size={14} /></button>
          </div>
        </div>
      )}
      {selecionado && (
        <PedidoDetalheDrawer
          pedidoId={selecionado}
          podeAlterarStatus={podeAlterarStatus}
          podeLogistica={podeLogistica}
          onClose={fecharDetalhe}
          onAlterado={load}
        />
      )}
    </section>
  );
};
