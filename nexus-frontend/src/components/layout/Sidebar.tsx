import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { menuByRole, MenuItem, MenuGroup } from '@/components/navigation/menuConfig';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { UserRole } from '@/types/auth';
import {
  LogOut,
  ChevronLeft,
  ChevronRight,
  User as UserIcon,
  ShieldCheck,
  Building,
  GraduationCap,
  School,
  BookOpen,
} from 'lucide-react';
import { authApi } from '@/features/auth/api';

interface SidebarProps {
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const navigate = useNavigate();
  const { user, perfil, logout, refreshToken } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const rawRole = (perfil?.nome || user?.perfil?.nome || 'aluno').toLowerCase().trim();
  const activeRole: UserRole = (['admin', 'polo', 'escola', 'professor', 'aluno'].includes(rawRole)
    ? rawRole
    : 'aluno') as UserRole;

  const menuGroups: MenuGroup[] = menuByRole[activeRole] || menuByRole.aluno;

  const handleLogout = async () => {
    try {
      await authApi.logout(refreshToken);
    } catch (e) {
      // Limpeza local mesmo se a requisição falhar
    }
    logout();
    navigate('/auth/login', { replace: true });
  };

  const getRoleBadgeInfo = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return {
          label: 'Administrador Central',
          icon: ShieldCheck,
          bg: 'bg-amber-500/15 border-amber-500/30 text-nexus-yellow',
        };
      case 'polo':
        return {
          label: 'Gestor de Polo',
          icon: Building,
          bg: 'bg-blue-500/15 border-blue-500/30 text-blue-400',
        };
      case 'escola':
        return {
          label: 'Unidade Escolar',
          icon: School,
          bg: 'bg-purple-500/15 border-purple-500/30 text-purple-300',
        };
      case 'professor':
        return {
          label: 'Corpo Docente',
          icon: GraduationCap,
          bg: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
        };
      case 'aluno':
        return {
          label: 'Área do Aluno',
          icon: BookOpen,
          bg: 'bg-sky-500/15 border-sky-500/30 text-sky-400',
        };
      default:
        return {
          label: role,
          icon: UserIcon,
          bg: 'bg-slate-800 border-slate-700 text-slate-300',
        };
    }
  };

  const roleInfo = getRoleBadgeInfo(activeRole);
  const RoleIcon = roleInfo.icon;

  const renderBadge = (item: MenuItem) => {
    if (!item.badge) return null;
    const colorClasses = {
      yellow: 'bg-nexus-yellow/20 text-nexus-yellow border-nexus-yellow/30',
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      emerald: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      purple: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      slate: 'bg-slate-800 text-slate-400 border-slate-700',
    };
    const c = item.badgeColor ? colorClasses[item.badgeColor] : colorClasses.slate;
    return (
      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${c}`}>
        {item.badge}
      </span>
    );
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 left-0 bottom-0 z-50 flex flex-col bg-[#0B0F19] border-r border-slate-800/80 transition-all duration-300 ease-in-out ${
          collapsed ? 'w-20' : 'w-72'
        } ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top Header & Brand */}
        <div className="h-20 flex items-center justify-between px-5 border-b border-slate-800/80 bg-slate-950/40">
          {!collapsed ? (
            <div className="flex items-center gap-2 overflow-hidden">
              <NexusLogo size="sm" />
            </div>
          ) : (
            <div className="w-full flex justify-center">
              <span className="font-display font-black text-2xl text-nexus-yellow">N</span>
            </div>
          )}

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={collapsed ? 'Expandir menu' : 'Recolher menu'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Role Banner */}
        <div className="px-4 py-3 border-b border-slate-800/60 bg-slate-950/20">
          <div
            className={`flex items-center gap-2.5 px-3 py-2 rounded-xl border ${
              roleInfo.bg
            } ${collapsed ? 'justify-center px-2' : ''}`}
          >
            <RoleIcon className="w-4 h-4 shrink-0" />
            {!collapsed && (
              <div className="flex flex-col overflow-hidden">
                <span className="text-xs font-bold uppercase tracking-wider truncate">
                  {roleInfo.label}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Menu List */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6 custom-scrollbar">
          {menuGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              {group.groupTitle && !collapsed && (
                <div className="px-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  {group.groupTitle}
                </div>
              )}

              {group.items.map((item, iIdx) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={iIdx}
                    to={item.path}
                    onClick={onCloseMobile}
                    className={({ isActive }) =>
                      `group flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 relative ${
                        isActive
                          ? 'bg-nexus-blue/15 text-white border border-nexus-blue/40 shadow-sm'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80 border border-transparent'
                      } ${collapsed ? 'justify-center px-0' : ''}`
                    }
                    title={collapsed ? item.title : undefined}
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <div className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-nexus-yellow rounded-r-full" />
                        )}
                        <Icon
                          className={`w-4 h-4 shrink-0 transition-colors ${
                            isActive
                              ? 'text-nexus-yellow'
                              : 'text-slate-400 group-hover:text-slate-200'
                          }`}
                        />
                        {!collapsed && (
                          <div className="flex-1 flex items-center justify-between overflow-hidden">
                            <span className="truncate">{item.title}</span>
                            {renderBadge(item)}
                          </div>
                        )}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Bottom Profile & Logout Footer */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          <div
            className={`flex items-center gap-3 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 ${
              collapsed ? 'justify-center p-2' : ''
            }`}
          >
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue flex items-center justify-center font-bold text-sm text-white shrink-0 shadow-md">
              {user?.nome ? user.nome.charAt(0).toUpperCase() : 'U'}
            </div>

            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-white truncate">
                  {user ? `${user.nome} ${user.sobrenome || ''}`.trim() : 'Usuário NEXUS'}
                </p>
                <p className="text-[11px] text-slate-400 truncate">
                  {user?.email || 'conectado'}
                </p>
              </div>
            )}

            <button
              onClick={handleLogout}
              className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Encerrar sessão"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
