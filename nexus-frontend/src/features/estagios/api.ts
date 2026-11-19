import { apiClient } from '@/api/client';
import { ArquivoEnviado, enviarArquivoDireto } from '@/lib/uploadDireto';
import { nomeDoArquivo } from '@/lib/download';

export type Etapa = 'teologia_ministerio' | 'homiletica';
export type StatusEstagio = 'em_analise' | 'aprovado' | 'negado';
export type TipoArquivo = 'carta' | 'relatorio' | 'foto';
export type ChaveBase = 'manual' | 'carta_modelo' | 'relatorio_modelo';
export type Situacao = 'concluido' | 'pendente';

export const FOTOS_MIN = 5;
export const FOTOS_MAX = 10;

export const STATUS_ESTAGIO: Record<StatusEstagio, { label: string; classe: string; ponto: string }> = {
  em_analise: { label: 'Em Análise', classe: 'border-amber-500/40 bg-amber-500/15 text-amber-300', ponto: 'bg-amber-400' },
  aprovado: { label: 'Aprovado', classe: 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300', ponto: 'bg-emerald-400' },
  negado: { label: 'Negado', classe: 'border-red-500/40 bg-red-500/15 text-red-300', ponto: 'bg-red-400' },
};

export const ETAPA_TITULO: Record<Etapa, string> = {
  teologia_ministerio: 'Teologia do Ministério',
  homiletica: 'Homilética',
};

export interface ArquivoEstagio {
  id: string;
  tipo: TipoArquivo;
  nome: string;
  mime: string;
  tamanho: number;
  url: string;
  criado_em?: string | null;
}

export interface EventoEstagio {
  acao: 'enviado' | 'reenviado' | 'aprovado' | 'negado';
  comentario?: string | null;
  usuario_nome?: string | null;
  criado_em?: string | null;
}

export interface Submissao {
  id: string;
  etapa: Etapa;
  etapa_titulo: string;
  status: StatusEstagio;
  horas: number;
  comentario_feedback?: string | null;
  avaliado_em?: string | null;
  avaliado_por_nome?: string | null;
  enviado_em?: string | null;
  codigo_comprovante?: string | null;
  arquivos: ArquivoEstagio[];
  eventos: EventoEstagio[];
}

export interface EtapaAluno {
  etapa: Etapa;
  titulo: string;
  ordem: number;
  descricao: string;
  horas: number;
  bloqueada: boolean;
  pode_enviar: boolean;
  submissao?: Submissao | null;
}

export interface ArquivoBase {
  chave: ChaveBase;
  titulo: string;
  nome?: string | null;
  mime?: string | null;
  tamanho?: number | null;
  url?: string | null;
  atualizado_em?: string | null;
  disponivel: boolean;
}

export interface CentralAluno {
  video_url?: string | null;
  arquivos_base: ArquivoBase[];
  etapas: EtapaAluno[];
  horas_cumpridas: number;
  horas_totais: number;
}

export interface AlunoResumo {
  id: string;
  usuario_id?: string | null;
  nome: string;
  numero_matricula?: string | null;
  cpf?: string | null;
  email?: string | null;
  telefone?: string | null;
  foto_url?: string | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
}

export interface SubmissaoLista {
  id: string;
  etapa: Etapa;
  etapa_titulo: string;
  status: StatusEstagio;
  enviado_em?: string | null;
  avaliado_em?: string | null;
  aluno: AlunoResumo;
  total_fotos: number;
  miniatura_url?: string | null;
  codigo_comprovante?: string | null;
}

export interface SubmissaoDetalhe extends Submissao {
  aluno: AlunoResumo;
}

export interface FiltrosSubmissoes {
  status?: StatusEstagio | '';
  etapa?: Etapa | '';
  polo_id?: string;
  escola_id?: string;
  de?: string;
  ate?: string;
  busca?: string;
  limite?: number;
  offset?: number;
}

export interface FiltrosRelatorio {
  situacao?: Situacao | '';
  polo_id?: string;
  escola_id?: string;
  de?: string;
  ate?: string;
}

export interface RelatorioLinha {
  aluno_id: string;
  aluno_nome: string;
  numero_matricula?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
  teologia_status?: StatusEstagio | null;
  teologia_aprovado_em?: string | null;
  homiletica_status?: StatusEstagio | null;
  homiletica_aprovado_em?: string | null;
  horas_cumpridas: number;
  situacao: Situacao;
}

export interface Relatorio {
  total: number;
  concluidos: number;
  pendentes: number;
  linhas: RelatorioLinha[];
}

/** Remove filtros vazios da query string. */
const limpar = <T extends object>(filtros: T) =>
  Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '' && v !== undefined && v !== null));

