export type UserRole = 'admin' | 'polo' | 'escola' | 'professor' | 'aluno';

export interface Perfil {
  id?: string | null;
  nome: string;
  descricao?: string | null;
}

export interface Permissao {
  id?: string | null;
  chave: string;
  descricao?: string | null;
}

export interface User {
  id: string;
  nome: string;
  sobrenome?: string;
  email?: string | null;
  cpf?: string | null;
  telefone?: string | null;
  celular?: string | null;
  foto_url?: string | null;
  status: string;
  perfil?: Perfil | null;
  polo_id?: string | null;
  escola_id?: string | null;
  permissoes: string[];
  ultimo_login_em?: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  usuario: User;
  perfil?: Perfil | null;
  permissoes: string[];
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface MessageResponse {
  message: string;
}
