import React, { useEffect, useState } from 'react';
import { Building, KeyRound, Loader2, RefreshCw, UserCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { DashboardPoloKpis } from '@/types/polos';

export const PoloDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const [kpis, setKpis] = useState<DashboardPoloKpis | null>(null);
  const [loading, setLoading] = useState(true);
  const poloId = user?.polo_id || '';
  const load = async () => { if (!poloId) { setLoading(false); return; } setLoading(true); setKpis(await polosEscolasApi.getResumoPolo(poloId).catch(() => null)); setLoading(false); };
  useEffect(() => { load(); }, [poloId]);
  const cards: Array<{ label: string; value: string | number; Icon: React.ElementType; color: string }> = kpis ? [{ label: 'Alunos/licenças vendidas', value: kpis.total_licencas_vendidas_alunos, Icon: UserCheck, color: 'text-emerald-400' }, { label: 'Licenças disponíveis', value: kpis.total_licencas_nao_vendidas, Icon: KeyRound, color: 'text-amber-300' }, { label: 'Taxa de distribuição', value: `${kpis.taxa_distribuicao}%`, Icon: Building, color: 'text-blue-400' }] : [];
  return <div className="max-w-7xl space-y-8"><header className="flex items-center justify-between rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-8 shadow-2xl"><div><p className="mb-3 text-xs font-bold uppercase tracking-wider text-blue-400">Gestão de polo regional</p><h1 className="text-3xl font-extrabold text-white">Painel do polo{user?.nome ? `, ${user.nome}` : ''}</h1><p className="mt-1 max-w-xl text-sm text-slate-400">Acompanhe conversão, estoque e distribuição de licenças em tempo real.</p></div><button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-3 text-slate-300 hover:text-white"><RefreshCw size={18} className={loading ? 'animate-spin' : ''} /></button></header>{loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : <><div className="grid grid-cols-1 gap-5 sm:grid-cols-3">{cards.map(({ label, value, Icon, color }) => <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5"><div className={`flex items-center justify-between ${color}`}><span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</span><Icon size={18} /></div><div className="mt-3 text-3xl font-black text-white">{value}</div></div>)}</div>{!kpis && <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Não foi possível carregar os indicadores deste polo.</p>}</>}</div>;
};
