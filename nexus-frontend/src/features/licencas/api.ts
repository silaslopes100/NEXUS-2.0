import { apiClient } from '@/api/client';

export interface LicencaKpis {
  total_licencas_compradas: number;
  total_licencas_vendidas_alunos: number;
  total_licencas_nao_vendidas: number;
  total_nao_vendidas_escolas: number;
  total_nao_vendidas_polo: number;
  taxa_conversao_global: number;
  taxa_distribuicao: number;
}

export interface EscolaLicencaKpis {
  licencas_recebidas: number;
  licencas_vendidas: number;
  licencas_nao_vendidas: number;
  taxa_conversao: number;
  taxa_ociosidade: number;
}

export interface MovimentacaoLicenca {
  id: string;
  tipo: string;
  polo_id?: string;
  escola_id?: string;
  aluno_id?: string;
  materia_id?: string | null;
  disciplina_nome?: string | null;
  quantidade: number;
  valor_unitario?: number;
  status: string;
  observacao?: string;
  criado_em?: string;
}

/** Saldo por disciplina. `materia_id` nulo = "Sem disciplina" (saldo anterior à Fase 3A). */
export interface EstoqueDisciplinaItem {
  materia_id: string | null;
  disciplina_nome: string | null;
  quantidade_disponivel: number;
  quantidade_vendida: number;
}

export interface EstoqueDisciplina {
  polo_id?: string | null;
  escola_id?: string | null;
  total_disponivel: number;
  total_vendida: number;
  items: EstoqueDisciplinaItem[];
}

export interface LicencaAlunoAtiva {
  id: string;
  aluno_id: string;
  materia_id: string | null;
  disciplina_nome: string | null;
  numero_licenca?: string | null;
  ativada_em?: string | null;
}

export const SEM_DISCIPLINA = 'Sem disciplina';
export const nomeDisciplina = (item: { materia_id?: string | null; disciplina_nome?: string | null }) =>
  item.materia_id ? item.disciplina_nome || 'Disciplina removida' : SEM_DISCIPLINA;

export interface CompraPayload { quantidade: number; fornecedor: string; valor_unitario: number; data: string; disciplina_id?: string | null; }
export interface DistribuicaoPayload { escola_id: string; quantidade: number; disciplina_id?: string | null; }
export interface VendaPayload { aluno_id: string; quantidade: number; disciplina_id?: string | null; }
export interface ReclassificarPayload { de_disciplina_id?: string | null; para_disciplina_id?: string | null; quantidade: number; }

export interface AlunoTurmaLicenca {
  aluno_id: string;
  nome: string;
  numero_matricula?: string | null;
  escola_id?: string | null;
  possui_licenca: boolean;
  numero_licenca?: string | null;
}

export interface TurmaAlunosLicenca {
  turma: { id: string; nome?: string | null };
  saldo_disponivel: number;
  alunos: AlunoTurmaLicenca[];
}

export interface DistribuicaoAlunosResultado {
  distribuidas: number;
  ja_possuiam: number;
  licencas: { licenca_id: string; aluno_id: string; aluno_nome?: string | null; numero_licenca: string }[];
}

export interface TurmaOpcao { id: string; nome: string; escola_id?: string | null }

export const licencasApi = {
  async turmasDoCurso(cursoId: string, poloId: string) {
    const data = (await apiClient.get('/turmas', { params: { curso_id: cursoId, polo_id: poloId } })).data;
    const itens = Array.isArray(data) ? data : (data?.items || []);
    return itens.map((t: TurmaOpcao) => ({ id: t.id, nome: t.nome, escola_id: t.escola_id })) as TurmaOpcao[];
  },
  async alunosTurma(poloId: string, turmaId: string, disciplinaId: string) {
    return (await apiClient.get<TurmaAlunosLicenca>(`/polos/${poloId}/licencas/turmas/${turmaId}/alunos`,
      { params: { disciplina_id: disciplinaId } })).data;
  },
  async distribuirAlunos(poloId: string, payload: { disciplina_id: string; turma_id: string; aluno_ids: string[] }) {
    return (await apiClient.post<DistribuicaoAlunosResultado>(`/polos/${poloId}/licencas/distribuir-alunos`, payload)).data;
  },
  async liberar(poloId: string, payload: { itens: { disciplina_id: string; quantidade: number }[]; enviar_livros: boolean; observacao?: string }) {
    return (await apiClient.post<{ message: string }>(`/polos/${poloId}/licencas/liberar`, payload)).data;
  },
  async cartoes(licencaIds: string[]) {
    return (await apiClient.post<Blob>('/licencas-alunos/cartoes', licencaIds, { responseType: 'blob' })).data;
  },
  async novoNumero(licencaId: string) {
    return (await apiClient.post<{ licenca_id: string; numero_licenca: string }>(`/licencas-alunos/${licencaId}/novo-numero`)).data;
  },
  async getKpis(poloId: string) { return (await apiClient.get<LicencaKpis>(`/polos/${poloId}/dashboard/kpis`)).data; },
  async getKpisEscola(escolaId: string) { return (await apiClient.get<EscolaLicencaKpis>(`/escolas/${escolaId}/dashboard/kpis`)).data; },
  async listMovimentacoes(poloId: string, params?: { limit?: number; offset?: number }) { return (await apiClient.get<{ total: number; items: MovimentacaoLicenca[] }>(`/polos/${poloId}/licencas/movimentacoes`, { params })).data; },
  async listMovimentacoesEscola(escolaId: string, params?: { limit?: number; offset?: number }) { return (await apiClient.get<{ total: number; items: MovimentacaoLicenca[] }>(`/escolas/${escolaId}/licencas/movimentacoes`, { params })).data; },
  async comprar(poloId: string, payload: CompraPayload) { return (await apiClient.post(`/polos/${poloId}/licencas/compra`, payload)).data; },
  async distribuir(poloId: string, payload: DistribuicaoPayload) { return (await apiClient.post(`/polos/${poloId}/licencas/distribuir`, payload)).data; },
  async vender(escolaId: string, payload: VendaPayload) { return (await apiClient.post(`/escolas/${escolaId}/licencas/vender`, payload)).data; },
  async devolverEscola(escolaId: string, quantidade: number, disciplinaId?: string | null) { return (await apiClient.post(`/escolas/${escolaId}/licencas/devolver`, { quantidade, disciplina_id: disciplinaId || null })).data; },
  async devolverAluno(alunoId: string, licencaId?: string) { return (await apiClient.post(`/alunos/${alunoId}/licencas/devolver`, licencaId ? { licenca_id: licencaId } : undefined)).data; },
  async estoquePolo(poloId: string) { return (await apiClient.get<EstoqueDisciplina>(`/polos/${poloId}/licencas/estoque`)).data; },
  async estoqueEscola(escolaId: string) { return (await apiClient.get<EstoqueDisciplina>(`/escolas/${escolaId}/licencas/estoque`)).data; },
  async licencasAluno(alunoId: string) { return (await apiClient.get<LicencaAlunoAtiva[]>(`/alunos/${alunoId}/licencas`)).data; },
  async reclassificar(poloId: string, payload: ReclassificarPayload) { return (await apiClient.post(`/polos/${poloId}/licencas/reclassificar`, payload)).data; },
};
