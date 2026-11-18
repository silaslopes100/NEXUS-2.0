import { apiClient } from '@/api/client';

export interface Alternativa {
  id?: string;
  texto: string;
  correta?: boolean | null;
}

export interface Questao {
  id?: string;
  enunciado: string;
  peso: number;
  ordem?: number;
  alternativas: Alternativa[];
}

export interface Avaliacao {
  id: string;
  disciplina_id: string;
  disciplina_nome?: string | null;
  titulo: string;
  instrucoes?: string | null;
  tempo_limite_min?: number | null;
  tentativas_max: number;
  nota_minima: number;
  embaralhar: boolean;
  ativo: boolean;
  origem: string;
  questoes: Questao[];
  atualizado_em?: string | null;
}

export interface AvaliacaoResumo {
  id: string;
  disciplina_id: string;
  titulo: string;
  ativo: boolean;
  origem: string;
  total_questoes: number;
}

export interface AvaliacaoSalvar {
  titulo: string;
  instrucoes?: string | null;
  tempo_limite_min?: number | null;
  tentativas_max: number;
  nota_minima: number;
  embaralhar: boolean;
  ativo: boolean;
  questoes: { enunciado: string; peso: number; alternativas: { texto: string; correta: boolean }[] }[];
}

export type SituacaoAvaliacao =
  | 'disponivel'
  | 'em_andamento'
  | 'aprovado'
  | 'reprovado'
  | 'sem_tentativas'
  | 'sem_avaliacao'
  | 'ava';

export interface AvaliacaoAluno {
  disciplina_id: string;
  disciplina_nome?: string | null;
  curso_id?: string | null;
  avaliacao_id?: string | null;
  titulo?: string | null;
  tempo_limite_min?: number | null;
  tentativas_max: number;
  tentativas_usadas: number;
  tentativas_restantes: number;
  melhor_nota?: number | null;
  nota_minima: number;
  situacao: SituacaoAvaliacao;
  tentativa_aberta_id?: string | null;
  pode_realizar: boolean;
}

export interface Tentativa {
  tentativa_id: string;
  avaliacao_id: string;
  titulo: string;
  instrucoes?: string | null;
  disciplina_nome?: string | null;
  expira_em?: string | null;
  questoes: Questao[];
  respostas: Record<string, string>;
}

export interface Resultado {
  tentativa_id: string;
  nota: number;
  aprovado: boolean;
  nota_minima: number;
  acertos: number;
  total_questoes: number;
  tentativas_restantes: number;
  melhor_nota?: number | null;
}

export const avaliacoesApi = {
  // Admin / professor
  listar: async (disciplinaId?: string) =>
    (await apiClient.get<AvaliacaoResumo[]>('/avaliacoes', { params: disciplinaId ? { disciplina_id: disciplinaId } : {} }))
      .data,
  daDisciplina: async (disciplinaId: string) =>
    (await apiClient.get<Avaliacao | null>(`/avaliacoes/disciplina/${disciplinaId}`)).data,
  salvar: async (disciplinaId: string, dados: AvaliacaoSalvar) =>
    (await apiClient.put<Avaliacao>(`/avaliacoes/disciplina/${disciplinaId}`, dados)).data,
  ativar: async (id: string) => (await apiClient.post<Avaliacao>(`/avaliacoes/${id}/ativar`)).data,
  desativar: async (id: string) => (await apiClient.post<Avaliacao>(`/avaliacoes/${id}/desativar`)).data,

  // Aluno
  minhas: async () => (await apiClient.get<AvaliacaoAluno[]>('/avaliacoes/minhas')).data,
  iniciar: async (avaliacaoId: string) =>
    (await apiClient.post<Tentativa>(`/avaliacoes/${avaliacaoId}/iniciar`)).data,
  salvarRespostas: async (tentativaId: string, respostas: Record<string, string>) =>
    (await apiClient.put(`/avaliacoes/tentativas/${tentativaId}/respostas`, { respostas })).data,
  finalizar: async (tentativaId: string, respostas: Record<string, string>) =>
    (await apiClient.post<Resultado>(`/avaliacoes/tentativas/${tentativaId}/finalizar`, { respostas })).data,
};

export const formatarNota = (nota?: number | null) =>
  nota == null ? '—' : nota.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
