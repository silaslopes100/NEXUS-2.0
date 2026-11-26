import React from 'react';
import { Link } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { useAuthStore } from '@/stores/authStore';

/** Barra superior das páginas públicas de matrícula EAD. */
export const CabecalhoPublico: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
        <Link to="/matricula-ead" className="flex items-center gap-2" aria-label="NEXUS EAD — Turmas abertas">
          <NexusLogo size="sm" className="!items-start [&>img]:h-7 sm:[&>img]:h-8" />
          <span className="hidden border-l border-slate-700 pl-2 text-[10px] font-bold uppercase tracking-widest text-nexus-yellow sm:block">EAD</span>
        </Link>
        {isAuthenticated && user?.aluno_ead ? (
          <Link to="/aluno/compras" className="rounded-xl bg-nexus-yellow px-4 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
            Minhas disciplinas
          </Link>
        ) : (
          <Link to="/auth/login" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-nexus-yellow/60 hover:text-white">
            <LogIn size={15} /> Já sou aluno
          </Link>
        )}
      </div>
    </header>
  );
};
