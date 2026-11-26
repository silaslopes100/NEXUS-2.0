import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BookOpen, CheckCircle2 } from 'lucide-react';
import { DisciplinaFrequencia, MinhaFrequencia } from '@/features/presencas/api';
import { formatarData } from '@/features/turmas/api';

/** Cor da frequência: verde a partir do mínimo, âmbar até 15 pontos abaixo, vermelho abaixo disso. */
export const corFrequencia = (percentual: number, minimo: number) =>
  percentual >= minimo ? 'bg-emerald-500' : percentual >= minimo - 15 ? 'bg-amber-500' : 'bg-red-500';

export const textoFrequencia = (percentual: number, minimo: number) =>
  percentual >= minimo ? 'text-emerald-300' : percentual >= minimo - 15 ? 'text-amber-300' : 'text-red-400';

export const BarraFrequencia: React.FC<{ percentual: number; minimo: number; className?: string }> = ({ percentual, minimo, className = 'h-2' }) => (
  <div className={`relative w-full overflow-hidden rounded-full bg-slate-800 ${className}`}>
    <div className={`h-full ${corFrequencia(percentual, minimo)}`} style={{ width: `${Math.min(100, percentual)}%` }} />
    <div className="absolute inset-y-0 w-px bg-white/40" style={{ left: `${minimo}%` }} title={`Mínimo ${minimo}%`} />
  </div>
);

interface DisciplinaAgrupada {
  chave: string;
  nome: string;
  turmas: DisciplinaFrequencia[];
  total: number;
  presencas: number;
  faltas: number;
  percentual: number;
}

const pct = (presencas: number, total: number) => (total ? Math.round((presencas / total) * 1000) / 10 : 0);

/** Agrupa as entradas (disciplina × turma) por Disciplina. */
const agrupar = (lista: DisciplinaFrequencia[]): DisciplinaAgrupada[] => {
  const mapa = new Map<string, DisciplinaAgrupada>();
  lista.forEach((d) => {
    const chave = d.disciplina_id || d.disciplina_nome;
    const g = mapa.get(chave) || { chave, nome: d.disciplina_nome, turmas: [], total: 0, presencas: 0, faltas: 0, percentual: 0 };
    g.turmas.push(d);
    g.total += d.total_aulas;
    g.presencas += d.presencas;
    g.faltas += d.faltas;
    mapa.set(chave, g);
  });
  return Array.from(mapa.values())
    .map((g) => ({ ...g, percentual: pct(g.presencas, g.total) }))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
};

