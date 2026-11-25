import React, { useEffect, useState } from 'react';
import { CheckCircle2, ChevronDown, ClipboardCheck, Lock, PlayCircle } from 'lucide-react';
import { formatarDuracao } from '../../api';
import { AulaResumoAluno, CapituloAluno } from '../../alunoApi';

const IconeAula: React.FC<{ aula: AulaResumoAluno; atual: boolean }> = ({ aula, atual }) => {
  if (aula.status === 'concluida') return <CheckCircle2 size={18} className="shrink-0 text-emerald-400" />;
  if (aula.status === 'bloqueada') return <Lock size={16} className="shrink-0 text-slate-600" />;
  if (aula.tipo === 'avaliacao') return <ClipboardCheck size={18} className={`shrink-0 ${atual ? 'text-nexus-yellow' : 'text-blue-300'}`} />;
  return <PlayCircle size={18} className={`shrink-0 ${atual ? 'text-nexus-yellow' : 'text-slate-400'}`} />;
};

const dicaBloqueio = (a: AulaResumoAluno) =>
  a.motivo_bloqueio === 'drip' && a.libera_em
    ? `Libera em ${new Date(a.libera_em).toLocaleDateString('pt-BR')}`
    : a.motivo_bloqueio === 'pre_requisito'
      ? 'Conclua as aulas anteriores'
      : 'Conclua a aula anterior';

interface Props {
  capitulos: CapituloAluno[];
  aulaAtualId?: string | null;
  onAbrir: (aulaId: string) => void;
}

/** Lista de capítulos e aulas (estilo "conteúdo do curso"), com progresso por capítulo. */
export const SidebarCapitulos: React.FC<Props> = ({ capitulos, aulaAtualId, onAbrir }) => {
  const capAtual = capitulos.find((c) => c.aulas.some((a) => a.id === aulaAtualId))?.id;
  const [abertos, setAbertos] = useState<Set<string>>(() => new Set(capAtual ? [capAtual] : capitulos.slice(0, 1).map((c) => c.id)));

  useEffect(() => {
    if (capAtual) setAbertos((s) => (s.has(capAtual) ? s : new Set([...s, capAtual])));
  }, [capAtual]);

  const alternar = (id: string) =>
    setAbertos((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  let numero = 0;
  return (
    <nav aria-label="Conteúdo da disciplina" className="space-y-2">
      {capitulos.map((c, ci) => {
        const aberto = abertos.has(c.id);
        const pct = c.total_aulas ? Math.round((c.aulas_concluidas / c.total_aulas) * 100) : 0;
        const duracao = c.aulas.reduce((s, a) => s + (a.duracao_min || 0), 0);
        const inicio = numero;
        numero += c.aulas.length;
        return (
          <section key={c.id} className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70">
            <button type="button" onClick={() => alternar(c.id)} aria-expanded={aberto}
              className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-slate-800/60">
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-black ${pct === 100 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-blue-600/20 text-blue-200'}`}>
                {pct === 100 ? <CheckCircle2 size={16} /> : ci + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-white">{c.titulo}</span>
                <span className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                  <span className="h-1 w-16 overflow-hidden rounded-full bg-slate-800">
                    <span className="block h-full bg-emerald-400" style={{ width: `${pct}%` }} />
                  </span>
                  {c.aulas_concluidas}/{c.total_aulas}{duracao ? ` · ${formatarDuracao(duracao)}` : ''}
                </span>
              </span>
              <ChevronDown size={16} className={`shrink-0 text-slate-500 transition ${aberto ? '' : '-rotate-90'}`} />
            </button>
            {aberto && (
              <ul className="border-t border-slate-800 py-1">
                {c.aulas.map((a, i) => {
                  const atual = a.id === aulaAtualId;
                  const bloqueada = a.status === 'bloqueada';
                  return (
                    <li key={a.id}>
                      <button type="button" disabled={bloqueada} onClick={() => onAbrir(a.id)}
                        aria-current={atual ? 'true' : undefined} title={bloqueada ? dicaBloqueio(a) : undefined}
                        className={`flex w-full items-start gap-3 px-3 py-2.5 text-left transition ${
                          atual ? 'bg-nexus-yellow/10 shadow-[inset_3px_0_0_#FFB800]' : 'hover:bg-slate-800/60'} ${bloqueada ? 'cursor-not-allowed opacity-60' : ''}`}>
                        <span className="mt-0.5"><IconeAula aula={a} atual={atual} /></span>
                        <span className="min-w-0 flex-1">
                          <span className={`block text-sm leading-snug ${atual ? 'font-semibold text-white' : 'text-slate-200'}`}>
                            <span className="text-slate-500">{inicio + i + 1}. </span>{a.titulo}
                          </span>
                          <span className="text-[11px] text-slate-500">
                            {bloqueada ? dicaBloqueio(a) : a.tipo === 'avaliacao' ? 'Avaliação' : a.duracao_min ? formatarDuracao(a.duracao_min) : 'Aula'}
                            {!a.obrigatoria && ' · opcional'}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}
    </nav>
  );
};
