import { apiClient } from '@/api/client';
import {
  UsuarioAdmin,
  UsuarioListResponse,
  UsuarioCreatePayload,
  UsuarioUpdatePayload,
  PerfilItem,
  PermissaoItem,
  LogAuditoriaListResponse,
  Configuracao,
  EtlSyncRunListResponse,
  EtlErro,
} from '@/types/admin';

export interface ListUsuariosParams {
  q?: string;
  perfil_id?: string;
  perfil?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface ListAuditLogsParams {
  usuario_id?: string;
  entidade?: string;
  acao?: string;
  data_inicio?: string;
  data_fim?: string;
  limit?: number;
  offset?: number;
}

export const adminApi = {
  // Usuários
  async listUsuarios(params?: ListUsuariosParams): Promise<UsuarioListResponse> {
    const response = await apiClient.get<UsuarioListResponse>('/admin/usuarios', { params });
    return response.data;
  },

  async getUsuario(id: string): Promise<UsuarioAdmin> {
    const response = await apiClient.get<UsuarioAdmin>(`/admin/usuarios/${id}`);
    return response.data;
  },

  async createUsuario(payload: UsuarioCreatePayload): Promise<UsuarioAdmin> {
    const response = await apiClient.post<UsuarioAdmin>('/admin/usuarios', payload);
    return response.data;
  },

  async updateUsuario(id: string, payload: UsuarioUpdatePayload): Promise<UsuarioAdmin> {
    const response = await apiClient.put<UsuarioAdmin>(`/admin/usuarios/${id}`, payload);
    return response.data;
  },

  async updateUsuarioPermissoes(id: string, permissoes: string[]): Promise<UsuarioAdmin> {
    const response = await apiClient.put<UsuarioAdmin>(`/admin/usuarios/${id}/permissoes`, {
      permissoes,
    });
    return response.data;
  },

  async resetUsuarioSenha(id: string, nova_senha: string): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(`/admin/usuarios/${id}/reset-senha`, {
      nova_senha,
    });
    return response.data;
  },

  async deleteUsuario(id: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/admin/usuarios/${id}`);
    return response.data;
  },

  // Perfis e Permissões
  async listPerfis(): Promise<PerfilItem[]> {
    const response = await apiClient.get<PerfilItem[]>('/admin/perfis');
    return response.data;
  },

  async listPermissoes(): Promise<PermissaoItem[]> {
    const response = await apiClient.get<PermissaoItem[]>('/admin/permissoes');
    return response.data;
  },

  // Logs de Auditoria
  async listAuditLogs(params?: ListAuditLogsParams): Promise<LogAuditoriaListResponse> {
    const response = await apiClient.get<LogAuditoriaListResponse>('/admin/logs-auditoria', { params });
    return response.data;
  },

  // Configurações
  async listConfiguracoes(): Promise<Configuracao[]> {
    const response = await apiClient.get<Configuracao[]>('/admin/configuracoes');
    return response.data;
  },

  async getConfiguracao(chave: string): Promise<Configuracao> {
    const response = await apiClient.get<Configuracao>(`/admin/configuracoes/${encodeURIComponent(chave)}`);
    return response.data;
  },

  async setConfiguracao(chave: string, valor: any): Promise<Configuracao> {
    const response = await apiClient.put<Configuracao>(
      `/admin/configuracoes/${encodeURIComponent(chave)}`,
      { valor }
    );
    return response.data;
  },

  // Execuções Batch ETL
  async listEtlExecucoes(params?: { status?: string; limit?: number; offset?: number }): Promise<EtlSyncRunListResponse> {
    const response = await apiClient.get<EtlSyncRunListResponse>('/admin/etl/execucoes', { params });
    return response.data;
  },

  async getEtlExecucaoErros(execucaoId: number, params?: { limit?: number; offset?: number }): Promise<EtlErro[]> {
    const response = await apiClient.get<EtlErro[]>(`/admin/etl/execucoes/${execucaoId}/erros`, { params });
    return response.data;
  },
};
