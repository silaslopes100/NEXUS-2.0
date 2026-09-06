import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import { School, UserCheck, CalendarDays, Clock } from 'lucide-react';

export const EscolaDashboardPage: React.FC = () => {
  const { user } = useAuthStore();

  return (
    <div className="space-y-8 max-w-7xl">
      <div className="p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-purple-950/40 border border-slate-800 shadow-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-xs font-bold uppercase tracking-wider mb-3">
          <School className="w-3.5 h-3.5" />
          Unidade Escolar
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Painel da Escola • {user?.nome}
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-xl">
          Acompanhamento de turmas, controle de presenças presenciais e requisição de material pedagógico.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-purple-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Turmas em Andamento</span>
            <CalendarDays className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">8</div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Alunos Matriculados</span>
            <UserCheck className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">126</div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Frequência Média</span>
            <Clock className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">94.2%</div>
        </div>
      </div>
    </div>
  );
};
