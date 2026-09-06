import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { UserRole } from '@/types/auth';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

interface RequireRoleProps {
  roles: UserRole[] | string[];
  children?: React.ReactNode;
}

export const RequireRole: React.FC<RequireRoleProps> = ({ roles, children }) => {
  const location = useLocation();
  const { isAuthenticated, perfil, isLoading, hasRole, getDashboardPath } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#0B0F19]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-nexus-yellow border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
            Validando permissões NEXUS 2.0...
          </span>
        </div>
      </div>
    );
  }

  // 1. Não autenticado -> Redireciona para o login com a rota pretendida gravada
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  // 2. Autenticado mas sem perfil compatível -> Tela de Acesso Negado (403)
  const isAuthorized = hasRole(roles);
  if (!isAuthorized) {
    const userRole = perfil?.nome || 'indefinido';
    const fallbackDashboard = getDashboardPath();

    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#0B0F19] p-6">
        <div className="max-w-md w-full bg-slate-900/90 border border-red-500/30 rounded-2xl p-8 text-center shadow-2xl backdrop-blur-xl">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-red-500/20 border border-red-500/30 flex items-center justify-center text-red-400 mb-5">
            <ShieldAlert className="w-8 h-8" />
          </div>

          <h2 className="text-2xl font-bold text-white tracking-tight">
            Acesso Não Autorizado
          </h2>

          <p className="text-sm text-slate-400 mt-2 leading-relaxed">
            Seu perfil atual (<strong className="text-nexus-yellow uppercase">{userRole}</strong>) não possui permissão para acessar este recurso ou módulo.
          </p>

          <div className="mt-4 p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-400">
            Perfis autorizados para esta área: <br />
            <span className="font-semibold text-slate-300">
              {roles.map((r) => r.toUpperCase()).join(', ')}
            </span>
          </div>

          <div className="mt-6">
            <a
              href={fallbackDashboard}
              className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm rounded-xl border border-slate-700 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Retornar ao Meu Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }

  return children ? <>{children}</> : <Outlet />;
};
