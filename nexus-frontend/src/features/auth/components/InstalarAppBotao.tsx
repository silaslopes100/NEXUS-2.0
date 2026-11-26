import React, { useState } from 'react';
import { Download, MoreVertical, PlusSquare, Share, Smartphone, X } from 'lucide-react';
import { useInstalarApp } from '@/lib/useInstalarApp';

/** Passo a passo para iPhone/iPad (o Safari não tem diálogo de instalação). */
const PassoAPassoIos: React.FC<{ onFechar: () => void }> = ({ onFechar }) => (
  <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 sm:items-center sm:p-4" onClick={onFechar}>
    <div role="dialog" aria-modal="true" aria-labelledby="instalar-titulo" onClick={(e) => e.stopPropagation()}
      className="max-h-[90dvh] w-full max-w-sm space-y-4 overflow-y-auto rounded-t-3xl border border-slate-700 bg-slate-900 p-6 pb-safe-4 text-left shadow-2xl sm:rounded-3xl">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <img src="/icons/icon-192.png" alt="" className="h-12 w-12 rounded-xl" />
          <div>
            <h2 id="instalar-titulo" className="font-bold text-white">Instalar o NEXUS</h2>
            <p className="text-xs text-slate-400">Abre em tela cheia, direto da tela inicial.</p>
          </div>
        </div>
        <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800"><X size={18} /></button>
      </div>
      <ol className="space-y-3 text-sm text-slate-200">
        <li className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/15 font-bold text-blue-300">1</span>
          <span>Toque em <Share size={16} className="mx-1 inline text-blue-300" /> <b>Compartilhar</b>, na barra do Safari.</span>
        </li>
        <li className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/15 font-bold text-blue-300">2</span>
          <span>Escolha <PlusSquare size={16} className="mx-1 inline text-blue-300" /> <b>Adicionar à Tela de Início</b>.</span>
        </li>
        <li className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/15 font-bold text-blue-300">3</span>
          <span>Toque em <b>Adicionar</b>. O ícone do NEXUS aparece na sua tela inicial.</span>
        </li>
      </ol>
      <p className="text-[11px] text-slate-500">Use o Safari: em outros navegadores do iPhone a opção pode não aparecer.</p>
      <button type="button" onClick={onFechar} className="w-full rounded-xl bg-nexus-yellow py-3 text-sm font-bold text-ink">Entendi</button>
    </div>
  </div>
);

/** Ajuda para navegadores Android sem o diálogo automático (ex.: aberto dentro de outro app). */
const PassoAPassoAndroid: React.FC<{ onFechar: () => void }> = ({ onFechar }) => (
  <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 sm:items-center sm:p-4" onClick={onFechar}>
    <div role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}
      className="max-h-[90dvh] w-full max-w-sm space-y-4 overflow-y-auto rounded-t-3xl border border-slate-700 bg-slate-900 p-6 pb-safe-4 text-left shadow-2xl sm:rounded-3xl">
      <h2 className="font-bold text-white">Instalar o NEXUS</h2>
      <p className="text-sm text-slate-300">
        No Chrome, toque em <MoreVertical size={15} className="mx-0.5 inline" /> <b>(menu)</b> e escolha <b>Instalar app</b> ou
        <b> Adicionar à tela inicial</b>.
      </p>
      <button type="button" onClick={onFechar} className="w-full rounded-xl bg-nexus-yellow py-3 text-sm font-bold text-ink">Entendi</button>
    </div>
  </div>
);

const ehCelular = () => typeof navigator !== 'undefined' && /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);

/** "Instalar app" na tela de login: diálogo nativo (Android) ou passo a passo (iPhone). Some quando já instalado. */
export const InstalarAppBotao: React.FC = () => {
  const { instalado, podeInstalar, ios, instalar } = useInstalarApp();
  const [ajuda, setAjuda] = useState<'ios' | 'android' | null>(null);

  if (instalado || (!podeInstalar && !ios && !ehCelular())) return null;

  const clicar = async () => {
    if (podeInstalar) {
      await instalar();
      return;
    }
    setAjuda(ios ? 'ios' : 'android');
  };

  return (
    <>
      <button type="button" onClick={() => void clicar()}
        className="flex w-full items-center gap-3 rounded-xl border border-slate-700/80 bg-slate-950/40 px-4 py-3 text-left transition hover:border-nexus-yellow/50">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-nexus-yellow/15 text-nexus-yellow">
          <Smartphone size={20} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-bold text-white">Instalar o app NEXUS</span>
          <span className="block text-[11px] text-slate-400">Acesse o AVA direto da tela inicial do celular.</span>
        </span>
        <Download size={18} className="shrink-0 text-nexus-yellow" />
      </button>
      {ajuda === 'ios' && <PassoAPassoIos onFechar={() => setAjuda(null)} />}
      {ajuda === 'android' && <PassoAPassoAndroid onFechar={() => setAjuda(null)} />}
    </>
  );
};
