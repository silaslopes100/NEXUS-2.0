import React, { useEffect, useState } from 'react';
import { authApi } from '@/features/auth/api';

interface UsuarioAvatarProprioProps {
  usuarioId?: string;
  fotoUrl?: string | null;
  nome?: string | null;
  className: string;
}

export const UsuarioAvatarProprio: React.FC<UsuarioAvatarProprioProps> = ({
  usuarioId,
  fotoUrl,
  nome,
  className,
}) => {
  const [foto, setFoto] = useState<{ key: string; url: string } | null>(null);
  const nomeExibido = nome?.trim() || 'Usuário';
  const inicial = nomeExibido.charAt(0).toUpperCase();

  useEffect(() => {
    if (!usuarioId) {
      setFoto(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    void authApi.getMyPhoto().then((image) => {
      objectUrl = URL.createObjectURL(image);
      if (cancelled) {
        URL.revokeObjectURL(objectUrl);
      } else {
        setFoto({ key: `${usuarioId}:${fotoUrl || ''}`, url: objectUrl });
      }
    }).catch(() => {
      if (!cancelled) setFoto(null);
    });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [usuarioId, fotoUrl]);

  const fotoKey = `${usuarioId}:${fotoUrl || ''}`;
  const fotoUrlAtiva = foto && foto.key === fotoKey ? foto.url : null;

  return (
    <div
      role={fotoUrlAtiva ? 'img' : undefined}
      aria-label={fotoUrlAtiva ? nomeExibido : undefined}
      className={`${className} overflow-hidden`}
    >
      {fotoUrlAtiva ? (
        <img src={fotoUrlAtiva} alt={nomeExibido} className="h-full w-full object-cover" />
      ) : (
        <span aria-hidden="true">{inicial}</span>
      )}
    </div>
  );
};
