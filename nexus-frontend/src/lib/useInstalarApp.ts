import { useCallback, useEffect, useState } from 'react';

/** Evento de instalação do Chrome/Edge/Samsung Internet (não tipado no DOM padrão). */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

// O navegador dispara o evento uma vez, cedo (às vezes antes da tela de login montar): guarda no módulo.
let promptGuardado: BeforeInstallPromptEvent | null = null;
const ouvintes = new Set<() => void>();
const avisar = () => ouvintes.forEach((f) => f());

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault(); // nós mostramos o botão "Instalar app"
    promptGuardado = e as BeforeInstallPromptEvent;
    avisar();
  });
  window.addEventListener('appinstalled', () => {
    promptGuardado = null;
    avisar();
  });
}

const emModoApp = () =>
  typeof window !== 'undefined' &&
  (window.matchMedia?.('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true);

const ehIos = () =>
  typeof navigator !== 'undefined' &&
  (/iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1));

/**
 * Instalação do NEXUS como app (PWA).
 * - Android/Chrome: `podeInstalar` + `instalar()` abre o diálogo nativo.
 * - iPhone/iPad (Safari): não há diálogo; `ios` = mostrar o passo a passo (Compartilhar → Tela de Início).
 * - Já instalado (aberto como app): `instalado` = true e nada aparece.
 */
export const useInstalarApp = () => {
  const [, forcar] = useState(0);
  useEffect(() => {
    const f = () => forcar((n) => n + 1);
    ouvintes.add(f);
    return () => { ouvintes.delete(f); };
  }, []);

  const instalar = useCallback(async (): Promise<boolean> => {
    if (!promptGuardado) return false;
    const evento = promptGuardado;
    await evento.prompt();
    const { outcome } = await evento.userChoice;
    promptGuardado = null;
    avisar();
    return outcome === 'accepted';
  }, []);

  const instalado = emModoApp();
  return {
    instalado,
    podeInstalar: !instalado && !!promptGuardado,
    ios: !instalado && ehIos(),
    instalar,
  };
};
