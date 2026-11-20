import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, FileText, X } from 'lucide-react';
import { urlArquivo } from '@/lib/uploadDireto';
import { tamanhoLegivel } from '@/features/chat/utils';
import { Midia } from '../api';
import { VideoEmbed } from './CartaoLink';

const Lightbox: React.FC<{ imagens: Midia[]; inicial: number; onFechar: () => void }> = ({
  imagens,
  inicial,
  onFechar,
}) => {
  const [i, setI] = useState(inicial);
  const total = imagens.length;
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onFechar();
      if (e.key === 'ArrowRight') setI((v) => (v + 1) % total);
      if (e.key === 'ArrowLeft') setI((v) => (v - 1 + total) % total);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [total, onFechar]);
  const atual = imagens[i];
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/90 p-4" onClick={onFechar}>
      <button type="button" aria-label="Fechar" className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
        <X size={20} />
      </button>
      {total > 1 && (
        <>
          <button type="button" aria-label="Anterior" onClick={(e) => { e.stopPropagation(); setI((v) => (v - 1 + total) % total); }}
            className="absolute left-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
            <ChevronLeft size={22} />
          </button>
          <button type="button" aria-label="Próxima" onClick={(e) => { e.stopPropagation(); setI((v) => (v + 1) % total); }}
            className="absolute right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
            <ChevronRight size={22} />
          </button>
        </>
      )}
      <img src={urlArquivo(atual.url)} alt={atual.nome ?? ''} onClick={(e) => e.stopPropagation()}
        className="max-h-[88vh] max-w-full rounded-lg object-contain" />
      {total > 1 && <p className="absolute bottom-4 text-xs text-white/70">{i + 1} / {total}</p>}
    </div>
  );
};

export const ChipArquivo: React.FC<{ m: Midia }> = ({ m }) => (
  <a href={urlArquivo(m.url)} target="_blank" rel="noreferrer" download={m.nome ?? undefined}
    className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2.5 hover:bg-slate-900">
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300">
      <FileText size={18} />
    </span>
    <span className="min-w-0 flex-1">
      <span className="block truncate text-sm font-medium text-slate-100">{m.nome}</span>
      <span className="text-[11px] text-slate-500">{tamanhoLegivel(m.tamanho)}</span>
    </span>
    <Download size={16} className="shrink-0 text-slate-400" />
  </a>
);

/** Mídias de um post/aviso: grade de imagens (com lightbox), vídeos, vídeos externos e arquivos. */
export const GaleriaMidias: React.FC<{ midias: Midia[] }> = ({ midias }) => {
  const [aberta, setAberta] = useState<number | null>(null);
  const imagens = midias.filter((m) => m.tipo === 'imagem');
  const videos = midias.filter((m) => m.tipo === 'video');
  const externos = midias.filter((m) => m.tipo === 'video_link' && m.embed_tipo && m.embed_id);
  const arquivos = midias.filter((m) => m.tipo === 'arquivo');
  if (!midias.length) return null;

  const visiveis = imagens.slice(0, 4);
  const extra = imagens.length - visiveis.length;
  const grade =
    visiveis.length === 1 ? 'grid-cols-1' : visiveis.length === 2 ? 'grid-cols-2' : 'grid-cols-2 grid-rows-2';

  return (
    <div className="space-y-2">
      {visiveis.length > 0 && (
        <div className={`grid gap-1 overflow-hidden rounded-xl ${grade} ${visiveis.length > 1 ? 'aspect-[4/3]' : ''}`}>
          {visiveis.map((m, idx) => (
            <button
              key={m.id ?? m.url}
              type="button"
              onClick={() => setAberta(idx)}
              className={`relative overflow-hidden bg-slate-950 ${visiveis.length === 3 && idx === 0 ? 'row-span-2' : ''}`}
            >
              <img
                src={urlArquivo(m.url)}
                alt={m.nome ?? ''}
                loading="lazy"
                className={`h-full w-full object-cover ${visiveis.length === 1 ? 'max-h-[520px]' : ''}`}
              />
              {extra > 0 && idx === visiveis.length - 1 && (
                <span className="absolute inset-0 flex items-center justify-center bg-black/60 text-2xl font-bold text-white">
                  +{extra}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
      {videos.map((m) => (
        <video key={m.id ?? m.url} src={urlArquivo(m.url)} controls preload="metadata"
          className="max-h-[520px] w-full rounded-xl bg-black" />
      ))}
      {externos.map((m) => (
        <VideoEmbed key={m.id ?? m.url} tipo={m.embed_tipo!} id={m.embed_id!} />
      ))}
      {arquivos.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {arquivos.map((m) => <ChipArquivo key={m.id ?? m.url} m={m} />)}
        </div>
      )}
      {aberta !== null && <Lightbox imagens={imagens} inicial={aberta} onFechar={() => setAberta(null)} />}
    </div>
  );
};