const baixar = async (url: string, params: object, padrao: string) => {
  const r = await apiClient.get<Blob>(url, { params, responseType: 'blob', timeout: 60_000 });
  return { blob: r.data, nome: nomeDoArquivo(r.headers['content-disposition'], padrao) };
};

export const estagiosApi = {
  enviarArquivo: (arquivo: File, onProgresso?: (pct: number) => void): Promise<ArquivoEnviado> =>
    enviarArquivoDireto('/estagios/uploads', arquivo, arquivo.name, onProgresso),

  // Aluno
  central: () => apiClient.get<CentralAluno>('/estagios/central').then((r) => r.data),
  resumoAluno: () => apiClient.get<{ pendentes: number }>('/estagios/me/resumo').then((r) => r.data),
  enviar: (etapa: Etapa, dados: { carta: ArquivoEnviado; relatorio: ArquivoEnviado; fotos: ArquivoEnviado[] }) =>
    apiClient.post<Submissao>(`/estagios/etapas/${etapa}/enviar`, dados).then((r) => r.data),
  comprovante: (id: string) =>
    baixar(`/estagios/submissoes/${id}/comprovante.pdf`, {}, 'comprovante-estagio.pdf'),

  // Admin / unidade
  listar: (filtros: FiltrosSubmissoes) =>
    apiClient.get<{ total: number; itens: SubmissaoLista[] }>('/estagios/submissoes', { params: limpar(filtros) })
      .then((r) => r.data),
  detalhe: (id: string) => apiClient.get<SubmissaoDetalhe>(`/estagios/submissoes/${id}`).then((r) => r.data),
  avaliar: (id: string, status: 'aprovado' | 'negado', comentario: string) =>
    apiClient.post<SubmissaoDetalhe>(`/estagios/admin/submissoes/${id}/avaliar`, { status, comentario: comentario || null })
      .then((r) => r.data),
  resumoAdmin: () => apiClient.get<{ pendentes: number }>('/estagios/admin/resumo').then((r) => r.data),
  relatorio: (filtros: FiltrosRelatorio) =>
    apiClient.get<Relatorio>('/estagios/relatorio', { params: limpar(filtros) }).then((r) => r.data),
  exportar: (filtros: FiltrosRelatorio, formato: 'pdf' | 'xlsx' | 'csv') =>
    baixar('/estagios/relatorio/exportar', { ...limpar(filtros), formato }, `estagios.${formato}`),

  arquivosBase: () => apiClient.get<ArquivoBase[]>('/estagios/admin/arquivos-base').then((r) => r.data),
  substituirBase: (chave: ChaveBase, arquivo: ArquivoEnviado) =>
    apiClient.put<ArquivoBase[]>(`/estagios/admin/arquivos-base/${chave}`, arquivo).then((r) => r.data),
  config: () => apiClient.get<{ video_url?: string | null }>('/estagios/admin/config').then((r) => r.data),
  salvarConfig: (video_url: string) =>
    apiClient.put<{ video_url?: string | null }>('/estagios/admin/config', { video_url: video_url || null })
      .then((r) => r.data),
};

export const erroEstagio = (e: unknown, padrao = 'Não foi possível concluir a operação.') => {
  const det = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof det === 'string') return det;
  if (Array.isArray(det) && det[0]?.msg) return String(det[0].msg).replace(/^Value error, /, '');
  return padrao;
};

export const formatarTamanho = (bytes?: number | null) => {
  if (!bytes) return '';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB`;
};

export const formatarDataHora = (valor?: string | null) =>
  valor ? new Date(valor).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
