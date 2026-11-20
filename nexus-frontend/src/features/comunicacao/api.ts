import { apiClient } from '@/api/client';
import { UserRole } from '@/types/auth';
import { ArquivoEnviado, enviarArquivoDireto } from '@/lib/uploadDireto';

/** Perfis da equipe Etademp que publicam no feed (aluno só curte, comenta e responde via chat). */
export const PERFIS_PUBLICAR: UserRole[] = ['admin', 'polo', 'escola', 'professor', 'financeiro', 'logistica'];

export const PERFIS_OPCOES: { valor: UserRole; rotulo: string }[] = [
  { valor: 'aluno', rotulo: 'Alunos' },
  { valor: 'professor', rotulo: 'Professores' },
  { valor: 'polo', rotulo: 'Polos' },
  { valor: 'escola', rotulo: 'Escolas' },
  { valor: 'admin', rotulo: 'Administração' },
  { valor: 'financeiro', rotulo: 'Financeiro' },
  { valor: 'logistica', rotulo: 'Logística' },
];

export const rotuloPerfis = (perfis?: string[] | null) =>
  !perfis?.length
    ? 'Todos'
    : perfis.map((p) => PERFIS_OPCOES.find((o) => o.valor === p)?.rotulo ?? p).join(', ');

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export interface Autor {
  id: string;
  nome: string;
  perfil?: string | null;
  foto_url?: string | null;
}

export interface Midia {
  id?: string | null;
  tipo: 'imagem' | 'video' | 'arquivo' | 'video_link' | string;
  url: string;
  pathname?: string | null;
  nome?: string | null;
  mime?: string | null;
  tamanho?: number | null;
  embed_tipo?: 'youtube' | 'vimeo' | null;
  embed_id?: string | null;
}

export interface LinkPreview {
  url: string;
  titulo?: string | null;
  descricao?: string | null;
  imagem_url?: string | null;
  site_nome?: string | null;
  embed_tipo?: 'youtube' | 'vimeo' | null;
  embed_id?: string | null;
}

export type StatusComentario = 'pendente' | 'aprovado' | 'rejeitado';

export interface Comentario {
  id: string;
  post_id: string;
  parent_id?: string | null;
  autor: Autor;
  texto: string;
  criado_em: string;
  /** Só vem para quem modera o post. */
  status?: StatusComentario | null;
  pode_excluir: boolean;
  pode_moderar: boolean;
}

export interface Post {
  id: string;
  autor: Autor;
  conteudo_html: string;
  midias: Midia[];
  links: LinkPreview[];
  publico_perfis?: string[] | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
  fixado: boolean;
  permite_comentarios: boolean;
  total_curtidas: number;
  total_comentarios: number;
  curtido_por_mim: boolean;
  editado: boolean;
  criado_em: string;
  atualizado_em?: string | null;
  pode_editar: boolean;
  pode_moderar: boolean;
  pendentes: number;
  comentarios_recentes: Comentario[];
}

export interface PostPayload {
  conteudo_html: string;
  midias: ArquivoEnviado[];
  links: { url: string }[];
  publico_perfis: string[] | null;
  polo_id?: string | null;
  escola_id?: string | null;
  permite_comentarios: boolean;
}

export interface Pagina<T> {
  itens: T[];
  proximo_cursor?: string | null;
}

export interface ItemModeracao {
  id: string;
  post_id: string;
  post_trecho: string;
  post_autor_nome?: string | null;
  parent_id?: string | null;
  autor: Autor;
  texto: string;
  status: StatusComentario;
  criado_em: string;
  moderado_em?: string | null;
  moderado_por_nome?: string | null;
  motivo_rejeicao?: string | null;
}

export type StatusAviso = 'agendado' | 'ativo' | 'expirado' | 'inativo';
export type FrequenciaAviso = 'uma_vez' | 'ate_confirmar' | 'toda_sessao';
export type LarguraAviso = 'pequena' | 'media' | 'grande';

