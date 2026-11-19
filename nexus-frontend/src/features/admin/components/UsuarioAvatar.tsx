import React from 'react';
import { UserAvatar } from '@/components/avatar/UserAvatar';

interface UsuarioAvatarProps {
  fotoUrl?: string | null;
  usuarioId?: string;
  nome: string;
  className: string;
}

/** Avatar usado em Usuários e na Ficha; a lógica de foto fica em UserAvatar. */
export const UsuarioAvatar: React.FC<UsuarioAvatarProps> = ({ fotoUrl, usuarioId, nome, className }) => (
  <UserAvatar usuarioId={usuarioId} fotoUrl={fotoUrl} nome={nome} className={className} />
);
