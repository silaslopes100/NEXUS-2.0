import React from 'react';
import { Check, CheckCheck, Download, FileText } from 'lucide-react';
import { Mensagem, urlAnexo } from '../api';
import { tamanhoLegivel } from '../utils';

interface Props {
  mensagem: Mensagem;
  minha: boolean;
  mostrarRemetente: boolean;
  /** Para mensagens minhas: undefined = não mostrar; true/false = lida/entregue. */
  lida?: boolean;
}

const AnexoPreview: React.FC<{ m: Mensagem }> = ({ m }) => {
  const url = urlAnexo(m.anexo_url);
  const mime = m.anexo_mime ?? '';
  if (mime.startsWith('image/')) {
    return (
      <a href={url} target="_blank" rel="noreferrer" className="block">
        <img src={url} alt={m.anexo_nome ?? 'Imagem'} loading="lazy"
          className="max-h-72 w-auto max-w-full rounded-lg object-contain" />
      </a>
    );
  }
  if (mime.startsWith('video/')) {
    return <video src={url} controls preload="metadata" className="max-h-80 w-full max-w-sm rounded-lg bg-black" />;
  }
  if (mime.startsWith('audio/')) {
    return <audio src={url} controls preload="metadata" className="w-64 max-w-full" />;
  }
  return (
    <a href={url} target="_blank" rel="noreferrer" download={m.anexo_nome ?? undefined}
      className="flex items-center gap-3 rounded-lg border border-white/10 bg-black/20 px-3 py-2 hover:bg-black/30">
      <FileText size={22} className="shrink-0" />
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium">{m.anexo_nome}</span>
        <span className="text-[11px] opacity-70">{tamanhoLegivel(m.anexo_tamanho)}</span>
      </span>
      <Download size={16} className="shrink-0 opacity-70" />
    </a>
  );
};

export const MensagemItem: React.FC<Props> = ({ mensagem: m, minha, mostrarRemetente, lida }) => {
  if (m.tipo === 'sistema') {
    return (
      <div className="my-2 flex justify-center">
        <span className="rounded-full bg-slate-800/70 px-3 py-1 text-[11px] text-slate-400">{m.texto}</span>
      </div>
    );
  }
  const hora = new Date(m.criado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return (
    <div className={`flex ${minha ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-3 py-2 shadow-sm sm:max-w-[70%] ${minha
        ? 'rounded-br-md bg-nexus-yellow/90 text-slate-950'
        : 'rounded-bl-md bg-slate-800 text-slate-100'}`}>
        {mostrarRemetente && !minha && (
          <p className="mb-0.5 text-xs font-semibold text-blue-300">{m.remetente_nome || 'Usuário'}</p>
        )}
        {m.tipo === 'anexo' && <div className="mb-1"><AnexoPreview m={m} /></div>}
        {m.texto && <p className="whitespace-pre-wrap break-words text-sm">{m.texto}</p>}
        <p className={`mt-0.5 flex items-center justify-end gap-1 text-[10px] ${minha ? 'text-slate-800/70' : 'text-slate-400'}`}>
          {hora}
          {minha && lida !== undefined && (lida
            ? <CheckCheck size={13} className="text-blue-700" aria-label="Lida" />
            : <Check size={13} aria-label="Enviada" />)}
        </p>
      </div>
    </div>
  );
};
