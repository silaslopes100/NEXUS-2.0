import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CalendarClock, CheckCircle2, Loader2, RefreshCw, X } from 'lucide-react';
import {
  Andamento,
  Cronograma,
  Frequencia,
  ROTULO_SITUACAO,
  Situacao,
  cargaHorariaApi,
  erroApi,
  fmtHoras,
} from '@/features/carga_horaria/api';
import { Turma } from '@/features/turmas/api';

type Aba = 'cronograma' | 'andamento' | 'frequencia';

const fmtData = (iso?: string | null) => (iso ? new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString('pt-BR') : '—');
const fmtPct = (v?: number | null) =>
  v === null || v === undefined ? '—' : `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(v)}%`;

const corSituacao: Record<Situacao, string> = {
  em_dia: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  atrasado: 'border-rose-500/40 bg-rose-500/10 text-rose-300',
  nao_iniciada: 'border-slate-700 bg-slate-800 text-slate-300',
  concluida: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
};

const SituacaoChip: React.FC<{ s: Situacao }> = ({ s }) => (
  <span className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold ${corSituacao[s]}`}>{ROTULO_SITUACAO[s]}</span>
);

const Barra: React.FC<{ pct: number }> = ({ pct }) => (
  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
    <div className="h-full rounded-full bg-[var(--serie-1)]" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
  </div>
);

const Alertas: React.FC<{ itens: string[] }> = ({ itens }) =>
  itens.length ? (
    <ul className="space-y-1.5">
      {itens.map((a) => (
        <li key={a} className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {a}
        </li>
      ))}
    </ul>
  ) : null;

interface Props {
  turma: Turma;
  podeGerar: boolean;
  podeConcluir: boolean;
  onClose: () => void;
}

/** Cronograma, andamento (previsto × realizado) e frequência da turma — RN04 a RN07. */
export const TurmaCargaHorariaPanel: React.FC<Props> = ({ turma, podeGerar, podeConcluir, onClose }) => {
  const [aba, setAba] = useState<Aba>('cronograma');
  const [cronograma, setCronograma] = useState<Cronograma | null>(null);
  const [andamento, setAndamento] = useState<Andamento | null>(null);
  const [frequencia, setFrequencia] = useState<Frequencia | null>(null);
  const [alertasGeracao, setAlertasGeracao] = useState<string[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const [c, a, f] = await Promise.all([
        cargaHorariaApi.cronograma(turma.id),
        cargaHorariaApi.andamento(turma.id),
        cargaHorariaApi.frequencia(turma.id),
      ]);
      setCronograma(c);
      setAndamento(a);
      setFrequencia(f);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar a carga horária da turma.'));
    } finally {
      setCarregando(false);
    }
  }, [turma.id]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const gerar = async () => {
    if (cronograma?.gerado && !window.confirm('Regerar o cronograma? As aulas já realizadas são mantidas; as pendentes são recriadas com as regras atuais do calendário.')) return;
    setProcessando(true);
    setErro('');
    setAviso('');
    try {
      const c = await cargaHorariaApi.gerarCronograma(turma.id);
      setAlertasGeracao(c.alertas);
      setAviso('Cronograma gerado.');
      await carregar();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível gerar o cronograma.'));
    } finally {
      setProcessando(false);
    }
  };

  const concluir = async () => {
    const saldo = andamento?.saldo ?? 0;
    const msg = saldo > 0
      ? `A turma tem saldo de ${fmtHoras(saldo)} não cumprido. Concluir mesmo assim?`
      : 'Concluir a turma? Depois disso ela não aceita novas atas.';
    if (!window.confirm(msg)) return;
    setProcessando(true);
    setErro('');
    try {
      const r = await cargaHorariaApi.concluir(turma.id);
      setAviso(r.message);
      await carregar();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível concluir a turma.'));
    } finally {
      setProcessando(false);
    }
  };

  const abaCls = (ativa: boolean) =>
    `rounded-xl px-4 py-2 text-sm font-semibold ${ativa ? 'bg-nexus-yellow/10 text-nexus-yellow' : 'text-slate-400 hover:bg-slate-800'}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/75 p-3 backdrop-blur-sm sm:p-6" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="carga-titulo" className="glass flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 p-5">
          <div>
            <h2 id="carga-titulo" className="flex items-center gap-2 text-xl font-extrabold text-white"><CalendarClock className="h-5 w-5 text-nexus-yellow" /> Carga horária · {turma.nome}</h2>
            <p className="mt-1 text-xs text-slate-400">
              {fmtData(turma.data_inicio)} a {fmtData(turma.data_fim)}
              {cronograma?.calendario_nome ? ` · Calendário: ${cronograma.calendario_nome}` : ' · Curso sem calendário vinculado'}
              {andamento?.concluida_em ? ` · Concluída em ${fmtData(andamento.concluida_em)}` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {podeGerar && !andamento?.concluida_em && (
              <button type="button" onClick={gerar} disabled={processando || carregando} className="inline-flex items-center gap-1.5 rounded-xl bg-nexus-yellow px-3 py-2 text-xs font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
                {processando ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                {cronograma?.gerado ? 'Regerar cronograma' : 'Gerar cronograma'}
              </button>
            )}
            {podeConcluir && !andamento?.concluida_em && cronograma?.gerado && (
              <button type="button" onClick={concluir} disabled={processando || !andamento?.pode_concluir} title={andamento?.pode_concluir ? 'Concluir turma' : 'O calendário bloqueia a conclusão com saldo pendente'} className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 px-3 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-40">
                <CheckCircle2 className="h-4 w-4" /> Concluir turma
              </button>
            )}
            <button type="button" aria-label="Fechar" onClick={onClose} className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
          </div>
        </header>

        <nav role="tablist" className="flex gap-1 border-b border-slate-800 px-5 py-2">
          {(['cronograma', 'andamento', 'frequencia'] as Aba[]).map((a) => (
            <button key={a} type="button" role="tab" aria-selected={aba === a} onClick={() => setAba(a)} className={abaCls(aba === a)}>
              {a === 'cronograma' ? 'Cronograma' : a === 'andamento' ? 'Andamento' : 'Frequência'}
            </button>
          ))}
        </nav>

        <div className="min-h-[300px] flex-1 space-y-4 overflow-y-auto p-5">
          {erro && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
          {aviso && <p role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{aviso}</p>}
          {carregando ? (
            <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
          ) : aba === 'cronograma' ? (
            <>
              <Alertas itens={alertasGeracao} />
              {!cronograma?.gerado ? (
                <p className="py-10 text-center text-sm text-slate-400">
                  Cronograma ainda não gerado. {podeGerar ? 'Use "Gerar cronograma" para criar as aulas previstas a partir do calendário do curso.' : ''}
                </p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {cronograma.disciplinas.map((d) => (
                    <section key={d.disciplina_id} className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <h3 className="text-sm font-bold text-white">{d.nome}</h3>
                      <p className="mb-2 text-xs text-slate-500">{fmtHoras(d.carga_horaria)} · {d.aulas.length} aula(s) prevista(s)</p>
                      {!d.aulas.length ? <p className="text-xs text-amber-300">Sem aulas no período da turma.</p> : (
                        <ul className="space-y-1">
                          {d.aulas.map((a) => (
                            <li key={a.id} className="flex items-center justify-between gap-2 text-xs">
                              <span className="text-slate-300">Aula {a.numero} · {fmtData(a.data_prevista)} · {fmtHoras(a.horas_previstas)}</span>
                              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${a.status === 'pendente' ? 'bg-slate-800 text-slate-300' : 'bg-emerald-500/15 text-emerald-300'}`}>
                                {a.status === 'pendente' ? 'Pendente' : a.status === 'realizada' ? 'Realizada' : `Reposta em ${fmtData(a.ata_data)}`}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </section>
                  ))}
                </div>
              )}
            </>
          ) : aba === 'andamento' && andamento ? (
            <>
              <Alertas itens={andamento.alertas} />
              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                  <p className="text-[11px] font-semibold uppercase text-slate-500">Progresso do curso</p>
                  <p className="mt-1 text-2xl font-black text-white">{fmtPct(andamento.progresso_pct)}</p>
                  <Barra pct={andamento.progresso_pct} />
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                  <p className="text-[11px] font-semibold uppercase text-slate-500">Cumprido / carga</p>
                  <p className="mt-1 text-lg font-black text-white">{fmtHoras(andamento.horas_abatidas)} <span className="text-sm text-slate-500">de {fmtHoras(andamento.carga_total)}</span></p>
                  <p className="text-xs text-slate-500">Saldo {fmtHoras(andamento.saldo)}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                  <p className="text-[11px] font-semibold uppercase text-slate-500">Previsto × realizado</p>
                  <p className="mt-1"><SituacaoChip s={andamento.situacao} /></p>
                  <p className="mt-1 text-xs text-slate-500">
                    {andamento.situacao === 'atrasado'
                      ? `${fmtHoras(andamento.atraso_horas)} · ${andamento.atraso_aulas} aula(s) de atraso`
                      : `Previsto até hoje: ${fmtHoras(andamento.previsto_ate_hoje_horas)}`}
                  </p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                  <p className="text-[11px] font-semibold uppercase text-slate-500">Horas complementares</p>
                  <p className="mt-1 text-lg font-black text-white">{fmtHoras(andamento.horas_complementares)}</p>
                  <p className="text-xs text-slate-500">Extra, reforço, complemento e revisão</p>
                </div>
              </section>
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                    <tr><th className="p-3">Disciplina</th><th className="p-3">Progresso</th><th className="p-3 text-right">Cumprido</th><th className="p-3 text-right">Saldo</th><th className="p-3 text-right">Aulas</th><th className="p-3 text-right">Compl.</th><th className="p-3">Situação</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {andamento.disciplinas.map((d) => (
                      <tr key={d.disciplina_id}>
                        <td className="p-3 font-semibold text-white">{d.nome}</td>
                        <td className="w-40 p-3"><div className="flex items-center gap-2"><Barra pct={d.progresso_pct} /><span className="w-12 text-right text-xs">{fmtPct(d.progresso_pct)}</span></div></td>
                        <td className="p-3 text-right">{fmtHoras(d.horas_abatidas)}</td>
                        <td className="p-3 text-right">{fmtHoras(d.saldo)}</td>
                        <td className="p-3 text-right">{d.aulas_realizadas}/{d.aulas_previstas}</td>
                        <td className="p-3 text-right">{fmtHoras(d.horas_complementares)}</td>
                        <td className="p-3"><SituacaoChip s={d.situacao} />{d.situacao === 'atrasado' && <span className="ml-1 text-[11px] text-slate-500">{d.atraso_aulas} aula(s)</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : aba === 'frequencia' && frequencia ? (
            <>
              <p className="text-xs text-slate-400">
                Medida em {frequencia.base}, só sobre aulas previstas e reposições. Mínimo: {fmtPct(frequencia.minimo_pct)} ·{' '}
                <strong className={frequencia.alunos_em_risco ? 'text-rose-300' : 'text-emerald-300'}>{frequencia.alunos_em_risco} aluno(s) em risco</strong>
              </p>
              {!frequencia.alunos.length ? <p className="py-10 text-center text-sm text-slate-400">Nenhum aluno ativo na turma.</p> : (
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full min-w-[560px] text-left text-sm">
                    <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                      <tr><th className="p-3">Aluno</th><th className="p-3 text-right">Frequência</th><th className="p-3">Por disciplina</th></tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {frequencia.alunos.map((a) => (
                        <tr key={a.aluno_id}>
                          <td className="p-3"><span className="font-semibold text-white">{a.nome}</span>{a.numero_matricula && <span className="block text-xs text-slate-500">{a.numero_matricula}</span>}</td>
                          <td className="p-3 text-right">
                            <span className={a.em_risco ? 'font-bold text-rose-300' : 'text-white'}>{fmtPct(a.frequencia_pct)}</span>
                            {a.em_risco && <span className="ml-1 inline-flex items-center gap-0.5 text-[11px] text-rose-300"><AlertTriangle className="h-3 w-3" /> em risco</span>}
                          </td>
                          <td className="p-3 text-xs text-slate-400">
                            {a.disciplinas.length ? a.disciplinas.map((d) => `${d.nome}: ${fmtPct(d.frequencia_pct)}`).join(' · ') : 'Sem chamadas registradas'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
};
