import React, { useEffect, useState } from 'react';
import { authApi } from '@/features/auth/api';

/** Nome do arquivo gravado em usuarios.foto_url pelo upload de foto (servido pela API autenticada). */
const FOTO_FILENAME = /^[a-f0-9]{32}\.(?:jpg|png|webp)$/;

// Uma busca por usuário/foto durante a sessão: listas e chat reaproveitam a mesma imagem.
const cache = new Map<string, Promise<string | null>>();

function urlExterna(fotoUrl: string): string | null {
  try {
    const url = new URL(fotoUrl);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}

function carregarFoto(usuarioId: string, fotoUrl: string): Promise<string | null> {
  const chave = `${usuarioId}:${fotoUrl}`;
  let promessa = cache.get(chave);
  if (!promessa) {
    promessa = authApi
      .getUsuarioFoto(usuarioId)
      .then((blob) => URL.createObjectURL(blob))
      .catch(() => {
        cache.delete(chave); // permite tentar de novo numa próxima montagem
        return null;
      });
    cache.set(chave, promessa);
  }
  return promessa;
}

interface UserAvatarProps {
  usuarioId?: string | null;
  fotoUrl?: string | null;
  nome?: string | null;
  /** Tamanho, forma e tipografia (aplicado na foto e no padrão). */
  className: string;
  /** Visual do padrão sem foto. */
  fallbackClassName?: string;
  /** Texto do padrão sem foto (padrão: inicial do nome). */
  fallbackTexto?: string;
}

/**
 * Avatar de qualquer usuário: mostra a foto de perfil quando existe e, sem foto,
 * o padrão com a inicial. Usuário sem foto não gera requisição.
 */
export const UserAvatar: React.FC<UserAvatarProps> = ({
  usuarioId,
  fotoUrl,
  nome,
  className,
  fallbackClassName = 'bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue font-bold text-on-accent',
  fallbackTexto,
}) => {
  const nomeExibido = nome?.trim() || 'Usuário';
  const externa = fotoUrl ? urlExterna(fotoUrl) : null;
  const local = Boolean(usuarioId && fotoUrl && FOTO_FILENAME.test(fotoUrl));
  const chave = `${usuarioId}:${fotoUrl}`;

  const [carregada, setCarregada] = useState<{ chave: string; url: string | null } | null>(null);
  const [falhou, setFalhou] = useState<string | null>(null);

  useEffect(() => {
    if (!local || !usuarioId || !fotoUrl) return;
    let ativo = true;
    void carregarFoto(usuarioId, fotoUrl).then((url) => {
      if (ativo) setCarregada({ chave: `${usuarioId}:${fotoUrl}`, url });
    });
    return () => {
      ativo = false;
    };
  }, [local, usuarioId, fotoUrl]);

  const url = externa ?? (local && carregada?.chave === chave ? carregada.url : null);

  if (url && falhou !== url) {
    return (
      <img
        src={url}
        alt={nomeExibido}
        loading="lazy"
        className={`${className} object-cover`}
        onError={() => setFalhou(url)}
      />
    );
  }

  return (
    <span aria-label={nomeExibido} className={`${className} flex items-center justify-center ${fallbackClassName}`}>
      {fallbackTexto ?? nomeExibido.charAt(0).toUpperCase()}
    </span>
  );
};
