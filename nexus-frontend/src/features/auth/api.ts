import { apiClient } from '@/api/client';
import {
  LoginResponse,
  RefreshTokenResponse,
  MessageResponse,
  User,
} from '@/types/auth';

export interface LoginPayload {
  email: string;
  senha: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface ResetPasswordPayload {
  token: string;
  nova_senha: string;
}

export const authApi = {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', payload);
    return response.data;
  },

  async refresh(refreshToken: string): Promise<RefreshTokenResponse> {
    const response = await apiClient.post<RefreshTokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async logout(refreshToken?: string | null): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/logout', {
      refresh_token: refreshToken || undefined,
    });
    return response.data;
  },

  async esqueciSenha(payload: ForgotPasswordPayload): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/esqueci-senha', payload);
    return response.data;
  },

  async redefinirSenha(payload: ResetPasswordPayload): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/redefinir-senha', payload);
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },
};
