import React from 'react';
import { Users } from 'lucide-react';
import { UserAvatar } from '@/components/avatar/UserAvatar';
import { iniciais } from '../utils';

interface Props {
  nome?: string | null;
  usuarioId?: string | null;
  fotoUrl?: string | null;
  grupo?: boolean;
  tamanho?: 'sm' | 'md';
}

export const Avatar: React.FC<Props> = ({ nome, usuarioId, fotoUrl, grupo, tamanho = 'md' }) => {
  const cls = tamanho === 'sm' ? 'h-8 w-8 text-[11px]' : 'h-10 w-10 text-xs';
  if (grupo) {
    return (
      <span className={`${cls} flex shrink-0 items-center justify-center rounded-full bg-blue-500/15 text-blue-300`}>
        <Users size={tamanho === 'sm' ? 14 : 18} />
      </span>
    );
  }
  return (
    <UserAvatar
      usuarioId={usuarioId}
      fotoUrl={fotoUrl}
      nome={nome}
      className={`${cls} shrink-0 rounded-full`}
      fallbackClassName="bg-nexus-yellow/15 font-semibold text-nexus-yellow"
      fallbackTexto={iniciais(nome)}
    />
  );
};
