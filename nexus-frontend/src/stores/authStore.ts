import { create } from 'zustand';
import { User, Perfil, UserRole } from '@/types/auth';

interface AuthState {
  // Estado em memória (nunca persistido no localStorage)
  user: User | null;
  perfil: Perfil | null;
  permissoes: string[];
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;

  // Ações
  setSession: (
    accessToken: string,
    refreshToken: string,
    user: User,
    perfil?: Perfil | null,
    permissoes?: string[]
  ) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User, perfil?: Perfil | null, permissoes?: string[]) => void;
  setLoading: (isLoading: boolean) => void;
  setInitialized: (isInitialized: boolean) => void;
  logout: () => void;

  // Helpers de verificação de acesso
  hasRole: (roles: UserRole | UserRole[] | string | string[]) => boolean;
  hasPermission: (permission: string) => boolean;
  getDashboardPath: () => string;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  perfil: null,
  permissoes: [],
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  isInitialized: false,

  setSession: (accessToken, refreshToken, user, perfil, permissoes = []) => {
    const activePerfil = perfil || user.perfil || null;
    const activePermissoes = permissoes.length > 0 ? permissoes : user.permissoes || [];

    set({
      accessToken,
      refreshToken,
      user,
      perfil: activePerfil,
      permissoes: activePermissoes,
      isAuthenticated: true,
      isLoading: false,
      isInitialized: true,
    });
  },

  setTokens: (accessToken, refreshToken) => {
    set({
      accessToken,
      refreshToken,
      isAuthenticated: true,
    });
  },

  setUser: (user, perfil, permissoes = []) => {
    const activePerfil = perfil || user.perfil || null;
    const activePermissoes = permissoes.length > 0 ? permissoes : user.permissoes || [];

    set({
      user,
      perfil: activePerfil,
      permissoes: activePermissoes,
      isAuthenticated: true,
    });
  },

  setLoading: (isLoading) => set({ isLoading }),

  setInitialized: (isInitialized) => set({ isInitialized }),

  logout: () => {
    set({
      user: null,
      perfil: null,
      permissoes: [],
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      isInitialized: true,
    });
  },

  hasRole: (roles) => {
    const { perfil } = get();
    if (!perfil || !perfil.nome) return false;

    const currentRole = perfil.nome.toLowerCase().trim();
    if (Array.isArray(roles)) {
      return roles.some((r) => r.toLowerCase().trim() === currentRole);
    }
    return roles.toLowerCase().trim() === currentRole;
  },

  hasPermission: (permission) => {
    const { perfil, permissoes } = get();
    // Admin possui bypass irrestrito
    if (perfil?.nome?.toLowerCase().trim() === 'admin') return true;

    const targetKey = permission.toLowerCase().trim();
    const targetPKey = targetKey.startsWith('p_') ? targetKey : `p_${targetKey}`;

    return permissoes.some((p) => {
      const lower = p.toLowerCase().trim();
      return (
        lower === targetKey ||
        lower === targetPKey ||
        (targetKey.startsWith('p_') && lower === targetKey.replace(/^p_/, ''))
      );
    });
  },

  getDashboardPath: () => {
    const { perfil } = get();
    const role = perfil?.nome?.toLowerCase().trim() || '';

    switch (role) {
      case 'admin':
        return '/admin/dashboard';
      case 'polo':
        return '/polo/dashboard';
      case 'escola':
        return '/escola/dashboard';
      case 'professor':
        return '/professor/dashboard';
      case 'aluno':
        return '/aluno/dashboard';
      default:
        return '/auth/login';
    }
  },
}));
