import React from 'react';
import { BellRing, CheckCircle2, X } from 'lucide-react';
import { LarguraAviso, Midia } from '../api';
import { ConteudoHtml } from './ConteudoHtml';
import { GaleriaMidias } from './GaleriaMidias';

export const LARGURAS: Record<LarguraAviso, { classe: string; rotulo: string }> = {
  pequena: { classe: 'max-w-md', rotulo: 'Pequena' },
  media: { classe: 'max-w-2xl', rotulo: 'Média' },
  grande: { classe: 'max-w-4xl', rotulo: 'Grande' },
};

interface ConteudoProps {
  titulo: string;
  conteudoHtml: string;
  midias: Midia[];
  corDestaque?: string | null;
  exigeConfirmacao: boolean;
  onFechar?: () => void;
  onConfirmar?: () => void;
  onAdiar?: () => void;
  ocupado?: boolean;
  /** Texto do rodapé (ex.: "1 de 3"). */
  contador?: string;
}

/** Corpo do pop-up de aviso (usado no aviso real e na pré-visualização do cadastro). */
export const AvisoConteudo: React.FC<ConteudoProps> = ({
  titulo,
  conteudoHtml,
  midias,
  corDestaque,
  exigeConfirmacao,
  onFechar,
  onConfirmar,
  onAdiar,
  ocupado,
  contador,
}) => {
  const cor = corDestaque || '#FFB800';
  return (
    <div className="flex max-h-[calc(100dvh-1.5rem)] flex-col overflow-hidden rounded-2xl sm:max-h-[88dvh] border border-slate-700 bg-slate-900 shadow-2xl">
      <div className="h-1.5 w-full shrink-0" style={{ background: cor }} />
      <div className="flex shrink-0 items-start gap-3 border-b border-slate-800 px-4 py-3 sm:px-5 sm:py-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" style={{ background: `${cor}26`, color: cor }}>
          <BellRing size={18} />
        </span>
        <h2 className="min-w-0 flex-1 break-words pt-1 text-base font-bold text-white sm:text-lg">{titulo || 'Título do aviso'}</h2>
        {!exigeConfirmacao && onFechar && (
          <button type="button" onClick={onFechar} aria-label="Fechar aviso" className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        )}
      </div>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-4 py-4 sm:px-5">
        <ConteudoHtml html={conteudoHtml} className="text-[15px]" />
        <GaleriaMidias midias={midias} />
      </div>
      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-slate-800 px-4 py-3 sm:px-5">
        {contador && <span className="mr-auto text-xs text-slate-500">{contador}</span>}
        {exigeConfirmacao ? (
          <>
            {onAdiar && (
              <button type="button" onClick={onAdiar} className="rounded-xl px-4 py-2 text-sm text-slate-300 hover:bg-slate-800">
                Ver depois
              </button>
            )}
            <button type="button" onClick={onConfirmar} disabled={ocupado}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold text-ink disabled:opacity-60 sm:flex-none"
              style={{ background: cor }}>
              <CheckCircle2 size={16} /> Li e estou ciente
            </button>
          </>
        ) : (
          <button type="button" onClick={onFechar} className="flex-1 rounded-xl px-5 py-2.5 text-sm font-bold text-ink sm:flex-none" style={{ background: cor }}>
            Entendi
          </button>
        )}
      </div>
    </div>
  );
};
