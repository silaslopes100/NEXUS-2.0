import { apiClient } from '@/api/client';
import { ArquivoEnviado, enviarArquivoDireto } from '@/lib/uploadDireto';

export type TipoAula = 'conteudo' | 'avaliacao';
export type TipoItem = 'video_embed' | 'arquivo' | 'imagem' | 'link' | 'texto';
export type Provedor = 'youtube' | 'vimeo' | 'panda' | 'iframe';

export interface DisciplinaAva {
  id: string;
  nome: string;
  curso_id?: string | null;
  curso_nome?: string | null;
  semestre?: number | null;
  ordem?: number | null;
  ativo: boolean;
  capa_url?: string | null;
  publicado: boolean;
  sequencial: boolean;
  total_capitulos: number;
  total_aulas: number;
  atualizado_em?: string | null;
}

export interface ConfigAva {
  disciplina_id: string;
  capa_url?: string | null;
  descricao_ava?: string | null;
  sequencial: boolean;
  publicado: boolean;
}

export interface ItemAula {
  id: string;
  aula_id: string;
  tipo: TipoItem;
  titulo?: string | null;
  url?: string | null;
  provedor?: Provedor | null;
  embed_id?: string | null;
  conteudo_html?: string | null;
  arquivo_nome?: string | null;
  arquivo_mime?: string | null;
  arquivo_tamanho?: number | null;
  permite_download: boolean;
  ordem: number;
}

export interface ItemPayload {
  tipo: TipoItem;
  titulo?: string | null;
  url?: string | null;
  conteudo_html?: string | null;
  arquivo?: ArquivoEnviado | null;
  permite_download: boolean;
}

export interface Aula {
  id: string;
  capitulo_id: string;
  titulo: string;
  descricao?: string | null;
  tipo: TipoAula;
  avaliacao_id?: string | null;
  avaliacao_titulo?: string | null;
  avaliacao_disciplina_nome?: string | null;
  duracao_min?: number | null;
  ordem: number;
  publicado: boolean;
  obrigatoria: boolean;
  liberar_apos_dias?: number | null;
  capa_url?: string | null;
  itens: ItemAula[];
}

export interface AulaPayload {
  titulo: string;
  descricao?: string | null;
  tipo: TipoAula;
  avaliacao_id?: string | null;
  duracao_min?: number | null;
  publicado: boolean;
  obrigatoria: boolean;
  liberar_apos_dias?: number | null;
  capa_url?: string | null;
}

export interface Capitulo {
  id: string;
  titulo: string;
  descricao?: string | null;
  ordem: number;
  publicado: boolean;
  aulas: Aula[];
}

export interface CapituloPayload {
  titulo: string;
  descricao?: string | null;
  publicado: boolean;
}

export interface Estrutura {
  disciplina: DisciplinaAva;
  config: ConfigAva;
  capitulos: Capitulo[];
}

export interface AvaliacaoOpcao {
  avaliacao_id: string;
  titulo: string;
  disciplina_id: string;
  disciplina_nome: string;
  ativo: boolean;
  total_questoes: number;
}

export interface EmbedResolvido {
  url: string;
  provedor: Provedor;
  embed_id?: string | null;
  embed_url: string;
  thumbnail_url?: string | null;
}

export interface ReordenarPayload {
  capitulos?: { id: string; ordem: number }[];
  aulas?: { id: string; ordem: number; capitulo_id: string }[];
  itens?: { id: string; ordem: number }[];
}

const A = '/ava/admin';

export const avaAdminApi = {
  disciplinas: (cursoId: string, q?: string) =>
    apiClient.get<DisciplinaAva[]>(`${A}/cursos/${cursoId}/disciplinas`, { params: { q: q || undefined } }).then((r) => r.data),
  avaliacoesDoCurso: (cursoId: string) =>
    apiClient.get<AvaliacaoOpcao[]>(`${A}/cursos/${cursoId}/avaliacoes`).then((r) => r.data),
  estrutura: (disciplinaId: string) =>
    apiClient.get<Estrutura>(`${A}/disciplinas/${disciplinaId}/estrutura`).then((r) => r.data),
  salvarConfig: (disciplinaId: string, payload: Omit<ConfigAva, 'disciplina_id'>) =>
    apiClient.put<ConfigAva>(`${A}/disciplinas/${disciplinaId}/config`, payload).then((r) => r.data),
  reordenar: (disciplinaId: string, payload: ReordenarPayload) =>
    apiClient.put<Estrutura>(`${A}/disciplinas/${disciplinaId}/reordenar`, payload).then((r) => r.data),

  criarCapitulo: (disciplinaId: string, payload: CapituloPayload) =>
    apiClient.post<Capitulo>(`${A}/disciplinas/${disciplinaId}/capitulos`, payload).then((r) => r.data),
  atualizarCapitulo: (id: string, payload: CapituloPayload) =>
    apiClient.put<Capitulo>(`${A}/capitulos/${id}`, payload).then((r) => r.data),
  duplicarCapitulo: (id: string) => apiClient.post<Capitulo>(`${A}/capitulos/${id}/duplicar`).then((r) => r.data),
  excluirCapitulo: (id: string) => apiClient.delete(`${A}/capitulos/${id}`),

  criarAula: (capituloId: string, payload: AulaPayload) =>
    apiClient.post<Aula>(`${A}/aulas`, { ...payload, capitulo_id: capituloId }).then((r) => r.data),
  obterAula: (id: string) => apiClient.get<Aula>(`${A}/aulas/${id}`).then((r) => r.data),
  atualizarAula: (id: string, payload: AulaPayload) => apiClient.put<Aula>(`${A}/aulas/${id}`, payload).then((r) => r.data),
  excluirAula: (id: string) => apiClient.delete(`${A}/aulas/${id}`),

  criarItem: (aulaId: string, payload: ItemPayload) =>
    apiClient.post<ItemAula>(`${A}/aulas/${aulaId}/itens`, payload).then((r) => r.data),
  atualizarItem: (id: string, payload: ItemPayload) =>
    apiClient.put<ItemAula>(`${A}/itens/${id}`, payload).then((r) => r.data),
  excluirItem: (id: string) => apiClient.delete(`${A}/itens/${id}`),

  resolverEmbed: (url: string) => apiClient.post<EmbedResolvido>(`${A}/embed/resolver`, { url }).then((r) => r.data),
  enviarArquivo: (arquivo: File, onProgresso?: (pct: number) => void) =>
    enviarArquivoDireto(`${A}/uploads`, arquivo, arquivo.name, onProgresso),
};

export const ACEITA_DOCUMENTOS = '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.zip';
export const ACEITA_IMAGENS = 'image/jpeg,image/png,image/webp,image/gif';

export const ROTULO_ITEM: Record<TipoItem, string> = {
  video_embed: 'Vídeo',
  arquivo: 'Arquivo',
  imagem: 'Imagem',
  link: 'Link',
  texto: 'Texto',
};

export const ROTULO_PROVEDOR: Record<Provedor, string> = {
  youtube: 'YouTube',
  vimeo: 'Vimeo',
  panda: 'Panda Video',
  iframe: 'Player externo',
};

/** Soma a duração (min) das aulas de um capítulo. */
export const duracaoCapitulo = (c: Capitulo) => c.aulas.reduce((s, a) => s + (a.duracao_min || 0), 0);

export const formatarDuracao = (min: number) => {
  if (!min) return '';
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}h${m ? ` ${m}min` : ''}` : `${m}min`;
};
