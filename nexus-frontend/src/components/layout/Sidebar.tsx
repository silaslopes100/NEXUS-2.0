import React, { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { menuByRole, MenuItem, MenuGroup } from '@/components/navigation/menuConfig';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { UserRole } from '@/types/auth';
import {
  LogOut,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from 'lucide-react';
import { authApi } from '@/features/auth/api';
import { UsuarioAvatarProprio } from '@/components/layout/UsuarioAvatarProprio';
import { estagiosApi } from '@/features/estagios/api';
import { PERFIS_PUBLICAR, feedApi } from '@/features/comunicacao/api';

const INTERVALO_CONTADORES_MS = 60_000;

/**
 * Contadores numéricos do menu (por caminho): solicitações de estágio em análise (Admin),
 * avaliações de estágio ainda não vistas (Aluno) e comentários do feed aguardando moderação
 * (Admin: todos; demais publicadores: os das próprias publicações). Atualiza a cada 60 s e no evento
 * `nexus:contadores-menu`, disparado pelas telas depois de uma ação.
 */
const useContadoresMenu = (perfil: UserRole, comAreaAluno: boolean, ativo: boolean) => {
  const [contadores, setContadores] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!ativo) return;
    let vivo = true;
    const atualizar = () => {
      if (document.hidden) return;
      if (perfil === 'admin') {
        estagiosApi.resumoAdmin()
          .then((r) => vivo && setContadores((c) => ({ ...c, '/admin/estagios': r.pendentes })))
          .catch(() => undefined);
      }
      if (PERFIS_PUBLICAR.includes(perfil)) {
        const rota = perfil === 'admin' ? '/admin/feed/moderacao' : '/feed/moderacao';
        feedApi.resumoModeracao()
          .then((r) => vivo && setContadores((c) => ({ ...c, [rota]: r.pendentes })))
          .catch(() => undefined);
      }
      if (perfil === 'aluno' || comAreaAluno) {
        estagiosApi.resumoAluno()
          .then((r) => vivo && setContadores((c) => ({ ...c, '/aluno/estagio': r.pendentes })))
          .catch(() => undefined);
      }
    };
    atualizar();
    const id = window.setInterval(atualizar, INTERVALO_CONTADORES_MS);
    window.addEventListener('nexus:contadores-menu', atualizar);
    return () => {
      vivo = false;
      window.clearInterval(id);
      window.removeEventListener('nexus:contadores-menu', atualizar);
    };
  }, [perfil, comAreaAluno, ativo]);
  return contadores;
};

