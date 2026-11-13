import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Filter, X } from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';

/**
 * Filtros padrão de período e unidade (data início/fim, mês, semestre, ano,
 * Polo, Escola, status, tipo). O estado vive na URL para permitir compartilhar
 * o link e voltar com o filtro aplicado. Polo e Escola são opcionais.
 */

export const CHAVES_FILTRO = [
  'data_inicio', 'data_fim', 'mes', 'semestre', 'ano', 'polo_id', 'escola_id', 'status', 'tipo',
] as const;
export type ChaveFiltro = (typeof CHAVES_FILTRO)[number];

export interface Opcao { value: string; label: string; }

/** Lê os filtros atuais da URL (inclui `page`). */
export const useFiltrosUrl = () => {
  const [params, setParams] = useSearchParams();
  const filtros = useMemo(() => {
    const out: Partial<Record<ChaveFiltro, string>> = {};
    CHAVES_FILTRO.forEach((k) => { const v = params.get(k); if (v) out[k] = v; });
    return out;
  }, [params]);
  const page = Math.max(Number(params.get('page') || 1), 1);
  const setPage = (p: number) => {
    const next = new URLSearchParams(params);
    if (p <= 1) next.delete('page'); else next.set('page', String(p));
    setParams(next);
  };
  return { filtros, page, setPage };
};

const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const selectCls = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const labelCls = 'mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-500';

interface Props {
  /** Exibe os seletores de Polo e Escola (usuários Polo/Escola já têm escopo fixo). */
  mostrarUnidade?: boolean;
  statusOpcoes?: Opcao[];
  tipoOpcoes?: Opcao[];
}

export const PeriodoFiltros: React.FC<Props> = ({ mostrarUnidade = true, statusOpcoes, tipoOpcoes }) => {
  const [params, setParams] = useSearchParams();
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const poloId = params.get('polo_id') || '';

  useEffect(() => {
    if (!mostrarUnidade) return;
    polosEscolasApi.listarPolos({ limit: 200 })
      .then((data: any) => setPolos((data?.items || data || []).map((p: any) => ({ value: p.id, label: p.nome }))))
      .catch(() => setPolos([]));
  }, [mostrarUnidade]);

  useEffect(() => {
    if (!mostrarUnidade) return;
    polosEscolasApi.listarEscolas({ polo_id: poloId || undefined, limit: 200 })
      .then((data: any) => setEscolas((data?.items || data || []).map((e: any) => ({ value: e.id, label: e.nome }))))
      .catch(() => setEscolas([]));
  }, [mostrarUnidade, poloId]);

  const anos = useMemo(() => {
    const atual = new Date().getFullYear();
    return Array.from({ length: 6 }, (_, i) => String(atual - i));
  }, []);

  const set = (chave: ChaveFiltro, valor: string) => {
    const next = new URLSearchParams(params);
    if (valor) next.set(chave, valor); else next.delete(chave);
    if (chave === 'polo_id') next.delete('escola_id');
    next.delete('page');
    setParams(next);
  };
  const limpar = () => setParams(new URLSearchParams());
  const ativos = CHAVES_FILTRO.filter((k) => params.get(k)).length;

  const select = (chave: ChaveFiltro, label: string, opcoes: Opcao[], vazio = 'Todos') => (
    <div>
      <label className={labelCls}>{label}</label>
      <select className={selectCls} value={params.get(chave) || ''} onChange={(e) => set(chave, e.target.value)}>
        <option value="">{vazio}</option>
        {opcoes.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-bold text-white">
          <Filter size={15} className="text-blue-400" /> Filtros
          {ativos > 0 && <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[11px] text-blue-300">{ativos} ativo(s)</span>}
        </h2>
        {ativos > 0 && (
          <button onClick={limpar} className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white">
            <X size={13} /> Limpar
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        <div>
          <label className={labelCls}>Data início</label>
          <input type="date" className={selectCls} value={params.get('data_inicio') || ''} onChange={(e) => set('data_inicio', e.target.value)} />
        </div>
        <div>
          <label className={labelCls}>Data fim</label>
          <input type="date" className={selectCls} value={params.get('data_fim') || ''} onChange={(e) => set('data_fim', e.target.value)} />
        </div>
        {select('mes', 'Mês', MESES.map((m, i) => ({ value: String(i + 1), label: m })))}
        {select('semestre', 'Semestre', [{ value: '1', label: '1º semestre' }, { value: '2', label: '2º semestre' }])}
        {select('ano', 'Ano', anos.map((a) => ({ value: a, label: a })))}
        {mostrarUnidade && select('polo_id', 'Polo', polos)}
        {mostrarUnidade && select('escola_id', 'Escola', escolas, 'Todas')}
        {statusOpcoes && select('status', 'Status', statusOpcoes)}
        {tipoOpcoes && select('tipo', 'Tipo', tipoOpcoes)}
      </div>
    </section>
  );
};
