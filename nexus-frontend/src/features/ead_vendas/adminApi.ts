// Gestão de Matrículas EAD (admin) — espelha app/modules/ead_vendas/admin_schemas.py.
import { apiClient } from '@/api/client';
import type { PedidoAluno, TurmaLoja } from './api';

export type TipoMatricula = 'regular' | 'bolsista';
export type MotivoLiberacao = 'bolsa' | 'pagamento_externo' | 'problema_pagamento' | 'cortesia' | 'outro';

export interface ResumoEad {
  matriculas_ativas: number;
  bolsistas: number;
  canceladas: number;
  novas_site: number;
  novas_manuais: number;
  compras_pagas: number;
  compras_pendentes: number;
  liberacoes_manuais: number;
  receita: number;
  vendas_com_livro: number;
}

export interface TurmaEadOpcao { id: string; nome: string; codigo?: string | null; curso_id: string; curso_nome: string; aberta: boolean }

export interface MatriculaEad {
  id: string;
  aluno_id: string;
  nome: string;
  email?: string | null;
  cpf?: string | null;
  numero_matricula?: string | null;
  curso_id?: string | null;
  curso_nome?: string | null;
  turma_id?: string | null;
  turma_nome?: string | null;
  tipo: TipoMatricula;
  origem: 'site' | 'manual' | 'legado';
  status: 'ativa' | 'cancelada';
  data_matricula?: string | null;
  observacao?: string | null;
  disciplinas_pagas: number;
  disciplinas_liberadas: number;
  disciplinas_pendentes: number;
  ultimo_movimento?: string | null;
  aluno_desistente: boolean;
}

export interface CompraEadAdmin {
  id: string;
  disciplina_id?: string | null;
  disciplina_nome?: string | null;
  turma_nome?: string | null;
  origem: 'loja' | 'manual' | 'bolsa' | 'legado';
  status_pagamento?: string | null;
  valor_pago?: number | null;
  com_livro: boolean;
  liberada_em?: string | null;
  motivo?: string | null;
  motivo_texto?: string | null;
  liberada_por_nome?: string | null;
  pedido_id?: string | null;
  pedido_numero?: string | null;
  criado_em?: string | null;
  cancelada_em?: string | null;
  pode_revogar: boolean;
}

export interface MovimentacaoEad {
  evento: string;
  data?: string | null;
  aluno_id?: string | null;
  aluno_nome?: string | null;
  numero_matricula?: string | null;
  turma_nome?: string | null;
  disciplina_nome?: string | null;
  valor?: number | null;
  detalhe?: string | null;
  pedido_id?: string | null;
  autor_nome?: string | null;
}

export interface FichaEad {
  aluno_id: string;
  usuario_id: string;
  nome: string;
  email?: string | null;
  cpf?: string | null;
  celular?: string | null;
  numero_matricula?: string | null;
  status_aluno?: string | null;
  matriculas: MatriculaEad[];
  turmas: TurmaLoja[];
  compras: CompraEadAdmin[];
  pedidos: PedidoAluno[];
  movimentacoes: MovimentacaoEad[];
}

export interface AlunoEadBusca { aluno_id: string; nome: string; email?: string | null; cpf?: string | null; numero_matricula?: string | null }

export interface NovoAluno { nome: string; sobrenome: string; email: string; cpf: string; celular?: string; data_nascimento: string }

export interface MatriculaManualPayload {
  aluno_id?: string;
  novo_aluno?: NovoAluno;
  turma_id: string;
  tipo: TipoMatricula;
  observacao?: string;
  ignorar_vagas?: boolean;
}

export type Filtros = Record<string, string | undefined>;

const limpo = (f: Filtros) => Object.fromEntries(Object.entries(f).filter(([, v]) => v));

