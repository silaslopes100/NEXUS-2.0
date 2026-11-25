import { apiClient } from '@/api/client';
import {
  UsuarioAdmin,
  UsuarioFicha,
  ResumoMetricasUsuario,
  UsuarioListResponse,
  UsuarioCreatePayload,
  UsuarioUpdatePayload,
  PerfilItem,
  PermissaoItem,
  LogAuditoriaListResponse,
  Configuracao,
  EtlSyncRunListResponse,
  EtlErro,
  AdminDashboardMetrics,
  CertificadoDashboardItem,
  DashboardExecutivo,
  FiltrosDashboard,
  ListaDashboard,
  MatriculaDashboardItem,
  OrdenacaoRanking,
  RankingPolos,
} from '@/types/admin';

const semVazios = (filtros: FiltrosDashboard = {}) =>
  Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '' && v !== undefined && v !== null));

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
  // Dashboard
  async getDashboardMetrics(): Promise<AdminDashboardMetrics> {
    const response = await apiClient.get<AdminDashboardMetrics>('/admin/dashboard/metrics');
    return response.data;
  },

  async getDashboardExecutivo(filtros?: FiltrosDashboard): Promise<DashboardExecutivo> {
    const response = await apiClient.get<DashboardExecutivo>('/admin/dashboard/executivo', {
      params: semVazios(filtros),
    });
    return response.data;
  },

  async getRankingPolos(filtros?: FiltrosDashboard, ordenar_por: OrdenacaoRanking = 'novas_licencas'): Promise<RankingPolos> {
    const response = await apiClient.get<RankingPolos>('/admin/dashboard/ranking-polos', {
      params: { ...semVazios(filtros), ordenar_por },
    });
    return response.data;
  },

  async exportarRankingPolos(
    filtros: FiltrosDashboard | undefined,
    ordenar_por: OrdenacaoRanking,
    formato: 'pdf' | 'xlsx',
  ): Promise<{ blob: Blob; disposition?: string }> {
    const response = await apiClient.get<Blob>('/admin/dashboard/ranking-polos/exportar', {
      params: { ...semVazios(filtros), ordenar_por, formato },
      responseType: 'blob',
    });
    return { blob: response.data, disposition: response.headers['content-disposition'] as string | undefined };
  },

  async listMatriculasDashboard(filtros?: FiltrosDashboard): Promise<ListaDashboard<MatriculaDashboardItem>> {
    const response = await apiClient.get<ListaDashboard<MatriculaDashboardItem>>('/admin/dashboard/matriculas', {
      params: semVazios(filtros),
    });
    return response.data;
  },

  async listCertificadosDashboard(filtros?: FiltrosDashboard): Promise<ListaDashboard<CertificadoDashboardItem>> {
    const response = await apiClient.get<ListaDashboard<CertificadoDashboardItem>>('/admin/dashboard/certificados', {
      params: semVazios(filtros),
    });
    return response.data;
  },

  // Usuários
  async listUsuarios(params?: ListUsuariosParams): Promise<UsuarioListResponse> {
    const response = await apiClient.get<UsuarioListResponse>('/admin/usuarios', { params });
    return response.data;
  },

  async getUsuario(id: string): Promise<UsuarioAdmin> {
    const response = await apiClient.get<UsuarioAdmin>(`/admin/usuarios/${id}`);
    return response.data;
  },

  async getUsuarioFicha(id: string): Promise<UsuarioFicha> {
    const response = await apiClient.get<UsuarioFicha>(`/admin/usuarios/${id}/ficha`);
    return response.data;
  },

  async getUsuarioFoto(id: string): Promise<Blob> {
    const response = await apiClient.get<Blob>(`/admin/usuarios/${id}/foto`, {
      responseType: 'blob',
    });
    return response.data;
  },

  async uploadUsuarioFoto(id: string, foto: File): Promise<{ foto_url: string }> {
    const formData = new FormData();
    formData.append('foto', foto);
    const response = await apiClient.post<{ foto_url: string }>(
      `/admin/usuarios/${id}/foto`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },

  async getResumoUsuario(id: string): Promise<ResumoMetricasUsuario> {
    const response = await apiClient.get<ResumoMetricasUsuario>(`/admin/usuarios/${id}/resumo`);
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
