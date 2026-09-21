import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { QueryProvider } from '@/contexts/QueryProvider'
import { Layout } from '@/components/layout/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Routes, Route } from 'react-router-dom'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { AlunosPage } from '@/pages/alunos/AlunosPage'
import { AlunoDetailPage } from '@/pages/alunos/AlunoDetailPage'
import { MatriculasPage } from '@/pages/matriculas/MatriculasPage'
import { PolosPage } from '@/pages/polos/PolosPage'
import { PoloDetailPage } from '@/pages/polos/PoloDetailPage'
import { EscolasPage } from '@/pages/escolas/EscolasPage'
import { EscolaDetailPage } from '@/pages/escolas/EscolaDetailPage'
import { CursosPage } from '@/pages/cursos/CursosPage'
import { EadPage } from '@/pages/ead/EadPage'
import { LicencasPage } from '@/pages/licencas/LicencasPage'
import { FinanceiroPage } from '@/pages/financeiro/FinanceiroPage'
import { LogisticaPage } from '@/pages/logistica/LogisticaPage'
import { CertificadosPage } from '@/pages/certificados/CertificadosPage'
import { ChatPage } from '@/pages/chat/ChatPage'
import { ConfiguracoesPage } from '@/pages/configuracoes/ConfiguracoesPage'
import { PerfilPage } from '@/pages/perfil/PerfilPage'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <QueryProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/alunos" element={<AlunosPage />} />
              <Route path="/alunos/:id" element={<AlunoDetailPage />} />
              <Route path="/matriculas" element={<MatriculasPage />} />
              <Route path="/polos" element={<PolosPage />} />
              <Route path="/polos/:id" element={<PoloDetailPage />} />
              <Route path="/escolas" element={<EscolasPage />} />
              <Route path="/escolas/:id" element={<EscolaDetailPage />} />
              <Route path="/cursos" element={<CursosPage />} />
              <Route path="/ead" element={<EadPage />} />
              <Route path="/licencas" element={<LicencasPage />} />
              <Route path="/financeiro" element={<FinanceiroPage />} />
              <Route path="/logistica" element={<LogisticaPage />} />
              <Route path="/certificados" element={<CertificadosPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/configuracoes" element={<ConfiguracoesPage />} />
              <Route path="/perfil" element={<PerfilPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </QueryProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

import { Navigate } from 'react-router-dom'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)