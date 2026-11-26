import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { EsqueciSenhaPage } from '@/features/auth/pages/EsqueciSenhaPage';
import { RedefinirSenhaPage } from '@/features/auth/pages/RedefinirSenhaPage';
import { RequireRole } from '@/components/guards/RequireRole';
import { RequireAlunoEad } from '@/components/guards/RequireAlunoEad';
import { AvaConteudoPage } from '@/features/ava/pages/admin/AvaConteudoPage';
import { AvaDisciplinaEditorPage } from '@/features/ava/pages/admin/AvaDisciplinaEditorPage';
import { AvaHomePage } from '@/features/ava/pages/aluno/AvaHomePage';
import { AvaDisciplinaPage } from '@/features/ava/pages/aluno/AvaDisciplinaPage';
import { AvaConquistasPage } from '@/features/ava/pages/aluno/AvaConquistasPage';
import { AvaRankingPage } from '@/features/ava/pages/aluno/AvaRankingPage';
import { TreinamentosAdminPage } from '@/features/ava/pages/admin/TreinamentosAdminPage';
import { TreinamentoEditorPage } from '@/features/ava/pages/admin/TreinamentoEditorPage';
import { TreinamentosCatalogoPage } from '@/features/ava/pages/treinamentos/TreinamentosCatalogoPage';
import { ValidarCertificadoPage } from '@/features/ava/pages/treinamentos/ValidarCertificadoPage';
import { treinamentoPlayerApi, treinamentosApi } from '@/features/ava/treinamentosApi';
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
import { TurmaDetalhePage } from '@/features/turmas/pages/TurmaDetalhePage';
import { NovaTurmaPage } from '@/features/turmas/pages/NovaTurmaPage';
import { CalendariosPage } from '@/features/carga_horaria/pages/CalendariosPage';
import { ProfessoresPage } from '@/features/professores/pages/ProfessoresPage';
import { MinhasDisciplinasPage as MinhasDisciplinasProfessorPage } from '@/features/professores/pages/MinhasDisciplinasPage';
import { MinhasConteudosPage as MinhasConteudosProfessorPage } from '@/features/professores/pages/MinhasConteudosPage';
import { PresencasPage } from '@/features/presencas/pages/PresencasPage';
import { MinhasPresencasPage } from '@/features/presencas/pages/MinhasPresencasPage';
import { FrequenciaUnidadePage } from '@/features/presencas/pages/FrequenciaUnidadePage';
import { DiarioAulasPage } from '@/features/aulas/pages/DiarioAulasPage';
import { AulasAuditoriaPage } from '@/features/aulas/pages/AulasAuditoriaPage';
import { CursosPage } from '@/features/cursos/pages/CursosPage';
import { DisciplinasPage } from '@/features/cursos/pages/DisciplinasPage';
import { TransferenciasPage } from '@/features/transferencias/pages/TransferenciasPage';
import { MinhasDisciplinasPage } from '@/features/alunos/pages/MinhasDisciplinasPage';
import { RealizarAvaliacaoPage } from '@/features/avaliacoes/pages/RealizarAvaliacaoPage';
import { SolicitacoesEscolaPage } from '@/features/solicitacoes/pages/SolicitacoesEscolaPage';
import { SolicitacoesPoloPage } from '@/features/solicitacoes/pages/SolicitacoesPoloPage';
import { NotasProfessorPage } from '@/features/notas_historico/pages/NotasProfessorPage';
import { HistoricoAlunoPage } from '@/features/notas_historico/pages/HistoricoAlunoPage';
import { LojaEadPage } from '@/features/ead_vendas/pages/LojaEadPage';
import { TurmaEadPage } from '@/features/ead_vendas/pages/TurmaEadPage';
import { VitrineEadPage } from '@/features/ead_vendas/pages/VitrineEadPage';
import { GatewaysPage } from '@/features/financeiro/pages/GatewaysPage';
import { PagamentosPage } from '@/features/financeiro/pages/PagamentosPage';
import { MeusPedidosPage } from '@/features/financeiro/pages/MeusPedidosPage';
import { PedidosPage } from '@/features/financeiro/pages/PedidosPage';
import { EstoquePage } from '@/features/financeiro/pages/EstoquePage';
import { ComprarLicencasPage } from '@/features/financeiro/pages/ComprarLicencasPage';
import { LogisticaPage } from '@/features/financeiro/pages/LogisticaPage';
import { RegrasPagamentoPage } from '@/features/financeiro/pages/RegrasPagamentoPage';
import { VendasPage } from '@/features/financeiro/pages/VendasPage';
import { FinanceiroDashboardPage } from '@/pages/dashboard/FinanceiroDashboardPage';
import { LogisticaDashboardPage } from '@/pages/dashboard/LogisticaDashboardPage';
import { ChatPage } from '@/features/chat/pages/ChatPage';
import { ChatAdminPage } from '@/features/chat/pages/ChatAdminPage';
import { CentralEstagioAdminPage } from '@/features/estagios/pages/CentralEstagioAdminPage';
import { CentralEstagioAlunoPage } from '@/features/estagios/pages/CentralEstagioAlunoPage';
import { FeedPage } from '@/features/comunicacao/pages/FeedPage';
import { FeedPostPage } from '@/features/comunicacao/pages/FeedPostPage';
import { ModeracaoFeedPage } from '@/features/comunicacao/pages/ModeracaoFeedPage';
import { AvisosAdminPage } from '@/features/comunicacao/pages/AvisosAdminPage';
import { useAuthStore } from '@/stores/authStore';

