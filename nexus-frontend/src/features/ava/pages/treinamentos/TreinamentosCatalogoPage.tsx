import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Award, CalendarClock, Clock, GraduationCap, Loader2, Play, Sparkles } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { formatarDuracao } from '../../api';
import { CATEGORIA, TreinamentoCatalogo, treinamentosApi } from '../../treinamentosApi';

type Filtro = 'todos' | 'andamento' | 'concluidos';

const dataBr = (d?: string | null) => (d ? new Date(`${d}T00:00`).toLocaleDateString('pt-BR') : '');

/** Treinamentos, workshops e capacitações disponíveis para o Polo, a Escola ou o Professor. */
export const TreinamentosCatalogoPage: React.FC = () => {
  const navigate = useNavigate();
  const [lista, setLista] = useState<TreinamentoCatalogo[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<Filtro>('todos');
  const [baixando, setBaixando] = useState<string | null>(null);

  useEffect(() => {
    treinamentosApi.meus().then(setLista).catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar os treinamentos.')));
  }, []);

  const visiveis = useMemo(() => {
    const l = lista ?? [];
    if (filtro === 'concluidos') return l.filter((t) => t.concluido_em);
    if (filtro === 'andamento') return l.filter((t) => !t.concluido_em && t.aulas_concluidas > 0);
    return l;
  }, [lista, filtro]);

  const continuar = (lista ?? []).find((t) => !t.concluido_em && t.aulas_concluidas > 0 && t.disponivel);

  const baixar = async (id: string) => {
    setBaixando(id);
    setErro(null);
    try {
      await treinamentosApi.baixarCertificado(id);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Não foi possível gerar o certificado.');
    } finally {
      setBaixando(null);
    }
  };

  if (erro && !lista) {
    return (
      <div role="alert" className="mx-auto mt-10 flex max-w-xl items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" /> {erro}
      </div>
    );
  }
  if (!lista) return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950 p-6 shadow-2xl sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-nexus-yellow/10 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div className="space-y-2">
            <p className="flex items-center gap-2 text-sm font-semibold text-nexus-yellow"><Sparkles size={16} /> Capacitação Nexus</p>
            <h1 className="text-3xl font-extrabold text-white sm:text-4xl">Treinamentos</h1>
            <p className="max-w-xl text-slate-300">Treinamentos, workshops e capacitações para a sua equipe. Conclua e baixe o seu certificado.</p>
          </div>
          {continuar && (
            <button type="button" onClick={() => navigate(`/treinamentos/${continuar.id}`)}
              className="group flex items-center gap-4 rounded-2xl border border-slate-700 bg-slate-950/70 p-4 text-left hover:border-nexus-yellow/60 md:w-96">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-nexus-yellow text-ink transition group-hover:scale-110"><Play size={20} className="ml-0.5" /></span>
              <span className="min-w-0 flex-1">
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-nexus-yellow">Continuar</span>
                <span className="block truncate font-bold text-white">{continuar.titulo}</span>
                <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-slate-800">
                  <span className="block h-full bg-nexus-yellow" style={{ width: `${continuar.progresso_pct}%` }} />
                </span>
              </span>
            </button>
          )}
        </div>
      </section>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      <div className="flex gap-1 self-start rounded-xl border border-slate-800 bg-slate-900/60 p-1">
        {([['todos', 'Todos'], ['andamento', 'Em andamento'], ['concluidos', 'Concluídos']] as const).map(([v, r]) => (
          <button key={v} type="button" onClick={() => setFiltro(v)}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${filtro === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
            {r}
          </button>
        ))}
      </div>

      {visiveis.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-12 text-center">
          <GraduationCap className="mx-auto mb-3 text-slate-600" size={36} />
          <p className="text-slate-300">{lista.length ? 'Nada neste filtro.' : 'Nenhum treinamento disponível para você no momento.'}</p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {visiveis.map((t) => {
            const concluido = !!t.concluido_em;
            return (
              <article key={t.id} className="group flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 transition hover:-translate-y-1 hover:border-nexus-yellow/50 hover:shadow-nexus-glow">
                <div className="relative aspect-video overflow-hidden">
                  {t.capa_url ? (
                    <img src={urlArquivo(t.capa_url)} alt="" className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
                  ) : (
                    <span className="flex h-full w-full items-center justify-center bg-gradient-to-br from-blue-800 via-indigo-900 to-slate-950 text-white/15"><GraduationCap size={56} /></span>
                  )}
                  <span className={`absolute left-3 top-3 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${CATEGORIA[t.categoria].classe}`}>{CATEGORIA[t.categoria].rotulo}</span>
                  {concluido && (
                    <span className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-emerald-500/90 px-2.5 py-0.5 text-[11px] font-bold text-white"><Award size={12} /> Concluído</span>
                  )}
                </div>
                <div className="flex flex-1 flex-col gap-3 p-4">
                  <div>
                    <h3 className="line-clamp-2 font-bold leading-snug text-white">{t.titulo}</h3>
                    {t.descricao && <p className="mt-1 line-clamp-2 text-xs text-slate-400">{t.descricao}</p>}
                  </div>
                  <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                    <span>{t.total_aulas} aulas</span>
                    {t.duracao_min ? <span className="flex items-center gap-1"><Clock size={11} /> {formatarDuracao(t.duracao_min)}</span> : null}
                    {t.carga_horaria ? <span>{t.carga_horaria}h certificadas</span> : null}
                    {t.data_fim && !concluido && <span className="flex items-center gap-1"><CalendarClock size={11} /> até {dataBr(t.data_fim)}</span>}
                  </p>
                  <div className="mt-auto space-y-3">
                    {!concluido && t.disponivel && (
                      <div>
                        <div className="mb-1 flex justify-between text-[11px] text-slate-400">
                          <span>{t.aulas_concluidas}/{t.total_aulas} concluídas</span>
                          <span className="font-bold text-white">{t.progresso_pct}%</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                          <div className="h-full rounded-full bg-nexus-yellow" style={{ width: `${t.progresso_pct}%` }} />
                        </div>
                      </div>
                    )}
                    {!t.disponivel ? (
                      <p className="rounded-xl border border-slate-800 py-2.5 text-center text-xs text-slate-400">
                        {t.data_inicio ? `Começa em ${dataBr(t.data_inicio)}` : 'Em preparação'}
                      </p>
                    ) : (
                      <div className="flex gap-2">
                        <button type="button" onClick={() => navigate(`/treinamentos/${t.id}`)}
                          className={`flex-1 rounded-xl py-2.5 text-sm font-bold ${concluido ? 'border border-slate-700 text-slate-200 hover:bg-slate-800' : 'bg-nexus-yellow text-ink hover:bg-nexus-yellow-hover'}`}>
                          {concluido ? 'Revisar' : t.aulas_concluidas ? 'Continuar' : 'Começar'}
                        </button>
                        {concluido && t.certificado_ativo && (
                          <button type="button" onClick={() => void baixar(t.id)} disabled={baixando === t.id}
                            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-emerald-500 py-2.5 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-50">
                            {baixando === t.id ? <Loader2 size={15} className="animate-spin" /> : <Award size={15} />} Certificado
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
};
