import { apiClient } from '@/api/client';
import { baixarArquivo, erroDeBlob, nomeDoArquivo } from '@/lib/download';
import { Capitulo, CapituloPayload, ReordenarPayload } from './api';
import { Anotacao, AulaAluno, Conclusao, DisciplinaPlayer, PlayerApi } from './alunoApi';

export type CategoriaTreinamento = 'treinamento' | 'workshop' | 'capacitacao';
export type PerfilAlvo = 'polo' | 'escola' | 'professor';

export interface Unidade {
  id: string;
  nome: string;
  polo_id?: string | null;
}

export interface Treinamento {
  id: string;
  titulo: string;
  descricao?: string | null;
  capa_url?: string | null;
  categoria: CategoriaTreinamento;
  carga_horaria?: number | null;
  perfis_alvo: PerfilAlvo[];
  polos: Unidade[];
  escolas: Unidade[];
  certificado_ativo: boolean;
  sequencial: boolean;
  data_inicio?: string | null;
  data_fim?: string | null;
  publicado: boolean;
  total_capitulos: number;
  total_aulas: number;
  total_participantes: number;
  total_concluintes: number;
  atualizado_em?: string | null;
}

export interface TreinamentoPayload {
  titulo: string;
  descricao?: string | null;
  capa_url?: string | null;
  categoria: CategoriaTreinamento;
  carga_horaria?: number | null;
  perfis_alvo: PerfilAlvo[];
  polo_ids: string[];
  escola_ids: string[];
  certificado_ativo: boolean;
  sequencial: boolean;
  data_inicio?: string | null;
  data_fim?: string | null;
  publicado: boolean;
}

export interface Participante {
  usuario_id: string;
  nome: string;
  perfil?: string | null;
  unidade?: string | null;
  aulas_concluidas: number;
  total_aulas: number;
  progresso_pct: number;
  ultimo_acesso_em?: string | null;
  concluido_em?: string | null;
  codigo_validacao?: string | null;
}

export interface TreinamentoCatalogo {
  id: string;
  titulo: string;
  descricao?: string | null;
  capa_url?: string | null;
  categoria: CategoriaTreinamento;
  carga_horaria?: number | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  certificado_ativo: boolean;
  total_aulas: number;
  aulas_concluidas: number;
  progresso_pct: number;
  duracao_min: number;
  concluido_em?: string | null;
  ultimo_acesso_em?: string | null;
  disponivel: boolean;
}

export interface ValidacaoCertificado {
  valido: boolean;
  codigo: string;
  nome?: string | null;
  treinamento?: string | null;
  categoria?: string | null;
  carga_horaria?: number | null;
  concluido_em?: string | null;
}

const T = '/ava/treinamentos';

export const treinamentosAdminApi = {
  listar: (params: { q?: string; situacao?: 'todos' | 'publicado' | 'rascunho'; limite?: number; offset?: number }) =>
    apiClient.get<{ items: Treinamento[]; total: number }>(`${T}/admin`, { params }).then((r) => r.data),
  obter: (id: string) => apiClient.get<Treinamento>(`${T}/admin/${id}`).then((r) => r.data),
  unidades: () => apiClient.get<{ polos: Unidade[]; escolas: Unidade[] }>(`${T}/admin/unidades`).then((r) => r.data),
  criar: (payload: TreinamentoPayload) => apiClient.post<Treinamento>(`${T}/admin`, payload).then((r) => r.data),
  atualizar: (id: string, payload: TreinamentoPayload) => apiClient.put<Treinamento>(`${T}/admin/${id}`, payload).then((r) => r.data),
  alternar: (id: string) => apiClient.post<Treinamento>(`${T}/admin/${id}/alternar`).then((r) => r.data),
  duplicar: (id: string) => apiClient.post<Treinamento>(`${T}/admin/${id}/duplicar`).then((r) => r.data),
  excluir: (id: string) => apiClient.delete(`${T}/admin/${id}`),
  estrutura: (id: string) =>
    apiClient.get<{ treinamento: Treinamento; capitulos: Capitulo[] }>(`${T}/admin/${id}/estrutura`).then((r) => r.data),
  criarCapitulo: (id: string, payload: CapituloPayload) =>
    apiClient.post<Capitulo>(`${T}/admin/${id}/capitulos`, payload).then((r) => r.data),
  reordenar: (id: string, payload: ReordenarPayload) => apiClient.put(`${T}/admin/${id}/reordenar`, payload),
  participantes: (id: string) => apiClient.get<Participante[]>(`${T}/admin/${id}/participantes`).then((r) => r.data),
};

/** API do player para treinamentos (mesmo contrato da Sala de Aula Virtual). */
export const treinamentoPlayerApi: PlayerApi = {
  disciplina: (id) => apiClient.get<DisciplinaPlayer>(`${T}/${id}`).then((r) => r.data),
  aula: (id) => apiClient.get<AulaAluno>(`${T}/aulas/${id}`).then((r) => r.data),
  progresso: (id, percentual, posicao_seg) =>
    apiClient.post<Conclusao | null>(`${T}/aulas/${id}/progresso`, { percentual, posicao_seg }).then((r) => r.data),
  concluir: (id) => apiClient.post<Conclusao>(`${T}/aulas/${id}/concluir`).then((r) => r.data),
  avaliarAula: (id, nota) => apiClient.put(`${T}/aulas/${id}/minha-nota`, { nota }),
  criarAnotacao: (aulaId, texto, posicao_seg) =>
    apiClient.post<Anotacao>(`${T}/aulas/${aulaId}/anotacoes`, { texto, posicao_seg }).then((r) => r.data),
  atualizarAnotacao: (id, texto) => apiClient.put<Anotacao>(`${T}/anotacoes/${id}`, { texto }).then((r) => r.data),
  excluirAnotacao: (id) => apiClient.delete(`${T}/anotacoes/${id}`),
};

export const treinamentosApi = {
  meus: () => apiClient.get<TreinamentoCatalogo[]>(`${T}/meus`).then((r) => r.data),
  baixarCertificado: async (id: string) => {
    try {
      const r = await apiClient.get<Blob>(`${T}/${id}/certificado`, { responseType: 'blob' });
      baixarArquivo(r.data, nomeDoArquivo(r.headers['content-disposition'], 'certificado.pdf'));
    } catch (e) {
      throw new Error(await erroDeBlob(e, 'Não foi possível gerar o certificado.'));
    }
  },
  validar: (codigo: string) =>
    apiClient.get<ValidacaoCertificado>(`${T}/certificados/validar/${encodeURIComponent(codigo)}`).then((r) => r.data),
};

export const CATEGORIA: Record<CategoriaTreinamento, { rotulo: string; classe: string }> = {
  treinamento: { rotulo: 'Treinamento', classe: 'bg-blue-500/90 text-white' },
  workshop: { rotulo: 'Workshop', classe: 'bg-purple-500/90 text-white' },
  capacitacao: { rotulo: 'Capacitação', classe: 'bg-emerald-500/90 text-white' },
};

export const PERFIS_ALVO: { valor: PerfilAlvo; rotulo: string }[] = [
  { valor: 'polo', rotulo: 'Polos' },
  { valor: 'escola', rotulo: 'Escolas' },
  { valor: 'professor', rotulo: 'Professores' },
];
