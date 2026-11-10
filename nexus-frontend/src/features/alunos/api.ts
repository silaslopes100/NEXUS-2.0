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
};

export type Observacao = 'formado' | 'churn' | 'transferido' | 'revalidado' | 'sem_movimentacao';

export interface AlunoGestao {
  id: string;
  usuario_id: string;
  numero_matricula?: string | null;
  nome: string;
  email?: string | null;
  modalidade?: string | null;
  status: string;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
  turmas: string[];
  percentual_presenca: number;
  ultimo_acesso_em?: string | null;
  disciplinas_em_curso: number;
  observacoes: Observacao[];
  reingresso_polo_destino_id?: string | null;
  reingresso_escola_destino_id?: string | null;
}

export interface AlunoGestaoLista {
  total: number;
  items: AlunoGestao[];
  limit: number;
  offset: number;
}

export interface DisciplinaAcademica {
  id: string;
  nome: string;
  semestre?: number | null;
  carga_horaria?: number | null;
  nota?: number | null;
  situacao: string;
  em_curso: boolean;
  total_conteudos: number;
  conteudos_concluidos: number;
  progresso?: number | null;
}

export interface CursoAcademico {
  id: string;
  nome: string;
  disciplinas: DisciplinaAcademica[];
}

export interface Academico {
  aluno_id: string;
  aluno_nome: string;
  numero_matricula?: string | null;
  cursos: CursoAcademico[];
}

export interface ReingressoPayload {
  modalidade: 'polo' | 'ead';
  polo_destino_id?: string;
  escola_destino_id?: string;
  taxa_confirmada: boolean;
}

export interface ReingressoResultado {
  aluno_id: string;
  numero_matricula: string;
  licencas_debitadas: number;
}

export interface ConteudoAprendizado {
  id: string;
  titulo?: string | null;
  tipo_midia?: string | null;
  url_arquivo?: string | null;
  concluido: boolean;
}

export interface CursoAprendizado {
  id: string;
  nome: string;
  disciplinas: { id: string; nome: string; conteudos: ConteudoAprendizado[] }[];
}

export const alunosGestaoApi = {
  listar: async (params: {
    polo_id?: string;
    escola_id?: string;
    somente_ead?: boolean;
    observacao?: Observacao;
    q?: string;
    limit: number;
    offset: number;
  }): Promise<AlunoGestaoLista> => {
    const { data } = await apiClient.get<AlunoGestaoLista>('/alunos/gestao', { params });
    return data;
  },

  academico: async (alunoId: string): Promise<Academico> => {
    const { data } = await apiClient.get<Academico>(`/alunos/gestao/${alunoId}/academico`);
    return data;
  },

  boletimPdf: async (alunoId: string, cursoId?: string): Promise<Blob> => {
    const { data } = await apiClient.get<Blob>(`/alunos/gestao/${alunoId}/boletim/pdf`, {
      params: cursoId ? { curso_id: cursoId } : undefined,
      responseType: 'blob',
    });
    return data;
  },

  confirmarChurn: async (alunoId: string): Promise<void> => {
    await apiClient.post(`/alunos/gestao/${alunoId}/churn`);
  },

  reingressar: async (
    alunoId: string,
    payload: ReingressoPayload
  ): Promise<ReingressoResultado> => {
    const { data } = await apiClient.post<ReingressoResultado>(
      `/alunos/gestao/${alunoId}/reingresso`,
      payload
    );
    return data;
  },

  aprendizado: async (): Promise<CursoAprendizado[]> => {
    const { data } = await apiClient.get<CursoAprendizado[]>('/alunos/aprendizado');
    return data;
  },

  marcarConteudo: async (conteudoId: string, concluido: boolean): Promise<void> => {
    const url = `/alunos/aprendizado/conteudos/${conteudoId}/concluido`;
    await (concluido ? apiClient.put(url) : apiClient.delete(url));
  },
};

export const apiErrorMessage = (err: unknown, fallback: string): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || fallback;
  return fallback;
};
