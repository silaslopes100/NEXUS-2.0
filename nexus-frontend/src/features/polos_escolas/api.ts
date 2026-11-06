import { apiClient } from '@/api/client';
import {
  EscolaCreatePayload,
  ResumoOperacionalEscola,
  ResumoOperacionalPolo,
} from '@/types/polos';

const http = apiClient;

export const polosEscolasApi = {
  // ---------- Polos ----------
  listarPolos: async (params?: { search?: string; limit?: number; offset?: number }) => {
    const { data } = await http.get('/polos', { params });
    return data;
  },

  obterPolo: async (id: string) => {
    const { data } = await http.get(`/polos/${id}`);
    return data;
  },

  obterKpisPolo: async (id: string) => {
    const { data } = await http.get(`/polos/${id}/dashboard/kpis`);
    return data;
  },

  getResumoPolo: async (id: string) => {
    const { data } = await http.get(`/polos/${id}/dashboard/kpis`);
    return data;
  },

  // Contagens operacionais do Polo (escolas, turmas, alunos, aulas, licenças, pedidos)
  getResumoOperacionalPolo: async (id: string): Promise<ResumoOperacionalPolo> => {
    const { data } = await http.get(`/polos/${id}/dashboard/resumo`);
    return data;
  },

  getResumoOperacionalEscola: async (id: string): Promise<ResumoOperacionalEscola> => {
    const { data } = await http.get(`/escolas/${id}/dashboard/resumo`);
    return data;
  },

  getEscolaKpis: async (id: string) => {
    const { data } = await http.get(`/escolas/${id}/dashboard/kpis`);
    return data;
  },

  criarPolo: async (payload: any) => {
    const { data } = await http.post('/polos', payload);
    return data;
  },

  atualizarPolo: async (id: string, payload: any) => {
    const { data } = await http.put(`/polos/${id}`, payload);
    return data;
  },

  excluirPolo: async (id: string) => {
    await http.delete(`/polos/${id}`);
  },

  listarEscolasDoPolo: async (poloId: string) => {
    const { data } = await http.get(`/polos/${poloId}/escolas`);
    return data;
  },

  // ---------- Escolas ----------
  listarEscolas: async (params?: {
    polo_id?: string;
    q?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const { data } = await http.get('/escolas', { params });
    return data;
  },

  obterEscola: async (id: string) => {
    const { data } = await http.get(`/escolas/${id}`);
    return data;
  },

  criarEscola: async (poloId: string, payload: EscolaCreatePayload) => {
    const { polo_id: _poloId, ...body } = payload;
    const { data } = await http.post(`/polos/${poloId}/escolas`, body);
    return data;
  },

  atualizarEscola: async (id: string, payload: Partial<EscolaCreatePayload> & { status?: string }) => {
    const { data } = await http.put(`/escolas/${id}`, payload);
    return data;
  },

  listarAulasEscola: async (id: string, params?: { limit?: number; offset?: number }) => {
    const { data } = await http.get(`/escolas/${id}/aulas`, { params });
    return data;
  },

  listarProfessoresEscola: async (id: string, params?: { limit?: number; offset?: number }) => {
    const { data } = await http.get(`/escolas/${id}/professores`, { params });
    return data;
  },

  // ---------- Vinculação de usuários (NOVO) ----------
  listarUsuariosVinculaveis: async (params: {
    perfil?: string; // Opcional: quando omitido, lista todos os usuários
    q?: string;
    polo_id?: string;
    escola_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const { data } = await http.get('/usuarios-vinculaveis', { params });
    return data;
  },
};