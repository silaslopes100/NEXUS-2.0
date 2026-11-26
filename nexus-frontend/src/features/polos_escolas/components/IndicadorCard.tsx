import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';

export type IndicadorAccent = 'blue' | 'emerald' | 'amber' | 'indigo';

const accentClass: Record<IndicadorAccent, string> = {
  blue: 'text-blue-400',
  emerald: 'text-emerald-400',
  amber: 'text-amber-300',
  indigo: 'text-indigo-400',
};

interface IndicadorCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  accent?: IndicadorAccent;
  /** Tela de destino; sem ela o card é apenas informativo. */
  to?: string;
  /** Dica exibida ao passar o mouse (ex.: limitação do filtro de destino). */
  hint?: string;
}

/** Card de indicador. Com `to`, vira um link para a tela que lista o que ele conta. */
export const IndicadorCard: React.FC<IndicadorCardProps> = ({ label, value, icon, accent = 'blue', to, hint }) => {
  const conteudo = (
    <>
      <div className="flex items-center justify-between gap-2 text-slate-500">
        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
        <span className={accentClass[accent]}>{icon}</span>
      </div>
      <div className="mt-2 flex items-end justify-between gap-2">
        <strong className="text-2xl font-black text-white">{value}</strong>
        {to && (
          <ArrowUpRight
            size={16}
            aria-hidden
            className="text-slate-600 transition-colors group-hover:text-blue-300 group-focus-visible:text-blue-300"
          />
        )}
      </div>
    </>
  );

  const base = 'rounded-2xl border border-slate-800 bg-slate-900/80 p-4';
  if (!to) {
    return <div className={base} title={hint}>{conteudo}</div>;
  }
  return (
    <Link
      to={to}
      title={hint || `Abrir ${label.toLowerCase()}`}
      aria-label={`${label}: ${value}, abrir`}
      className={`group block ${base} transition-colors hover:border-blue-500/50 hover:bg-slate-900 focus:outline-none focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/40`}
    >
      {conteudo}
    </Link>
  );
};

/** Agrupa indicadores sob um título curto. */
export const IndicadorGrupo: React.FC<{ titulo: string; colunas?: string; children: React.ReactNode }> = ({
  titulo,
  colunas = 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5',
  children,
}) => (
  <section>
    <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{titulo}</h4>
    <div className={`grid gap-3 ${colunas}`}>{children}</div>
  </section>
);
