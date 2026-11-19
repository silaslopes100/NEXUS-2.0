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

// ---------------------------------------------------------------------------
// Visão do aluno: presenças e frequência (chamadas e atas dos professores)
// ---------------------------------------------------------------------------

export interface AulaFrequencia {
  data_aula?: string | null;
  numero_aula?: number | null;
  presente: boolean;
  conteudo_ministrado?: string | null;
}

export interface DisciplinaFrequencia {
  disciplina_id?: string | null;
  disciplina_nome: string;
  turma_nome?: string | null;
  professor_nome?: string | null;
  total_aulas: number;
  presencas: number;
  faltas: number;
  percentual: number;
  situacao: 'regular' | 'em_risco';
  aulas: AulaFrequencia[];
}

export interface MinhaFrequencia {
  total_aulas: number;
  presencas: number;
  faltas: number;
  percentual: number | null;
  frequencia_minima: number;
  disciplinas: DisciplinaFrequencia[];
}

export const minhasPresencasApi = {
  carregar: async (): Promise<MinhaFrequencia> => {
    const { data } = await apiClient.get<MinhaFrequencia>('/presencas/me');
    return data;
  },
};

export interface OpcaoFrequencia {
  id: string;
  nome: string;
}

/** Frequência de um aluno numa disciplina/turma (visão da unidade). */
export interface FrequenciaAlunoLinha {
  aluno_id: string;
  aluno_nome: string;
  numero_matricula?: string | null;
  escola_nome?: string | null;
  disciplina_id?: string | null;
  disciplina_nome: string;
  turma_id?: string | null;
  turma_nome?: string | null;
  total_aulas: number;
  presencas: number;
  faltas: number;
  percentual: number;
  situacao: 'regular' | 'em_risco';
}

export interface FrequenciaUnidade {
  frequencia_minima: number;
  total_alunos: number;
  alunos_em_risco: number;
  percentual?: number | null;
  disciplinas: OpcaoFrequencia[];
  turmas: OpcaoFrequencia[];
  linhas: FrequenciaAlunoLinha[];
}

export interface FiltrosFrequenciaUnidade {
  disciplina_id?: string;
  turma_id?: string;
  escola_id?: string;
  busca?: string;
  situacao?: '' | 'regular' | 'em_risco';
}

export interface FrequenciaAlunoDetalhe extends MinhaFrequencia {
  aluno_id: string;
  aluno_nome: string;
  numero_matricula?: string | null;
}

export const frequenciaUnidadeApi = {
  carregar: async (filtros: FiltrosFrequenciaUnidade): Promise<FrequenciaUnidade> => {
    const params = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v));
    const { data } = await apiClient.get<FrequenciaUnidade>('/presencas/unidade', { params });
    return data;
  },
  aluno: async (alunoId: string): Promise<FrequenciaAlunoDetalhe> => {
    const { data } = await apiClient.get<FrequenciaAlunoDetalhe>(`/presencas/unidade/alunos/${alunoId}`);
    return data;
  },
};
