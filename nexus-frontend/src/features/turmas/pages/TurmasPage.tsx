import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle, Ban, CheckCircle2, ChevronLeft, ChevronRight, Clock, Loader2, Plus, PlayCircle, Search, X,
} from 'lucide-react';
import { apiErrorMessage } from '@/features/alunos/api';
import {
  formatarData,
  ModalidadeTurma,
  ROTULO_MODALIDADE,
  ROTULO_SITUACAO_TURMA,
  SituacaoTurma,
  Turma,
  turmasApi,
} from '@/features/turmas/api';
import { inputCls, useOpcoesTurma } from '@/features/turmas/components/TurmaFormModal';

const PAGE_SIZE = 10;
const BUSCA_DEBOUNCE_MS = 300;

/** Raiz das telas de turma conforme o perfil (admin, polo, escola). */
export const baseTurmas = (role?: string | null) =>
  role === 'polo' ? '/polo/turmas' : role === 'escola' ? '/escola/turmas' : '/admin/turmas-calendarios';

const ICONE_SITUACAO: Record<SituacaoTurma, React.ElementType> = {
  planejada: Clock,
  em_andamento: PlayCircle,
  concluida: CheckCircle2,
  cancelada: Ban,
};

const COR_SITUACAO: Record<SituacaoTurma, string> = {
  planejada: 'border-slate-600 bg-slate-800 text-slate-200',
  em_andamento: 'border-blue-500/40 bg-blue-500/10 text-blue-200',
  concluida: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  cancelada: 'border-red-500/40 bg-red-500/10 text-red-200',
};

