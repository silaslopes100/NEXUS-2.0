import { apiClient } from '@/api/client';
import {
  EstoqueLicenca,
  LicencaAtribuida,
  DistribuirEstoquePayload,
  AtribuirLicencaPayload,
} from '@/types/licencas';

export interface ListEstoqueParams {
  disciplina_id?: string;
  escola_id?: string;
}

export interface ListLicencasAtribuidasParams {
  polo_id?: string;
  escola_id?: string;
  aluno_id?: string;
}

export const licencasApi = {
  async listEstoque(params?: ListEstoqueParams): Promise<EstoqueLicenca[]> {
    const response = await apiClient.get<EstoqueLicenca[]>('/licencas/estoque', { params });
    return response.data;
  },

  async adicionarEstoque(disciplina_id: string, quantidade: number): Promise<EstoqueLicenca> {
    const response = await apiClient.post<EstoqueLicenca>(
      `/licencas/estoque/adicionar?disciplina_id=${encodeURIComponent(disciplina_id)}&quantidade=${quantidade}`
    );
    return response.data;
  },

  async distribuirEstoque(payload: DistribuirEstoquePayload): Promise<EstoqueLicenca> {
    const response = await apiClient.post<EstoqueLicenca>('/licencas/estoque/distribuir', payload);
    return response.data;
  },

  async listLicencasAtribuidas(params?: ListLicencasAtribuidasParams): Promise<LicencaAtribuida[]> {
    const response = await apiClient.get<LicencaAtribuida[]>('/licencas/atribuidas', { params });
    return response.data;
  },

  async atribuirLicenca(payload: AtribuirLicencaPayload): Promise<LicencaAtribuida> {
    const response = await apiClient.post<LicencaAtribuida>('/licencas/atribuir', payload);
    return response.data;
  },
};
