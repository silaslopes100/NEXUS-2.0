/** Polo (com escola opcional) em que o professor atua. */
export interface Lotacao {
  id: string;
  polo_id: string;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
}

export interface LotacaoInput {
  polo_id?: string | null;
  escola_id?: string | null;
}

/** Dados mínimos para escolher um professor de qualquer unidade (sem remuneração). */
export interface ProfessorDisponivel {
  id: string;
  nome?: string | null;
  email?: string | null;
  lotacoes: Lotacao[];
}

export const rotuloLotacao = (lotacao: Lotacao): string =>
  [lotacao.polo_nome || 'Polo', lotacao.escola_nome].filter(Boolean).join(' · ');

export interface Professor {
  id: string;
  usuario_id?: string | null;
  nome?: string | null;
  email?: string | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
  lotacoes?: Lotacao[];
  materias?: string[];
  disciplina_ids?: string[];
  data_inicio?: string | null;
  quantidade_aulas?: number;
  horas_totais?: number;
  valor_hora_aula?: number | null;
  pix?: string | null;
  conteudo_programatico?: string | null;
  status?: string;
  criado_em?: string | null;
  atualizado_em?: string | null;
}

export interface ProfessorListResponse {
  total: number;
  items: Professor[];
  limit: number;
  offset: number;
}

export interface ProfessorDetalhe {
  professor: Professor;
  disciplinas: {
    id: string;
    nome: string;
    curso_id?: string | null;
    curso_nome?: string | null;
    carga_horaria?: number | null;
    qtd_aulas_prevista?: number | null;
  }[];
  turmas: {
    id: string;
    nome: string;
    polo_id?: string | null;
    polo_nome?: string | null;
    escola_id?: string | null;
    escola_nome?: string | null;
    alunos: {
      id: string;
      nome?: string | null;
      numero_matricula?: string | null;
      email?: string | null;
    }[];
  }[];
}

export interface ProfessorTurmaResumo {
  id: string;
  nome: string;
  professor_disciplina_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
}

export interface ProfessorDisciplinaResumo {
  id: string;
  nome: string;
  curso_nome?: string | null;
  semestre?: number | null;
  carga_horaria?: number | null;
  qtd_aulas_prevista?: number | null;
  turmas: ProfessorTurmaResumo[];
}

export interface ProfessorDisciplinaListResponse {
  items: ProfessorDisciplinaResumo[];
}

export interface ProfessorTurmaVinculo {
  id: string;
  professor_id: string;
  professor_nome: string;
  professor_email?: string | null;
  disciplina_id: string;
  disciplina_nome: string;
  turma_id: string;
}

export interface ProfessorTurmaVinculosResponse {
  items: ProfessorTurmaVinculo[];
}

export interface ProfessorConteudoItem {
  id: string;
  disciplina_id: string;
  titulo?: string | null;
  tipo_midia?: string | null;
  url_arquivo?: string | null;
  ordem: number;
  arquivo_nome?: string | null;
  arquivo_mime_type?: string | null;
  arquivo_tamanho_bytes?: number | null;
  tem_arquivo: boolean;
}

export interface ProfessorMaterialResumo {
  id: string;
  professor_disciplina_id: string;
  disciplina_id: string;
  turma_id?: string | null;
  turma_nome?: string | null;
  arquivo_url?: string | null;
  data_aula?: string | null;
  descricao?: string | null;
  expira_em?: string | null;
  arquivo_nome?: string | null;
  arquivo_mime_type?: string | null;
  arquivo_tamanho_bytes?: number | null;
  tem_arquivo: boolean;
}

export interface ProfessorDisciplinaConteudosResumo {
  id: string;
  nome: string;
  curso_nome?: string | null;
  turmas: ProfessorTurmaResumo[];
  conteudos: ProfessorConteudoItem[];
  materiais: ProfessorMaterialResumo[];
}

export interface ProfessorConteudosResponse {
  items: ProfessorDisciplinaConteudosResumo[];
}

export interface ProfessorCreate {
  usuario_id: string;
  polo_id?: string | null;
  escola_id?: string | null;
  lotacoes?: LotacaoInput[];
  materias?: string[];
  disciplina_ids?: string[];
  data_inicio?: string | null;
  quantidade_aulas?: number;
  horas_totais?: number;
  valor_hora_aula?: number | null;
  pix?: string | null;
  conteudo_programatico?: string | null;
}

export interface ProfessorUpdate {
  usuario_id?: string;
  polo_id?: string | null;
  escola_id?: string | null;
  lotacoes?: LotacaoInput[];
  materias?: string[];
  disciplina_ids?: string[];
  data_inicio?: string | null;
  quantidade_aulas?: number;
  horas_totais?: number;
  valor_hora_aula?: number | null;
  pix?: string | null;
  conteudo_programatico?: string | null;
  status?: 'ativo' | 'inativo' | string;
}

export interface UnidadeOption {
  id: string;
  nome: string;
}