const RootRedirect: React.FC = () => {
  const { isAuthenticated, getDashboardPath } = useAuthStore();
  if (isAuthenticated) {
    return <Navigate to={getDashboardPath()} replace />;
  }
  return <Navigate to="/auth/login" replace />;
};

/** Player do AVA no modo treinamento (mesma experiência da Sala de Aula Virtual). */
const TreinamentoPlayer: React.FC<{ previa?: boolean }> = ({ previa }) => (
  <AvaDisciplinaPage modo="treinamento" previa={previa} api={treinamentoPlayerApi} onBaixarCertificado={treinamentosApi.baixarCertificado} />
);

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

      {/* Validação pública de certificado (fora do layout logado) */}
      <Route path="/certificados/validar" element={<ValidarCertificadoPage />} />
      <Route path="/certificados/validar/:codigo" element={<ValidarCertificadoPage />} />

      {/* Página pública de vendas do EAD: Turmas EAD abertas e inscrição gratuita */}
      <Route path="/matricula-ead" element={<VitrineEadPage />} />
      <Route path="/matricula-ead/:turmaId" element={<TurmaEadPage />} />

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
          <Route path="/admin/aulas" element={<AulasAuditoriaPage />} />
          <Route path="/admin/turmas-calendarios" element={<TurmasPage />} />
          <Route path="/admin/turmas-calendarios/nova" element={<NovaTurmaPage />} />
          <Route path="/admin/turmas-calendarios/:turmaId" element={<TurmaDetalhePage />} />
          <Route path="/admin/calendarios" element={<CalendariosPage />} />
          <Route path="/admin/alunos" element={<AlunosPage />} />
          <Route path="/admin/ead" element={<Navigate to="/admin/ava" replace />} />
          <Route path="/admin/ava" element={<AvaConteudoPage />} />
          <Route path="/admin/ava/disciplinas/:disciplinaId" element={<AvaDisciplinaEditorPage />} />
          <Route path="/admin/ava/disciplinas/:disciplinaId/previa" element={<AvaDisciplinaPage previa />} />
          <Route path="/admin/ava/disciplinas/:disciplinaId/previa/aulas/:aulaId" element={<AvaDisciplinaPage previa />} />
          <Route path="/admin/presencas" element={<PresencasPage />} />
          <Route path="/admin/licencas" element={<LicencasPage />} />
          <Route path="/admin/cupons" element={<ModulePlaceholderPage />} />
          <Route path="/admin/transferencias" element={<TransferenciasPage />} />
          <Route path="/admin/auditoria" element={<LogsAuditoriaPage />} />
          <Route path="/admin/configuracoes" element={<ConfiguracoesPage />} />
          <Route path="/admin/execucoes-batch" element={<ExecucoesBatchPage />} />
          <Route path="/admin/chat" element={<ChatAdminPage />} />
          <Route path="/admin/etl" element={<ExecucoesBatchPage />} />
          <Route path="/admin/estoque" element={<EstoquePage />} />
          <Route path="/admin/estagios" element={<CentralEstagioAdminPage />} />
          <Route path="/admin/feed/moderacao" element={<ModeracaoFeedPage />} />
          <Route path="/admin/treinamentos" element={<TreinamentosAdminPage />} />
          <Route path="/admin/treinamentos/:treinamentoId" element={<TreinamentoEditorPage />} />
          <Route path="/admin/treinamentos/:disciplinaId/previa" element={<TreinamentoPlayer previa />} />
          <Route path="/admin/treinamentos/:disciplinaId/previa/aulas/:aulaId" element={<TreinamentoPlayer previa />} />
          <Route path="/admin/avisos" element={<AvisosAdminPage />} />
        </Route>

        {/* Módulo 2.4 — Financeiro (admin + perfil financeiro; o backend restringe por área) */}
        <Route element={<RequireRole roles={['admin', 'financeiro']} />}>
          <Route path="/financeiro/dashboard" element={<FinanceiroDashboardPage />} />
          <Route path="/admin/financeiro" element={<PagamentosPage />} />
          <Route path="/admin/vendas" element={<VendasPage />} />
          <Route path="/admin/pedidos" element={<PedidosPage />} />
          <Route path="/admin/regras-pagamento" element={<RegrasPagamentoPage />} />
          <Route path="/admin/gateways" element={<GatewaysPage />} />
        </Route>

        {/* Módulo 2.4 — Logística (admin + perfil logística) */}
        <Route element={<RequireRole roles={['admin', 'logistica']} />}>
          <Route path="/logistica/dashboard" element={<LogisticaDashboardPage />} />
          <Route path="/admin/logistica/pendentes" element={<LogisticaPage modo="pendentes" />} />
          <Route path="/admin/logistica/historico" element={<LogisticaPage modo="historico" />} />
          <Route path="/admin/pedidos-livros" element={<Navigate to="/admin/logistica/pendentes" replace />} />
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
          <Route path="/polo/turmas/nova" element={<NovaTurmaPage />} />
          <Route path="/polo/turmas/:turmaId" element={<TurmaDetalhePage />} />
          <Route path="/polo/transferencias" element={<TransferenciasPage />} />
          <Route path="/polo/presencas" element={<FrequenciaUnidadePage />} />
          <Route path="/polo/licencas" element={<LicencasPage />} />
          <Route path="/polo/comprar-licencas" element={<ComprarLicencasPage />} />
          <Route path="/polo/livros" element={<MeusPedidosPage />} />
          <Route path="/polo/solicitacoes" element={<SolicitacoesPoloPage />} />
          <Route path="/polo/estagios" element={<CentralEstagioAdminPage />} />
        </Route>

        {/* Módulo Escola */}
        <Route element={<RequireRole roles={['admin', 'escola']} />}>
          <Route path="/escola/dashboard" element={<EscolaDashboardPage />} />
          <Route path="/escola/cursos" element={<CursosPage />} />
          <Route path="/escola/alunos" element={<AlunosPage />} />
          <Route path="/escola/turmas" element={<TurmasPage />} />
          <Route path="/escola/turmas/nova" element={<NovaTurmaPage />} />
          <Route path="/escola/turmas/:turmaId" element={<TurmaDetalhePage />} />
          <Route path="/escola/transferencias" element={<TransferenciasPage />} />
          <Route path="/escola/presencas" element={<FrequenciaUnidadePage />} />
          <Route path="/escola/licencas" element={<LicencasPage />} />
          <Route path="/escola/livros" element={<MeusPedidosPage />} />
          <Route path="/escola/solicitacoes" element={<SolicitacoesEscolaPage />} />
          <Route path="/escola/estagios" element={<CentralEstagioAdminPage />} />
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
            <Route path="/aluno/avaliacoes/:avaliacaoId" element={<RealizarAvaliacaoPage />} />
            <Route path="/aluno/presenca" element={<MinhasPresencasPage />} />
            <Route path="/aluno/estagio" element={<CentralEstagioAlunoPage />} />
          </Route>
          <Route element={<RequireAlunoEad />}>
            <Route path="/aluno/ava" element={<AvaHomePage />} />
            <Route path="/aluno/ava/disciplinas/:disciplinaId" element={<AvaDisciplinaPage />} />
            <Route path="/aluno/ava/disciplinas/:disciplinaId/aulas/:aulaId" element={<AvaDisciplinaPage />} />
            <Route path="/aluno/ava/conquistas" element={<AvaConquistasPage />} />
            <Route path="/aluno/ava/ranking" element={<AvaRankingPage />} />
          </Route>
          <Route path="/aluno/historico" element={<HistoricoAlunoPage />} />
          <Route path="/aluno/livros" element={<ModulePlaceholderPage />} />
          <Route element={<RequireAlunoEad />}>
            <Route path="/aluno/compras" element={<LojaEadPage />} />
          </Route>
        </Route>

        {/* Chat Interno (todos os perfis) */}
        <Route
          element={<RequireRole roles={['admin', 'polo', 'escola', 'professor', 'aluno', 'financeiro', 'logistica']} />}
        >
          <Route path="/chat" element={<ChatPage />} />
        </Route>

        {/* Feed de Notícias (todos leem, curtem e comentam; a equipe publica e modera os próprios posts) */}
        <Route
          element={<RequireRole roles={['admin', 'polo', 'escola', 'professor', 'aluno', 'financeiro', 'logistica']} />}
        >
          <Route path="/feed" element={<FeedPage />} />
          <Route path="/feed/:postId" element={<FeedPostPage />} />
        </Route>
        <Route
          element={<RequireRole roles={['admin', 'polo', 'escola', 'professor', 'financeiro', 'logistica']} />}
        >
          <Route path="/feed/moderacao" element={<ModeracaoFeedPage />} />
        </Route>

        {/* Treinamentos (Polos, Escolas e Professores) */}
        <Route element={<RequireRole roles={['polo', 'escola', 'professor']} />}>
          <Route path="/treinamentos" element={<TreinamentosCatalogoPage />} />
          <Route path="/treinamentos/:disciplinaId" element={<TreinamentoPlayer />} />
          <Route path="/treinamentos/:disciplinaId/aulas/:aulaId" element={<TreinamentoPlayer />} />
        </Route>

      </Route>

      {/* Rota Raiz & Fallback */}
      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
