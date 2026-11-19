import React from 'react';

/**
 * Fundo fixo com manchas de luz desfocadas, para o vidro (.glass) dos cards e da
 * barra lateral ter o que refratar. Puramente decorativo.
 * As cores vêm dos tokens do tema (blue-300 e amber-200 se espelham no modo claro).
 */
export const AppBackdrop: React.FC = () => (
  <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
    <div className="absolute -top-32 -left-24 h-[28rem] w-[28rem] rounded-full bg-nexus-blue/25 blur-3xl" />
    <div className="absolute top-1/3 right-[-8rem] h-[32rem] w-[32rem] rounded-full bg-blue-800/30 blur-3xl" />
    <div className="absolute bottom-[-10rem] left-1/3 h-[26rem] w-[26rem] rounded-full bg-nexus-yellow/10 blur-3xl" />
    <div className="absolute top-2/3 left-[-6rem] h-[20rem] w-[20rem] rounded-full bg-indigo-500/15 blur-3xl" />
  </div>
);
