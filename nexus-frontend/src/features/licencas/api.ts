import { apiClient } from '@/api/client';

export interface LicencaKpis {
  total_licencas_compradas: number;
  total_licencas_vendidas_alunos: number;
  total_licencas_nao_vendidas: number;
  total_nao_vendidas_escolas: number;
  total_nao_vendidas_polo: number;
  taxa_conversao_global: number;
  taxa_distribuicao: number;
}

export interface MovimentacaoLicenca {
  id: string;
  tipo: string;
  polo_id?: string;
  escola_id?: string;
  aluno_id?: string;
  quantidade: number;
  valor_unitario?: number;
  status: string;
  observacao?: string;
  criado_em?: string;
}

export interface CompraPayload { quantidade: number; fornecedor: string; valor_unitario: number; data: string; }
export interface DistribuicaoPayload { escola_id: string; quantidade: number; }
export interface VendaPayload { aluno_id: string; quantidade: number; }

export const licencasApi = {
  async getKpis(poloId: string) { return (await apiClient.get<LicencaKpis>(`/polos/${poloId}/dashboard/kpis`)).data; },
  async listMovimentacoes(poloId: string, params?: { limit?: number; offset?: number }) { return (await apiClient.get<{ total: number; items: MovimentacaoLicenca[] }>(`/polos/${poloId}/licencas/movimentacoes`, { params })).data; },
  async comprar(poloId: string, payload: CompraPayload) { return (await apiClient.post(`/polos/${poloId}/licencas/compra`, payload)).data; },
  async distribuir(poloId: string, payload: DistribuicaoPayload) { return (await apiClient.post(`/polos/${poloId}/licencas/distribuir`, payload)).data; },
  async vender(escolaId: string, payload: VendaPayload) { return (await apiClient.post(`/escolas/${escolaId}/licencas/vender`, payload)).data; },
  async devolverEscola(escolaId: string, quantidade: number) { return (await apiClient.post(`/escolas/${escolaId}/licencas/devolver`, { quantidade })).data; },
  async devolverAluno(alunoId: string) { return (await apiClient.post(`/alunos/${alunoId}/licencas/devolver`)).data; },
};