export interface Aviso {
  id: string;
  titulo: string;
  conteudo_html: string;
  publico_tipo: 'todos' | 'perfis' | 'usuarios';
  perfis: string[];
  usuarios: Autor[];
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
  inicio_em: string;
  fim_em: string;
  frequencia: FrequenciaAviso;
  exige_confirmacao: boolean;
  prioridade: number;
  ativo: boolean;
  cor_destaque?: string | null;
  largura: LarguraAviso;
  midias: Midia[];
  status: StatusAviso;
  criado_por_nome?: string | null;
  criado_em?: string | null;
  atualizado_em?: string | null;
  total_visualizacoes: number;
  total_confirmacoes: number;
}

export type AvisoMidiaPayload =
  | { tipo: 'arquivo_enviado'; arquivo: ArquivoEnviado }
  | { tipo: 'video_link'; url: string };

export interface AvisoPayload {
  titulo: string;
  conteudo_html: string;
  publico_tipo: 'todos' | 'perfis' | 'usuarios';
  perfis: string[];
  usuarios: string[];
  polo_id?: string | null;
  escola_id?: string | null;
  inicio_em: string;
  fim_em: string;
  frequencia: FrequenciaAviso;
  exige_confirmacao: boolean;
  prioridade: number;
  ativo: boolean;
  cor_destaque?: string | null;
  largura: LarguraAviso;
  midias: AvisoMidiaPayload[];
}

export interface AvisoPopup {
  id: string;
  titulo: string;
  conteudo_html: string;
  midias: Midia[];
  frequencia: FrequenciaAviso;
  exige_confirmacao: boolean;
  cor_destaque?: string | null;
  largura: LarguraAviso;
}

export interface UsuarioBusca extends Autor {
  email?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
}

export interface EstatisticasAviso {
  publico_estimado: number;
  visualizacoes: number;
  confirmacoes: number;
  total: number;
  itens: {
    usuario: Autor;
    primeira_vez_em: string;
    ultima_vez_em: string;
    vezes: number;
    confirmado_em?: string | null;
  }[];
}

/** Converte uma mídia já salva (do post/aviso) de volta para o formato de envio. */
export const midiaParaArquivo = (m: Midia): ArquivoEnviado => ({
  url: m.url,
  pathname: m.pathname ?? '',
  nome: m.nome ?? 'arquivo',
  mime: m.mime ?? '',
  tamanho: m.tamanho ?? 0,
});

// ---------------------------------------------------------------------------
// Feed
// ---------------------------------------------------------------------------

const F = '/comunicacao/feed';

export const feedApi = {
  listar: (cursor?: string | null, limite = 10) =>
    apiClient.get<Pagina<Post>>(F, { params: { cursor: cursor || undefined, limite } }).then((r) => r.data),
  obter: (id: string) => apiClient.get<Post>(`${F}/${id}`).then((r) => r.data),
  criar: (dados: PostPayload) => apiClient.post<Post>(F, dados, { timeout: 30_000 }).then((r) => r.data),
  editar: (id: string, dados: PostPayload) =>
    apiClient.patch<Post>(`${F}/${id}`, dados, { timeout: 30_000 }).then((r) => r.data),
  excluir: (id: string) => apiClient.delete(`${F}/${id}`),
  fixar: (id: string) => apiClient.post<Post>(`${F}/${id}/fixar`).then((r) => r.data),
  curtir: (id: string, curtir: boolean) =>
    (curtir ? apiClient.post(`${F}/${id}/curtir`) : apiClient.delete(`${F}/${id}/curtir`)).then(
      (r) => r.data as { curtido: boolean; total_curtidas: number },
    ),
  curtidas: (id: string) => apiClient.get<Autor[]>(`${F}/${id}/curtidas`).then((r) => r.data),
  comentarios: (id: string, cursor?: string | null) =>
    apiClient
      .get<Pagina<Comentario>>(`${F}/${id}/comentarios`, { params: { cursor: cursor || undefined } })
      .then((r) => r.data),
  comentar: (id: string, texto: string, parentId?: string | null) =>
    apiClient.post<Comentario>(`${F}/${id}/comentarios`, { texto, parent_id: parentId || null }).then((r) => r.data),
  excluirComentario: (id: string) => apiClient.delete(`${F}/comentarios/${id}`),
  aprovar: (id: string) => apiClient.post(`${F}/comentarios/${id}/aprovar`),
  rejeitar: (id: string, motivo?: string) => apiClient.post(`${F}/comentarios/${id}/rejeitar`, { motivo: motivo || null }),
  moderarLote: (ids: string[], acao: 'aprovar' | 'rejeitar') =>
    apiClient.post<{ processados: number }>(`${F}/moderacao/lote`, { ids, acao }).then((r) => r.data),
  moderacao: (status: StatusComentario, offset = 0, limite = 30) =>
    apiClient
      .get<{ total: number; itens: ItemModeracao[] }>(`${F}/moderacao`, { params: { status, offset, limite } })
      .then((r) => r.data),
  resumoModeracao: () => apiClient.get<{ pendentes: number }>(`${F}/moderacao/resumo`).then((r) => r.data),
  linkPreview: (url: string) =>
    apiClient.post<LinkPreview>(`${F}/link-preview`, { url }, { timeout: 12_000 }).then((r) => r.data),
  responderChat: (id: string, texto: string) =>
    apiClient.post<{ conversa_id: string }>(`${F}/${id}/responder-chat`, { texto }).then((r) => r.data),
  enviarMidia: (arquivo: File, onProgresso?: (pct: number) => void) =>
    enviarArquivoDireto(`${F}/uploads`, arquivo, arquivo.name, onProgresso),
};

