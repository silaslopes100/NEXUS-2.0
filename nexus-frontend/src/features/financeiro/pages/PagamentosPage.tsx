import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Ban, ChevronLeft, ChevronRight, CreditCard, ExternalLink, Loader2, Package, RefreshCw, ShieldCheck } from 'lucide-react';
import { PeriodoFiltros, useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { financeiroApi } from '@/features/financeiro/api';
import { COR_STATUS_PAGAMENTO, Pagamento, erroApi, formatBRL, formatData } from '@/features/financeiro/types';

const PAGE_SIZE = 20;
const STATUS_OPCOES = ['pendente', 'pago', 'vencido', 'cancelado', 'estornado', 'falhou'].map((s) => ({
  value: s, label: s.charAt(0).toUpperCase() + s.slice(1),
}));

/** Consulta de pagamentos/boletos (inclui os boletos migrados). Vira a tela completa de Boletos na Fase 3. */
export const PagamentosPage: React.FC = () => {
  const { filtros, page, setPage } = useFiltrosUrl();
  const [items, setItems] = useState<Pagamento[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [cancelando, setCancelando] = useState<string | null>(null);

  const cancelar = async (pg: Pagamento) => {
    if (!window.confirm(`Cancelar a cobrança de ${formatBRL(pg.valor)}${pg.pedido_numero ? ` do pedido ${pg.pedido_numero}` : ''}?`)) return;
    setCancelando(pg.id);
    try {
      await financeiroApi.cancelarPagamento(pg.id);
      await load();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível cancelar a cobrança.'));
    } finally {
      setCancelando(null);
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    setErro('');
    try {
      const res = await financeiroApi.listPagamentos({ ...filtros, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
      setItems(res.items);
      setTotal(res.total);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar os pagamentos.'));
    } finally {
      setLoading(false);
    }
  }, [filtros, page]);

  useEffect(() => { load(); }, [load]);
  const paginas = Math.max(Math.ceil(total / PAGE_SIZE), 1);

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-300"><CreditCard size={15} /> Financeiro</p>
          <h1 className="text-3xl font-extrabold text-white">Pagamentos & Boletos</h1>
          <p className="mt-1 text-sm text-slate-400">Cobranças registradas (boletos, PIX e cartão). Status atualizados automaticamente pelos webhooks dos gateways.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/admin/gateways" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-200 hover:text-white">
            <ShieldCheck size={16} /> Gateways
          </Link>
          <Link to="/admin/produtos" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-200 hover:text-white">
            <Package size={16} /> Produtos & Preços
          </Link>
        </div>
      </header>

      <PeriodoFiltros statusOpcoes={STATUS_OPCOES} />

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <p className="text-xs text-slate-500">{total} pagamento(s)</p>
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
                  <th className="p-4">Criado em</th><th className="p-4">Polo</th><th className="p-4">Pedido</th>
                  <th className="p-4">Meio</th><th className="p-4">Gateway</th><th className="p-4">Vencimento</th>
                  <th className="p-4">Status</th><th className="p-4 text-right">Valor</th><th className="p-4" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {items.map((pg) => {
                  const link = pg.boleto_url || pg.invoice_url;
                  return (
                    <tr key={pg.id} className="text-slate-300 hover:bg-slate-800/40">
                      <td className="p-4 text-xs">{formatData(pg.criado_em)}</td>
                      <td className="p-4 text-xs">{pg.polo_nome || '-'}</td>
                      <td className="p-4 font-mono text-xs">{pg.pedido_numero || '-'}</td>
                      <td className="p-4 text-xs">{pg.billing_type || '-'}</td>
                      <td className="p-4 text-xs">{pg.gateway || '-'}{pg.ambiente ? ` (${pg.ambiente})` : ''}</td>
                      <td className="p-4 text-xs">{formatData(pg.vencimento_em)}</td>
                      <td className={`p-4 text-xs font-semibold ${COR_STATUS_PAGAMENTO[pg.status || ''] || 'text-slate-300'}`}>{pg.status || '-'}</td>
                      <td className="p-4 text-right font-semibold text-white">{formatBRL(pg.valor)}</td>
                      <td className="flex justify-end gap-1 p-4">
                        {(pg.status === 'pendente' || pg.status === 'vencido') && pg.gateway && (
                          <button onClick={() => cancelar(pg)} disabled={cancelando === pg.id} title="Cancelar cobrança" className="inline-flex rounded-lg border border-red-500/40 p-1.5 text-red-300 disabled:opacity-50">
                            {cancelando === pg.id ? <Loader2 size={14} className="animate-spin" /> : <Ban size={14} />}
                          </button>
                        )}
                        {link && (
                          <a href={link} target="_blank" rel="noreferrer" title="Abrir boleto/fatura" className="inline-flex rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white">
                            <ExternalLink size={14} />
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {!items.length && <tr><td colSpan={9} className="p-12 text-center text-slate-500">Nenhum pagamento encontrado.</td></tr>}
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
      </section>
    </div>
  );
};
