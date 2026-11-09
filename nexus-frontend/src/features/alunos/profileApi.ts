import { apiClient } from '@/api/client';
import { onlyDigits, PerfilAlunoForm } from '@/features/alunos/profileSchema';

export interface PerfilAluno {
  id: string;
  nome: string;
  sobrenome?: string | null;
  email?: string | null;
  telefone?: string | null;
  celular?: string | null;
  foto_url?: string | null;
  endereco: {
    cep?: string | null;
    logradouro?: string | null;
    numero?: string | null;
    complemento?: string | null;
    bairro?: string | null;
    cidade?: string | null;
    uf?: string | null;
  };
}

export interface FotoAlunoResponse {
  foto_url: string;
}

export const perfilAlunoApi = {
  async get(): Promise<PerfilAluno> {
    const { data } = await apiClient.get<PerfilAluno>('/alunos/meu-perfil');
    return data;
  },

  async update(payload: PerfilAlunoForm): Promise<PerfilAluno> {
    const { data } = await apiClient.put<PerfilAluno>('/alunos/meu-perfil', {
      ...payload,
      telefone: onlyDigits(payload.telefone),
      celular: onlyDigits(payload.celular),
      cep: onlyDigits(payload.cep),
    });
    return data;
  },

  async getFoto(fotoUrl: string): Promise<Blob> {
    const { data } = await apiClient.get<Blob>(fotoUrl, { responseType: 'blob' });
    return data;
  },

  async uploadFoto(foto: File): Promise<FotoAlunoResponse> {
    const formData = new FormData();
    formData.append('foto', foto);
    const { data } = await apiClient.post<FotoAlunoResponse>(
      '/alunos/meu-perfil/foto',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return data;
  },
};
