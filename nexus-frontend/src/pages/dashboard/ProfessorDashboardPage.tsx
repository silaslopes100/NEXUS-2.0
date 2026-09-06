import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import { GraduationCap, BookOpen, Award, Clock } from 'lucide-react';

export const ProfessorDashboardPage: React.FC = () => {
  const { user } = useAuthStore();

  return (
    <div className="space-y-8 max-w-7xl">
      <div className="p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 border border-slate-800 shadow-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-3">
          <GraduationCap className="w-3.5 h-3.5" />
          Corpo Docente
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Olá, Professor(a) {user?.nome}!
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-xl">
          Ambiente para lançamento de notas, diário de presenças, upload de materiais e interação com as turmas.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Minhas Disciplinas</span>
            <BookOpen className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">4</div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-nexus-yellow">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Avaliações Pendentes</span>
            <Award className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">18</div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Próximas Aulas</span>
            <Clock className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">Hoje, 19:30</div>
        </div>
      </div>
    </div>
  );
};
