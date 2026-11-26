import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, History, Loader2, PackageCheck, RefreshCw, Truck } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { useAuthStore } from '@/stores/authStore';

interface Contagens { pendentes: number; enviados: number; entreguesMes: number }

/** Painel do perfil Logística: fila de envio e atalhos. */
export const LogisticaDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const [dados, setDados] = useState<Contagens | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const hoje = new Date();
    const total = (status: string, extra: Record<string, string> = {}) =>
      financeiroApi.listPedidos({ tipo: 'com_envio', status, limit: 1, ...extra }).then((r) => r.total);
    try {
      // Pedido pelo mês de criação: "entregues no mês" aproxima os pedidos do mês já entregues.
      const [pendentes, enviados, entreguesMes] = await Promise.all([
        total('fila_envio'), // venda paga ou troca solicitada
        total('enviado'),
        total('entregue', { ano: String(hoje.getFullYear()), mes: String(hoje.getMonth() + 1) }),
      ]);
      setDados({ pendentes, enviados, entreguesMes });
    } catch {
      setDados(null);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const cards = dados ? [
    { label: 'Aguardando envio', value: dados.pendentes, Icon: PackageCheck, color: 'text-amber-300' },
    { label: 'Em trânsito', value: dados.enviados, Icon: Truck, color: 'text-indigo-300' },
    { label: 'Pedidos do mês entregues', value: dados.entreguesMes, Icon: History, color: 'text-emerald-400' },
  ] : [];

  return (
    <div className="max-w-7xl space-y-8">
      <header className="glass flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/40 p-5 shadow-2xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <h1 className="break-words text-2xl font-extrabold text-white sm:text-3xl">Painel de logística{user?.nome ? `, ${user.nome}` : ''}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">Envio e entrega dos livros didáticos pagos pelos Polos.</p>
        </div>
        <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-3 text-slate-300 hover:text-white"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button>
      </header>
      {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
        <>
          {dados ? (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
              {cards.map(({ label, value, Icon, color }) => (
                <div key={label} className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                  <div className={`flex items-center justify-between ${color}`}><span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</span><Icon size={18} /></div>
                  <div className="mt-3 text-3xl font-black text-white">{value}</div>
                </div>
              ))}
            </div>
          ) : <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Não foi possível carregar os indicadores.</p>}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Link to="/admin/logistica/pendentes" className="glass flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm font-semibold text-slate-200 hover:border-indigo-500/40 hover:text-white">
              <span className="flex items-center gap-2"><Truck size={16} /> Pendentes de envio</span><ArrowRight size={14} />
            </Link>
            <Link to="/admin/logistica/historico" className="glass flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm font-semibold text-slate-200 hover:border-indigo-500/40 hover:text-white">
              <span className="flex items-center gap-2"><History size={16} /> Histórico de pedidos</span><ArrowRight size={14} />
            </Link>
          </div>
        </>
      )}
    </div>
  );
};
