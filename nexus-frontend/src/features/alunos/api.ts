import { apiClient } from '@/api/client';

export type Modalidade = 'polo' | 'escola' | 'ead';

export interface AlunoItem {
  id: string;
  usuario_id?: string | null;
  numero_matricula?: string | null;
  data_nascimento?: string | null;
  nome: string;
  sobrenome?: string | null;
  email?: string | null;
  cpf?: string | null;
  escola_id?: string | null;
  modalidade: Modalidade;
  status: string;
  quantidade_presencas: number;
  percentual_presenca: number;
  convite_enviado?: boolean | null;
}

export interface AlunoListResponse {
  total: number;
  items: AlunoItem[];
  limit: number;
  offset: number;
}

export interface AlunoCreatePayload {
  nome: string;
  sobrenome?: string;
  cpf: string;
  email: string;
  data_nascimento: string;
  modalidade: Modalidade;
  escola_id?: string | null;
}

export interface EscolaOption {
  id: string;
  nome: string;
}

export interface TurmaItem {
  id: string;
  escola_id: string;
  nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
  total_alunos: number;
}

export interface TurmaCreatePayload {
  nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
}

export const alunosApi = {
  listar: async (
    poloId: string,
    params: { q?: string; escola_id?: string; status?: string; limit?: number; offset?: number }
  ): Promise<AlunoListResponse> => {
    const { data } = await apiClient.get(`/polos/${poloId}/alunos`, { params });
    return data;
  },

  criar: async (poloId: string, payload: AlunoCreatePayload): Promise<AlunoItem> => {
    const { data } = await apiClient.post(`/polos/${poloId}/alunos`, payload);
    return data;
  },

  listarEscolas: async (poloId: string): Promise<EscolaOption[]> => {
    const { data } = await apiClient.get(`/polos/${poloId}/escolas`, { params: { limit: 200 } });
    return data.items ?? [];
  },

  listarPolos: async (): Promise<EscolaOption[]> => {
    const { data } = await apiClient.get('/polos', { params: { limit: 200 } });
    return data.items ?? [];
  },

  listarTurmasEscola: async (escolaId: string): Promise<{ total: number; items: TurmaItem[] }> => {
    const { data } = await apiClient.get(`/escolas/${escolaId}/turmas`, { params: { limit: 200 } });
    return data;
  },

  criarTurmaEscola: async (escolaId: string, payload: TurmaCreatePayload): Promise<TurmaItem> => {
    const { data } = await apiClient.post(`/escolas/${escolaId}/turmas`, payload);
    return data;
  },
};

export const apiErrorMessage = (err: unknown, fallback: string): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || fallback;
  return fallback;
};
