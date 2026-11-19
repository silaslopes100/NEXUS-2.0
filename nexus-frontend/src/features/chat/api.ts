import { apiClient } from '@/api/client';
import { enviarArquivoDireto, urlArquivo } from '@/lib/uploadDireto';

export type TipoConversa = 'individual' | 'grupo';
export type StatusConversa = 'ativa' | 'encerrada';

export interface UsuarioResumo {
  id: string;
  nome: string;
  perfil?: string | null;
  foto_url?: string | null;
}

export interface Contato extends UsuarioResumo {
  polo_nome?: string | null;
  escola_nome?: string | null;
}

export interface Membro extends UsuarioResumo {
  papel: 'membro' | 'moderador';
  ultima_leitura_em?: string | null;
}

export interface Conversa {
  id: string;
  tipo: TipoConversa;
  titulo: string;
  turma_id?: string | null;
  status: StatusConversa;
  papel?: string | null;
  nao_lidas: number;
  total_membros: number;
  outro?: UsuarioResumo | null;
  ultima_mensagem_em?: string | null;
  ultima_mensagem?: string | null;
  ultima_remetente_id?: string | null;
  criado_em?: string | null;
}

export interface ConversaDetalhe extends Conversa {
  membros: Membro[];
  pode_encerrar: boolean;
  pode_gerenciar_membros: boolean;
}

export interface Mensagem {
  id: string;
  conversa_id: string;
  remetente_id?: string | null;
  remetente_nome?: string | null;
  tipo: 'texto' | 'anexo' | 'sistema';
  texto?: string | null;
  anexo_url?: string | null;
  anexo_nome?: string | null;
  anexo_mime?: string | null;
  anexo_tamanho?: number | null;
  criado_em: string;
}

export interface TurmaChat {
  id: string;
  nome: string;
  curso_nome?: string | null;
  escola_nome?: string | null;
  polo_nome?: string | null;
  conversa_id?: string | null;
}

export interface AnexoEnviado {
  url: string;
  pathname: string;
  nome: string;
  mime: string;
  tamanho: number;
}

export interface ConversaAdmin {
  id: string;
  tipo: TipoConversa;
  titulo: string;
  status: StatusConversa;
  turma_id?: string | null;
  membros: UsuarioResumo[];
  total_mensagens: number;
  ultima_mensagem_em?: string | null;
  criado_em?: string | null;
}

/** URLs locais (desenvolvimento) são relativas à API; as do Blob já são absolutas. */
export const urlAnexo = urlArquivo;

export const chatApi = {
  listar: (tipo?: TipoConversa) =>
    apiClient.get<Conversa[]>('/chat/conversas', { params: { tipo, limite: 100 } }).then((r) => r.data),
  resumo: () => apiClient.get<{ nao_lidas: number }>('/chat/resumo').then((r) => r.data),
  contatos: (busca: string) =>
    apiClient.get<Contato[]>('/chat/contatos', { params: { busca: busca || undefined } }).then((r) => r.data),
  turmas: (busca: string) =>
    apiClient.get<TurmaChat[]>('/chat/turmas', { params: { busca: busca || undefined } }).then((r) => r.data),
  detalhe: (id: string) => apiClient.get<ConversaDetalhe>(`/chat/conversas/${id}`).then((r) => r.data),
  iniciarIndividual: (usuarioId: string) =>
    apiClient.post<ConversaDetalhe>('/chat/conversas/individual', { usuario_id: usuarioId }).then((r) => r.data),
  criarGrupo: (titulo: string, membros: string[]) =>
    apiClient.post<ConversaDetalhe>('/chat/grupos', { titulo, membros }).then((r) => r.data),
  abrirGrupoTurma: (turmaId: string) =>
    apiClient.post<ConversaDetalhe>(`/chat/grupos/turma/${turmaId}`).then((r) => r.data),
  alterarMembros: (id: string, adicionar: string[], remover: string[]) =>
    apiClient.patch<ConversaDetalhe>(`/chat/grupos/${id}/membros`, { adicionar, remover }).then((r) => r.data),
  mensagens: (id: string, params: { antes?: string; depois?: string; limite?: number } = {}) =>
    apiClient.get<Mensagem[]>(`/chat/conversas/${id}/mensagens`, { params }).then((r) => r.data),
  enviar: (id: string, texto: string | null, anexo?: AnexoEnviado | null) =>
    apiClient.post<Mensagem>(`/chat/conversas/${id}/mensagens`, { texto, anexo: anexo ?? null }).then((r) => r.data),
  marcarLida: (id: string) => apiClient.post(`/chat/conversas/${id}/lida`).then(() => undefined),
  encerrar: (id: string) => apiClient.post<ConversaDetalhe>(`/chat/conversas/${id}/encerrar`).then((r) => r.data),
  reabrir: (id: string) => apiClient.post<ConversaDetalhe>(`/chat/conversas/${id}/reabrir`).then((r) => r.data),
  ocultar: (id: string) => apiClient.delete(`/chat/conversas/${id}/minha`).then(() => undefined),

  /** Envia o arquivo direto ao armazenamento (Blob em produção, disco em dev) e devolve os metadados. */
  enviarArquivo(arquivo: File | Blob, nome: string, onProgresso?: (pct: number) => void): Promise<AnexoEnviado> {
    return enviarArquivoDireto('/chat/anexos/upload', arquivo, nome, onProgresso);
  },

  // Admin
  adminListar: (params: { usuario_id?: string; tipo?: TipoConversa; busca?: string; limite?: number; offset?: number }) =>
    apiClient.get<{ total: number; itens: ConversaAdmin[] }>('/chat/admin/conversas', { params }).then((r) => r.data),
  exportar: (id: string) =>
    apiClient.get<Blob>(`/chat/conversas/${id}/exportar`, { responseType: 'blob', timeout: 60_000 }).then((r) => r.data),
  excluir: (id: string) => apiClient.delete(`/chat/conversas/${id}`).then(() => undefined),
};

export const erroApi = (e: unknown, padrao = 'Não foi possível concluir a operação.') => {
  const det = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof det === 'string') return det;
  if (Array.isArray(det) && det[0]?.msg) return String(det[0].msg).replace(/^Value error, /, '');
  return padrao;
};
