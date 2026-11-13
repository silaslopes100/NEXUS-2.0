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
import { UsuarioFichaPage } from '@/features/admin/pages/UsuarioFichaPage';
import { LogsAuditoriaPage } from '@/features/admin/pages/LogsAuditoriaPage';
import { ConfiguracoesPage } from '@/features/admin/pages/ConfiguracoesPage';
import { ExecucoesBatchPage } from '@/features/admin/pages/ExecucoesBatchPage';
import { LicencasPage } from '@/features/licencas/pages/LicencasPage';
import { PolosEscolasPage } from '@/features/polos_escolas/pages/PolosEscolasPage';
import { EscolasPage } from '@/features/polos_escolas/pages/EscolasPage';
import { LicencasEscolaPage } from '@/features/licencas/pages/LicencasEscolaPage';
import { AlunosPage } from '@/features/alunos/pages/AlunosPage';
import { PerfilAlunoPage } from '@/features/alunos/pages/PerfilAlunoPage';
import { TurmasPage } from '@/features/turmas/pages/TurmasPage';
import { ProfessoresPage } from '@/features/professores/pages/ProfessoresPage';
import { MinhasDisciplinasPage as MinhasDisciplinasProfessorPage } from '@/features/professores/pages/MinhasDisciplinasPage';
import { MinhasConteudosPage as MinhasConteudosProfessorPage } from '@/features/professores/pages/MinhasConteudosPage';
import { PresencasPage } from '@/features/presencas/pages/PresencasPage';
import { DiarioAulasPage } from '@/features/aulas/pages/DiarioAulasPage';
import { AulasAuditoriaPage } from '@/features/aulas/pages/AulasAuditoriaPage';
import { CursosPage } from '@/features/cursos/pages/CursosPage';
import { DisciplinasPage } from '@/features/cursos/pages/DisciplinasPage';
import { TransferenciasPage } from '@/features/transferencias/pages/TransferenciasPage';
import { MinhasDisciplinasPage } from '@/features/alunos/pages/MinhasDisciplinasPage';
import { NotasAdminPage } from '@/features/notas_historico/pages/NotasAdminPage';
import { NotasProfessorPage } from '@/features/notas_historico/pages/NotasProfessorPage';
import { HistoricoAlunoPage } from '@/features/notas_historico/pages/HistoricoAlunoPage';
import { ComprasEadPage } from '@/features/alunos/components/RegularizacaoEadModal';
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
          <Route path="/admin/usuarios/:usuarioId" element={<UsuarioFichaPage />} />
          <Route path="/admin/perfis-permissoes" element={<ModulePlaceholderPage />} />
          <Route path="/admin/polos-escolas" element={<PolosEscolasPage />} />
          <Route path="/admin/escolas" element={<EscolasPage />} />
          <Route path="/admin/escolas/:escolaId/licencas" element={<LicencasEscolaPage />} />
          <Route path="/admin/professores" element={<ProfessoresPage />} />
          <Route path="/admin/cursos" element={<CursosPage />} />
          <Route path="/admin/disciplinas" element={<DisciplinasPage />} />
          <Route path="/admin/disciplinas/:disciplinaId/aulas" element={<AulasAuditoriaPage />} />
          <Route path="/admin/aulas" element={<AulasAuditoriaPage />} />
          <Route path="/admin/turmas-calendarios" element={<TurmasPage />} />
          <Route path="/admin/alunos" element={<AlunosPage />} />
          <Route path="/admin/ead" element={<ModulePlaceholderPage />} />
          <Route path="/admin/notas-historico" element={<NotasAdminPage />} />
          <Route path="/admin/presencas" element={<PresencasPage />} />
          <Route path="/admin/certificados" element={<ModulePlaceholderPage />} />
          <Route path="/admin/licencas" element={<LicencasPage />} />
          <Route path="/admin/financeiro" element={<ModulePlaceholderPage />} />
          <Route path="/admin/cupons" element={<ModulePlaceholderPage />} />
          <Route path="/admin/pedidos-livros" element={<ModulePlaceholderPage />} />
          <Route path="/admin/transferencias" element={<TransferenciasPage />} />
          <Route path="/admin/auditoria" element={<LogsAuditoriaPage />} />
          <Route path="/admin/configuracoes" element={<ConfiguracoesPage />} />
          <Route path="/admin/execucoes-batch" element={<ExecucoesBatchPage />} />
          <Route path="/admin/etl" element={<ExecucoesBatchPage />} />
        </Route>

        {/* Módulo Polo */}
        <Route element={<RequireRole roles={['admin', 'polo']} />}>
          <Route path="/polo/dashboard" element={<PoloDashboardPage />} />
          <Route path="/polo/cursos" element={<CursosPage />} />
          <Route path="/polo/escolas" element={<PolosEscolasPage />} />
          <Route path="/polo/escolas/gestao" element={<EscolasPage />} />
          <Route path="/polo/escolas/:escolaId/licencas" element={<LicencasEscolaPage />} />
          <Route path="/polo/alunos" element={<AlunosPage />} />
          <Route path="/polo/turmas" element={<TurmasPage />} />
          <Route path="/polo/certificados" element={<ModulePlaceholderPage />} />
          <Route path="/polo/transferencias" element={<TransferenciasPage />} />
          <Route path="/polo/licencas" element={<LicencasPage />} />
          <Route path="/polo/comprar-licencas" element={<ModulePlaceholderPage />} />
          <Route path="/polo/livros" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulo Escola */}
        <Route element={<RequireRole roles={['admin', 'escola']} />}>
          <Route path="/escola/dashboard" element={<EscolaDashboardPage />} />
          <Route path="/escola/cursos" element={<CursosPage />} />
          <Route path="/escola/alunos" element={<AlunosPage />} />
          <Route path="/escola/turmas" element={<TurmasPage />} />
          <Route path="/escola/transferencias" element={<TransferenciasPage />} />
          <Route path="/escola/presencas" element={<ModulePlaceholderPage />} />
          <Route path="/escola/licencas" element={<LicencasPage />} />
          <Route path="/escola/livros" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulo Professor */}
        <Route element={<RequireRole roles={['admin', 'professor']} />}>
          <Route path="/professor/dashboard" element={<ProfessorDashboardPage />} />
          <Route path="/professor/disciplinas" element={<MinhasDisciplinasProfessorPage />} />
          <Route path="/professor/conteudos" element={<MinhasConteudosProfessorPage />} />
          <Route path="/professor/notas" element={<NotasProfessorPage />} />
          <Route path="/professor/aulas" element={<DiarioAulasPage />} />
          {/* Presença e atas agora vivem no Diário de Aulas */}
          <Route path="/professor/presencas" element={<Navigate to="/professor/aulas" replace />} />
          <Route path="/professor/atas" element={<Navigate to="/professor/aulas" replace />} />
          <Route path="/professor/calendario" element={<ModulePlaceholderPage />} />
        </Route>

        {/* Módulo Aluno */}
        <Route element={<RequireRole roles={['admin', 'aluno']} />}>
          <Route path="/aluno/dashboard" element={<AlunoDashboardPage />} />
          <Route element={<RequireRole roles={['aluno']} />}>
            <Route path="/aluno/perfil" element={<PerfilAlunoPage />} />
            <Route path="/aluno/transferencias" element={<TransferenciasPage modo="aluno" />} />
            <Route path="/aluno/disciplinas" element={<MinhasDisciplinasPage />} />
          </Route>
          <Route path="/aluno/ava" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/historico" element={<HistoricoAlunoPage />} />
          <Route path="/aluno/presenca" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/certificados" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/livros" element={<ModulePlaceholderPage />} />
          <Route path="/aluno/compras" element={<ComprasEadPage />} />
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
