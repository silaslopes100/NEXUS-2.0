import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Filter, GraduationCap, History, Loader2, Plus, RefreshCw, Search, Users, X } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { EVENTO, MatriculaEad, MovimentacaoEad, ResumoEad, TurmaEadOpcao, gestaoEadApi } from '../../adminApi';
import { brl } from '../../api';
import { FichaEadDrawer } from '../../components/admin/FichaEadDrawer';
import { ListaMovimentacoes } from '../../components/admin/Movimentacoes';
import { NovaMatriculaModal } from '../../components/admin/NovaMatriculaModal';

const POR_PAGINA = 20;
const selectCls = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-nexus-yellow focus:outline-none';
const labelCls = 'mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-500';
const FILTROS = ['busca', 'turma_id', 'tipo', 'origem', 'status', 'evento', 'data_inicio', 'data_fim'] as const;

const Kpi: React.FC<{ rotulo: string; valor: string | number; detalhe?: string }> = ({ rotulo, valor, detalhe }) => (
  <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
    <p className="text-xs font-semibold uppercase text-slate-500">{rotulo}</p>
    <strong className="mt-2 block text-2xl font-black text-white">{valor}</strong>
    {detalhe && <p className="mt-1 text-xs text-slate-400">{detalhe}</p>}
  </div>
);

