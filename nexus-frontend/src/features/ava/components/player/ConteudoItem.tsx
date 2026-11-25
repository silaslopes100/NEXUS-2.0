import React, { useState } from 'react';
import { Download, ExternalLink, FileText, Link2, X } from 'lucide-react';
import { urlArquivo } from '@/lib/uploadDireto';
import { tamanhoLegivel } from '@/features/chat/utils';
import { ConteudoHtml } from '@/features/comunicacao/components/ConteudoHtml';
import { ItemAula } from '../../api';

const OFFICE = /\.(docx?|pptx?|xlsx?)$/i;

const extensao = (item: ItemAula) => (item.arquivo_nome || item.url || '').split('.').pop()?.toUpperCase() || 'ARQ';

/** Documentos do Office só abrem no visualizador online quando o arquivo é público (https). */
const urlVisualizador = (item: ItemAula) => {
  const url = urlArquivo(item.url);
  if (item.arquivo_mime === 'application/pdf') return url;
  if (OFFICE.test(item.arquivo_nome || '') && url.startsWith('https://')) {
    return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(url)}`;
  }
  return null;
};

export const BotaoDownload: React.FC<{ item: ItemAula; compacto?: boolean }> = ({ item, compacto }) =>
  item.permite_download ? (
    <a href={urlArquivo(item.url)} target="_blank" rel="noopener noreferrer" download={item.arquivo_nome || undefined}
      className={`inline-flex items-center gap-1.5 rounded-xl border border-slate-700 font-semibold text-slate-200 hover:border-nexus-yellow/60 hover:text-white ${compacto ? 'p-2' : 'px-3 py-2 text-xs'}`}
      aria-label={`Baixar ${item.arquivo_nome || 'arquivo'}`}>
      <Download size={14} /> {!compacto && 'Baixar'}
    </a>
  ) : null;

/** Um item de conteúdo (exceto vídeo, que tem player próprio). */
export const ConteudoItem: React.FC<{ item: ItemAula }> = ({ item }) => {
  const [ampliada, setAmpliada] = useState(false);

  if (item.tipo === 'texto') {
    return (
      <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-6">
        {item.titulo && <h3 className="mb-3 text-lg font-bold text-white">{item.titulo}</h3>}
        <ConteudoHtml html={item.conteudo_html || ''} className="text-slate-200" />
      </article>
    );
  }

  if (item.tipo === 'imagem') {
    return (
      <figure className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
        <button type="button" onClick={() => setAmpliada(true)} className="block w-full" aria-label="Ampliar imagem">
          <img src={urlArquivo(item.url)} alt={item.titulo || ''} className="max-h-[70vh] w-full object-contain" loading="lazy" />
        </button>
        {item.titulo && <figcaption className="px-4 py-2 text-xs text-slate-400">{item.titulo}</figcaption>}
        {ampliada && (
          <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/90 p-4" onClick={() => setAmpliada(false)}>
            <button type="button" aria-label="Fechar" className="absolute right-4 top-4 rounded-full bg-slate-800 p-2 text-white"><X size={18} /></button>
            <img src={urlArquivo(item.url)} alt={item.titulo || ''} className="max-h-full max-w-full object-contain" />
          </div>
        )}
      </figure>
    );
  }

  if (item.tipo === 'link') {
    let host = '';
    try {
      host = new URL(item.url || '').hostname.replace(/^www\./, '');
    } catch {
      host = item.url || '';
    }
    return (
      <a href={item.url || '#'} target="_blank" rel="noopener noreferrer"
        className="group flex items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 hover:border-nexus-yellow/60">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300"><Link2 size={20} /></span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold text-white">{item.titulo || host}</span>
          <span className="block truncate text-xs text-slate-500">{host}</span>
        </span>
        <ExternalLink size={16} className="text-slate-500 group-hover:text-nexus-yellow" />
      </a>
    );
  }

  // arquivo
  const visualizador = urlVisualizador(item);
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
      <div className="flex items-center gap-3 p-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-nexus-yellow/15 text-[10px] font-black text-nexus-yellow">
          {extensao(item)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold text-white">{item.titulo || item.arquivo_nome}</span>
          <span className="block truncate text-xs text-slate-500">
            {item.arquivo_nome}{item.arquivo_tamanho ? ` · ${tamanhoLegivel(item.arquivo_tamanho)}` : ''}
          </span>
        </span>
        <BotaoDownload item={item} />
      </div>
      {visualizador ? (
        <iframe src={visualizador} title={item.titulo || item.arquivo_nome || 'Documento'} className="h-[70vh] w-full border-t border-slate-800 bg-white" />
      ) : (
        <div className="flex items-center gap-2 border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
          <FileText size={14} />
          {item.permite_download ? 'Baixe o arquivo para abrir.' : 'A visualização deste arquivo não está disponível no navegador.'}
        </div>
      )}
    </div>
  );
};
