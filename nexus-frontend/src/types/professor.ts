export interface Professor {
  id: string;
  usuario_id?: string | null;
  nome?: string | null;
  email?: string | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
  materias?: string[];
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

export interface ProfessorCreate {
  usuario_id: string;
  polo_id?: string | null;
  escola_id?: string | null;
  materias?: string[];
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
  materias?: string[];
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
