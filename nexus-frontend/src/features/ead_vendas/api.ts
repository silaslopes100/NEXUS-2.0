// Vendas EAD: vitrine pública das Turmas EAD e loja de disciplinas do aluno
// (espelham app/modules/ead_vendas/schemas.py).
import { apiClient } from '@/api/client';
import type { LoginResponse } from '@/types/auth';

export interface TurmaVitrine {
  id: string;
  nome: string;
  codigo?: string | null;
  turno?: string | null;
  curso_id: string;
  curso_nome: string;
  curso_descricao?: string | null;
  nivel_academico?: string | null;
  carga_horaria_total?: number | null;
  semestres?: number | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  vagas?: number | null;
  vagas_restantes?: number | null;
  total_disciplinas: number;
  valor_minimo?: number | null;
}

export interface DisciplinaVitrine {
  id: string;
  nome: string;
  semestre?: number | null;
  carga_horaria: number;
  valor_ead: number;
  livro_disponivel: boolean;
  valor_livro_ead: number;
  prazo_dias?: number | null;
  libera_em_prevista?: string | null;
}

export interface TurmaVitrineDetalhe extends TurmaVitrine {
  liberacao: 'sequencial' | 'todas_no_inicio' | string;
  disciplinas: DisciplinaVitrine[];
}

export interface InscricaoPayload {
  turma_id: string;
  nome: string;
  sobrenome: string;
  email: string;
  cpf: string;
  celular: string;
  data_nascimento: string;
  senha: string;
  aceite_termos: boolean;
  site?: string;
}

export type EstadoDisciplina = 'disponivel' | 'aguardando' | 'em_breve' | 'pendente' | 'comprada' | 'concluida' | 'recompra';

export interface DisciplinaLoja {
  id: string;
  nome: string;
  semestre?: number | null;
  carga_horaria: number;
  capa_url?: string | null;
  descricao?: string | null;
  total_aulas: number;
  valor_ead: number;
  livro_disponivel: boolean;
  valor_livro_ead: number;
  estado: EstadoDisciplina;
  libera_em?: string | null;
  data_limite?: string | null;
  prazo_dias?: number | null;
  pedido_id?: string | null;
  com_livro: boolean;
}

export interface TurmaLoja {
  id: string;
  nome: string;
  codigo?: string | null;
  curso_id: string;
  curso_nome: string;
  data_inicio?: string | null;
  data_fim?: string | null;
  disciplinas: DisciplinaLoja[];
}

export interface Endereco {
  cep?: string | null;
  logradouro?: string | null;
  numero?: string | null;
  complemento?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  uf?: string | null;
}

export interface Loja {
  nome: string;
  turmas: TurmaLoja[];
  outras_turmas: TurmaVitrine[];
  endereco: Endereco;
}

export interface CheckoutPayload {
  disciplina_id: string;
  turma_id?: string | null;
  com_livro: boolean;
  meio: 'PIX' | 'BOLETO';
  endereco?: Endereco | null;
}

export interface PedidoAluno {
  id: string;
  numero: string;
  tipo: 'ead' | 'ead_livro' | string;
  status: string;
  valor_total: number;
  criado_em?: string | null;
  pago_em?: string | null;
  enviado_em?: string | null;
  entregue_em?: string | null;
  disciplina_id?: string | null;
  disciplina_nome?: string | null;
  com_livro: boolean;
  pagamento_id?: string | null;
  pagamento_status?: string | null;
  billing_type?: string | null;
  vencimento_em?: string | null;
  pix_copia_cola?: string | null;
  pix_qrcode_base64?: string | null;
  boleto_url?: string | null;
  invoice_url?: string | null;
  linha_digitavel?: string | null;
  transportadora?: string | null;
  codigo_rastreio?: string | null;
}

export const vitrineApi = {
  turmas: () => apiClient.get<TurmaVitrine[]>('/ead/vitrine/turmas').then((r) => r.data),
  turma: (id: string) => apiClient.get<TurmaVitrineDetalhe>(`/ead/vitrine/turmas/${id}`).then((r) => r.data),
  inscrever: (payload: InscricaoPayload) =>
    apiClient.post<LoginResponse>('/ead/vitrine/inscricao', payload).then((r) => r.data),
};

export const lojaApi = {
  loja: () => apiClient.get<Loja>('/ead/loja').then((r) => r.data),
  entrarNaTurma: (turmaId: string) => apiClient.post<Loja>(`/ead/loja/turmas/${turmaId}/inscrever`).then((r) => r.data),
  checkout: (payload: CheckoutPayload) => apiClient.post<PedidoAluno>('/ead/loja/checkout', payload).then((r) => r.data),
  pedidos: () => apiClient.get<PedidoAluno[]>('/ead/loja/pedidos').then((r) => r.data),
  pedido: (id: string) => apiClient.get<PedidoAluno>(`/ead/loja/pedidos/${id}`).then((r) => r.data),
  cancelar: (id: string) => apiClient.post<PedidoAluno>(`/ead/loja/pedidos/${id}/cancelar`).then((r) => r.data),
};

export const brl = (v?: number | null) => (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/** 'AAAA-MM-DD' -> 'dd/mm/aaaa' sem deslocar o fuso. */
export const dataBr = (d?: string | null) => (d ? new Date(`${d.slice(0, 10)}T00:00`).toLocaleDateString('pt-BR') : '');

export const ESTADO: Record<EstadoDisciplina, { rotulo: string; classe: string }> = {
  disponivel: { rotulo: 'Disponível', classe: 'bg-nexus-yellow text-ink' },
  aguardando: { rotulo: 'Aguardando liberação', classe: 'bg-slate-800 text-slate-300' },
  em_breve: { rotulo: 'Em breve', classe: 'bg-blue-500/15 text-blue-300' },
  pendente: { rotulo: 'Pagamento em aberto', classe: 'bg-amber-500/15 text-amber-300' },
  comprada: { rotulo: 'Liberada', classe: 'bg-emerald-500/15 text-emerald-300' },
  concluida: { rotulo: 'Concluída', classe: 'bg-emerald-500/90 text-white' },
  recompra: { rotulo: 'Prazo encerrado', classe: 'bg-red-500/15 text-red-300' },
};

export const STATUS_PEDIDO: Record<string, string> = {
  aguardando_pagamento: 'Aguardando pagamento',
  pago_aguardando_envio: 'Pago · livro em separação',
  enviado: 'Livro enviado',
  entregue: 'Livro entregue',
  concluido: 'Pago',
  cancelado: 'Cancelado',
};
