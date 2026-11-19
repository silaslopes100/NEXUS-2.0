import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, AlertTriangle, CalendarCheck, ChevronDown, Loader2, RefreshCw } from 'lucide-react';
import { DisciplinaFrequencia, MinhaFrequencia, minhasPresencasApi } from '@/features/presencas/api';
import { formatarData } from '@/features/turmas/api';

const erroTexto = (error: unknown, padrao: string) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : padrao;
};

/** Cor da frequência: verde a partir do mínimo, âmbar até 15 pontos abaixo, vermelho abaixo disso. */
const corFrequencia = (percentual: number, minimo: number) =>
  percentual >= minimo ? 'bg-emerald-500' : percentual >= minimo - 15 ? 'bg-amber-500' : 'bg-red-500';

const textoFrequencia = (percentual: number, minimo: number) =>
  percentual >= minimo ? 'text-emerald-300' : percentual >= minimo - 15 ? 'text-amber-300' : 'text-red-400';

/** Presenças e frequência do aluno, vindas das chamadas e atas registradas pelos professores. */
export const MinhasPresencasPage: React.FC = () => {
  const [dados, setDados] = useState<MinhaFrequencia | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [filtro, setFiltro] = useState('');
  const [aberta, setAberta] = useState<string | null>(null);

  const carregar = async () => {
    setCarregando(true);
    setErro('');
    try {
      setDados(await minhasPresencasApi.carregar());
    } catch (error) {
      setErro(erroTexto(error, 'Não foi possível carregar suas presenças.'));
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => { void carregar(); }, []);

  const minimo = dados?.frequencia_minima ?? 75;
  const chave = (d: DisciplinaFrequencia) => `${d.disciplina_id || d.disciplina_nome}|${d.turma_nome || ''}`;
  const disciplinas = useMemo(
    () => (dados?.disciplinas || []).filter((d) => !filtro || chave(d) === filtro),
    [dados, filtro],
  );
  const emRisco = (dados?.disciplinas || []).filter((d) => d.situacao === 'em_risco').length;

  return (
    <div className="max-w-6xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/30 p-6 shadow-xl sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Frequência &amp; Presença</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Suas presenças em cada disciplina, conforme as chamadas e atas registradas pelos professores. A frequência
            mínima é de {minimo}%.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void carregar()}
          disabled={carregando}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} /> Atualizar
        </button>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {carregando && !dados ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : dados && dados.disciplinas.length === 0 ? (
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-16 text-center">
          <CalendarCheck className="mx-auto mb-3 h-8 w-8 text-slate-500" />
          <h2 className="font-semibold text-white">Nenhuma chamada registrada ainda</h2>
          <p className="mt-1 text-sm text-slate-400">Assim que os professores fizerem a chamada, suas presenças aparecem aqui.</p>
        </div>
      ) : dados ? (
        <>
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

          {dados.disciplinas.length > 1 && (
            <select
              aria-label="Filtrar disciplina"
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-nexus-yellow sm:w-80"
            >
              <option value="">Todas as disciplinas</option>
              {dados.disciplinas.map((d) => (
                <option key={chave(d)} value={chave(d)}>{d.disciplina_nome}{d.turma_nome ? ` · ${d.turma_nome}` : ''}</option>
              ))}
            </select>
          )}

          <ul className="space-y-3">
            {disciplinas.map((d) => {
              const id = chave(d);
              const expandida = aberta === id;
              return (
                <li key={id} className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
                  <button
                    type="button"
                    onClick={() => setAberta(expandida ? null : id)}
                    aria-expanded={expandida}
                    className="flex w-full flex-col gap-3 p-5 text-left hover:bg-slate-800/30 sm:flex-row sm:items-center"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="font-bold text-white">{d.disciplina_nome}</h2>
                        {d.situacao === 'em_risco' && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[11px] font-semibold text-red-300">
                            <AlertTriangle size={12} /> Em risco
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {[d.turma_nome, d.professor_nome && `Prof. ${d.professor_nome}`].filter(Boolean).join(' · ') || '—'}
                      </p>
                      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                        <div className={`h-full ${corFrequencia(d.percentual, minimo)}`} style={{ width: `${Math.min(100, d.percentual)}%` }} />
                      </div>
                    </div>
                    <div className="flex items-center gap-4 sm:w-56 sm:justify-end">
                      <div className="text-right">
                        <p className={`text-xl font-black ${textoFrequencia(d.percentual, minimo)}`}>{d.percentual.toLocaleString('pt-BR')}%</p>
                        <p className="text-xs text-slate-500">{d.presencas} de {d.total_aulas} aula(s) · {d.faltas} falta(s)</p>
                      </div>
                      <ChevronDown size={18} className={`shrink-0 text-slate-500 transition-transform ${expandida ? 'rotate-180' : ''}`} />
                    </div>
                  </button>
                  {expandida && (
                    <div className="overflow-x-auto border-t border-slate-800">
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
                          {d.aulas.map((aula, indice) => (
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
                  )}
                </li>
              );
            })}
          </ul>
        </>
      ) : null}
    </div>
  );
};
