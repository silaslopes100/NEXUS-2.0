import { apiClient } from '@/api/client';

export type StatusSolicitacao = 'pendente' | 'atendida' | 'atendida_parcial' | 'recusada';

export interface ItemSolicitacao {
  id: string;
  disciplina_id: string;
  disciplina_nome?: string | null;
  quantidade: number;
  quantidade_atendida: number;
  valor_unitario: number;
  saldo_polo?: number | null;
}

export interface Solicitacao {
  id: string;
  numero: string;
  escola_id: string;
  escola_nome?: string | null;
  polo_id: string;
  polo_nome?: string | null;
  status: StatusSolicitacao;
  observacao?: string | null;
  motivo_recusa?: string | null;
  criado_em?: string | null;
  resolvido_em?: string | null;
  itens: ItemSolicitacao[];
  valor_estimado: number;
  nota_id?: string | null;
  nota_numero?: string | null;
  nota_status?: 'emitida' | 'repasse_recebido' | 'cancelada' | null;
  nota_valor_total?: number | null;
  nota_vencimento?: string | null;
  nota_repasse_em?: string | null;
}

export interface Notificacao {
  id: string;
  titulo: string;
  mensagem?: string | null;
  link?: string | null;
  lida: boolean;
  criado_em?: string | null;
}

export const solicitacoesApi = {
  criar: async (escolaId: string, itens: { disciplina_id: string; quantidade: number }[], observacao?: string) =>
    (await apiClient.post<Solicitacao>(`/escolas/${escolaId}/solicitacoes`, { itens, observacao: observacao || null })).data,
  daEscola: async (escolaId: string) => (await apiClient.get<Solicitacao[]>(`/escolas/${escolaId}/solicitacoes`)).data,
  doPolo: async (poloId: string, status?: StatusSolicitacao) =>
    (await apiClient.get<Solicitacao[]>(`/polos/${poloId}/solicitacoes`, { params: status ? { status } : {} })).data,
  atender: async (poloId: string, id: string, itens: { item_id: string; quantidade_atendida: number }[]) =>
    (await apiClient.post<Solicitacao>(`/polos/${poloId}/solicitacoes/${id}/atender`, { itens })).data,
  recusar: async (poloId: string, id: string, motivo: string) =>
    (await apiClient.post<Solicitacao>(`/polos/${poloId}/solicitacoes/${id}/recusar`, { motivo })).data,
  repasseRecebido: async (poloId: string, notaId: string) =>
    (await apiClient.post<Solicitacao>(`/polos/${poloId}/prestacoes/${notaId}/repasse-recebido`)).data,
  notaPdf: async (id: string) =>
    (await apiClient.get<Blob>(`/solicitacoes/${id}/nota.pdf`, { responseType: 'blob' })).data,
};

export const notificacoesApi = {
  listar: async () => (await apiClient.get<Notificacao[]>('/notificacoes')).data,
  resumo: async () => (await apiClient.get<{ nao_lidas: number }>('/notificacoes/resumo')).data,
  marcarLida: async (id: string) => (await apiClient.post<{ nao_lidas: number }>(`/notificacoes/${id}/lida`)).data,
  marcarTodas: async () => (await apiClient.post<{ nao_lidas: number }>('/notificacoes/lidas')).data,
};

export const STATUS_SOLICITACAO: Record<StatusSolicitacao, { texto: string; classe: string }> = {
  pendente: { texto: 'Aguardando o Polo', classe: 'border-amber-500/40 bg-amber-500/10 text-amber-200' },
  atendida: { texto: 'Atendida', classe: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' },
  atendida_parcial: { texto: 'Atendida em parte', classe: 'border-blue-500/40 bg-blue-500/10 text-blue-200' },
  recusada: { texto: 'Recusada', classe: 'border-red-500/40 bg-red-500/10 text-red-200' },
};

export const brl = (v?: number | null) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v || 0));

export const dataBR = (v?: string | null) => {
  if (!v) return '—';
  const d = v.length === 10 ? new Date(`${v}T12:00:00`) : new Date(v);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('pt-BR');
};
