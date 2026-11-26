import React, { useCallback, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { Menu, Search } from 'lucide-react';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { NotificacoesSino } from '@/features/solicitacoes/components/NotificacoesSino';
import { ChatBadge } from '@/features/chat/components/ChatBadge';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
import { AppBackdrop } from '@/components/layout/AppBackdrop';
import { UsuarioAvatarProprio } from '@/components/layout/UsuarioAvatarProprio';
import { BarraInferiorAluno } from '@/components/layout/BarraInferiorAluno';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { AvisosPopupHost } from '@/features/comunicacao/components/AvisosPopupHost';

const CHAVE_RECOLHIDO = 'nexus:menu-recolhido';

const lerRecolhido = () => {
  try {
    return localStorage.getItem(CHAVE_RECOLHIDO) === '1';
  } catch {
    return false;
  }
};

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [recolhido, setRecolhido] = useState(lerRecolhido);
  const { user, perfil, viaLicenca } = useAuthStore();
  const location = useLocation();

  const roleName = perfil?.nome || user?.perfil?.nome || 'aluno';
  const ehAluno = normalizeUserRole(perfil?.nome || user?.perfil?.nome) === 'aluno';
  // No player da disciplina a barra fixa da aula ocupa o rodapé.
  const noPlayer = /^\/aluno\/ava\/disciplinas\//.test(location.pathname);
  const barraAluno = ehAluno && !viaLicenca && !noPlayer;
  const alunoEad = !!user?.aluno_ead && !user?.tambem_aluno;

  const fecharMenu = useCallback(() => setMobileMenuOpen(false), []);
  const alternarRecolhido = () => {
    setRecolhido((v) => {
      try {
        localStorage.setItem(CHAVE_RECOLHIDO, v ? '0' : '1');
      } catch {
        /* armazenamento indisponível */
      }
      return !v;
    });
  };

  return (
    <div
      className="relative isolate min-h-screen min-h-dvh bg-nexus-page text-slate-100 flex"
      style={{ '--sidebar-w': recolhido ? '5rem' : '18rem' } as React.CSSProperties}
    >
      <AppBackdrop />
      {/* Dynamic Role-Based Sidebar */}
      <Sidebar
        isMobileOpen={mobileMenuOpen}
        onCloseMobile={fecharMenu}
        recolhido={recolhido}
        onAlternarRecolhido={alternarRecolhido}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:pl-[var(--sidebar-w)] transition-all duration-300 min-w-0">

        {/* Top Navbar */}
        <header className="glass-panel pt-safe border-b border-slate-800/80 sticky top-0 z-30">
          <div className="h-14 sm:h-16 px-3 sm:px-6 flex items-center justify-between gap-2">
            <div className="flex items-center gap-3 min-w-0">
              <button
                onClick={() => setMobileMenuOpen(true)}
                aria-label="Abrir menu"
                className="lg:hidden p-2.5 rounded-xl bg-slate-800 text-slate-300 hover:text-white"
              >
                <Menu className="w-5 h-5" />
              </button>

              <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
                <span className="font-semibold text-slate-300">NEXUS 2.0</span>
                <span>/</span>
                <span className="text-nexus-yellow font-medium capitalize">{roleName}</span>
              </div>
              <NexusLogo size="sm" className="sm:hidden !items-start [&>img]:h-7" />
            </div>

            <div className="flex items-center gap-1.5 sm:gap-3.5">
              {/* Quick Search */}
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 w-64 focus-within:border-nexus-yellow transition-colors">
                <Search className="w-3.5 h-3.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Buscar no sistema..."
                  className="bg-transparent text-white placeholder-slate-500 focus:outline-none w-full text-xs"
                />
              </div>

              <ThemeToggle />
              <ChatBadge />
              <NotificacoesSino />

              {/* User Profile Tag */}
              <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800">
                <div className="text-right hidden sm:block">
                  <p className="text-xs font-semibold text-white leading-tight">
                    {user?.nome || 'Usuário'}
                  </p>
                  <p className="text-[10px] font-bold text-nexus-yellow uppercase tracking-wider">
                    {roleName}
                  </p>
                </div>
                <UsuarioAvatarProprio
                  usuarioId={user?.id}
                  fotoUrl={user?.foto_url}
                  nome={user?.nome}
                  className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-nexus-yellow"
                />
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className={`flex-1 px-3 py-4 sm:p-6 lg:p-8 overflow-y-auto ${barraAluno ? 'pb-28 lg:pb-8' : ''}`}>
          <Outlet />
        </main>
      </div>
      {barraAluno && <BarraInferiorAluno ead={alunoEad} onAbrirMenu={() => setMobileMenuOpen(true)} />}
      <AvisosPopupHost />
    </div>
  );
};
