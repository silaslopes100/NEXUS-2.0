import { useEffect, useRef } from 'react';

/**
 * Executa `fn` imediatamente e a cada `ms`, pausando com a aba oculta e
 * disparando de novo assim que ela volta a ficar visível (polling do chat).
 */
export function useIntervalo(fn: () => void, ms: number, ativo = true) {
  const ref = useRef(fn);
  ref.current = fn;

  useEffect(() => {
    if (!ativo) return undefined;
    const tick = () => {
      if (!document.hidden) ref.current();
    };
    tick();
    const id = window.setInterval(tick, ms);
    const aoVoltar = () => {
      if (!document.hidden) ref.current();
    };
    document.addEventListener('visibilitychange', aoVoltar);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', aoVoltar);
    };
  }, [ms, ativo]);
}