/** Seletor de Disciplina (lista lateral / select no celular) e o detalhe da disciplina escolhida. */
export const FrequenciaPorDisciplina: React.FC<{ dados: MinhaFrequencia }> = ({ dados }) => {
  const minimo = dados.frequencia_minima ?? 75;
  const disciplinas = useMemo(() => agrupar(dados.disciplinas), [dados]);
  const [selecionada, setSelecionada] = useState<string>('');

  useEffect(() => {
    if (!disciplinas.some((d) => d.chave === selecionada)) setSelecionada(disciplinas[0]?.chave || '');
  }, [disciplinas, selecionada]);

  const atual = disciplinas.find((d) => d.chave === selecionada);
  if (!disciplinas.length) return null;

  return (
    <div className="grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
      {/* Celular: select */}
      <label className="block lg:hidden">
        <span className="mb-1 block text-xs font-semibold uppercase text-slate-500">Disciplina</span>
        <select
          value={selecionada}
          onChange={(e) => setSelecionada(e.target.value)}
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-nexus-yellow"
        >
          {disciplinas.map((d) => (
            <option key={d.chave} value={d.chave}>{d.nome} — {d.percentual.toLocaleString('pt-BR')}%</option>
          ))}
        </select>
      </label>

      {/* Desktop: lista de disciplinas */}
      <nav aria-label="Disciplinas" className="glass hidden self-start overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 lg:block">
        <p className="border-b border-slate-800 px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
          Disciplinas ({disciplinas.length})
        </p>
        <ul className="max-h-[560px] divide-y divide-slate-800/70 overflow-y-auto">
          {disciplinas.map((d) => {
            const ativa = d.chave === selecionada;
            return (
              <li key={d.chave}>
                <button
                  type="button"
                  onClick={() => setSelecionada(d.chave)}
                  aria-current={ativa ? 'true' : undefined}
                  className={`relative w-full px-4 py-3 text-left transition-colors ${ativa ? 'bg-blue-500/10' : 'hover:bg-slate-800/40'}`}
                >
                  {ativa && <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-nexus-yellow" />}
                  <div className="flex items-center justify-between gap-2">
                    <span className={`truncate text-sm font-semibold ${ativa ? 'text-white' : 'text-slate-300'}`}>{d.nome}</span>
                    <span className={`shrink-0 text-sm font-black ${textoFrequencia(d.percentual, minimo)}`}>
                      {d.percentual.toLocaleString('pt-BR')}%
                    </span>
                  </div>
                  <BarraFrequencia percentual={d.percentual} minimo={minimo} className="mt-2 h-1.5" />
                  <p className="mt-1 text-[11px] text-slate-500">{d.presencas} de {d.total} aula(s) · {d.faltas} falta(s)</p>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {atual && (
        <section className="glass min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
          <header className="space-y-3 border-b border-slate-800 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300"><BookOpen size={18} /></span>
                <div>
                  <h2 className="text-xl font-bold text-white">{atual.nome}</h2>
                  <p className="text-xs text-slate-500">
                    {atual.turmas.map((t) => [t.turma_nome, t.professor_nome && `Prof. ${t.professor_nome}`].filter(Boolean).join(' · ')).filter(Boolean).join(' | ') || '—'}
                  </p>
                </div>
              </div>
              {atual.percentual >= minimo ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                  <CheckCircle2 size={13} /> Regular
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-0.5 text-xs font-semibold text-red-300">
                  <AlertTriangle size={13} /> Em risco
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 [&>*:last-child:nth-child(odd)]:col-span-2 sm:[&>*:last-child:nth-child(odd)]:col-span-1">
              <div>
                <p className="text-[11px] uppercase text-slate-500">Frequência</p>
                <p className={`text-2xl font-black ${textoFrequencia(atual.percentual, minimo)}`}>{atual.percentual.toLocaleString('pt-BR')}%</p>
              </div>
              <div>
                <p className="text-[11px] uppercase text-slate-500">Presenças</p>
                <p className="text-2xl font-black text-white">{atual.presencas}<span className="text-sm font-medium text-slate-500">/{atual.total}</span></p>
              </div>
              <div>
                <p className="text-[11px] uppercase text-slate-500">Faltas</p>
                <p className="text-2xl font-black text-white">{atual.faltas}</p>
              </div>
            </div>
            <BarraFrequencia percentual={atual.percentual} minimo={minimo} />
            {atual.percentual < minimo && (
              <p className="text-xs text-red-300">
                Abaixo da frequência mínima de {minimo}%.
              </p>
            )}
          </header>

          {atual.turmas.map((t) => (
            <div key={`${t.disciplina_id}-${t.turma_nome}`} className="overflow-x-auto">
              {atual.turmas.length > 1 && (
                <p className="bg-slate-950/40 px-4 py-2 text-xs font-semibold text-slate-400">
                  {t.turma_nome || 'Sem turma'} · {t.percentual.toLocaleString('pt-BR')}% ({t.presencas}/{t.total_aulas})
                </p>
              )}
              <table className="w-full min-w-[560px] text-left text-sm text-slate-300">
                <thead className="bg-slate-950/50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-2.5">Data</th>
                    <th className="px-4 py-2.5">Aula</th>
                    <th className="px-4 py-2.5">Presença</th>
                    <th className="px-4 py-2.5">Conteúdo da aula</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {t.aulas.map((aula, indice) => (
                    <tr key={`${aula.data_aula}-${aula.numero_aula}-${indice}`}>
                      <td className="whitespace-nowrap px-4 py-2.5">{aula.data_aula ? formatarData(aula.data_aula) : '—'}</td>
                      <td className="px-4 py-2.5">{aula.numero_aula ?? '—'}</td>
                      <td className="px-4 py-2.5">
                        {aula.presente ? (
                          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-300">Presente</span>
                        ) : (
                          <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-xs font-semibold text-red-300">Falta</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-400">{aula.conteudo_ministrado || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </section>
      )}
    </div>
  );
};

/** Cards de resumo (frequência geral, presenças, faltas, disciplinas em risco). */
export const ResumoFrequencia: React.FC<{ dados: MinhaFrequencia }> = ({ dados }) => {
  const minimo = dados.frequencia_minima ?? 75;
  const emRisco = agrupar(dados.disciplinas).filter((d) => d.percentual < minimo).length;
  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Frequência geral</p>
        <strong className={`mt-2 block text-2xl font-black ${textoFrequencia(dados.percentual ?? 0, minimo)}`}>
          {dados.percentual == null ? '—' : `${dados.percentual.toLocaleString('pt-BR')}%`}
        </strong>
      </div>
      <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Presenças</p>
        <strong className="mt-2 block text-2xl font-black text-white">{dados.presencas}</strong>
      </div>
      <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Faltas</p>
        <strong className="mt-2 block text-2xl font-black text-white">{dados.faltas}</strong>
      </div>
      <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Disciplinas em risco</p>
        <strong className={`mt-2 block text-2xl font-black ${emRisco ? 'text-red-400' : 'text-emerald-300'}`}>{emRisco}</strong>
      </div>
    </section>
  );
};
