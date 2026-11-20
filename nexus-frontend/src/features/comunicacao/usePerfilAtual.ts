import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { UserRole } from '@/types/auth';
import { PERFIS_PUBLICAR } from './api';

/** Quem está logado e o que pode fazer no Feed. */
export const usePerfilAtual = () => {
  const { user, perfil } = useAuthStore();
  const papel: UserRole = normalizeUserRole(perfil?.nome || user?.perfil?.nome) || 'aluno';
  return {
    user,
    userId: user?.id ?? '',
    nome: [user?.nome, user?.sobrenome].filter(Boolean).join(' '),
    papel,
    admin: papel === 'admin',
    podePublicar: PERFIS_PUBLICAR.includes(papel),
    /** Rota da tela de moderação do perfil. */
    rotaModeracao: papel === 'admin' ? '/admin/feed/moderacao' : '/feed/moderacao',
  };
};
