import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

/**
 * Áreas do módulo 2.4 que o usuário pode operar (espelha `require_area` no backend):
 * admin opera tudo; o perfil financeiro opera cobrança/status; o perfil logística opera envio/entrega.
 */
export const useAcessoModulo = () => {
  const { perfil, hasPermission } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome);
  const ehAdmin = role === 'admin';
  return {
    ehAdmin,
    financeiro: ehAdmin || role === 'financeiro' || hasPermission('p_financeiro'),
    logistica: ehAdmin || role === 'logistica' || hasPermission('p_logistica'),
  };
};
