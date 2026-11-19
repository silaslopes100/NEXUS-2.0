import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, CalendarCheck, Loader2, RefreshCw, Search, X } from 'lucide-react';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  FiltrosFrequenciaUnidade,
  FrequenciaAlunoDetalhe,
  FrequenciaUnidade,
  frequenciaUnidadeApi,
} from '@/features/presencas/api';
import {
  BarraFrequencia,
  FrequenciaPorDisciplina,
  ResumoFrequencia,
  textoFrequencia,
} from '@/features/presencas/components/FrequenciaPorDisciplina';

interface Opcao { id: string; nome: string }

const erroTexto = (error: unknown, padrao: string) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : padrao;
};

const listaDe = (data: unknown): Opcao[] => {
  const itens = Array.isArray(data) ? data : ((data as { items?: Opcao[] })?.items || []);
  return itens.map((i: Opcao) => ({ id: String(i.id), nome: i.nome }));
};

const campo = 'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-nexus-yellow';

/** Detalhe da frequência de um aluno, navegando por Disciplina. */
const DetalheAlunoDrawer: React.FC<{ alunoId: string; onFechar: () => void }> = ({ alunoId, onFechar }) => {
  const [dados, setDados] = useState<FrequenciaAlunoDetalhe | null>(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    let ativo = true;
    frequenciaUnidadeApi.aluno(alunoId)
      .then((d) => ativo && setDados(d))
      .catch((e) => ativo && setErro(erroTexto(e, 'Não foi possível carregar a frequência do aluno.')));
    return () => { ativo = false; };
  }, [alunoId]);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && onFechar();
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [onFechar]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onFechar}>
      <aside
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Frequência do aluno"
        className="h-full w-full max-w-5xl space-y-5 overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Frequência do aluno</p>
            <h2 className="text-xl font-bold text-white">{dados?.aluno_nome || 'Carregando…'}</h2>
            {dados?.numero_matricula && <p className="text-xs text-slate-500">Matrícula {dados.numero_matricula}</p>}
          </div>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        </div>
        {erro && <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}
        {!dados ? (
          !erro && <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : dados.disciplinas.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500">Nenhuma chamada registrada para este aluno.</p>
        ) : (
          <>
            <ResumoFrequencia dados={dados} />
            <FrequenciaPorDisciplina dados={dados} />
          </>
        )}
      </aside>
    </div>
  );
};

