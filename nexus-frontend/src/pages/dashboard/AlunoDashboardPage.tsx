import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import { BookOpen, Laptop, Award, FileCheck2 } from 'lucide-react';

export const AlunoDashboardPage: React.FC = () => {
  const { user } = useAuthStore();

  return (
    <div className="space-y-8 max-w-7xl">
      <div className="p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/15 border border-sky-500/30 text-sky-400 text-xs font-bold uppercase tracking-wider mb-3">
          <Laptop className="w-3.5 h-3.5" />
          Ambiente Virtual de Aprendizagem (AVA)
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Olá, {user?.nome || 'Estudante'}!
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-xl">
          Acesse suas disciplinas em andamento, videoaulas gravadas, histórico escolar e certificados.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-sky-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Disciplinas Matriculadas</span>
            <BookOpen className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">6</div>
          <p className="text-xs text-slate-400 mt-1">Neste semestre</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-nexus-yellow">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Média Geral Acumulada</span>
            <Award className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">8.8</div>
          <p className="text-xs text-emerald-400 mt-1">Status: Regular / Aprovado</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Certificados Disponíveis</span>
            <FileCheck2 className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">2</div>
          <p className="text-xs text-slate-400 mt-1">Prontos para download</p>
        </div>
      </div>
    </div>
  );
};
