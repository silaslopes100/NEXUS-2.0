import React, { useEffect, useState } from 'react';
import { Clock3, Loader2, RefreshCw, School, UserCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { polosEscolasApi } from '@/features/polos_escolas/api';

interface EscolaKpis { licencas_recebidas: number; licencas_vendidas: number; licencas_nao_vendidas: number; taxa_conversao: number; taxa_ociosidade: number; }

export const EscolaDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const [kpis, setKpis] = useState<EscolaKpis | null>(null);
  const [loading, setLoading] = useState(true);
  const escolaId = user?.escola_id || '';
  const load = async () => { if (!escolaId) { setLoading(false); return; } setLoading(true); setKpis(await polosEscolasApi.getEscolaKpis(escolaId).catch(() => null)); setLoading(false); };
  useEffect(() => { load(); }, [escolaId]);
  const cards: Array<{ label: string; value: string | number; Icon: React.ElementType; color: string }> = kpis ? [{ label: 'Licenças recebidas', value: kpis.licencas_recebidas, Icon: School, color: 'text-purple-400' }, { label: 'Licenças vendidas', value: kpis.licencas_vendidas, Icon: UserCheck, color: 'text-blue-400' }, { label: 'Conversão', value: `${kpis.taxa_conversao}%`, Icon: Clock3, color: 'text-emerald-400' }] : [];
  return <div className="max-w-7xl space-y-8"><header className="flex items-center justify-between rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/40 p-8 shadow-2xl"><div><p className="mb-3 text-xs font-bold uppercase tracking-wider text-indigo-300">Unidade escolar</p><h1 className="text-3xl font-extrabold text-white">Painel da escola{user?.nome ? `, ${user.nome}` : ''}</h1><p className="mt-1 max-w-xl text-sm text-slate-400">Acompanhe o uso das licenças e a conversão da unidade.</p></div><button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-3 text-slate-300 hover:text-white"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button></header>{loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : <><div className="grid grid-cols-1 gap-5 sm:grid-cols-3">{cards.map(({ label, value, Icon, color }) => <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5"><div className={`flex items-center justify-between ${color}`}><span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</span><Icon size={18} /></div><div className="mt-3 text-3xl font-black text-white">{value}</div></div>)}</div>{kpis && <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 text-sm text-slate-300">{kpis.licencas_nao_vendidas} licenças não vendidas. Ociosidade atual: <strong className="text-amber-300">{kpis.taxa_ociosidade}%</strong>.</div>}{!kpis && <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Não foi possível carregar os indicadores desta escola.</p>}</>}</div>;
};
