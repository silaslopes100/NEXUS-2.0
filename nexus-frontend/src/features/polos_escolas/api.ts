import { apiClient } from '@/api/client';
import {
  PoloItem,
  EscolaItem,
  PoloCreatePayload,
  EscolaCreatePayload,
  CoordenadorCreatePayload,
  ResumoPoloResponse,
} from '@/types/polos';

export interface ListPolosParams {
  limit?: number;
  offset?: number;
}

export interface ListEscolasParams {
  polo_id?: string;
  limit?: number;
  offset?: number;
}

export const polosEscolasApi = {
  // Polos
  async listPolos(params?: ListPolosParams): Promise<PoloItem[]> {
    const response = await apiClient.get<PoloItem[]>('/polos', { params });
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

  async createCoordenador(poloId: string, payload: CoordenadorCreatePayload): Promise<any> {
    const response = await apiClient.post(`/polos/${poloId}/coordenador`, payload);
    return response.data;
  },

  async getResumoPolo(poloId: string): Promise<ResumoPoloResponse> {
    const response = await apiClient.get<ResumoPoloResponse>(`/polos/${poloId}/resumo`);
    return response.data;
  },

  // Escolas
  async listEscolas(params?: ListEscolasParams): Promise<EscolaItem[]> {
    const response = await apiClient.get<EscolaItem[]>('/escolas', { params });
    return response.data;
  },

  async getEscola(id: string): Promise<EscolaItem> {
    const response = await apiClient.get<EscolaItem>(`/escolas/${id}`);
    return response.data;
  },

  async createEscola(payload: EscolaCreatePayload): Promise<EscolaItem> {
    const response = await apiClient.post<EscolaItem>('/escolas', payload);
    return response.data;
  },

  async updateEscola(id: string, payload: Partial<EscolaCreatePayload>): Promise<EscolaItem> {
    const response = await apiClient.put<EscolaItem>(`/escolas/${id}`, payload);
    return response.data;
  },
};
