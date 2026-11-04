import { apiClient } from '@/api/client';

export type NivelAcademico =
  | 'bacharelado'
  | 'licenciatura'
  | 'tecnologo'
  | 'pos_graduacao'
  | 'mestrado';

export type ModalidadeCurso = 'hibrido' | 'presencial' | 'ead';
export type StatusCurso = 'ativo' | 'cancelado';

export interface Curso {
  id: string;
  nome: string;
  descricao?: string | null;
  nivel_academico?: NivelAcademico | null;
}

export interface CursoCreate {
  nome: string;
  descricao: string;
  nivel_academico: NivelAcademico;
  modalidade: ModalidadeCurso;
  carga_horaria_total: number;
  semestres: number;
  status: StatusCurso;
}

export interface Disciplina {
  id: string;
  nome: string;
  semestre?: number | null;
  ordem: number;
  carga_horaria?: number | null;
  qtd_aulas_prevista?: number | null;
}

export interface Turma {
  id: string;
  nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
}

export const cursosApi = {
  listar: async (): Promise<Curso[]> => {
    const { data } = await apiClient.get<Curso[]>('/cursos-disciplinas/cursos');
    return data;
  },

  criar: async (payload: CursoCreate): Promise<Curso> => {
    const { data } = await apiClient.post<Curso>('/cursos-disciplinas/cursos', payload);
    return data;
  },

  listarDisciplinas: async (cursoId: string): Promise<Disciplina[]> => {
    const { data } = await apiClient.get<Disciplina[]>('/cursos-disciplinas/disciplinas', {
      params: { curso_id: cursoId },
    });
    return data;
  },

  listarTurmas: async (cursoId: string): Promise<Turma[]> => {
    const { data } = await apiClient.get<Turma[]>('/turmas', { params: { curso_id: cursoId } });
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