/** Gestão de Matrículas EAD: matrículas (site e manuais), bolsistas, liberações e todas as movimentações. */
export const GestaoMatriculasEadPage: React.FC = () => {
  const [params, setParams] = useSearchParams();
  const aba = params.get('aba') === 'movimentacoes' ? 'movimentacoes' : 'matriculas';
  const pagina = Math.max(Number(params.get('page') || 1), 1);
  const filtros = useMemo(() => Object.fromEntries(FILTROS.map((k) => [k, params.get(k) || undefined])), [params]);
  const [buscaLocal, setBuscaLocal] = useState(params.get('busca') || '');

  const [turmas, setTurmas] = useState<TurmaEadOpcao[]>([]);
  const [resumo, setResumo] = useState<ResumoEad | null>(null);
  const [matriculas, setMatriculas] = useState<{ total: number; items: MatriculaEad[] } | null>(null);
  const [movs, setMovs] = useState<{ total: number; items: MovimentacaoEad[] } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [nova, setNova] = useState(false);
  const [ficha, setFicha] = useState<string | null>(null);

  const set = (chave: string, valor?: string) => {
    const next = new URLSearchParams(params);
    if (valor) next.set(chave, valor); else next.delete(chave);
    if (chave !== 'page') next.delete('page');
    setParams(next, { replace: chave === 'busca' });
  };

  useEffect(() => {
    const t = window.setTimeout(() => { if (buscaLocal !== (params.get('busca') || '')) set('busca', buscaLocal.trim() || undefined); }, 400);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buscaLocal]);

  useEffect(() => { gestaoEadApi.turmas().then(setTurmas).catch(() => setTurmas([])); }, []);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const periodo = { data_inicio: filtros.data_inicio, data_fim: filtros.data_fim };
      const offset = (pagina - 1) * POR_PAGINA;
      const [r, lista] = await Promise.all([
        gestaoEadApi.resumo(periodo),
        aba === 'matriculas'
          ? gestaoEadApi.matriculas({ ...filtros, evento: undefined }, POR_PAGINA, offset)
          : gestaoEadApi.movimentacoes({ busca: filtros.busca, turma_id: filtros.turma_id, evento: filtros.evento, ...periodo }, POR_PAGINA, offset),
      ]);
      setResumo(r);
      if (aba === 'matriculas') setMatriculas(lista as { total: number; items: MatriculaEad[] });
      else setMovs(lista as { total: number; items: MovimentacaoEad[] });
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar as matrículas EAD.'));
    } finally {
      setCarregando(false);
    }
  }, [aba, filtros, pagina]);

  useEffect(() => { void carregar(); }, [carregar]);
  useEffect(() => {
    if (!aviso) return;
    const t = window.setTimeout(() => setAviso(null), 3500);
    return () => window.clearTimeout(t);
  }, [aviso]);

  const total = (aba === 'matriculas' ? matriculas?.total : movs?.total) ?? 0;
  const paginas = Math.max(Math.ceil(total / POR_PAGINA), 1);
  const ativos = FILTROS.filter((k) => params.get(k)).length;

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-extrabold text-white"><GraduationCap className="text-nexus-yellow" /> Matrículas EAD</h1>
          <p className="mt-1 text-sm text-slate-400">Matrículas pelo site e manuais, bolsistas, liberações de disciplina e todas as movimentações do EAD.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void carregar()} title="Recarregar" className="rounded-xl border border-slate-700 p-2.5 text-slate-400 hover:text-white">
            <RefreshCw size={16} className={carregando ? 'animate-spin' : ''} />
          </button>
          <button type="button" onClick={() => setNova(true)} className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
            <Plus size={16} /> Nova matrícula manual
          </button>
        </div>
      </header>

      {resumo && (
        <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Kpi rotulo="Matrículas ativas" valor={resumo.matriculas_ativas} detalhe={`${resumo.canceladas} cancelada(s)`} />
          <Kpi rotulo="Bolsistas" valor={resumo.bolsistas} />
          <Kpi rotulo="Novas no período" valor={resumo.novas_site + resumo.novas_manuais} detalhe={`${resumo.novas_site} site · ${resumo.novas_manuais} manuais`} />
          <Kpi rotulo="Compras pagas" valor={resumo.compras_pagas} detalhe={`${resumo.compras_pendentes} pendente(s) agora`} />
          <Kpi rotulo="Liberações manuais" valor={resumo.liberacoes_manuais} />
          <Kpi rotulo="Receita EAD" valor={brl(resumo.receita)} detalhe={`${resumo.vendas_com_livro} venda(s) com livro`} />
        </section>
      )}

      <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-bold text-white">
            <Filter size={15} className="text-blue-400" /> Filtros
            {ativos > 0 && <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[11px] text-blue-300">{ativos} ativo(s)</span>}
          </h2>
          {ativos > 0 && (
            <button type="button" onClick={() => { setBuscaLocal(''); setParams(new URLSearchParams(aba === 'movimentacoes' ? { aba } : {})); }}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"><X size={13} /> Limpar</button>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
          <div className="col-span-2">
            <label className={labelCls}>Busca</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input value={buscaLocal} onChange={(e) => setBuscaLocal(e.target.value)} placeholder="Nome, e-mail, CPF, matrícula"
                className={`${selectCls} pl-8`} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Turma</label>
            <select className={selectCls} value={filtros.turma_id || ''} onChange={(e) => set('turma_id', e.target.value)}>
              <option value="">Todas</option>
              {turmas.map((t) => <option key={t.id} value={t.id}>{t.nome}{t.aberta ? '' : ' (encerrada)'}</option>)}
            </select>
          </div>
          {aba === 'matriculas' ? (
            <>
              <div>
                <label className={labelCls}>Tipo</label>
                <select className={selectCls} value={filtros.tipo || ''} onChange={(e) => set('tipo', e.target.value)}>
                  <option value="">Todos</option><option value="regular">Regular</option><option value="bolsista">Bolsista</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Origem</label>
                <select className={selectCls} value={filtros.origem || ''} onChange={(e) => set('origem', e.target.value)}>
                  <option value="">Todas</option><option value="site">Site</option><option value="manual">Manual</option><option value="legado">Legado</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Situação</label>
                <select className={selectCls} value={filtros.status || ''} onChange={(e) => set('status', e.target.value)}>
                  <option value="">Todas</option><option value="ativa">Ativa</option><option value="cancelada">Cancelada</option>
                </select>
              </div>
            </>
          ) : (
            <div className="col-span-2 md:col-span-1 xl:col-span-3">
              <label className={labelCls}>Evento</label>
              <select className={selectCls} value={filtros.evento || ''} onChange={(e) => set('evento', e.target.value)}>
                <option value="">Todos</option>
                {Object.entries(EVENTO).map(([v, e]) => <option key={v} value={v}>{e.rotulo}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className={labelCls}>De</label>
            <input type="date" className={selectCls} value={filtros.data_inicio || ''} onChange={(e) => set('data_inicio', e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Até</label>
            <input type="date" className={selectCls} value={filtros.data_fim || ''} onChange={(e) => set('data_fim', e.target.value)} />
          </div>
        </div>
      </section>

      <div className="flex gap-1 self-start rounded-xl border border-slate-800 bg-slate-900/60 p-1">
        {([['matriculas', 'Matrículas', Users], ['movimentacoes', 'Movimentações', History]] as const).map(([v, r, Icone]) => (
          <button key={v} type="button" onClick={() => set('aba', v === 'matriculas' ? undefined : v)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-semibold ${aba === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
            <Icone size={13} /> {r}
          </button>
        ))}
      </div>

      {erro && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}

      <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <p className="text-xs text-slate-500">{total} {aba === 'matriculas' ? 'matrícula(s)' : 'movimentação(ões)'}</p>
          {carregando && <Loader2 size={16} className="animate-spin text-blue-400" />}
        </div>
        {aba === 'matriculas' ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="p-3">Aluno</th><th className="p-3">Turma / curso</th><th className="p-3">Tipo</th><th className="p-3">Origem</th>
                  <th className="p-3 text-center">Pagas</th><th className="p-3 text-center">Liberadas</th><th className="p-3 text-center">Pendentes</th>
                  <th className="p-3">Situação</th><th className="p-3">Matrícula</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {(matriculas?.items ?? []).map((m) => (
                  <tr key={m.id} onClick={() => setFicha(m.aluno_id)} className="cursor-pointer hover:bg-slate-800/50">
                    <td className="p-3">
                      <p className="font-semibold text-white">{m.nome}</p>
                      <p className="text-[11px] text-slate-500">{[m.numero_matricula, m.email].filter(Boolean).join(' · ')}</p>
                    </td>
                    <td className="p-3"><p className="text-white">{m.turma_nome || '—'}</p><p className="text-[11px] text-slate-500">{m.curso_nome}</p></td>
                    <td className="p-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${m.tipo === 'bolsista' ? 'bg-violet-500/20 text-violet-200' : 'bg-slate-800 text-slate-300'}`}>
                        {m.tipo === 'bolsista' ? 'Bolsista' : 'Regular'}
                      </span>
                    </td>
                    <td className="p-3 text-xs capitalize">{m.origem}</td>
                    <td className="p-3 text-center font-semibold text-emerald-300">{m.disciplinas_pagas}</td>
                    <td className="p-3 text-center font-semibold text-teal-300">{m.disciplinas_liberadas}</td>
                    <td className="p-3 text-center font-semibold text-amber-300">{m.disciplinas_pendentes}</td>
                    <td className="p-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${m.status === 'ativa' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-500/15 text-red-300'}`}>
                        {m.status === 'ativa' ? 'Ativa' : 'Cancelada'}
                      </span>
                      {m.aluno_desistente && <span className="ml-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-bold text-amber-300">Desistente</span>}
                    </td>
                    <td className="p-3 text-xs">{m.data_matricula ? new Date(m.data_matricula).toLocaleDateString('pt-BR') : '—'}</td>
                  </tr>
                ))}
                {matriculas && !matriculas.items.length && <tr><td colSpan={9} className="p-10 text-center text-slate-500">Nenhuma matrícula encontrada.</td></tr>}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6"><ListaMovimentacoes itens={movs?.items ?? []} onAbrirAluno={setFicha} /></div>
        )}
        {paginas > 1 && (
          <div className="flex items-center justify-end gap-2 border-t border-slate-800 p-3 text-xs text-slate-400">
            <button type="button" disabled={pagina <= 1} onClick={() => set('page', String(pagina - 1))} className="rounded-lg border border-slate-700 p-1.5 disabled:opacity-40"><ChevronLeft size={14} /></button>
            Página {pagina} de {paginas}
            <button type="button" disabled={pagina >= paginas} onClick={() => set('page', String(pagina + 1))} className="rounded-lg border border-slate-700 p-1.5 disabled:opacity-40"><ChevronRight size={14} /></button>
          </div>
        )}
      </section>

      {aviso && <div role="status" className="fixed bottom-6 right-6 z-[70] rounded-xl border border-emerald-500/30 bg-emerald-950/90 px-4 py-3 text-sm font-semibold text-emerald-200 shadow-2xl">{aviso}</div>}
      {nova && (
        <NovaMatriculaModal turmas={turmas} onFechar={() => setNova(false)}
          onCriada={(alunoId, convite) => {
            setNova(false);
            setAviso(convite === false ? 'Matrícula criada, mas o e-mail de convite não foi enviado.' : convite ? 'Matrícula criada e convite enviado por e-mail.' : 'Matrícula criada.');
            void carregar();
            setFicha(alunoId);
          }} />
      )}
      {ficha && <FichaEadDrawer alunoId={ficha} turmas={turmas} onFechar={() => setFicha(null)} onMudou={() => void carregar()} />}
    </div>
  );
};
