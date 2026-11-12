import { apiClient } from '@/api/client';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  Professor,
  ProfessorCreate,
  ProfessorDetalhe,
  ProfessorConteudoItem,
  ProfessorConteudosResponse,
  ProfessorDisciplinaListResponse,
  ProfessorMaterialResumo,
  ProfessorListResponse,
  ProfessorTurmaVinculo,
  ProfessorTurmaVinculosResponse,
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

  detalhe: async (id: string): Promise<ProfessorDetalhe> => {
    const { data } = await apiClient.get<ProfessorDetalhe>(`/professores/${id}/detalhe`);
    return data;
  },

  minhasDisciplinas: async (): Promise<ProfessorDisciplinaListResponse> => {
    const { data } = await apiClient.get<ProfessorDisciplinaListResponse>(
      '/professores/me/disciplinas'
    );
    return data;
  },

  listarVinculosTurma: async (turmaId: string): Promise<ProfessorTurmaVinculo[]> => {
    const { data } = await apiClient.get<ProfessorTurmaVinculosResponse>(
      `/professores/turmas/${turmaId}/vinculos`
    );
    return data.items;
  },

  vincularProfessorTurma: async (
    turmaId: string,
    professorId: string,
    disciplinaId: string
  ): Promise<ProfessorTurmaVinculo> => {
    const { data } = await apiClient.post<ProfessorTurmaVinculo>(
      `/professores/turmas/${turmaId}/vinculos`,
      { professor_id: professorId, disciplina_id: disciplinaId }
    );
    return data;
  },

  arquivarVinculoTurma: async (turmaId: string, vinculoId: string): Promise<string> => {
    const { data } = await apiClient.delete<{ message: string }>(
      `/professores/turmas/${turmaId}/vinculos/${vinculoId}`
    );
    return data.message;
  },

  meusConteudos: async (): Promise<ProfessorConteudosResponse> => {
    const { data } = await apiClient.get<ProfessorConteudosResponse>(
      '/professores/me/conteudos'
    );
    return data;
  },

  criarConteudo: async (form: FormData): Promise<ProfessorConteudoItem> => {
    const { data } = await apiClient.post<ProfessorConteudoItem>(
      '/professores/me/conteudos',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  atualizarConteudo: async (id: string, form: FormData): Promise<ProfessorConteudoItem> => {
    const { data } = await apiClient.put<ProfessorConteudoItem>(
      `/professores/me/conteudos/${id}`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  criarMaterial: async (form: FormData): Promise<ProfessorMaterialResumo> => {
    const { data } = await apiClient.post<ProfessorMaterialResumo>(
      '/professores/me/materiais',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  atualizarMaterial: async (id: string, form: FormData): Promise<ProfessorMaterialResumo> => {
    const { data } = await apiClient.put<ProfessorMaterialResumo>(
      `/professores/me/materiais/${id}`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },

  baixarConteudo: async (id: string): Promise<Blob> => {
    const { data } = await apiClient.get<Blob>(
      `/professores/me/conteudos/${id}/arquivo`,
      { responseType: 'blob' }
    );
    return data;
  },

  baixarMaterial: async (id: string): Promise<Blob> => {
    const { data } = await apiClient.get<Blob>(
      `/professores/me/materiais/${id}/arquivo`,
      { responseType: 'blob' }
    );
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
