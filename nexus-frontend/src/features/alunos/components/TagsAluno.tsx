import React from 'react';
import { Observacao } from '@/features/alunos/api';

export const observacaoInfo: Record<Observacao, { label: string; className: string }> = {
  formado: { label: 'Formado', className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' },
  churn: { label: 'Churn', className: 'border-red-500/30 bg-red-500/10 text-red-200' },
  transferido: { label: 'Transferido', className: 'border-blue-500/30 bg-blue-500/10 text-blue-200' },
  revalidado: { label: 'Revalidado', className: 'border-purple-500/30 bg-purple-500/10 text-purple-200' },
  sem_movimentacao: {
    label: 'Sem movimentação +1 ano',
    className: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  },
};

export const TagsAluno: React.FC<{ observacoes: Observacao[] }> = ({ observacoes }) => {
  if (observacoes.length === 0) return <span className="text-slate-500">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {observacoes.map((observacao) => (
        <span
          key={observacao}
          className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold ${observacaoInfo[observacao].className}`}
        >
          {observacaoInfo[observacao].label}
        </span>
      ))}
    </div>
  );
};
