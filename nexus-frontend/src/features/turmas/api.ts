import { apiClient } from '@/api/client';

export type SituacaoTurma = 'planejada' | 'em_andamento' | 'concluida' | 'cancelada';
export type ModalidadeTurma = 'presencial' | 'ead';
export type TurnoTurma = 'manha' | 'tarde' | 'noite' | 'integral';

export interface Turma {
  id: string;
  codigo?: string | null;
  curso_id?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
  nome: string;
  modalidade?: ModalidadeTurma;
  data_inicio?: string | null;
  data_fim?: string | null;
  situacao?: SituacaoTurma;
  curso_nome?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
  calendario_nome?: string | null;
  total_alunos: number;
  turno?: TurnoTurma | null;
  horario_inicio?: string | null;
  horario_fim?: string | null;
  vagas?: number | null;
  local_aulas?: string | null;
  responsavel_id?: string | null;
  responsavel_nome?: string | null;
  concluida_em?: string | null;
  cancelada_em?: string | null;
  motivo_cancelamento?: string | null;
  periodo_encerrado?: boolean;
  andamento_pct?: number | null;
}

/** Início e fim não são enviados: vêm da vigência do calendário do curso. */
export interface TurmaInput {
  nome: string;
  curso_id: string;
  polo_id: string | null;
  escola_id: string | null;
  modalidade: ModalidadeTurma;
  turno: TurnoTurma | null;
  horario_inicio: string | null;
  horario_fim: string | null;
  vagas: number | null;
  local_aulas: string | null;
  responsavel_id: string | null;
}

export interface TurmasPagina {
  items: Turma[];
  total: number;
  limit: number;
  offset: number;
}

export interface FiltrosTurmas {
  q?: string;
  curso_id?: string;
  polo_id?: string;
  escola_id?: string;
  situacao?: SituacaoTurma;
  modalidade?: ModalidadeTurma;
  ano?: number;
}

export interface SugestaoTurma {
  codigo: string;
  nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
  calendario_nome?: string | null;
}

export interface ResponsavelTurma {
  id: string;
  nome: string;
  perfil: string;
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

export type SituacaoPrazoEad = 'aguardando' | 'liberada' | 'concluida' | 'vencida';

export interface PrazoDisciplinaEad {
  disciplina_id: string;
  nome?: string | null;
  ordem: number;
  prazo_dias: number;
  liberada_em?: string | null;
  data_limite?: string | null;
  concluida_em?: string | null;
  situacao: SituacaoPrazoEad;
}

export interface PrazosEad {
  turma_id: string;
  regras: Record<string, string | number>;
  disciplinas: { disciplina_id: string; nome?: string | null; prazo_dias: number }[];
  alunos: {
    aluno_id: string;
    nome?: string | null;
    numero_matricula?: string | null;
    inicio: string;
    vencidas: number;
    disciplinas: PrazoDisciplinaEad[];
  }[];
}

export const ROTULO_SITUACAO_TURMA: Record<SituacaoTurma, string> = {
  planejada: 'Planejada',
  em_andamento: 'Em andamento',
  concluida: 'Concluída',
  cancelada: 'Cancelada',
};

export const ROTULO_TURNO: Record<TurnoTurma, string> = {
  manha: 'Manhã',
  tarde: 'Tarde',
  noite: 'Noite',
  integral: 'Integral',
};

export const ROTULO_MODALIDADE: Record<ModalidadeTurma, string> = { presencial: 'Presencial', ead: 'EAD' };

export const somenteLeitura = (t?: Pick<Turma, 'situacao'> | null) =>
  t?.situacao === 'concluida' || t?.situacao === 'cancelada';

export const turmasApi = {
  listarPaginado: async (params: FiltrosTurmas & { limit: number; offset: number }): Promise<TurmasPagina> => {
    const { data } = await apiClient.get<TurmasPagina>('/turmas/paginadas', { params });
    return data;
  },

  obter: async (turmaId: string): Promise<Turma> => {
    const { data } = await apiClient.get<Turma>(`/turmas/${turmaId}`);
    return data;
  },

  sugestao: async (params: {
    curso_id: string; modalidade: ModalidadeTurma; polo_id?: string; escola_id?: string;
  }): Promise<SugestaoTurma> => {
    const { data } = await apiClient.get<SugestaoTurma>('/turmas/sugestao', { params });
    return data;
  },

  responsaveis: async (params: { polo_id?: string; escola_id?: string }): Promise<ResponsavelTurma[]> => {
    const { data } = await apiClient.get<ResponsavelTurma[]>('/turmas/responsaveis-possiveis', { params });
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

  cancelar: async (turmaId: string, motivo: string): Promise<Turma> => {
    const { data } = await apiClient.post<Turma>(`/turmas/${turmaId}/cancelar`, { motivo });
    return data;
  },

  reabrir: async (turmaId: string): Promise<Turma> => {
    const { data } = await apiClient.post<Turma>(`/turmas/${turmaId}/reabrir`);
    return data;
  },

  prazosEad: async (turmaId: string): Promise<PrazosEad> => {
    const { data } = await apiClient.get<PrazosEad>(`/turmas/${turmaId}/prazos-ead`);
    return data;
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

export const formatarHora = (valor?: string | null): string => (valor ? valor.slice(0, 5) : '');
