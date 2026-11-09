import React, { useEffect, useState } from 'react';
import { adminApi } from '@/features/admin/api';

interface UsuarioAvatarProps {
  fotoUrl?: string | null;
  usuarioId?: string;
  nome: string;
  className: string;
}

const FOTO_FILENAME = /^[a-f0-9]{32}\.(?:jpg|png|webp)$/;

function getFotoUrlValida(fotoUrl?: string | null): string | null {
  if (!fotoUrl) return null;

  try {
    const url = new URL(fotoUrl);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}

export const UsuarioAvatar: React.FC<UsuarioAvatarProps> = ({
  fotoUrl,
  usuarioId,
  nome,
  className,
}) => {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const [fotoAutenticada, setFotoAutenticada] = useState<{
    key: string;
    url: string;
  } | null>(null);
  const fotoLocal = Boolean(fotoUrl && FOTO_FILENAME.test(fotoUrl));

  useEffect(() => {
    if (!usuarioId || !fotoUrl || !FOTO_FILENAME.test(fotoUrl)) {
      setFotoAutenticada(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    void adminApi.getUsuarioFoto(usuarioId).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      if (cancelled) {
        URL.revokeObjectURL(objectUrl);
      } else {
        setFotoAutenticada({ key: `${usuarioId}:${fotoUrl}`, url: objectUrl });
      }
    }).catch(() => {
      if (!cancelled) setFotoAutenticada(null);
    });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [usuarioId, fotoUrl]);

  const fotoKey = `${usuarioId}:${fotoUrl}`;
  const url = fotoLocal
    ? (fotoAutenticada?.key === fotoKey ? fotoAutenticada.url : null)
    : getFotoUrlValida(fotoUrl);

  if (url && failedUrl !== url) {
    return (
      <img
        src={url}
        alt={nome}
        loading="lazy"
        className={className}
        onError={() => setFailedUrl(url)}
      />
    );
  }

  return (
    <div
      aria-label={nome}
      className={`${className} flex items-center justify-center bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue font-bold text-white`}
    >
      {nome.trim().charAt(0).toUpperCase()}
    </div>
  );
};
