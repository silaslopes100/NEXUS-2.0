import React from 'react';
import { Lotacao, rotuloLotacao } from '@/types/professor';

interface Props {
  lotacoes?: Lotacao[] | null;
  /** Quantas mostrar antes do "+N" (sem limite quando omitido). */
  limite?: number;
}

/** Polos/escolas em que o professor atua, em chips compactos. */
export const LotacoesChips: React.FC<Props> = ({ lotacoes, limite }) => {
  const itens = lotacoes ?? [];
  if (itens.length === 0) return <span className="text-slate-500">—</span>;
  const visiveis = limite ? itens.slice(0, limite) : itens;
  const ocultas = itens.length - visiveis.length;
  return (
    <ul className="flex max-w-xs flex-wrap gap-1" title={itens.map(rotuloLotacao).join('\n')}>
      {visiveis.map((lotacao) => (
        <li
          key={lotacao.id}
          className="rounded-md border border-slate-800 bg-slate-950 px-2 py-0.5 text-[10px] text-slate-300"
        >
          {rotuloLotacao(lotacao)}
        </li>
      ))}
      {ocultas > 0 && (
        <li className="rounded-md border border-slate-800 bg-slate-950 px-2 py-0.5 text-[10px] text-nexus-yellow">
          +{ocultas}
        </li>
      )}
    </ul>
  );
};
