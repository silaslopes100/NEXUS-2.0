import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { Menu, Bell, Search } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, perfil } = useAuthStore();

  const roleName = perfil?.nome || user?.perfil?.nome || 'aluno';

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex">
      {/* Dynamic Role-Based Sidebar */}
      <Sidebar
        isMobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:pl-72 transition-all duration-300 min-w-0">
        
        {/* Top Navbar */}
        <header className="h-16 px-6 bg-slate-900/60 border-b border-slate-800/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
              <span className="font-semibold text-slate-300">NEXUS 2.0</span>
              <span>/</span>
              <span className="text-nexus-yellow font-medium capitalize">{roleName}</span>
            </div>
          </div>

          <div className="flex items-center gap-3.5">
            {/* Quick Search */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 w-64 focus-within:border-nexus-yellow transition-colors">
              <Search className="w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Buscar no sistema..."
                className="bg-transparent text-white placeholder-slate-500 focus:outline-none w-full text-xs"
              />
            </div>

            {/* Notifications Pill */}
            <button className="p-2 rounded-xl bg-slate-800/60 border border-slate-700/60 text-slate-300 hover:text-nexus-yellow hover:border-nexus-yellow/30 transition-colors relative">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-nexus-yellow rounded-full ring-2 ring-slate-900" />
            </button>

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
              <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-nexus-yellow">
                {user?.nome ? user.nome.charAt(0).toUpperCase() : 'U'}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
