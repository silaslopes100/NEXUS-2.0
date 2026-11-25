import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { ArrowLeft, Laptop } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

/**
 * A Sala de Aula Virtual (AVA) é exclusiva do aluno EAD. Alunos de Polo/Escola e usuários
 * de Polo/Escola que também são alunos veem uma explicação amigável. O admin entra para conferir.
 * O backend aplica a mesma regra em todas as rotas /ava/aluno.
 */
export const RequireAlunoEad: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { user, hasRole, getDashboardPath } = useAuthStore();
  const ehAdmin = (user?.perfil?.nome || '').toLowerCase() === 'admin';
  const liberado = ehAdmin || (!!user?.aluno_ead && hasRole(['aluno']) && !user?.tambem_aluno);

  if (!liberado) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-6">
        <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-center shadow-2xl">
          <span className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-nexus-yellow/15 text-nexus-yellow">
            <Laptop className="h-7 w-7" />
          </span>
          <h2 className="text-2xl font-bold text-white">Sala de Aula Virtual</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            A Sala de Aula Virtual é exclusiva para alunos da modalidade EAD. Suas aulas acontecem no seu Polo ou na sua
            Escola, e as avaliações ficam em <strong className="text-slate-200">Minhas Disciplinas</strong>.
          </p>
          <Link to={getDashboardPath()}
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">
            <ArrowLeft className="h-4 w-4" /> Voltar ao início
          </Link>
        </div>
      </div>
    );
  }

  return children ? <>{children}</> : <Outlet />;
};