// ---------------------------------------------------------------------------
// Avisos
// ---------------------------------------------------------------------------

const A = '/comunicacao/avisos';

export const avisosApi = {
  listar: (params: { status?: StatusAviso | ''; busca?: string; offset?: number; limite?: number }) =>
    apiClient
      .get<{ total: number; itens: Aviso[] }>(A, {
        params: { status: params.status || undefined, busca: params.busca || undefined,
          offset: params.offset ?? 0, limite: params.limite ?? 20 },
      })
      .then((r) => r.data),
  obter: (id: string) => apiClient.get<Aviso>(`${A}/${id}`).then((r) => r.data),
  criar: (dados: AvisoPayload) => apiClient.post<Aviso>(A, dados).then((r) => r.data),
  editar: (id: string, dados: AvisoPayload) => apiClient.patch<Aviso>(`${A}/${id}`, dados).then((r) => r.data),
  excluir: (id: string) => apiClient.delete(`${A}/${id}`),
  duplicar: (id: string) => apiClient.post<Aviso>(`${A}/${id}/duplicar`).then((r) => r.data),
  alternar: (id: string) => apiClient.post<Aviso>(`${A}/${id}/alternar`).then((r) => r.data),
  estatisticas: (id: string, offset = 0) =>
    apiClient.get<EstatisticasAviso>(`${A}/${id}/estatisticas`, { params: { offset } }).then((r) => r.data),
  buscarUsuarios: (q: string) =>
    apiClient.get<UsuarioBusca[]>(`${A}/usuarios/busca`, { params: { q } }).then((r) => r.data),
  pendentes: () => apiClient.get<AvisoPopup[]>(`${A}/pendentes`).then((r) => r.data),
  visualizado: (id: string) => apiClient.post(`${A}/${id}/visualizado`),
  confirmar: (id: string) => apiClient.post(`${A}/${id}/confirmar`),
  enviarMidia: (arquivo: File, onProgresso?: (pct: number) => void) =>
    enviarArquivoDireto(`${A}/uploads`, arquivo, arquivo.name, onProgresso),
};

/** Mensagem de erro amigável a partir da resposta da API. */
export const mensagemErro = (e: unknown, padrao = 'Não foi possível concluir a ação.') => {
  const det = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof det === 'string') return det;
  if (Array.isArray(det) && det[0]?.msg) return String(det[0].msg).replace(/^Value error, /, '');
  return padrao;
};

/** Tempo relativo curto: "agora", "5 min", "3 h", "2 d" ou a data. */
export const tempoRelativo = (v: string) => {
  const s = Math.max(0, (Date.now() - new Date(v).getTime()) / 1000);
  if (s < 60) return 'agora';
  if (s < 3600) return `${Math.floor(s / 60)} min`;
  if (s < 86400) return `${Math.floor(s / 3600)} h`;
  if (s < 7 * 86400) return `${Math.floor(s / 86400)} d`;
  return new Date(v).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
};

/** Avisa o Sidebar para recarregar os contadores (moderação pendente). */
export const atualizarContadoresMenu = () => window.dispatchEvent(new Event('nexus:contadores-menu'));
