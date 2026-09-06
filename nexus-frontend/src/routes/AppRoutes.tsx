import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { EsqueciSenhaPage } from '@/features/auth/pages/EsqueciSenhaPage';
import { RedefinirSenhaPage } from '@/features/auth/pages/RedefinirSenhaPage';
import { RequireRole } from '@/components/guards/RequireRole';
import { AppLayout } from '@/components/layout/AppLayout';
import { AdminDashboardPage } from '@/pages/dashboard/AdminDashboardPage';
import { PoloDashboardPage } from '@/pages/dashboard/PoloDashboardPage';
import { EscolaDashboardPage } from '@/pages/dashboard/EscolaDashboardPage';
import { ProfessorDashboardPage } from '@/pages/dashboard/ProfessorDashboardPage';
import { AlunoDashboardPage } from '@/pages/dashboard/AlunoDashboardPage';
import { ModulePlaceholderPage } from '@/pages/dashboard/ModulePlaceholderPage';
import { UsuariosInternosPage } from '@/features/admin/pages/UsuariosInternosPage';
import { LogsAuditoriaPage } from '@/features/admin/pages/LogsAuditoriaPage';
import { ConfiguracoesPage } from '@/features/admin/pages/ConfiguracoesPage';
import { ExecucoesBatchPage } from '@/features/admin/pages/ExecucoesBatchPage';
import { useAuthStore } from '@/stores/authStore';

const RootRedirect: React.FC = () => {
  const { isAuthenticated, getDashboardPath } = useAuthStore();
  if (isAuthenticated) {
    return <Navigate to={getDashboardPath()} replace />;
  }
  return <Navigate to="/auth/login" replace />;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Rotas Públicas de Autenticação */}
      <Route path="/auth">
        <Route path="login" element={<LoginPage />} />
        <Route path="esqueci-senha" element={<EsqueciSenhaPage />} />
        <Route path="redefinir-senha" element={<RedefinirSenhaPage />} />
        <Route index element={<Navigate to="/auth/login" replace />} />
      </Route>

      {/* Rotas Protegidas - Layout Principal */}
      <Route element={<AppLayout />}>
        
        {/* Módulo Admin */}
        <Route element={<RequireRole roles={['admin']} />}>
          <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
          <Route path="/admin/usuarios" element={<UsuariosInternosPage />} />
          <Route path="/admin/perfis-permissoes" element={<ModulePlaceholderPage />} />
          <Route path="/admin/polos-escolas" element={<ModulePlaceholderPage />} />
          <Route path="/admin/professores" element={<ModulePlaceholderPage />} />
          <Route path="/admin/cursos" element={<ModulePlaceholderPage />} />
          <Route path="/admin/disciplinas" element={<ModulePlaceholderPage />} />
          <Route path="/admin/turmas-calendarios" element={<ModulePlaceholderPage />} />
          <Route path="/admin/alunos" element={<ModulePlaceholderPage />} />
          <Route path="/admin/ead" element={<ModulePlaceholderPage />} />
          <Route path="/admin/notas-historico" element={<ModulePlaceholderPage />} />
          <Route path="/admin/presencas" element={<ModulePlaceholderPage />} />
          <Route path="/admin/certificados" element={<ModulePlaceholderPage />} />
          <Route path="/admin/licencas" element={<ModulePlaceholderPage />} />
          <Route path="/admin/financeiro" element={<ModulePlaceholderPage />} />
          <Route path="/admin/cupons" element={<ModulePlaceholderPage />} />
          <Route path="/admin/pedidos-livros" element={<ModulePlaceholderPage />} />
          <Route path="/admin/transferencias" element={<ModulePlaceholderPage />} />
          <Route path="/admin/auditoria" element={<LogsAuditoriaPage />} />
          <Route path="/admin/configuracoes" element={<ConfiguracoesPage />} />
          <Route path="/admin/execucoes-batch" element={<ExecucoesBatchPage />} />
          <Route path="/admin/etl" element={<ExecucoesBatchPage />} />
        </Route>

        {/* Módulo Polo */}
        <Route element={<RequireRole roles={['admin', 'polo']} />}>
          <Route path="/polo/dashboard" element={<PoloDashboardPage />} />
          <Route path="/polo/escolas" element={<ModulePlaceholderPage />} />
          <Route path="/polo/alunos" element={<ModulePlaceholderPage />} />
          <Route path="/polo/turmas" element={<ModulePlaceholderPage />} />
          <Route path="/polo/certificados" element={<ModulePlaceholderPage />} />
          <Route path="/polo/transferencias" element={<ModulePlaceholderPage />} />
          <Route path="/polo/licencas" element={<ModulePlaceholderPage />} />
          <Route path="/polo/comprar-licencas" element={<ModulePlaceholderPage />} />
          <Route path="/polo/livros" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulo Escola */}
        <Route element={<RequireRole roles={['admin', 'escola']} />}>
          <Route path="/escola/dashboard" element={<EscolaDashboardPage />} />
          <Route path="/escola/alunos" element={<ModulePlaceholderPage />} />
          <Route path="/escola/turmas" element={<ModulePlaceholderPage />} />
          <Route path="/escola/presencas" element={<ModulePlaceholderPage />} />
          <Route path="/escola/licencas" element={<ModulePlaceholderPage />} />
          <Route path="/escola/livros" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulo Professor */}
        <Route element={<RequireRole roles={['admin', 'professor']} />}>
          <Route path="/professor/dashboard" element={<ProfessorDashboardPage />} />
          <Route path="/professor/disciplinas" element={<ModulePlaceholderPage />} />
          <Route path="/professor/conteudos" element={<ModulePlaceholderPage />} />
          <Route path="/professor/notas" element={<ModulePlaceholderPage />} />
          <Route path="/professor/presencas" element={<ModulePlaceholderPage />} />
          <Route path="/professor/atas" element={<ModulePlaceholderPage />} />
          <Route path="/professor/calendario" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulo Aluno */}
        <Route element={<RequireRole roles={['admin', 'aluno']} />}>
          <Route path="/aluno/dashboard" element={<AlunoDashboardPage />} />
          <Route path="/aluno/ava" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/disciplinas" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/historico" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/presenca" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/certificados" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/livros" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/compras" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulos Compartilhados (Chat e Feed) */}
        <Route
          element={<RequireRole roles={['admin', 'polo', 'escola', 'professor', 'aluno']} />}
        >
          <Route path="/chat" element={<ModulePlaceholderPage />} />
          <Route path="/feed" element={<ModulePlaceholderPage />} />
        </Route>

      </Route>

      {/* Rota Raiz & Fallback */}
      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
