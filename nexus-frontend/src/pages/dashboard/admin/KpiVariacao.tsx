import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { fmtPct } from './formato';

interface Props {
  rotulo: string;
  valor: string;
  icone: React.ElementType;
  /** Variação em % (ou p.p. quando `unidadeVariacao="p.p."`); null = sem base de comparação. */
  variacao?: number | null;
  unidadeVariacao?: '%' | 'p.p.';
  /** Quando subir é ruim (ex.: inadimplência), a cor da seta inverte. */
  subirEhRuim?: boolean;
  detalhe?: string;
  to?: string;
  carregando?: boolean;
}

/** Cartão de indicador com seta de tendência em relação ao período anterior. */
export const KpiVariacao: React.FC<Props> = ({
  rotulo, valor, icone: Icone, variacao, unidadeVariacao = '%', subirEhRuim = false, detalhe, to, carregando,
}) => {
  const temVariacao = variacao !== undefined;
  const semBase = variacao === null;
  const subiu = (variacao ?? 0) > 0;
  const desceu = (variacao ?? 0) < 0;
  const bom = subirEhRuim ? desceu : subiu;
  const ruim = subirEhRuim ? subiu : desceu;
  const Seta = subiu ? ArrowUpRight : desceu ? ArrowDownRight : Minus;
  const corSeta = bom ? 'text-emerald-400' : ruim ? 'text-rose-400' : 'text-slate-500';
  const textoVariacao = semBase
    ? 'sem base anterior'
    : unidadeVariacao === 'p.p.'
      ? `${subiu ? '+' : ''}${fmtPct(variacao, 1).replace('%', '')} p.p.`
      : `${subiu ? '+' : ''}${fmtPct(variacao, 1)}`;

  const corpo = (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{rotulo}</span>
        <span className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-nexus-yellow"><Icone className="h-4 w-4" /></span>
      </div>
      <div className="mt-3 text-2xl font-black text-white">{carregando ? '…' : valor}</div>
      {temVariacao && !carregando && (
        <div className="mt-2 flex items-center gap-1 text-xs">
          {!semBase && <Seta className={`h-3.5 w-3.5 ${corSeta}`} aria-hidden />}
          <span className={semBase ? 'text-slate-500' : 'text-slate-300'}>{textoVariacao}</span>
          <span className="text-slate-500">vs. período anterior</span>
        </div>
      )}
      {detalhe && !carregando && <p className="mt-1 text-xs text-slate-500">{detalhe}</p>}
    </>
  );

  const cls = 'glass block rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-md transition-all';
  return to ? (
    <Link to={to} className={`${cls} hover:border-nexus-yellow/40 hover:bg-slate-900`}>{corpo}</Link>
  ) : (
    <div className={cls}>{corpo}</div>
  );
};
