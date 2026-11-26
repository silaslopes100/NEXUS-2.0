/**
 * Efeitos sonoros da gamificação do AVA, sintetizados com Web Audio (sem arquivos de áudio).
 * - O AudioContext só nasce depois de um toque/clique (política de autoplay dos navegadores).
 * - Preferência liga/desliga salva no aparelho (localStorage `nexus:sons`), padrão ligado.
 * - Vibração leve nas celebrações (celular), seguindo a mesma preferência.
 */
import { useEffect, useState } from 'react';

export type EventoSom = 'aula' | 'xp' | 'capitulo' | 'conquista' | 'nivel' | 'disciplina' | 'aprovado' | 'podio' | 'clique';

const CHAVE = 'nexus:sons';
const VOLUME = 0.18;

let ctx: AudioContext | null = null;
let ligado = (() => {
  try {
    return localStorage.getItem(CHAVE) !== '0';
  } catch {
    return true;
  }
})();
const ouvintes = new Set<(v: boolean) => void>();

const contexto = (): AudioContext | null => {
  if (typeof window === 'undefined') return null;
  const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  if (!ctx) {
    try {
      ctx = new Ctor();
    } catch {
      return null;
    }
  }
  if (ctx.state === 'suspended') void ctx.resume().catch(() => undefined);
  return ctx;
};

// Destrava o áudio no primeiro toque/clique/tecla da sessão.
if (typeof window !== 'undefined') {
  const destravar = () => {
    if (ligado) contexto();
    window.removeEventListener('pointerdown', destravar);
    window.removeEventListener('keydown', destravar);
  };
  window.addEventListener('pointerdown', destravar, { passive: true });
  window.addEventListener('keydown', destravar);
}

/** Uma nota com envelope (ataque rápido, decaimento exponencial). */
const nota = (c: AudioContext, freq: number, inicio: number, duracao: number,
  tipo: OscillatorType = 'sine', volume = 1, deslizeAte?: number) => {
  const osc = c.createOscillator();
  const ganho = c.createGain();
  osc.type = tipo;
  osc.frequency.setValueAtTime(freq, inicio);
  if (deslizeAte) osc.frequency.exponentialRampToValueAtTime(deslizeAte, inicio + duracao * 0.6);
  ganho.gain.setValueAtTime(0.0001, inicio);
  ganho.gain.exponentialRampToValueAtTime(VOLUME * volume, inicio + 0.012);
  ganho.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
  osc.connect(ganho).connect(c.destination);
  osc.start(inicio);
  osc.stop(inicio + duracao + 0.05);
};

// Frequências (Hz) das notas usadas.
const N = { C5: 523.25, D5: 587.33, E5: 659.25, G5: 783.99, A5: 880, B5: 987.77, C6: 1046.5, E6: 1318.5, G6: 1568, C4: 261.63, E4: 329.63, G4: 392 };

const RECEITAS: Record<EventoSom, (c: AudioContext, t: number) => void> = {
  // "ding" curto e limpo
  aula: (c, t) => { nota(c, N.E5, t, 0.18, 'triangle'); nota(c, N.A5, t + 0.08, 0.35, 'sine', 0.9); },
  // moedinha
  xp: (c, t) => { nota(c, N.B5, t, 0.08, 'square', 0.35); nota(c, N.E6, t + 0.07, 0.25, 'square', 0.35); },
  // arpejo de 3 notas
  capitulo: (c, t) => [N.C5, N.E5, N.G5].forEach((f, i) => nota(c, f, t + i * 0.09, 0.3, 'triangle')),
  // fanfarra curta
  conquista: (c, t) => {
    [N.G5, N.C6, N.E6].forEach((f, i) => nota(c, f, t + i * 0.1, 0.28, 'triangle', 0.8));
    nota(c, N.G6, t + 0.32, 0.6, 'sine', 0.7);
    nota(c, N.C5, t + 0.32, 0.6, 'triangle', 0.4);
  },
  // arpejo ascendente com brilho
  nivel: (c, t) => {
    [N.C5, N.E5, N.G5, N.C6, N.E6].forEach((f, i) => nota(c, f, t + i * 0.075, 0.32, 'triangle', 0.8));
    nota(c, N.G6, t + 0.4, 0.7, 'sine', 0.6, N.C6 * 2);
  },
  // fanfarra mais longa (disciplina concluída)
  disciplina: (c, t) => {
    const frase = [N.C5, N.C5, N.G5, N.E5, N.G5, N.C6];
    const tempos = [0, 0.12, 0.24, 0.42, 0.54, 0.7];
    frase.forEach((f, i) => nota(c, f, t + tempos[i], i === frase.length - 1 ? 0.9 : 0.2, 'triangle', 0.8));
    [N.C4, N.E4, N.G4].forEach((f) => nota(c, f, t + 0.7, 1.0, 'sine', 0.5));
  },
  // acorde maior (aprovação)
  aprovado: (c, t) => { [N.C5, N.E5, N.G5].forEach((f) => nota(c, f, t, 0.7, 'triangle', 0.6)); nota(c, N.C6, t + 0.12, 0.6, 'sine', 0.6); },
  // sino (pódio)
  podio: (c, t) => { nota(c, N.E6, t, 1.2, 'sine', 0.7); nota(c, N.E6 * 2.01, t, 0.6, 'sine', 0.25); nota(c, N.B5, t + 0.15, 1.0, 'sine', 0.4); },
  // toque sutil
  clique: (c, t) => nota(c, 1400, t, 0.05, 'sine', 0.35, 900),
};

const VIBRACAO: Partial<Record<EventoSom, number | number[]>> = {
  capitulo: 30, conquista: [40, 40, 60], nivel: [30, 30, 30, 30, 80], disciplina: [60, 50, 60, 50, 120], aprovado: [40, 40, 80], podio: 50,
};

/** Toca o efeito do evento (se o som estiver ligado). Nunca lança erro. */
export const tocar = (evento: EventoSom) => {
  if (!ligado) return;
  try {
    const c = contexto();
    if (c) RECEITAS[evento](c, c.currentTime + 0.01);
    const v = VIBRACAO[evento];
    if (v && typeof navigator !== 'undefined' && 'vibrate' in navigator) navigator.vibrate(v);
  } catch {
    /* áudio indisponível: segue sem som */
  }
};

export const somLigado = () => ligado;

export const definirSom = (valor: boolean) => {
  ligado = valor;
  try {
    localStorage.setItem(CHAVE, valor ? '1' : '0');
  } catch {
    /* armazenamento indisponível */
  }
  ouvintes.forEach((f) => f(valor));
  if (valor) tocar('clique');
};

/** Estado do som para o botão liga/desliga (sincronizado entre componentes). */
export const useSons = () => {
  const [valor, setValor] = useState(ligado);
  useEffect(() => {
    ouvintes.add(setValor);
    return () => { ouvintes.delete(setValor); };
  }, []);
  return { ligado: valor, alternar: () => definirSom(!valor), tocar };
};