export const SeloSituacao: React.FC<{ turma: Pick<Turma, 'situacao' | 'periodo_encerrado'> }> = ({ turma }) => {
  const s = turma.situacao ?? 'em_andamento';
  const Icone = ICONE_SITUACAO[s];
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold ${COR_SITUACAO[s]}`}>
        <Icone className="h-3 w-3" aria-hidden /> {ROTULO_SITUACAO_TURMA[s]}
      </span>
      {turma.periodo_encerrado && (
        <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-200">
          <AlertTriangle className="h-3 w-3" aria-hidden /> Período encerrado
        </span>
      )}
    </span>
  );
};

const FILTROS = ['q', 'situacao', 'modalidade', 'curso_id', 'polo_id', 'escola_id', 'ano'] as const;
type Filtro = (typeof FILTROS)[number];

export const TurmasPage: React.FC = () => {
  const navigate = useNavigate();
  const { role, isAdmin, isPolo, cursos, polos, escolas, erro: erroOpcoes } = useOpcoesTurma();
  const base = baseTurmas(role);
  const [params, setParams] = useSearchParams();
  const filtro = (k: Filtro) => params.get(k) || '';
  const page = Math.max(Number(params.get('page') || 1), 1);
  const offset = (page - 1) * PAGE_SIZE;

  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [total, setTotal] = useState(0);
  const [busca, setBusca] = useState(filtro('q'));
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');

  const definir = (mudancas: Partial<Record<Filtro | 'page', string>>) => {
    const next = new URLSearchParams(params);
    Object.entries(mudancas).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!('page' in mudancas)) next.delete('page');
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (busca.trim() !== filtro('q')) definir({ q: busca.trim() });
    }, BUSCA_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busca]);

  const chave = params.toString();
  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setErro('');
    turmasApi
      .listarPaginado({
        q: filtro('q') || undefined,
        situacao: (filtro('situacao') || undefined) as SituacaoTurma | undefined,
        modalidade: (filtro('modalidade') || undefined) as ModalidadeTurma | undefined,
        curso_id: filtro('curso_id') || undefined,
        polo_id: filtro('polo_id') || undefined,
        escola_id: filtro('escola_id') || undefined,
        ano: filtro('ano') ? Number(filtro('ano')) : undefined,
        limit: PAGE_SIZE,
        offset,
      })
      .then((pagina) => {
        if (!ativo) return;
        setTurmas(pagina.items);
        setTotal(pagina.total);
      })
      .catch((e) => ativo && setErro(apiErrorMessage(e, 'Erro ao carregar turmas.')))
      .finally(() => ativo && setLoading(false));
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave]);

  const temFiltro = FILTROS.some((k) => filtro(k));
  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const anoAtual = new Date().getFullYear();
  const anos = [anoAtual + 1, anoAtual, anoAtual - 1, anoAtual - 2];
  const escolasDoPolo = escolas.filter((e) => !filtro('polo_id') || !e.polo_id || e.polo_id === filtro('polo_id'));
  const selectCls = `${inputCls} py-2`;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{isAdmin ? 'Turmas & Calendários' : 'Turmas'}</h1>
          {isAdmin && (
            <p className="mt-1 text-sm text-slate-400">
              Início e fim de cada turma vêm do Calendário Acadêmico do curso.{' '}
              <Link to="/admin/calendarios" className="font-semibold text-blue-400 hover:text-blue-300">
                Gerenciar calendários
              </Link>
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => navigate(`${base}/nova`)}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-blue-500"
        >
          <Plus size={16} /> Nova turma
        </button>
      </header>

      {(erro || erroOpcoes) && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          {erro || erroOpcoes}
        </div>
      )}

      <section aria-label="Filtros" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="relative block sm:col-span-2">
          <span className="sr-only">Buscar por nome ou código</span>
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" aria-hidden />
          <input className={`${inputCls} pl-9`} placeholder="Buscar por nome ou código" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </label>
        <label>
          <span className="sr-only">Situação</span>
          <select className={selectCls} value={filtro('situacao')} onChange={(e) => definir({ situacao: e.target.value })}>
            <option value="">Todas as situações</option>
            {(Object.keys(ROTULO_SITUACAO_TURMA) as SituacaoTurma[]).map((s) => (
              <option key={s} value={s}>{ROTULO_SITUACAO_TURMA[s]}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">Modalidade</span>
          <select className={selectCls} value={filtro('modalidade')} onChange={(e) => definir({ modalidade: e.target.value })}>
            <option value="">Presencial e EAD</option>
            <option value="presencial">Presencial</option>
            <option value="ead">EAD</option>
          </select>
        </label>
        <label>
          <span className="sr-only">Curso</span>
          <select className={selectCls} value={filtro('curso_id')} onChange={(e) => definir({ curso_id: e.target.value })}>
            <option value="">Todos os cursos</option>
            {cursos.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </label>
        {isAdmin && (
          <label>
            <span className="sr-only">Polo</span>
            <select className={selectCls} value={filtro('polo_id')} onChange={(e) => definir({ polo_id: e.target.value, escola_id: '' })}>
              <option value="">Todos os polos</option>
              {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          </label>
        )}
        {(isAdmin || isPolo) && escolas.length > 0 && (
          <label>
            <span className="sr-only">Escola</span>
            <select className={selectCls} value={filtro('escola_id')} onChange={(e) => definir({ escola_id: e.target.value })}>
              <option value="">Todas as escolas</option>
              {escolasDoPolo.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
            </select>
          </label>
        )}
        <label>
          <span className="sr-only">Ano de início</span>
          <select className={selectCls} value={filtro('ano')} onChange={(e) => definir({ ano: e.target.value })}>
            <option value="">Qualquer ano</option>
            {anos.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
        {temFiltro && (
          <button
            type="button"
            onClick={() => {
              setBusca('');
              setParams(new URLSearchParams(), { replace: true });
            }}
            className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            <X size={14} /> Limpar filtros
          </button>
        )}
      </section>

      <div className="glass overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/80">
        <table className="w-full min-w-[880px] text-left text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-4">Código</th>
              <th className="p-4">Turma</th>
              <th className="p-4">Curso</th>
              <th className="p-4">Unidade</th>
              <th className="p-4">Período</th>
              <th className="p-4">Situação</th>
              <th className="p-4 text-right">Alunos</th>
              <th className="p-4 text-right">Andamento</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-300">
            {loading && (
              <tr>
                <td colSpan={8} className="p-8 text-center">
                  <Loader2 className="mx-auto animate-spin text-slate-400" />
                </td>
              </tr>
            )}
            {!loading && turmas.length === 0 && (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-500">
                  {temFiltro ? 'Nenhuma turma com esses filtros.' : 'Nenhuma turma cadastrada.'}
                </td>
              </tr>
            )}
            {!loading &&
              turmas.map((turma) => (
                <tr
                  key={turma.id}
                  className="cursor-pointer hover:bg-slate-800/40"
                  onClick={() => navigate(`${base}/${turma.id}`)}
                >
                  <td className="p-4 font-mono text-xs text-slate-400 whitespace-nowrap">{turma.codigo || '—'}</td>
                  <td className="p-4">
                    <Link
                      to={`${base}/${turma.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-semibold text-white hover:text-nexus-yellow"
                    >
                      {turma.nome}
                    </Link>
                    <span className="block text-xs text-slate-500">{ROTULO_MODALIDADE[turma.modalidade ?? 'presencial']}</span>
                  </td>
                  <td className="p-4">{turma.curso_nome || '—'}</td>
                  <td className="p-4">{turma.escola_nome || turma.polo_nome || '—'}</td>
                  <td className="p-4 whitespace-nowrap tabular-nums">{formatarData(turma.data_inicio)} – {formatarData(turma.data_fim)}</td>
                  <td className="p-4"><SeloSituacao turma={turma} /></td>
                  <td className="p-4 text-right tabular-nums">
                    {turma.total_alunos}
                    {turma.vagas ? <span className="text-slate-500">/{turma.vagas}</span> : null}
                  </td>
                  <td className="p-4 text-right tabular-nums">
                    {turma.andamento_pct != null ? `${turma.andamento_pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : '—'}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between text-sm text-slate-400">
        <span>{total} turma(s)</span>
        <span className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Página anterior"
            disabled={page <= 1}
            onClick={() => definir({ page: String(page - 1) })}
            className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800 disabled:opacity-40"
          >
            <ChevronLeft size={16} />
          </button>
          Página {page} de {totalPaginas}
          <button
            type="button"
            aria-label="Próxima página"
            disabled={page >= totalPaginas}
            onClick={() => definir({ page: String(page + 1) })}
            className="rounded-lg border border-slate-700 p-2 hover:bg-slate-800 disabled:opacity-40"
          >
            <ChevronRight size={16} />
          </button>
        </span>
      </footer>
    </div>
  );
};
