import { apiClient } from '@/api/client';

export interface PresencaVinculo {
  id: string;
  disciplina_id: string;
  turma_id: string;
  disciplina_nome?: string | null;
  turma_nome?: string | null;
  professor_nome?: string | null;
}

export interface AlunoChamada {
  aluno_id: string;
  nome: string;
  numero_matricula?: string | null;
  presente: boolean | null;
}

export interface ChamadaInput {
  professor_disciplina_id: string;
  data_aula: string;
  numero_aula: number;
  presencas: Array<{ aluno_id: string; presente: boolean }>;
}

export interface ChamadaResponse {
  professor_disciplina_id: string;
  data_aula: string;
  numero_aula: number;
  presencas: Array<{ id: string; aluno_id: string; presente: boolean }>;
}

export const presencasApi = {
  listarVinculos: async (): Promise<PresencaVinculo[]> => {
    const { data } = await apiClient.get<PresencaVinculo[]>('/presencas/vinculos');
    return data;
  },

  listarAlunos: async (
    vinculoId: string,
    dataAula: string,
    numeroAula: number
  ): Promise<AlunoChamada[]> => {
    const { data } = await apiClient.get<AlunoChamada[]>(
      `/presencas/vinculos/${vinculoId}/alunos`,
      { params: { data_aula: dataAula, numero_aula: numeroAula } }
    );
    return data;
  },

  salvarChamada: async (payload: ChamadaInput): Promise<ChamadaResponse> => {
    const { data } = await apiClient.put<ChamadaResponse>('/presencas/chamadas', payload);
    return data;
  },
};
