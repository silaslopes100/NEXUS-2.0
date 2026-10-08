import { apiClient } from '@/api/client';

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
  listarEscolas: async (params?: { polo_id?: string; q?: string; limit?: number; offset?: number }) => {
    const { data } = await http.get('/escolas', { params });
    return data;
  },

  criarEscola: async (poloId: string, payload: any) => {
    const { data } = await http.post(`/polos/${poloId}/escolas`, payload);
    return data;
  },

  atualizarEscola: async (id: string, payload: any) => {
    const { data } = await http.put(`/escolas/${id}`, payload);
    return data;
  },

  // ---------- Vinculação de usuários (NOVO) ----------
  listarUsuariosVinculaveis: async (params: {
    perfil: 'coordenador_polo' | 'secretario_escola';
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