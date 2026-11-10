import { apiClient } from '@/api/client';

export type TipoTransferencia = 'troca_polo' | 'polo_para_ead' | 'ead_para_polo' | 'reingresso';
export type StatusTransferencia = 'pendente' | 'aprovada' | 'rejeitada' | 'churn';
export type EscopoTransferencia = 'aluno' | undefined;

export interface Transferencia {
  id: string;
  aluno_id?: string | null;
  aluno_nome?: string | null;
  numero_matricula?: string | null;
  tipo: TipoTransferencia;
  status: StatusTransferencia;
  polo_origem_nome?: string | null;
  escola_origem_nome?: string | null;
  polo_destino_nome?: string | null;
  escola_destino_nome?: string | null;
  modalidade_origem?: string | null;
  modalidade_destino?: string | null;
  solicitado_por_nome?: string | null;
  observacao?: string | null;
  motivo_rejeicao?: string | null;
  alerta_churn: boolean;
  resolvido_em?: string | null;
  criado_em?: string | null;
}

export interface TransferenciaLista {
  total: number;
  items: Transferencia[];
  limit: number;
  offset: number;
}

export interface PendenciasResumo {
  total: number;
  items: Transferencia[];
}

export interface AlunoElegivel {
  id: string;
  nome: string;
  numero_matricula?: string | null;
  modalidade?: string | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
}

export interface Opcao {
  id: string;
  nome: string;
}

export interface TransferenciaInput {
  aluno_id?: string;
  tipo: TipoTransferencia;
  polo_destino_id?: string;
  escola_destino_id?: string;
  observacao?: string;
}

export interface TransferenciaDecisao {
  aprovado: boolean;
  motivo?: string;
  confirmar_churn?: boolean;
}

export const tipoLabel: Record<TipoTransferencia, string> = {
  troca_polo: 'Troca de Polo',
  polo_para_ead: 'Migração de Modalidade: Polo → EAD',
  ead_para_polo: 'Migração de Modalidade: EAD → Polo',
  reingresso: 'Reingresso (Churn)',
};

export const transferenciasApi = {
  listar: async (params: {
    status?: StatusTransferencia;
    tipo?: TipoTransferencia;
    q?: string;
    escopo?: EscopoTransferencia;
    limit: number;
    offset: number;
  }): Promise<TransferenciaLista> => {
    const { data } = await apiClient.get<TransferenciaLista>('/transferencias', { params });
    return data;
  },

  solicitar: async (
    payload: TransferenciaInput,
    escopo?: EscopoTransferencia
  ): Promise<Transferencia> => {
    const { data } = await apiClient.post<Transferencia>('/transferencias', payload, {
      params: { escopo },
    });
    return data;
  },

  resolver: async (id: string, payload: TransferenciaDecisao): Promise<Transferencia> => {
    const { data } = await apiClient.put<Transferencia>(`/transferencias/${id}/resolver`, payload);
    return data;
  },

  meuCadastro: async (): Promise<AlunoElegivel> => {
    const { data } = await apiClient.get<AlunoElegivel>('/transferencias/meu-cadastro');
    return data;
  },

  buscarAlunos: async (q: string, desistentes = false): Promise<AlunoElegivel[]> => {
    const { data } = await apiClient.get<AlunoElegivel[]>('/transferencias/alunos', {
      params: { q, desistentes: desistentes || undefined },
    });
    return data;
  },

  polos: async (): Promise<Opcao[]> => {
    const { data } = await apiClient.get<Opcao[]>('/transferencias/opcoes/polos');
    return data;
  },

  escolas: async (poloId: string): Promise<Opcao[]> => {
    const { data } = await apiClient.get<Opcao[]>(`/transferencias/opcoes/polos/${poloId}/escolas`);
    return data;
  },

  resumoPendentes: async (): Promise<PendenciasResumo> => {
    const { data } = await apiClient.get<PendenciasResumo>('/transferencias/pendentes/resumo');
    return data;
  },
};

export const transferenciasErro = (error: unknown, fallback: string): string => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('; ') || fallback;
  }
  return fallback;
};
