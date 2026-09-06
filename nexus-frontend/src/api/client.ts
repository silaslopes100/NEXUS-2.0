import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { RefreshTokenResponse } from '@/types/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Interceptor de Requisição: Anexa access_token em memória
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Fila e controle de concorrência para o Refresh Token
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Interceptor de Resposta: Trata 401 e executa auto-refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Se o erro não for 401 ou já foi feita tentativa de retry ou a rota era de login/refresh
    if (
      !error.response ||
      error.response.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error);
    }

    const { refreshToken, logout, setTokens } = useAuthStore.getState();

    // Se não há refresh token disponível em memória, desloga imediatamente
    if (!refreshToken) {
      logout();
      if (!window.location.pathname.startsWith('/auth/')) {
        window.location.href = '/auth/login';
      }
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Se já houver um refresh em andamento, enfileira a requisição
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((newToken) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Chamada direta para renovar token sem acionar o interceptor recursivo
      const response = await axios.post<RefreshTokenResponse>(
        `${API_BASE_URL}/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { 'Content-Type': 'application/json' } }
      );

      const { access_token: newAccessToken, refresh_token: newRefreshToken } = response.data;

      // Atualiza os tokens no Zustand authStore (em memória)
      setTokens(newAccessToken, newRefreshToken);

      // Processa requisições da fila com o novo token
      processQueue(null, newAccessToken);

      // Atualiza o header da requisição original que falhou e reexecuta
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      }
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      logout();
      if (!window.location.pathname.startsWith('/auth/')) {
        window.location.href = '/auth/login';
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
