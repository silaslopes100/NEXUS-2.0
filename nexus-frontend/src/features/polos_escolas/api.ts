import { apiClient } from '@/api/client';
import {
  PoloItem,
  EscolaItem,
  PoloCreatePayload,
  EscolaCreatePayload,
  PaginacaoResponse,
  DashboardPoloKpis,
  AlertaItem,
} from '@/types/polos';

export interface ListPolosParams {
  limit?: number;
  offset?: number;
  q?: string;
}

export interface ListEscolasParams {
  polo_id?: string;
  limit?: number;
  offset?: number;
}

export const polosEscolasApi = {
  // Polos
  async listPolos(params?: ListPolosParams): Promise<PaginacaoResponse<PoloItem>> {
    const response = await apiClient.get<PaginacaoResponse<PoloItem>>('/polos', { params });
    return response.data;
  },

  async getPolo(id: string): Promise<PoloItem> {
    const response = await apiClient.get<PoloItem>(`/polos/${id}`);
    return response.data;
  },

  async createPolo(payload: PoloCreatePayload): Promise<PoloItem> {
    const response = await apiClient.post<PoloItem>('/polos', payload);
    return response.data;
  },

  async updatePolo(id: string, payload: Partial<PoloCreatePayload>): Promise<PoloItem> {
    const response = await apiClient.put<PoloItem>(`/polos/${id}`, payload);
    return response.data;
  },

  async getResumoPolo(poloId: string): Promise<DashboardPoloKpis> {
    const response = await apiClient.get<DashboardPoloKpis>(`/polos/${poloId}/dashboard/kpis`);
    return response.data;
  },

  async getAlertasPolo(poloId: string): Promise<{ total: number; items: AlertaItem[] }> {
    const response = await apiClient.get(`/polos/${poloId}/dashboard/alertas`);
    return response.data;
  },

  async getEscolaKpis(escolaId: string) {
    const response = await apiClient.get<{
      licencas_recebidas: number;
      licencas_vendidas: number;
      licencas_nao_vendidas: number;
      taxa_conversao: number;
      taxa_ociosidade: number;
    }>(`/escolas/${escolaId}/dashboard/kpis`);
    return response.data;
  },

  // Escolas
  async listEscolas(poloId: string, params?: Omit<ListEscolasParams, 'polo_id'>): Promise<PaginacaoResponse<EscolaItem>> {
    const response = await apiClient.get<PaginacaoResponse<EscolaItem>>(`/polos/${poloId}/escolas`, { params });
    return response.data;
  },

  async getEscola(id: string): Promise<EscolaItem> {
    const response = await apiClient.get<EscolaItem>(`/escolas/${id}`);
    return response.data;
  },

  async createEscola(payload: EscolaCreatePayload): Promise<EscolaItem> {
    const { polo_id, ...body } = payload;
    const response = await apiClient.post<EscolaItem>(`/polos/${polo_id}/escolas`, body);
    return response.data;
  },

  async updateEscola(id: string, payload: Partial<EscolaCreatePayload>): Promise<EscolaItem> {
    const response = await apiClient.put<EscolaItem>(`/escolas/${id}`, payload);
    return response.data;
  },
};
