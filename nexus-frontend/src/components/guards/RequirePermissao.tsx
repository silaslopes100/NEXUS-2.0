import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

interface RequirePermissaoProps {
  permissao: string;
  children?: React.ReactNode;
}

export const RequirePermissao: React.FC<RequirePermissaoProps> = ({
  permissao,
  children,
}) => {
  const location = useLocation();
  const { isAuthenticated, hasPermission, getDashboardPath } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  const isPermitted = hasPermission(permissao);
  if (!isPermitted) {
    const fallbackDashboard = getDashboardPath();

    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#0B0F19] p-6">
        <div className="max-w-md w-full bg-slate-900/90 border border-amber-500/30 rounded-2xl p-8 text-center shadow-2xl backdrop-blur-xl">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-5">
            <ShieldAlert className="w-8 h-8" />
          </div>

          <h2 className="text-2xl font-bold text-white tracking-tight">
            Permissão Insuficiente
          </h2>

          <p className="text-sm text-slate-400 mt-2 leading-relaxed">
            Seu usuário não possui a permissão granular <strong className="text-nexus-yellow">{permissao}</strong> necessária para operar este módulo.
          </p>

          <div className="mt-6">
            <a
              href={fallbackDashboard}
              className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm rounded-xl border border-slate-700 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Retornar ao Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }

  return children ? <>{children}</> : <Outlet />;
};
