import { apiClient } from '@/api/client';

export interface AulaResumo {
  id: string;
  professor_disciplina_id: string;
  disciplina_id: string;
  disciplina_nome?: string | null;
  curso_nome?: string | null;
  turma_id?: string | null;
  turma_nome?: string | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
  professor_id: string;
  professor_nome?: string | null;
  data_aula: string;
  numero_aula: number;
  conteudo_ministrado?: string | null;
  observacoes?: string | null;
  visivel_aluno: boolean;
  total_materiais: number;
  presentes: number;
  total_chamada: number;
  criado_em?: string | null;
  atualizado_em?: string | null;
}

export interface MaterialAula {
  id: string;
  descricao?: string | null;
  arquivo_url?: string | null;
  arquivo_nome?: string | null;
  arquivo_mime_type?: string | null;
  arquivo_tamanho_bytes?: number | null;
  tem_arquivo: boolean;
}

export interface AlunoChamadaAula {
  aluno_id: string;
  nome: string;
  numero_matricula?: string | null;
  presente: boolean | null;
}

export interface AulaDetalhe extends AulaResumo {
  materiais: MaterialAula[];
  chamada: AlunoChamadaAula[];
}

export interface AulaLista {
  total: number;
  items: AulaResumo[];
  limit: number;
  offset: number;
}

export interface AulaCreatePayload {
  professor_disciplina_id: string;
  data_aula: string;
  numero_aula: number;
  conteudo_ministrado?: string | null;
  observacoes?: string | null;
}

export type AulaUpdatePayload = Partial<Omit<AulaCreatePayload, 'professor_disciplina_id'>>;

export interface OpcaoFiltro {
  id: string;
  nome: string;
}

export interface FiltrosAuditoria {
  disciplinas: OpcaoFiltro[];
  polos: OpcaoFiltro[];
  professores: OpcaoFiltro[];
}

export interface DisciplinaAulasResumo {
  disciplina_id: string;
  total_aulas: number;
  ultima_aula?: string | null;
}

export interface AtividadeDocente {
  dias: number;
  dias_sem_registro: number;
  data_inicio: string;
  aulas_registradas: number;
  disciplinas_com_aula: number;
  polos_com_aula: number;
  top_disciplinas: Array<{ id: string; nome: string; total_aulas: number }>;
  polos_sem_registro: Array<{ id: string; nome: string; ultima_aula?: string | null }>;
}

export interface ListarAulasParams {
  disciplina_id?: string;
  vinculo_id?: string;
  polo_id?: string;
  professor_id?: string;
  data_inicio?: string;
  data_fim?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

/** Remove filtros vazios para não mandar `?polo_id=` (o backend rejeitaria). */
const limpar = (params: ListarAulasParams) =>
  Object.fromEntries(Object.entries(params).filter(([, valor]) => valor !== '' && valor != null));

/**
 * Garante que veio uma lista de aulas. Se o proxy não repassar `/aulas`, o servidor
 * de desenvolvimento responde o index.html com status 200, e sem esta checagem a
 * tela quebraria em `items.length`.
 */
const exigirLista = (data: unknown): AulaLista => {
  const lista = data as Partial<AulaLista> | null;
  if (!lista || !Array.isArray(lista.items)) {
    throw new Error('Resposta inesperada do servidor ao carregar aulas.');
  }
  return lista as AulaLista;
};

export const aulasApi = {
  // ----- Diário de Aulas (professor) -----
  listarMinhas: async (params: ListarAulasParams): Promise<AulaLista> => {
    const { data } = await apiClient.get<AulaLista>('/aulas/me', { params: limpar(params) });
    return exigirLista(data);
  },
  registrar: async (payload: AulaCreatePayload): Promise<AulaDetalhe> => {
    const { data } = await apiClient.post<AulaDetalhe>('/aulas/me', payload);
    return data;
  },
  obter: async (id: string): Promise<AulaDetalhe> => {
    const { data } = await apiClient.get<AulaDetalhe>(`/aulas/me/${id}`);
    return data;
  },
  atualizar: async (id: string, payload: AulaUpdatePayload): Promise<AulaDetalhe> => {
    const { data } = await apiClient.put<AulaDetalhe>(`/aulas/me/${id}`, payload);
    return data;
  },
  excluir: async (id: string): Promise<void> => {
    await apiClient.delete(`/aulas/me/${id}`);
  },
  excluirMaterial: async (aulaId: string, materialId: string): Promise<void> => {
    await apiClient.delete(`/aulas/me/${aulaId}/materiais/${materialId}`);
  },

  // ----- Auditoria (admin) -----
  auditoria: async (params: ListarAulasParams): Promise<AulaLista> => {
    const { data } = await apiClient.get<AulaLista>('/aulas/auditoria', { params: limpar(params) });
    return exigirLista(data);
  },
  auditoriaDetalhe: async (id: string): Promise<AulaDetalhe> => {
    const { data } = await apiClient.get<AulaDetalhe>(`/aulas/auditoria/${id}`);
    return data;
  },
  filtros: async (disciplinaId?: string): Promise<FiltrosAuditoria> => {
    const { data } = await apiClient.get<FiltrosAuditoria>('/aulas/auditoria/filtros', {
      params: disciplinaId ? { disciplina_id: disciplinaId } : undefined,
    });
    return data;
  },
  resumoDisciplinas: async (): Promise<DisciplinaAulasResumo[]> => {
    const { data } = await apiClient.get<DisciplinaAulasResumo[]>('/aulas/auditoria/disciplinas');
    return data;
  },
  atividade: async (dias = 30, diasSemRegistro = 14): Promise<AtividadeDocente> => {
    const { data } = await apiClient.get<AtividadeDocente>('/aulas/auditoria/atividade', {
      params: { dias, dias_sem_registro: diasSemRegistro },
    });
    return data;
  },
};

export const dataLocalMenosDias = (dias: number): string => {
  const data = new Date();
  data.setDate(data.getDate() - dias);
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${data.getFullYear()}-${mes}-${dia}`;
};

export const dataLocalHoje = (): string => dataLocalMenosDias(0);
