import React, { useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import { tocar } from '../../utils/sons';
import { Recompensa } from '../../alunoApi';
import { AnelNivel, ConquistaBadge } from './Gamificacao';

interface Props {
  recompensa: Recompensa;
  onFechar: () => void;
}

/** Modal para conquista nova ou subida de nível (o XP comum aparece só como aviso). */
export const CelebracaoRecompensa: React.FC<Props> = ({ recompensa: r, onFechar }) => {
  // Fanfarra ao abrir: subida de nível tem a própria; conquista nova, a de conquista.
  useEffect(() => {
    const t = window.setTimeout(() => tocar(r.subiu_nivel ? 'nivel' : 'conquista'), 150);
    return () => window.clearTimeout(t);
  }, [r]);

  return (
  <div className="fixed inset-0 z-[75] flex items-center justify-center bg-black/70 p-4 overflow-y-auto" onClick={onFechar}>
    <div role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}
      className="my-auto w-full max-w-md rounded-3xl border border-nexus-yellow/40 bg-gradient-to-b from-slate-900 to-slate-950 p-7 text-center shadow-nexus-glow">
      <p className="mb-4 flex items-center justify-center gap-2 text-sm font-bold uppercase tracking-wide text-nexus-yellow">
        <Sparkles size={16} /> {r.subiu_nivel ? 'Você subiu de nível!' : r.conquistas.length > 1 ? 'Novas conquistas!' : 'Nova conquista!'}
      </p>
      {r.subiu_nivel && r.nivel && (
        <div className="mb-5 flex flex-col items-center gap-2">
          <AnelNivel nivel={r.nivel} tamanho={96} />
          <p className="text-2xl font-extrabold text-white">{r.nivel.nome}</p>
        </div>
      )}
      {r.conquistas.length > 0 && (
        <div className="mb-5 flex flex-wrap justify-center gap-5">
          {r.conquistas.map((c) => <div key={c.codigo} className="w-[44%] max-w-[8rem]"><ConquistaBadge conquista={c} tamanho="lg" /></div>)}
        </div>
      )}
      <p className="text-sm text-slate-300">
        Você ganhou <strong className="text-nexus-yellow">+{r.xp_ganho} XP</strong> agora.
      </p>
      <button type="button" onClick={onFechar} autoFocus
        className="mt-6 w-full rounded-xl bg-nexus-yellow px-5 py-3 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
        Continuar estudando
      </button>
    </div>
  </div>
  );
};
