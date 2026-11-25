import { apiClient } from '@/api/client';

export interface Turma {
  id: string;
  curso_id?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
  nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
  curso_nome?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
  total_alunos: number;
}

export interface TurmaInput {
  nome: string;
  curso_id: string | null;
  polo_id: string | null;
  escola_id: string | null;
  data_inicio: string | null;
  data_fim: string | null;
}

export interface TurmasPagina {
  items: Turma[];
  total: number;
  limit: number;
  offset: number;
}

export interface AlunoTurma {
  aluno_id: string;
  nome?: string | null;
  email?: string | null;
  numero_matricula?: string | null;
  status?: string | null;
  data_matricula?: string | null;
}

export interface AlunosTurmaPagina {
  items: AlunoTurma[];
  total: number;
  limit: number;
  offset: number;
}

export const turmasApi = {
  listarPaginado: async (params: {
    q?: string;
    curso_id?: string;
    escola_id?: string;
    limit: number;
    offset: number;
  }): Promise<TurmasPagina> => {
    const { data } = await apiClient.get<TurmasPagina>('/turmas/paginadas', { params });
    return data;
  },

  criar: async (payload: TurmaInput): Promise<Turma> => {
    const { data } = await apiClient.post<Turma>('/turmas', payload);
    return data;
  },

  atualizar: async (turmaId: string, payload: TurmaInput): Promise<Turma> => {
    const { data } = await apiClient.put<Turma>(`/turmas/${turmaId}`, payload);
    return data;
  },

  excluir: async (turmaId: string): Promise<void> => {
    await apiClient.delete(`/turmas/${turmaId}`);
  },

  listarAlunos: async (turmaId: string): Promise<AlunosTurmaPagina> => {
    const { data } = await apiClient.get<AlunosTurmaPagina>(`/turmas/${turmaId}/alunos`, {
      params: { limit: 200 },
    });
    return data;
  },

  buscarAlunosDisponiveis: async (turmaId: string, q: string): Promise<AlunoTurma[]> => {
    const { data } = await apiClient.get<AlunoTurma[]>(`/turmas/${turmaId}/alunos-disponiveis`, {
      params: { q: q || undefined },
    });
    return data;
  },

  matricularAluno: async (turmaId: string, alunoId: string): Promise<void> => {
    await apiClient.post(`/turmas/${turmaId}/matricular-aluno`, null, {
      params: { aluno_id: alunoId },
    });
  },

  removerAluno: async (turmaId: string, alunoId: string): Promise<void> => {
    await apiClient.delete(`/turmas/${turmaId}/alunos/${alunoId}`);
  },

};

/** Formata 'AAAA-MM-DD' sem passar por Date, evitando deslocamento de fuso. */
export const formatarData = (valor?: string | null): string => {
  if (!valor) return '—';
  const [ano, mes, dia] = valor.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
};
