import React, { useState } from 'react';

interface UsuarioAvatarProps {
  fotoUrl?: string | null;
  nome: string;
  className: string;
}

function getFotoUrlValida(fotoUrl?: string | null): string | null {
  if (!fotoUrl) return null;

  try {
    const url = new URL(fotoUrl);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}

export const UsuarioAvatar: React.FC<UsuarioAvatarProps> = ({ fotoUrl, nome, className }) => {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const url = getFotoUrlValida(fotoUrl);

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
