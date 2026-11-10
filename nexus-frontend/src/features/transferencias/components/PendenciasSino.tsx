import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeftRight, Bell } from 'lucide-react';
import { tipoLabel } from '@/features/transferencias/api';
import { useTransferenciasStore } from '@/stores/transferenciasStore';

const INTERVALO_MS = 60_000;

export const PendenciasSino: React.FC = () => {
  const { pathname } = useLocation();
  const { total, itens, carregar } = useTransferenciasStore();
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    void carregar();
  }, [carregar, pathname]);

  useEffect(() => {
    const timer = window.setInterval(() => void carregar(), INTERVALO_MS);
    return () => window.clearInterval(timer);
  }, [carregar]);

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={`Notificações: ${total} transferência(s) pendente(s)`}
        aria-expanded={aberto}
        onClick={() => setAberto((atual) => !atual)}
        className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/60 text-slate-300 hover:text-nexus-yellow hover:border-nexus-yellow/30 transition-colors relative"
      >
        <Bell className="w-4 h-4" />
        {total > 0 && (
          <span className="absolute -top-1.5 -right-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white ring-2 ring-slate-900">
            {total > 99 ? '99+' : total}
          </span>
        )}
      </button>

      {aberto && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setAberto(false)} />
          <div className="absolute right-0 z-50 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
            <header className="border-b border-slate-800 px-4 py-3">
              <p className="text-sm font-semibold text-white">Transferências pendentes</p>
              <p className="text-xs text-slate-400">{total} aguardando análise</p>
            </header>
            <div className="max-h-72 overflow-y-auto">
              {itens.map((item) => (
                <Link
                  key={item.id}
                  to="/admin/transferencias"
                  onClick={() => setAberto(false)}
                  className="flex items-start gap-3 border-b border-slate-800/70 px-4 py-3 hover:bg-slate-800/60"
                >
                  <ArrowLeftRight className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                  <span className="min-w-0">
                    <span className="block truncate text-xs font-semibold text-white">
                      {item.aluno_nome || 'Aluno'}
                    </span>
                    <span className="block truncate text-[11px] text-slate-400">
                      {tipoLabel[item.tipo]}
                    </span>
                  </span>
                </Link>
              ))}
              {itens.length === 0 && (
                <p className="px-4 py-8 text-center text-xs text-slate-500">
                  Nenhuma pendência no momento.
                </p>
              )}
            </div>
            <Link
              to="/admin/transferencias"
              onClick={() => setAberto(false)}
              className="block px-4 py-2.5 text-center text-xs font-semibold text-blue-300 hover:bg-slate-800/60"
            >
              Ver todas as transferências
            </Link>
          </div>
        </>
      )}
    </div>
  );
};