interface SidebarProps {
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
  /** Menu recolhido no desktop (o estado mora no AppLayout, que ajusta o espaçamento do conteúdo). */
  recolhido?: boolean;
  onAlternarRecolhido?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isMobileOpen = false,
  onCloseMobile,
  recolhido = false,
  onAlternarRecolhido,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, perfil, logout, refreshToken, viaLicenca } = useAuthStore();
  // Na gaveta do celular o menu aparece sempre completo.
  const collapsed = recolhido && !isMobileOpen;

  // Gaveta aberta no celular: trava a rolagem do fundo, fecha com Esc e com um deslize para a esquerda.
  useEffect(() => {
    if (!isMobileOpen) return;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const aoTeclar = (e: KeyboardEvent) => { if (e.key === 'Escape') onCloseMobile?.(); };
    window.addEventListener('keydown', aoTeclar);
    return () => {
      document.body.style.overflow = anterior;
      window.removeEventListener('keydown', aoTeclar);
    };
  }, [isMobileOpen, onCloseMobile]);
  const [toqueX, setToqueX] = useState<number | null>(null);
  const [areaAlunoAberta, setAreaAlunoAberta] = useState(() =>
    location.pathname.startsWith('/aluno/')
  );

  const activeRole: UserRole =
    normalizeUserRole(perfil?.nome || user?.perfil?.nome) || 'aluno';

  // Entrou pelo número da licença: só a prova e as notas (sem perfil, compras etc.).
  const ROTAS_LICENCA = ['/aluno/disciplinas', '/aluno/historico'];
  // Itens do AVA (somenteEad) só aparecem para o aluno EAD.
  const alunoEad = !!user?.aluno_ead && !user?.tambem_aluno;
  const menuBase: MenuGroup[] = (menuByRole[activeRole] || menuByRole.aluno)
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => (!item.somenteEad || alunoEad) && !(item.ocultarEad && alunoEad)),
    }))
    .filter((group) => group.items.length > 0);
  const menuGroups: MenuGroup[] = viaLicenca
    ? menuBase
        .map((group) => ({ ...group, items: group.items.filter((item) => ROTAS_LICENCA.includes(item.path)) }))
        .filter((group) => group.items.length > 0)
    : menuBase;

  // Chat e Mural já existem nos menus de Polo e Escola; aqui entram só as telas próprias do aluno.
  const itensAreaAluno: MenuItem[] = user?.tambem_aluno
    ? menuByRole.aluno.flatMap((group) => group.items).filter((item) => item.path.startsWith('/aluno/') && !item.somenteEad)
    : [];

  const contadores = useContadoresMenu(activeRole, !!user?.tambem_aluno, !!user && !viaLicenca);

  const handleLogout = async () => {
    try {
      await authApi.logout(refreshToken);
    } catch (e) {
      // Limpeza local mesmo se a requisição falhar
    }
    // Vai para o login antes de limpar a sessão: assim os guards não guardam a tela atual como
    // "rota pretendida" (o próximo usuário, de outro perfil, cairia nela com "Acesso Não Autorizado").
    navigate('/auth/login', { replace: true, state: null });
    logout();
  };

  const renderBadge = (item: MenuItem) => {
    const total = item.contador ? contadores[item.path] || 0 : 0;
    if (total > 0) {
      return (
        <span className="min-w-[20px] rounded-full bg-amber-500 px-1.5 py-0.5 text-center text-[10px] font-bold text-slate-950">
          {total > 99 ? '99+' : total}
        </span>
      );
    }
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

  const renderMenuItem = (item: MenuItem) => {
    const Icon = item.icon;
    return (
      <NavLink
        key={item.path}
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
            {collapsed && item.contador && (contadores[item.path] || 0) > 0 && (
              <span className="absolute right-3 top-1.5 h-2 w-2 rounded-full bg-amber-400" />
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
        onTouchStart={(e) => isMobileOpen && setToqueX(e.touches[0].clientX)}
        onTouchEnd={(e) => {
          if (toqueX !== null && toqueX - e.changedTouches[0].clientX > 60) onCloseMobile?.();
          setToqueX(null);
        }}
        className={`fixed top-0 left-0 bottom-0 z-50 flex max-w-[85vw] flex-col glass-panel border-r border-slate-800/80 pb-safe pt-safe transition-all duration-300 ease-in-out ${
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
            onClick={() => onAlternarRecolhido?.()}
            className="hidden lg:flex p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={collapsed ? 'Expandir menu' : 'Recolher menu'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
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

              {group.items.map(renderMenuItem)}
            </div>
          ))}

          {itensAreaAluno.length > 0 && (
            <div className="space-y-1 border-t border-slate-800/80 pt-4">
              <button
                type="button"
                aria-expanded={areaAlunoAberta}
                title={collapsed ? 'Área do Aluno' : undefined}
                onClick={() => setAreaAlunoAberta((aberta) => !aberta)}
                className={`flex w-full items-center gap-3 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3.5 py-2.5 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20 ${
                  collapsed ? 'justify-center px-0' : ''
                }`}
              >
                <BookOpen className="w-4 h-4 shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1 truncate text-left">Área do Aluno</span>
                    <ChevronDown
                      className={`w-4 h-4 shrink-0 transition-transform ${
                        areaAlunoAberta ? 'rotate-180' : ''
                      }`}
                    />
                  </>
                )}
              </button>
              {areaAlunoAberta && itensAreaAluno.map(renderMenuItem)}
            </div>
          )}
        </nav>

        {/* Bottom Profile & Logout Footer */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          <div
            className={`glass flex items-center gap-3 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 ${
              collapsed ? 'justify-center p-2' : ''
            }`}
          >
            <UsuarioAvatarProprio
              usuarioId={user?.id}
              fotoUrl={user?.foto_url}
              nome={user?.nome}
              className="w-9 h-9 rounded-lg bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue flex items-center justify-center font-bold text-sm text-on-accent shrink-0 shadow-md"
            />

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
