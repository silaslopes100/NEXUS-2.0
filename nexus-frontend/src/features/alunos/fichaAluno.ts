import type React from 'react';
import { normalizeUserRole } from '@/stores/authStore';

/** Destino do botão "Voltar" da ficha, passado no `state` da navegação. */
export type VoltarPara = { to: string; rotulo: string };

export const estadoVoltar = (to: string, rotulo: string) => ({ voltar: { to, rotulo } });

/** Lê o destino do "Voltar" do `state`; sem um destino válido (rota interna), usa o padrão. */
export const voltarDoEstado = (state: unknown, padrao: VoltarPara): VoltarPara => {
  const voltar = (state as { voltar?: Partial<VoltarPara> } | null)?.voltar;
  return voltar && typeof voltar.to === 'string' && voltar.to.startsWith('/') && typeof voltar.rotulo === 'string'
    ? { to: voltar.to, rotulo: voltar.rotulo }
    : padrao;
};

/**
 * Ficha cadastral de um aluno conforme o perfil de quem abre:
 * admin → ficha completa e editável do usuário; Polo/Escola → ficha somente leitura
 * da própria área (o backend restringe à unidade). Outros perfis não abrem ficha.
 */
export const rotaFichaAluno = (
  perfil: string | null | undefined,
  aluno: { id: string; usuario_id?: string | null },
): string | null => {
  const papel = normalizeUserRole(perfil);
  if (papel === 'admin') return aluno.usuario_id ? `/admin/usuarios/${aluno.usuario_id}` : null;
  if (papel === 'polo' || papel === 'escola') return aluno.id ? `/${papel}/alunos/${aluno.id}/ficha` : null;
  return null;
};

/** Cliques em botões/links dentro de uma linha clicável não devem abrir a ficha. */
export const cliqueEmControle = (event: React.MouseEvent) =>
  Boolean((event.target as HTMLElement).closest('button, a, input, select, label'));
