import React, { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';

interface Props {
  titulo: string;
  onFechar: () => void;
  children: React.ReactNode;
  /** Seletor do item a centralizar ao abrir (ex.: a aula atual). */
  focarSeletor?: string;
}

/**
 * Painel que sobe da borda inferior (celular): alça para arrastar para baixo e fechar, trava a rolagem
 * do fundo, fecha com Esc ou tocando fora, e respeita a área segura da barra de gestos.
 */
export const BottomSheet: React.FC<Props> = ({ titulo, onFechar, children, focarSeletor }) => {
  const painel = useRef<HTMLDivElement>(null);
  const inicio = useRef<number | null>(null);
  const [arraste, setArraste] = useState(0);

  useEffect(() => {
    const anterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const aoTeclar = (e: KeyboardEvent) => { if (e.key === 'Escape') onFechar(); };
    window.addEventListener('keydown', aoTeclar);
    if (focarSeletor) {
      window.setTimeout(() => painel.current?.querySelector(focarSeletor)?.scrollIntoView({ block: 'center' }), 60);
    }
    return () => {
      document.body.style.overflow = anterior;
      window.removeEventListener('keydown', aoTeclar);
    };
  }, [onFechar, focarSeletor]);

  const soltar = () => {
    if (arraste > 110) onFechar();
    setArraste(0);
    inicio.current = null;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/60 lg:hidden" onClick={onFechar}>
      <div
        ref={painel}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        onClick={(e) => e.stopPropagation()}
        style={{ transform: arraste ? `translateY(${arraste}px)` : undefined }}
        className={`flex max-h-[85vh] max-h-[85dvh] w-full flex-col rounded-t-3xl border-t border-slate-700 bg-slate-950 pb-safe shadow-2xl ${
          arraste ? '' : 'transition-transform duration-200'}`}
      >
        <div
          className="shrink-0 cursor-grab touch-none px-4 pb-2 pt-3"
          onTouchStart={(e) => { inicio.current = e.touches[0].clientY; }}
          onTouchMove={(e) => { if (inicio.current !== null) setArraste(Math.max(0, e.touches[0].clientY - inicio.current)); }}
          onTouchEnd={soltar}
        >
          <span className="mx-auto mb-3 block h-1.5 w-12 rounded-full bg-slate-700" aria-hidden="true" />
          <div className="flex items-center justify-between">
            <p className="font-bold text-white">{titulo}</p>
            <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800"><X size={18} /></button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-4">{children}</div>
      </div>
    </div>
  );
};
