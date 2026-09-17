import React, { useCallback, useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, CheckCircle2, KeyRound, Loader2, Plus, RefreshCw, X } from 'lucide-react';
import { licencasApi, LicencaKpis, MovimentacaoLicenca } from '@/features/licencas/api';
import { useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

export const LicencasPage: React.FC = () => {
  const { user } = useAuthStore();
  const role = user?.perfil?.nome?.toLowerCase() || '';
  const poloId = user?.polo_id || '';
  const isManagement = ['admin', 'polo', 'coordenador_polo'].includes(role);
  const isEscola = ['escola', 'secretario_escola'].includes(role);
  const [kpis, setKpis] = useState<LicencaKpis | null>(null);
  const [items, setItems] = useState<MovimentacaoLicenca[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [action, setAction] = useState<'compra' | 'distribuir' | 'venda' | null>(null);
  const [form, setForm] = useState({ quantidade: 1, fornecedor: '', valor_unitario: 0, data: new Date().toISOString().slice(0, 10), escola_id: '', aluno_id: '' });

  const load = useCallback(async () => {
    if (!poloId) { setLoading(false); return; }
    setLoading(true);
    try { const [kpiResponse, movementResponse] = await Promise.all([licencasApi.getKpis(poloId), licencasApi.listMovimentacoes(poloId)]); setKpis(kpiResponse); setItems(movementResponse.items); }
    catch (error: any) { setFeedback(error.response?.data?.detail || 'Não foi possível carregar as licenças.'); }
    finally { setLoading(false); }
  }, [poloId]);
  useEffect(() => { load(); }, [load]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setSaving(true);
    try {
      if (action === 'compra') await licencasApi.comprar(poloId, { quantidade: form.quantidade, fornecedor: form.fornecedor, valor_unitario: form.valor_unitario, data: form.data });
      if (action === 'distribuir') await licencasApi.distribuir(poloId, { escola_id: form.escola_id, quantidade: form.quantidade });
      if (action === 'venda' && user?.escola_id) await licencasApi.vender(user.escola_id, { aluno_id: form.aluno_id, quantidade: 1 });
      setFeedback('Movimentação registrada com sucesso.'); setAction(null); await load();
    } catch (error: any) { setFeedback(error.response?.data?.detail || 'A movimentação não pôde ser concluída.'); }
    finally { setSaving(false); }
  };

  const metricCards = kpis ? [['Compradas', kpis.total_licencas_compradas, 'text-white'], ['Vendidas', kpis.total_licencas_vendidas_alunos, 'text-emerald-400'], ['Disponíveis', kpis.total_licencas_nao_vendidas, 'text-amber-300'], ['No polo', kpis.total_nao_vendidas_polo, 'text-blue-400'], ['Conversão', `${kpis.taxa_conversao_global}%`, 'text-indigo-300']] : [];
  return <div className="max-w-7xl space-y-6">
    <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl sm:flex-row sm:items-center"><div><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300"><KeyRound size={15} /> Fluxo de licenças</p><h1 className="text-3xl font-extrabold text-white">Estoque e distribuição</h1><p className="mt-1 text-sm text-slate-400">Compra, distribuição, venda e devolução por unidade.</p></div><div className="flex flex-wrap gap-2">{isManagement && <><button onClick={() => setAction('compra')} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus size={16} /> Comprar</button><button onClick={() => setAction('distribuir')} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white"><ArrowUpFromLine size={16} /> Distribuir</button></>}{isEscola && <button onClick={() => setAction('venda')} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white"><ArrowDownToLine size={16} /> Vender</button>}</div></header>
    {feedback && <div className="flex items-center justify-between rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200"><span className="flex items-center gap-2"><CheckCircle2 size={16} /> {feedback}</span><button onClick={() => setFeedback('')}><X size={16} /></button></div>}
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">{metricCards.map(([label, value, color]) => <div key={String(label)} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4"><p className="text-xs font-semibold uppercase text-slate-500">{label}</p><strong className={`mt-2 block text-2xl font-black ${color}`}>{value}</strong></div>)}</section>
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80"><div className="flex items-center justify-between border-b border-slate-800 p-4"><div><h2 className="font-bold text-white">Últimas movimentações</h2><p className="text-xs text-slate-500">{items.length} registros carregados</p></div><button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button></div>{loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-slate-800 text-xs uppercase text-slate-500"><tr><th className="p-4">Tipo</th><th className="p-4">Destino</th><th className="p-4 text-center">Qtd.</th><th className="p-4">Status</th><th className="p-4 text-right">Data</th></tr></thead><tbody className="divide-y divide-slate-800">{items.map((item) => <tr key={item.id} className="text-slate-300 hover:bg-slate-800/40"><td className="p-4 font-semibold text-white">{item.tipo.split('_').join(' ')}</td><td className="p-4 text-xs text-slate-400">{item.aluno_id ? `Aluno: ${item.aluno_id}` : item.escola_id ? `Escola: ${item.escola_id}` : `Polo: ${item.polo_id || '-'}`}</td><td className="p-4 text-center font-bold">{item.quantidade}</td><td className="p-4 text-xs text-emerald-400">{item.status}</td><td className="p-4 text-right text-xs text-slate-500">{item.criado_em ? new Date(item.criado_em).toLocaleDateString('pt-BR') : '-'}</td></tr>)}{!items.length && <tr><td colSpan={5} className="p-12 text-center text-slate-500">Nenhuma movimentação encontrada.</td></tr>}</tbody></table></div>}</section>
    {action && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"><div className="flex items-center justify-between"><h2 className="text-xl font-bold text-white">{action === 'compra' ? 'Comprar licenças' : action === 'distribuir' ? 'Distribuir para escola' : 'Vender para aluno'}</h2><button type="button" onClick={() => setAction(null)} className="text-slate-400"><X /></button></div>{action === 'compra' && <><input className={inputClass} required placeholder="Fornecedor" value={form.fornecedor} onChange={(e) => setForm({ ...form, fornecedor: e.target.value })} /><input className={inputClass} type="number" min={1} required placeholder="Quantidade" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: Number(e.target.value) })} /><input className={inputClass} type="number" min={0} step="0.01" required placeholder="Valor unitário" value={form.valor_unitario} onChange={(e) => setForm({ ...form, valor_unitario: Number(e.target.value) })} /><input className={inputClass} type="date" required value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} /></>}{action === 'distribuir' && <><input className={inputClass} required placeholder="ID da escola" value={form.escola_id} onChange={(e) => setForm({ ...form, escola_id: e.target.value })} /><input className={inputClass} type="number" min={1} required placeholder="Quantidade" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: Number(e.target.value) })} /></>}{action === 'venda' && <input className={inputClass} required placeholder="ID do aluno" value={form.aluno_id} onChange={(e) => setForm({ ...form, aluno_id: e.target.value })} />}<button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-white disabled:opacity-50">{saving && <Loader2 className="animate-spin" size={16} />} Confirmar movimentação</button></form></div>}
  </div>;
};
