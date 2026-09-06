import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import { Building, UserCheck, Key, BookMarked } from 'lucide-react';

export const PoloDashboardPage: React.FC = () => {
  const { user } = useAuthStore();

  return (
    <div className="space-y-8 max-w-7xl">
      <div className="p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-400 text-xs font-bold uppercase tracking-wider mb-3">
          <Building className="w-3.5 h-3.5" />
          Gestão de Polo Regional
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Painel do Polo • {user?.nome}
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-xl">
          Controle de escolas associadas, discentes matriculados, estoque de licenças e pedidos de material didático.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Alunos Ativos</span>
            <UserCheck className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">342</div>
          <p className="text-xs text-slate-400 mt-1">Discentes vinculados</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-nexus-yellow">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Licenças Disponíveis</span>
            <Key className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">85</div>
          <p className="text-xs text-slate-400 mt-1">Prontas para atribuição</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Pedidos de Livros</span>
            <BookMarked className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">12</div>
          <p className="text-xs text-slate-400 mt-1">Em trânsito logístico</p>
        </div>
      </div>
    </div>
  );
};
