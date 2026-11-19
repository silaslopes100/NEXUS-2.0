import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, CreditCard, Loader2, RefreshCw, TrendingUp, Wallet } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { VendasKpis, formatBRL } from '@/features/financeiro/types';
import { useAuthStore } from '@/stores/authStore';

const ATALHOS = [
  { to: '/admin/vendas', label: 'Vendas', icon: TrendingUp },
  { to: '/admin/financeiro?status=vencido', label: 'Boletos vencidos', icon: AlertTriangle },
  { to: '/admin/financeiro', label: 'Boletos & Pagamentos', icon: CreditCard },
  { to: '/admin/regras-pagamento', label: 'Regras de Pagamento', icon: Wallet },
];

/** Painel do perfil Financeiro: indicadores do ano corrente e atalhos. */
export const FinanceiroDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const ano = new Date().getFullYear();
  const [kpis, setKpis] = useState<VendasKpis | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setKpis(await financeiroApi.vendasKpis({ ano: String(ano) }).catch(() => null));
    setLoading(false);
  }, [ano]);
  useEffect(() => { load(); }, [load]);

  const cards = kpis ? [
    { label: `Receita paga (${ano})`, value: formatBRL(kpis.receita_paga), detalhe: `${kpis.pedidos_pagos} pedido(s) pago(s)` },
    { label: 'A receber', value: formatBRL(kpis.a_receber), detalhe: 'Pedidos aguardando pagamento' },
    { label: 'Vencido', value: formatBRL(kpis.vencido), detalhe: 'Cobranças vencidas sem pagamento' },
    { label: 'Ticket médio', value: formatBRL(kpis.ticket_medio), detalhe: `${kpis.licencas_vendidas} licença(s) · ${kpis.livros_vendidos} livro(s)` },
  ] : [];

  return (
    <div className="max-w-7xl space-y-8">
      <header className="flex items-center justify-between rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/40 p-8 shadow-2xl">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Painel financeiro{user?.nome ? `, ${user.nome}` : ''}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">Vendas aos Polos, cobranças e regras de pagamento.</p>
        </div>
        <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-3 text-slate-300 hover:text-white"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button>
      </header>
      {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
        <>
          {kpis ? (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {cards.map((c) => (
                <div key={c.label} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{c.label}</span>
                  <div className="mt-3 text-2xl font-black text-white">{c.value}</div>
                  <p className="mt-1 text-xs text-slate-500">{c.detalhe}</p>
                </div>
              ))}
            </div>
          ) : <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Não foi possível carregar os indicadores.</p>}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {ATALHOS.map(({ to, label, icon: Icon }) => (
              <Link key={to} to={to} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm font-semibold text-slate-200 hover:border-emerald-500/40 hover:text-white">
                <span className="flex items-center gap-2"><Icon size={16} /> {label}</span><ArrowRight size={14} />
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
