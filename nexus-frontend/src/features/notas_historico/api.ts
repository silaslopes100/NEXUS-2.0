import { apiClient } from '@/api/client';

export interface Nota {
  id: string;
  aluno_id: string;
  aluno_nome?: string | null;
  disciplina_id?: string | null;
  disciplina_nome?: string | null;
  turma_id?: string | null;
  turma_nome?: string | null;
  origem: 'ava' | 'manual' | string;
  valor: number;
  lancado_por?: string | null;
  lancado_em?: string | null;
  atualizado_em?: string | null;
}

export interface AdminNota extends Nota {
  aluno_email?: string | null;
  aluno_matricula?: string | null;
  aluno_cpf?: string | null;
}

export interface AdminNotaListResponse {
  items: AdminNota[];
  total: number;
  limit: number;
  offset: number;
}

export interface NotaCreate {
  aluno_id: string;
  disciplina_id: string;
  turma_id: string;
  origem?: 'ava' | 'manual';
  valor: number;
}

export interface HistoricoItem {
  id?: string | null;
  aluno_id: string;
  disciplina_id?: string | null;
  disciplina_nome?: string | null;
  curso_id?: string | null;
  curso_nome?: string | null;
  nota_final?: number | null;
  status: string;
  eh_extra_grade: boolean;
}

export const notasHistoricoApi = {
  listarNotas: async (params?: {
    aluno_id?: string;
    disciplina_id?: string;
    turma_id?: string;
  }): Promise<Nota[]> => {
    const { data } = await apiClient.get<Nota[]>('/notas-historico/notas', { params });
    return data;
  },

  listarNotasAdmin: async (params?: {
    q?: string;
    aluno_id?: string;
    disciplina_id?: string;
    disciplina_nome?: string;
    limit?: number;
    offset?: number;
  }): Promise<AdminNotaListResponse> => {
    const { data } = await apiClient.get<AdminNotaListResponse>('/notas-historico/notas/admin', {
      params: { limit: 30, ...params },
    });
    return data;
  },

  lancarNota: async (payload: NotaCreate): Promise<Nota> => {
    const { data } = await apiClient.post<Nota>('/notas-historico/notas', payload);
    return data;
  },

  corrigirNota: async (notaId: string, valor: number): Promise<Nota> => {
    const { data } = await apiClient.put<Nota>(`/notas-historico/notas/${notaId}`, { valor });
    return data;
  },

  meuHistorico: async (): Promise<HistoricoItem[]> => {
    const { data } = await apiClient.get<HistoricoItem[]>('/notas-historico/historico/me');
    return data;
  },

  baixarMeuHistoricoPdf: async (): Promise<Blob> => {
    const { data } = await apiClient.get<Blob>('/notas-historico/historico/me/pdf', {
      responseType: 'blob',
    });
    return data;
  },
};

export const mensagemErroNotas = (err: unknown, fallback: string): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const mensagens = detail
      .map((item: { msg?: string }) => item.msg)
      .filter((message): message is string => Boolean(message));
    if (mensagens.length) return mensagens.join('; ');
  }
  return fallback;
};
