import React from 'react';
import { Link } from 'react-router-dom';
import { GraduationCap, LogIn } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

/** Barra superior das páginas públicas de matrícula EAD. */
export const CabecalhoPublico: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
        <Link to="/matricula-ead" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-nexus-yellow text-ink"><GraduationCap size={20} /></span>
          <span className="leading-tight">
            <span className="block text-sm font-extrabold tracking-wide text-white">NEXUS EAD</span>
            <span className="block text-[10px] font-semibold uppercase tracking-widest text-nexus-yellow">ETADEMP</span>
          </span>
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
