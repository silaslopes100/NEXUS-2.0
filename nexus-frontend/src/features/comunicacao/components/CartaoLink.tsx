import React, { useState } from 'react';
import { ExternalLink, Play, X } from 'lucide-react';
import { LinkPreview } from '../api';

const dominio = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
};

export const urlEmbed = (tipo?: string | null, id?: string | null) =>
  tipo === 'youtube'
    ? `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`
    : tipo === 'vimeo'
      ? `https://player.vimeo.com/video/${id}?autoplay=1`
      : '';

/** Vídeo do YouTube/Vimeo: miniatura e o player só carrega ao clicar. */
export const VideoEmbed: React.FC<{ tipo: string; id: string; miniatura?: string | null; titulo?: string | null }> = ({
  tipo,
  id,
  miniatura,
  titulo,
}) => {
  const [tocar, setTocar] = useState(false);
  const thumb = miniatura || (tipo === 'youtube' ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : null);
  if (tocar) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          src={urlEmbed(tipo, id)}
          title={titulo || 'Vídeo'}
          className="absolute inset-0 h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
        />
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={() => setTocar(true)}
      className="group relative block aspect-video w-full overflow-hidden rounded-xl bg-slate-950"
      aria-label={`Reproduzir ${titulo || 'vídeo'}`}
    >
      {thumb && <img src={thumb} alt="" loading="lazy" className="h-full w-full object-cover" />}
      <span className="absolute inset-0 flex items-center justify-center bg-black/25 transition-colors group-hover:bg-black/40">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-red-600 text-white shadow-lg">
          <Play size={26} className="ml-1" fill="currentColor" />
        </span>
      </span>
    </button>
  );
};

interface Props {
  link: LinkPreview;
  onRemover?: () => void;
  carregando?: boolean;
}

/** Cartão de link externo com miniatura (estilo LinkedIn); vídeos viram player. */
export const CartaoLink: React.FC<Props> = ({ link, onRemover, carregando }) => {
  const remover = onRemover && (
    <button
      type="button"
      onClick={onRemover}
      aria-label="Remover link"
      className="absolute right-2 top-2 z-10 rounded-full bg-black/70 p-1 text-white hover:bg-black"
    >
      <X size={14} />
    </button>
  );

  if (link.embed_tipo && link.embed_id) {
    return (
      <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
        {remover}
        <VideoEmbed tipo={link.embed_tipo} id={link.embed_id} miniatura={link.imagem_url} titulo={link.titulo} />
        {(link.titulo || link.site_nome) && (
          <a href={link.url} target="_blank" rel="noopener noreferrer nofollow" className="block px-3 py-2 hover:bg-slate-900">
            <p className="text-[11px] uppercase tracking-wide text-slate-500">{link.site_nome}</p>
            {link.titulo && <p className="line-clamp-2 text-sm font-semibold text-slate-100">{link.titulo}</p>}
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
      {remover}
      <a href={link.url} target="_blank" rel="noopener noreferrer nofollow" className="block hover:bg-slate-900/70">
        {link.imagem_url && (
          <div className="aspect-[1.91/1] w-full overflow-hidden bg-slate-900">
            <img
              src={link.imagem_url}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              className="h-full w-full object-cover"
              onError={(e) => ((e.currentTarget.parentElement as HTMLElement).style.display = 'none')}
            />
          </div>
        )}
        <div className="px-3 py-2.5">
          <p className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-slate-500">
            {link.site_nome || dominio(link.url)} <ExternalLink size={11} />
          </p>
          <p className="line-clamp-2 text-sm font-semibold text-slate-100">
            {carregando ? 'Carregando prévia…' : link.titulo || link.url}
          </p>
          {link.descricao && <p className="mt-0.5 line-clamp-2 text-xs text-slate-400">{link.descricao}</p>}
        </div>
      </a>
    </div>
  );
};
