import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building, ChevronRight, KeyRound, Loader2, RefreshCw, School, UserCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { IndicadorCard } from '@/features/polos_escolas/components/IndicadorCard';
import { IndicadoresPolo } from '@/features/polos_escolas/components/IndicadoresUnidade';
import { DashboardPoloKpis, ResumoOperacionalPolo } from '@/types/polos';

export const PoloDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const poloId = user?.polo_id || '';
  const [kpis, setKpis] = useState<DashboardPoloKpis | null>(null);
  const [resumo, setResumo] = useState<ResumoOperacionalPolo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!poloId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    // Cada bloco falha sozinho: um erro nos KPIs de licença não esconde a visão operacional.
    const [kpisResp, resumoResp] = await Promise.allSettled([
      polosEscolasApi.getResumoPolo(poloId),
      polosEscolasApi.getResumoOperacionalPolo(poloId),
    ]);
    setKpis(kpisResp.status === 'fulfilled' ? kpisResp.value : null);
    setResumo(resumoResp.status === 'fulfilled' ? resumoResp.value : null);
    setLoading(false);
  }, [poloId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="max-w-7xl space-y-8">
      <header className="glass flex items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-8 shadow-2xl">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Painel do polo{user?.nome ? `, ${user.nome}` : ''}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Acompanhe licenças, escolas, turmas e alunos do seu polo. Clique em um indicador para abrir a lista correspondente.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Link
            to="/polo/escolas"
            className="hidden items-center gap-1.5 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:text-white sm:inline-flex"
          >
            <School size={16} /> Ver escolas do polo <ChevronRight size={14} />
          </Link>
          <button onClick={() => void load()} title="Recarregar" aria-label="Recarregar indicadores" className="rounded-xl border border-slate-700 p-3 text-slate-300 hover:text-white">
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </header>

      {loading && !kpis && !resumo ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : !poloId ? (
        <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Nenhum polo vinculado ao seu usuário.</p>
      ) : (
        <>
          <section className="space-y-3">
            <h2 className="text-base font-bold text-white">Licenças</h2>
            {kpis ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <IndicadorCard label="Alunos / licenças vendidas" value={kpis.total_licencas_vendidas_alunos} icon={<UserCheck size={18} />} accent="emerald" to="/polo/licencas" />
                <IndicadorCard label="Licenças disponíveis" value={kpis.total_licencas_nao_vendidas} icon={<KeyRound size={18} />} accent="amber" to="/polo/licencas" />
                <IndicadorCard label="Taxa de distribuição" value={`${kpis.taxa_distribuicao}%`} icon={<Building size={18} />} to="/polo/licencas" />
              </div>
            ) : (
              <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Não foi possível carregar os indicadores de licenças deste polo.</p>
            )}
          </section>

          <section className="glass space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
            <h2 className="text-base font-bold text-white">Visão operacional</h2>
            {resumo ? (
              <IndicadoresPolo resumo={resumo} poloId={poloId} area="polo" />
            ) : (
              <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">Não foi possível carregar a visão operacional deste polo.</p>
            )}
          </section>
        </>
      )}
    </div>
  );
};
