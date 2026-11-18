import React from 'react';
import { Users } from 'lucide-react';
import { iniciais } from '../utils';

interface Props {
  nome?: string | null;
  fotoUrl?: string | null;
  grupo?: boolean;
  tamanho?: 'sm' | 'md';
}

export const Avatar: React.FC<Props> = ({ nome, fotoUrl, grupo, tamanho = 'md' }) => {
  const cls = tamanho === 'sm' ? 'h-8 w-8 text-[11px]' : 'h-10 w-10 text-xs';
  if (grupo) {
    return (
      <span className={`${cls} flex shrink-0 items-center justify-center rounded-full bg-blue-500/15 text-blue-300`}>
        <Users size={tamanho === 'sm' ? 14 : 18} />
      </span>
    );
  }
  if (fotoUrl) {
    return <img src={fotoUrl} alt="" className={`${cls} shrink-0 rounded-full object-cover`} />;
  }
  return (
    <span className={`${cls} flex shrink-0 items-center justify-center rounded-full bg-nexus-yellow/15 font-semibold text-nexus-yellow`}>
      {iniciais(nome)}
    </span>
  );
};
