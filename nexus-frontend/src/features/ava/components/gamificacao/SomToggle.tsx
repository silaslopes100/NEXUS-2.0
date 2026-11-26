import React from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import { useSons } from '../../utils/sons';

/** Liga/desliga os efeitos sonoros da gamificação (a escolha fica salva no aparelho). */
export const SomToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { ligado, alternar } = useSons();
  return (
    <button type="button" onClick={alternar} aria-pressed={ligado}
      aria-label={ligado ? 'Desligar sons' : 'Ligar sons'} title={ligado ? 'Sons ligados' : 'Sons desligados'}
      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border transition ${
        ligado ? 'border-nexus-yellow/40 bg-nexus-yellow/10 text-nexus-yellow' : 'border-slate-700 text-slate-500 hover:text-slate-300'} ${className}`}>
      {ligado ? <Volume2 size={18} /> : <VolumeX size={18} />}
    </button>
  );
};