export const gestaoEadApi = {
  resumo: (f: Filtros) => apiClient.get<ResumoEad>('/ead/admin/resumo', { params: limpo(f) }).then((r) => r.data),
  turmas: () => apiClient.get<TurmaEadOpcao[]>('/ead/admin/turmas').then((r) => r.data),
  buscarAlunos: (q: string) => apiClient.get<AlunoEadBusca[]>('/ead/admin/alunos', { params: { q } }).then((r) => r.data),
  matriculas: (f: Filtros, limit: number, offset: number) =>
    apiClient.get<{ total: number; items: MatriculaEad[] }>('/ead/admin/matriculas', { params: { ...limpo(f), limit, offset } }).then((r) => r.data),
  matricular: (p: MatriculaManualPayload) =>
    apiClient.post<{ matricula_id: string; aluno_id: string; convite_enviado?: boolean | null }>('/ead/admin/matriculas', p).then((r) => r.data),
  atualizar: (id: string, p: { tipo?: TipoMatricula; turma_id?: string; observacao?: string }) =>
    apiClient.patch<MatriculaEad>(`/ead/admin/matriculas/${id}`, p).then((r) => r.data),
  cancelar: (id: string, motivo: string) => apiClient.post<MatriculaEad>(`/ead/admin/matriculas/${id}/cancelar`, { motivo }).then((r) => r.data),
  reativar: (id: string) => apiClient.post<MatriculaEad>(`/ead/admin/matriculas/${id}/reativar`).then((r) => r.data),
  ficha: (alunoId: string) => apiClient.get<FichaEad>(`/ead/admin/alunos/${alunoId}`).then((r) => r.data),
  liberar: (alunoId: string, disciplinaId: string, p: { motivo: MotivoLiberacao; texto?: string; turma_id?: string }) =>
    apiClient.post<FichaEad>(`/ead/admin/alunos/${alunoId}/disciplinas/${disciplinaId}/liberar`, p).then((r) => r.data),
  revogar: (compraId: string, motivo: string) => apiClient.post<FichaEad>(`/ead/admin/compras/${compraId}/revogar`, { motivo }).then((r) => r.data),
  movimentacoes: (f: Filtros, limit: number, offset: number) =>
    apiClient.get<{ total: number; items: MovimentacaoEad[] }>('/ead/admin/movimentacoes', { params: { ...limpo(f), limit, offset } }).then((r) => r.data),
};

export const MOTIVOS: { valor: MotivoLiberacao; rotulo: string }[] = [
  { valor: 'pagamento_externo', rotulo: 'Pagamento recebido por fora' },
  { valor: 'problema_pagamento', rotulo: 'Problema no pagamento' },
  { valor: 'bolsa', rotulo: 'Bolsa' },
  { valor: 'cortesia', rotulo: 'Cortesia' },
  { valor: 'outro', rotulo: 'Outro' },
];
export const ROTULO_MOTIVO: Record<string, string> = Object.fromEntries(MOTIVOS.map((m) => [m.valor, m.rotulo]));

export const EVENTO: Record<string, { rotulo: string; cor: string }> = {
  matricula_site: { rotulo: 'Inscrição pelo site', cor: 'bg-blue-500' },
  matricula_manual: { rotulo: 'Matrícula manual', cor: 'bg-indigo-500' },
  matricula: { rotulo: 'Matrícula', cor: 'bg-slate-500' },
  matricula_cancelada: { rotulo: 'Matrícula cancelada', cor: 'bg-red-500' },
  ead_matricula_reativada: { rotulo: 'Matrícula reativada', cor: 'bg-emerald-500' },
  ead_tipo_alterado: { rotulo: 'Tipo alterado', cor: 'bg-violet-500' },
  ead_transferencia: { rotulo: 'Transferência de turma', cor: 'bg-cyan-500' },
  compra_criada: { rotulo: 'Compra iniciada', cor: 'bg-amber-500' },
  pagamento_confirmado: { rotulo: 'Pagamento confirmado', cor: 'bg-emerald-500' },
  liberacao_manual: { rotulo: 'Liberação manual', cor: 'bg-teal-500' },
  compra_cancelada: { rotulo: 'Compra cancelada', cor: 'bg-slate-500' },
  ead_compra_revogada: { rotulo: 'Liberação/compra revogada', cor: 'bg-red-400' },
  livro_enviado: { rotulo: 'Livro enviado', cor: 'bg-orange-500' },
};

export const ORIGEM_COMPRA: Record<string, string> = { loja: 'Loja', manual: 'Liberação manual', bolsa: 'Bolsa', legado: 'Legado' };
