import { apiClient } from '@/api/client';
import { PerfilAlunoForm } from '@/features/alunos/profileSchema';

export interface PerfilAluno {
  id: string;
  nome: string;
  sobrenome?: string | null;
  email?: string | null;
  telefone?: string | null;
  celular?: string | null;
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

export const perfilAlunoApi = {
  async get(): Promise<PerfilAluno> {
    const { data } = await apiClient.get<PerfilAluno>('/alunos/meu-perfil');
    return data;
  },

  async update(payload: PerfilAlunoForm): Promise<PerfilAluno> {
    const { data } = await apiClient.put<PerfilAluno>('/alunos/meu-perfil', payload);
    return data;
  },
};
