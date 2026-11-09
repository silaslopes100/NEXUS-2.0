import { apiClient } from '@/api/client';

export type NivelAcademico =
  | 'bacharelado'
  | 'licenciatura'
  | 'tecnologo'
  | 'pos_graduacao'
  | 'mestrado'
  | 'curso_livre';

// 'polo' e 'inativo' existem apenas em cursos importados do legado.
export type ModalidadeCurso = 'hibrido' | 'presencial' | 'ead' | 'polo';
export type StatusCurso = 'ativo' | 'cancelado' | 'inativo';

export interface Curso {
  id: string;
  nome: string;
  descricao?: string | null;
  nivel_academico?: NivelAcademico | null;
  modalidade?: ModalidadeCurso | null;
  carga_horaria_total?: number | null;
  semestres?: number | null;
  status?: StatusCurso | null;
}

export interface CursosPagina {
  items: Curso[];
  total: number;
  limit: number;
  offset: number;
}

export interface CursoCreate {
  nome: string;
  descricao: string;
  nivel_academico: NivelAcademico;
  modalidade: ModalidadeCurso;
  carga_horaria_total: number;
  semestres: number;
  status: StatusCurso;
  disciplina_ids: string[];
}

// Sem disciplina_ids, a API mantém os vínculos atuais do curso.
export type CursoUpdate = Omit<CursoCreate, 'disciplina_ids'> & { disciplina_ids?: string[] };

export interface Disciplina {
  id: string;
  curso_id?: string | null;
  nome: string;
  semestre?: number | null;
  ordem: number;
  carga_horaria?: number | null;
  qtd_aulas_prevista?: number | null;
  tipo?: string;
  eh_extra_grade?: boolean;
}

export interface DisciplinaInput {
  curso_id: string | null;
  semestre: number | null;
  nome: string;
  ordem: number;
  carga_horaria: number | null;
  qtd_aulas_prevista: number | null;
  tipo: string;
  eh_extra_grade: boolean;
}

export interface Turma {
  id: string;
  nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
}

export interface CursoDetalhes {
  disciplinas: Disciplina[];
  turmas: Turma[];
}

export const cursosApi = {
  listar: async (): Promise<Curso[]> => {
    const { data } = await apiClient.get<Curso[]>('/cursos-disciplinas/cursos');
    return data;
  },

  listarPaginado: async (params: {
    q?: string;
    limit: number;
    offset: number;
  }): Promise<CursosPagina> => {
    const { data } = await apiClient.get<CursosPagina>(
      '/cursos-disciplinas/cursos/paginados',
      { params }
    );
    return data;
  },

  criar: async (payload: CursoCreate): Promise<Curso> => {
    const { data } = await apiClient.post<Curso>('/cursos-disciplinas/cursos', payload);
    return data;
  },

  atualizar: async (cursoId: string, payload: CursoUpdate): Promise<Curso> => {
    const { data } = await apiClient.put<Curso>(`/cursos-disciplinas/cursos/${cursoId}`, payload);
    return data;
  },

  excluir: async (cursoId: string): Promise<void> => {
    await apiClient.delete(`/cursos-disciplinas/cursos/${cursoId}`);
  },

  listarDisciplinas: async (cursoId?: string): Promise<Disciplina[]> => {
    const { data } = await apiClient.get<Disciplina[]>('/cursos-disciplinas/disciplinas', {
      params: cursoId ? { curso_id: cursoId } : undefined,
    });
    return data;
  },

  criarDisciplina: async (payload: DisciplinaInput): Promise<Disciplina> => {
    const { data } = await apiClient.post<Disciplina>('/cursos-disciplinas/disciplinas', payload);
    return data;
  },

  atualizarDisciplina: async (
    disciplinaId: string,
    payload: DisciplinaInput
  ): Promise<Disciplina> => {
    const { data } = await apiClient.put<Disciplina>(
      `/cursos-disciplinas/disciplinas/${disciplinaId}`,
      payload
    );
    return data;
  },

  excluirDisciplina: async (disciplinaId: string): Promise<void> => {
    await apiClient.delete(`/cursos-disciplinas/disciplinas/${disciplinaId}`);
  },

  listarTurmas: async (cursoId: string): Promise<Turma[]> => {
    const { data } = await apiClient.get<Turma[]>('/turmas', { params: { curso_id: cursoId } });
    return data;
  },

  detalhesCurso: async (cursoId: string): Promise<CursoDetalhes> => {
    const { data } = await apiClient.get<CursoDetalhes>(
      `/turmas/cursos/${cursoId}/detalhes`
    );
    return data;
  },
};

export const cursosApiErrorMessage = (error: unknown, fallback: string): string => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('; ') || fallback;
  }
  return fallback;
};
