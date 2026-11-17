import React, { useEffect, useState } from 'react';
import { Layers } from 'lucide-react';
import { cursosApi, Disciplina } from '@/features/cursos/api';
import { EstoqueDisciplina, EstoqueDisciplinaItem, nomeDisciplina, SEM_DISCIPLINA } from '@/features/licencas/api';

const selectClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

/** Valor do <select> para o balde "Sem disciplina". */
export const VALOR_SEM_DISCIPLINA = '__sem__';
export const paraDisciplinaId = (valor: string): string | null =>
  !valor || valor === VALOR_SEM_DISCIPLINA ? null : valor;

/** Lista de disciplinas do catálogo (carregada uma vez). */
export const useDisciplinas = () => {
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  useEffect(() => {
    cursosApi.listarDisciplinas()
      .then((items) => setDisciplinas([...items].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))))
      .catch(() => setDisciplinas([]));
  }, []);
  return disciplinas;
};

interface SelectProps {
  value: string;
  onChange: (valor: string) => void;
  /** Quando informado, só mostra disciplinas com saldo e exibe o disponível. */
  saldos?: EstoqueDisciplinaItem[];
  disciplinas?: Disciplina[];
  incluirSemDisciplina?: boolean;
  required?: boolean;
  label?: string;
}

/** Seletor de disciplina. Com `saldos`, lista apenas onde há licenças disponíveis. */
export const DisciplinaSelect: React.FC<SelectProps> = ({
  value, onChange, saldos, disciplinas = [], incluirSemDisciplina = true, required = true, label = 'Disciplina',
}) => {
  const opcoes = saldos
    ? saldos
      .filter((s) => s.quantidade_disponivel > 0 && (incluirSemDisciplina || s.materia_id))
      .map((s) => ({ valor: s.materia_id || VALOR_SEM_DISCIPLINA, rotulo: `${nomeDisciplina(s)} — ${s.quantidade_disponivel} disponível(is)` }))
    : [
      ...(incluirSemDisciplina ? [{ valor: VALOR_SEM_DISCIPLINA, rotulo: SEM_DISCIPLINA }] : []),
      ...disciplinas.map((d) => ({ valor: d.id, rotulo: d.nome })),
    ];
  return (
    <label className="block space-y-1 text-sm text-slate-300">
      <span>{label}</span>
      <select required={required} value={value} onChange={(e) => onChange(e.target.value)} className={selectClass}>
        <option value="">Selecione</option>
        {opcoes.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
      </select>
      {saldos && !opcoes.length && <span className="block text-xs text-amber-300">Nenhuma disciplina com saldo disponível.</span>}
    </label>
  );
};

/** Tabela de saldo por disciplina (Polo ou Escola). */
export const TabelaEstoqueDisciplina: React.FC<{ estoque: EstoqueDisciplina | null; acao?: React.ReactNode }> = ({ estoque, acao }) => (
  <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
      <div>
        <h2 className="flex items-center gap-2 font-bold text-white"><Layers size={16} /> Saldo por disciplina</h2>
        <p className="text-xs text-slate-500">
          {estoque ? `${estoque.total_disponivel} disponível(is) · ${estoque.total_vendida} vendida(s)` : '—'}
        </p>
      </div>
      {acao}
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
          <tr><th className="p-4">Disciplina</th><th className="p-4 text-right">Disponíveis</th><th className="p-4 text-right">Vendidas</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {(estoque?.items || []).map((i) => (
            <tr key={i.materia_id || 'sem'} className="text-slate-300">
              <td className={`p-4 ${i.materia_id ? 'font-semibold text-white' : 'italic text-amber-300'}`}>{nomeDisciplina(i)}</td>
              <td className="p-4 text-right font-bold">{i.quantidade_disponivel}</td>
              <td className="p-4 text-right">{i.quantidade_vendida}</td>
            </tr>
          ))}
          {!estoque?.items.length && <tr><td colSpan={3} className="p-10 text-center text-slate-500">Nenhum saldo registrado.</td></tr>}
        </tbody>
      </table>
    </div>
  </section>
);
