import { apiClient } from '@/api/client';

/** Regras do Calendário Acadêmico — os pontos em aberto do documento, parametrizados. */
export interface RegrasCalendario {
  carga_horaria_padrao: number;
  disciplinas_por_mes: number;
  aulas_por_disciplina_mes: number;
  fonte_qtd_aulas: 'calendario' | 'disciplina';
  duracao_aula: 'dividir_carga' | 'fixa';
  duracao_aula_horas: number;
  quinta_semana: 'aula_extra' | 'ignorar';
  organizacao_disciplinas_mes: 'paralelo' | 'sequencial';
  capacidade_insuficiente: 'alertar' | 'bloquear';
  frequencia_base: 'aulas' | 'horas';
  frequencia_minima_pct: number;
  horas_abatidas: 'previstas' | 'registradas';
  excluir_ata_devolve_saldo: boolean;
  perfis_alteram_tipo_aula: string[];
  saldo_ao_fim_turma: 'alertar' | 'bloquear_conclusao';
  bloquear_ata_fora_periodo: boolean;
  ead_prazo_dias_padrao: number;
  ead_liberacao: 'sequencial' | 'todas_no_inicio';
  ead_proxima_libera: 'anterior_concluida_ou_vencida' | 'anterior_vencida' | 'anterior_concluida';
  ead_ao_vencer: 'bloquear' | 'alertar';
}

export interface Feriado { data: string; descricao?: string | null }

export interface CalendarioInput {
  nome: string;
  descricao?: string | null;
  data_inicio: string;
  data_fim: string;
  dias_semana: number[];
  meses_recesso: number[];
  feriados: Feriado[];
  datas_excluidas: string[];
  datas_extras: string[];
  regras: RegrasCalendario;
  ativo: boolean;
}

export interface Calendario extends CalendarioInput {
  id: string;
  total_cursos: number;
}

export interface MesLetivo { mes: string; datas: string[]; quinta_semana: string[]; recesso: boolean }
export interface DatasLetivas { inicio: string; fim: string; total: number; meses: MesLetivo[] }

export type TipoAula = 'prevista' | 'reposicao' | 'extra' | 'reforco' | 'complemento' | 'revisao';
export type StatusAulaPrevista = 'pendente' | 'realizada' | 'realizada_reposicao';

export const ROTULO_TIPO_AULA: Record<TipoAula, string> = {
  prevista: 'Aula prevista',
  reposicao: 'Reposição',
  extra: 'Extra',
  reforco: 'Reforço',
  complemento: 'Complemento de aula',
  revisao: 'Revisão de aula',
};
export const TIPOS_QUE_ABATEM: TipoAula[] = ['prevista', 'reposicao'];

export interface AulaPrevista {
  id: string;
  turma_id: string;
  disciplina_id: string;
  disciplina_nome?: string | null;
  numero: number;
  data_prevista: string;
  horas_previstas: number;
  status: StatusAulaPrevista;
  ata_id?: string | null;
  ata_data?: string | null;
}

export interface Cronograma {
  turma_id: string;
  calendario_id?: string | null;
  calendario_nome?: string | null;
  gerado: boolean;
  alertas: string[];
  disciplinas: { disciplina_id: string; nome: string; carga_horaria: number; aulas: AulaPrevista[] }[];
}

export type Situacao = 'em_dia' | 'atrasado' | 'nao_iniciada' | 'concluida';

export interface AndamentoDisciplina {
  disciplina_id: string;
  nome: string;
  carga_horaria: number;
  horas_abatidas: number;
  saldo: number;
  progresso_pct: number;
  horas_complementares: number;
  concluida: boolean;
  aulas_previstas: number;
  aulas_realizadas: number;
  previsto_ate_hoje_horas: number;
  situacao: Situacao;
  atraso_horas: number;
  atraso_aulas: number;
}

export interface Andamento {
  turma_id: string;
  data_referencia: string;
  cronograma_gerado: boolean;
  carga_total: number;
  horas_abatidas: number;
  saldo: number;
  progresso_pct: number;
  horas_complementares: number;
  previsto_ate_hoje_horas: number;
  situacao: Situacao;
  atraso_horas: number;
  atraso_aulas: number;
  turma_encerrada: boolean;
  alertas: string[];
  concluida_em?: string | null;
  pode_concluir: boolean;
  disciplinas: AndamentoDisciplina[];
}

export interface FrequenciaAluno {
  aluno_id: string;
  nome: string;
  numero_matricula?: string | null;
  frequencia_pct: number | null;
  em_risco: boolean;
  disciplinas: { disciplina_id: string; nome: string; presencas: number; registros: number; frequencia_pct: number | null }[];
}

export interface Frequencia {
  turma_id: string;
  base: 'aulas' | 'horas';
  minimo_pct: number;
  alunos_em_risco: number;
  alunos: FrequenciaAluno[];
}

export const ROTULO_SITUACAO: Record<Situacao, string> = {
  em_dia: 'Em dia',
  atrasado: 'Atrasado',
  nao_iniciada: 'Não iniciada',
  concluida: 'Concluída',
};

export const DIAS_SEMANA = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
export const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

export const fmtHoras = (h?: number | null) =>
  h === undefined || h === null ? '—' : `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(h)} h`;

export const cargaHorariaApi = {
  regrasPadrao: async () => (await apiClient.get<RegrasCalendario>('/calendarios-academicos/regras-padrao')).data,
  listarCalendarios: async () => (await apiClient.get<Calendario[]>('/calendarios-academicos')).data,
  criarCalendario: async (dados: CalendarioInput) => (await apiClient.post<Calendario>('/calendarios-academicos', dados)).data,
  atualizarCalendario: async (id: string, dados: CalendarioInput) =>
    (await apiClient.put<Calendario>(`/calendarios-academicos/${id}`, dados)).data,
  excluirCalendario: async (id: string) => { await apiClient.delete(`/calendarios-academicos/${id}`); },
  turmasAfetadas: async (id: string) =>
    (await apiClient.get<{ total: number }>(`/calendarios-academicos/${id}/turmas-afetadas`)).data.total,
  datasLetivas: async (id: string, inicio?: string, fim?: string) =>
    (await apiClient.get<DatasLetivas>(`/calendarios-academicos/${id}/datas-letivas`, { params: { inicio, fim } })).data,

  cronograma: async (turmaId: string) => (await apiClient.get<Cronograma>(`/turmas/${turmaId}/cronograma`)).data,
  gerarCronograma: async (turmaId: string) => (await apiClient.post<Cronograma>(`/turmas/${turmaId}/cronograma/gerar`)).data,
  andamento: async (turmaId: string) => (await apiClient.get<Andamento>(`/turmas/${turmaId}/andamento`)).data,
  frequencia: async (turmaId: string) => (await apiClient.get<Frequencia>(`/turmas/${turmaId}/frequencia`)).data,
  concluir: async (turmaId: string) =>
    (await apiClient.post<{ message: string; saldo_pendente: number }>(`/turmas/${turmaId}/concluir`)).data,
};

export const erroApi = (error: unknown, padrao: string): string => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ');
  return padrao;
};
