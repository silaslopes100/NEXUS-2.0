import { apiClient } from '@/api/client';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  Professor,
  ProfessorCreate,
  ProfessorListResponse,
  ProfessorUpdate,
  UnidadeOption,
} from '@/types/professor';

export interface ListProfessoresParams {
  search?: string;
  polo_id?: string;
  escola_id?: string;
  disciplina?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export const professoresApi = {
  listar: async (params?: ListProfessoresParams): Promise<ProfessorListResponse> => {
    const { data } = await apiClient.get<ProfessorListResponse>('/professores/', { params });
    return data;
  },

  obter: async (id: string): Promise<Professor> => {
    const { data } = await apiClient.get<Professor>(`/professores/${id}`);
    return data;
  },

  criar: async (payload: ProfessorCreate): Promise<Professor> => {
    const { data } = await apiClient.post<Professor>('/professores/', payload);
    return data;
  },

  atualizar: async (id: string, payload: ProfessorUpdate): Promise<Professor> => {
    const { data } = await apiClient.put<Professor>(`/professores/${id}`, payload);
    return data;
  },

  excluir: async (id: string): Promise<void> => {
    await apiClient.delete(`/professores/${id}`);
  },

  // Opções de filtro/cadastro (endpoints do módulo polos_escolas)
  listarPolos: async (): Promise<UnidadeOption[]> => {
    const data = await polosEscolasApi.listarPolos({ limit: 200 });
    return (data?.items ?? []) as UnidadeOption[];
  },

  listarEscolasDoPolo: async (poloId: string): Promise<UnidadeOption[]> => {
    const data = await polosEscolasApi.listarEscolasDoPolo(poloId);
    return (data?.items ?? []) as UnidadeOption[];
  },
};

export const apiErrorMessage = (err: unknown, fallback: string): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || fallback;
  }
  return fallback;
};