/** Polo e Escola: frequência dos alunos da unidade por Disciplina (somente leitura). */
export const FrequenciaUnidadePage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const papel = normalizeUserRole(perfil?.nome || user?.perfil?.nome);
  const ehPolo = papel === 'polo';
  const [filtros, setFiltros] = useState<FiltrosFrequenciaUnidade>({ disciplina_id: '', turma_id: '', escola_id: '', busca: '', situacao: '' });
  const [busca, setBusca] = useState('');
  const [dados, setDados] = useState<FrequenciaUnidade | null>(null);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [alunoAberto, setAlunoAberto] = useState<string | null>(null);

  useEffect(() => {
    if (!ehPolo || !user?.polo_id) return;
    polosEscolasApi.listarEscolasDoPolo(user.polo_id).then((d) => setEscolas(listaDe(d))).catch(() => setEscolas([]));
  }, [ehPolo, user?.polo_id]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      setDados(await frequenciaUnidadeApi.carregar(filtros));
    } catch (e) {
      setErro(erroTexto(e, 'Não foi possível carregar a frequência dos alunos.'));
    } finally {
      setCarregando(false);
    }
  }, [filtros]);

  useEffect(() => { void carregar(); }, [carregar]);

  const minimo = dados?.frequencia_minima ?? 75;
  const disciplinaAtual = dados?.disciplinas.find((d) => d.id === filtros.disciplina_id);

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-emerald-950/30 p-6 shadow-xl sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Presenças &amp; Frequência</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Frequência dos alunos {ehPolo ? 'do polo' : 'da escola'} em cada disciplina, conforme as chamadas registradas
            pelos professores. Frequência mínima: {minimo}%.
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

      {/* Disciplina: filtro principal */}
      {dados && dados.disciplinas.length > 0 && (
        <nav aria-label="Disciplinas" className="flex gap-2 overflow-x-auto pb-1">
          {[{ id: '', nome: 'Todas as disciplinas' }, ...dados.disciplinas].map((d) => {
            const ativa = (filtros.disciplina_id || '') === d.id;
            return (
              <button
                key={d.id || 'todas'}
                type="button"
                onClick={() => setFiltros({ ...filtros, disciplina_id: d.id, turma_id: '' })}
                aria-pressed={ativa}
                className={`shrink-0 rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors ${
                  ativa ? 'border-blue-500 bg-blue-600 text-on-accent' : 'border-slate-700 text-slate-300 hover:bg-slate-800'
                }`}
              >
                {d.nome}
              </button>
            );
          })}
        </nav>
      )}

      <div className="glass flex flex-wrap items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
        <form className="relative min-w-[200px] flex-1" onSubmit={(e) => { e.preventDefault(); setFiltros({ ...filtros, busca: busca.trim() }); }}>
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar aluno ou matrícula (Enter)" className={`${campo} w-full pl-9`} />
        </form>
        <select aria-label="Turma" value={filtros.turma_id} onChange={(e) => setFiltros({ ...filtros, turma_id: e.target.value })} className={campo}>
          <option value="">Todas as turmas</option>
          {(dados?.turmas || []).map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
        </select>
        {ehPolo && (
          <select aria-label="Escola" value={filtros.escola_id} onChange={(e) => setFiltros({ ...filtros, escola_id: e.target.value })} className={campo}>
            <option value="">Todas as escolas</option>
            {escolas.map((esc) => <option key={esc.id} value={esc.id}>{esc.nome}</option>)}
          </select>
        )}
        <select aria-label="Situação" value={filtros.situacao} onChange={(e) => setFiltros({ ...filtros, situacao: e.target.value as FiltrosFrequenciaUnidade['situacao'] })} className={campo}>
          <option value="">Todas as situações</option>
          <option value="em_risco">Em risco (&lt; {minimo}%)</option>
          <option value="regular">Regular</option>
        </select>
      </div>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {dados && (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Frequência média{disciplinaAtual ? ` · ${disciplinaAtual.nome}` : ''}</p>
            <strong className={`mt-2 block text-2xl font-black ${textoFrequencia(dados.percentual ?? 0, minimo)}`}>
              {dados.percentual == null ? '—' : `${dados.percentual.toLocaleString('pt-BR')}%`}
            </strong>
          </div>
          <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Alunos</p>
            <strong className="mt-2 block text-2xl font-black text-white">{dados.total_alunos}</strong>
          </div>
          <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Alunos em risco</p>
            <strong className={`mt-2 block text-2xl font-black ${dados.alunos_em_risco ? 'text-red-400' : 'text-emerald-300'}`}>{dados.alunos_em_risco}</strong>
          </div>
        </section>
      )}

      <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm text-slate-300">
            <thead className="bg-slate-950/50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Aluno</th>
                {ehPolo && <th className="px-4 py-3">Escola</th>}
                <th className="px-4 py-3">Disciplina</th>
                <th className="px-4 py-3">Turma</th>
                <th className="px-4 py-3 text-center">Presenças</th>
                <th className="px-4 py-3 text-center">Faltas</th>
                <th className="w-48 px-4 py-3">Frequência</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {carregando && !dados ? (
                <tr><td colSpan={7} className="py-12 text-center text-blue-400"><Loader2 className="mx-auto animate-spin" /></td></tr>
              ) : !dados || dados.linhas.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-14 text-center">
                    <CalendarCheck className="mx-auto mb-2 h-7 w-7 text-slate-600" />
                    <p className="text-slate-400">Nenhuma chamada registrada para os filtros escolhidos.</p>
                  </td>
                </tr>
              ) : dados.linhas.map((l) => (
                <tr
                  key={`${l.aluno_id}-${l.disciplina_id}-${l.turma_id}`}
                  onClick={() => setAlunoAberto(l.aluno_id)}
                  className="cursor-pointer hover:bg-slate-800/40"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-white">{l.aluno_nome}</p>
                    {l.numero_matricula && <p className="text-xs text-slate-500">{l.numero_matricula}</p>}
                  </td>
                  {ehPolo && <td className="px-4 py-3 text-xs">{l.escola_nome || '—'}</td>}
                  <td className="px-4 py-3">{l.disciplina_nome}</td>
                  <td className="px-4 py-3 text-xs">{l.turma_nome || '—'}</td>
                  <td className="px-4 py-3 text-center">{l.presencas}/{l.total_aulas}</td>
                  <td className="px-4 py-3 text-center">{l.faltas}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <BarraFrequencia percentual={l.percentual} minimo={minimo} className="h-1.5 flex-1" />
                      <span className={`w-14 text-right text-sm font-bold ${textoFrequencia(l.percentual, minimo)}`}>
                        {l.percentual.toLocaleString('pt-BR')}%
                      </span>
                      {l.situacao === 'em_risco' && <AlertTriangle size={14} className="shrink-0 text-red-400" aria-label="Em risco" />}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {alunoAberto && <DetalheAlunoDrawer alunoId={alunoAberto} onFechar={() => setAlunoAberto(null)} />}
    </div>
  );
};
