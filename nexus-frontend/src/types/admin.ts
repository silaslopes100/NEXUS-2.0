export interface PerfilItem {
  id: string;
  nome: string;
  descricao?: string | null;
}

export interface PermissaoItem {
  id: string;
  chave: string;
  descricao?: string | null;
}

export interface UsuarioAdmin {
  id: string;
  nome: string;
  sobrenome?: string;
  email?: string | null;
  cpf?: string | null;
  telefone?: string | null;
  celular?: string | null;
  foto_url?: string | null;
  status: 'ativo' | 'inativo' | 'bloqueado' | string;
  perfil_id?: string | null;
  perfil_nome?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
  polo_nome?: string | null;
  escola_nome?: string | null;
  permissoes: string[];
  ultimo_login_em?: string | null;
  criado_em?: string | null;
  atualizado_em?: string | null;
}

export interface AlunoVinculoFicha {
  id: string;
  usuario_id?: string | null;
  numero_matricula?: string | null;
  modalidade?: string | null;
  status?: string | null;
  data_nascimento?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
}

export interface ProfessorVinculoFicha {
  id: string;
  usuario_id?: string | null;
  materias: string[];
  data_inicio?: string | null;
  quantidade_aulas: number;
  horas_totais?: number | null;
  valor_hora_aula?: number | null;
  status?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
}

export interface UsuarioFicha extends UsuarioAdmin {
  aluno?: AlunoVinculoFicha | null;
  professor?: ProfessorVinculoFicha | null;
}

export interface MetricasAlunoFicha {
  matriculas_total: number;
  total_notas: number;
  media_notas?: number | null;
  total_presencas: number;
  presencas_positivas: number;
  percentual_presenca?: number | null;
  certificados_total: number;
}

export interface MetricasProfessorFicha {
  aulas_registradas: number;
  treinamentos_total: number;
}

export interface MetricasUnidadeFicha {
  escolas: number;
  turmas: number;
  professores: number;
  alunos: number;
  aulas: number;
  licencas_estoque: number;
  licencas_atribuidas: number;
  licencas_movimentacoes: number;
  pedidos_licencas: number;
  pedidos_livros: number;
}

export interface ConsolidadoAcessoFicha {
  status: string;
  perfil_nome?: string | null;
  ultimo_login_em?: string | null;
  criado_em?: string | null;
  atualizado_em?: string | null;
  permissoes: string[];
}

export interface ResumoMetricasUsuario {
  usuario_id: string;
  aluno?: MetricasAlunoFicha | null;
  professor?: MetricasProfessorFicha | null;
  unidade?: MetricasUnidadeFicha | null;
  consolidado: ConsolidadoAcessoFicha;
}

export interface UsuarioListResponse {
  total: number;
  items: UsuarioAdmin[];
  limit: number;
  offset: number;
}

export interface UsuarioCreatePayload {
  nome: string;
  sobrenome?: string;
  email: string;
  cpf?: string;
  senha: string;
  perfil_id?: string;
  perfil_nome?: string;
  polo_id?: string;
  escola_id?: string;
  telefone?: string;
  celular?: string;
  status?: string;
  permissoes?: string[];
}

export interface UsuarioUpdatePayload {
  nome?: string;
  sobrenome?: string;
  email?: string;
  cpf?: string;
  perfil_id?: string;
  perfil_nome?: string;
  polo_id?: string;
  escola_id?: string;
  telefone?: string;
  celular?: string;
  status?: string;
  permissoes?: string[];
}

export interface LogAuditoria {
  id: string;
  usuario_id?: string | null;
  usuario_nome?: string | null;
  usuario_email?: string | null;
  acao: string;
  entidade?: string | null;
  entidade_id?: string | null;
  dados_antes?: Record<string, any> | null;
  dados_depois?: Record<string, any> | null;
  ip?: string | null;
  criado_em?: string | null;
}

export interface LogAuditoriaListResponse {
  total: number;
  items: LogAuditoria[];
  limit: number;
  offset: number;
}

export interface Configuracao {
  id?: string | null;
  chave: string;
  valor: any;
  criado_em?: string | null;
  atualizado_em?: string | null;
}

export interface EtlSyncRun {
  id: number;
  modo: string;
  iniciado_em: string;
  finalizado_em?: string | null;
  total_lido: number;
  total_inserido: number;
  total_atualizado: number;
  total_erro: number;
  status: string;
  duracao_segundos?: number | null;
  total_erros_detalhados?: number;
}

export interface EtlSyncRunListResponse {
  total: number;
  items: EtlSyncRun[];
  taxa_sucesso_geral?: number | null;
}

export interface EtlErro {
  id: number;
  execucao_id?: number | null;
  tabela_origem?: string | null;
  id_origem?: string | null;
  erro?: string | null;
  linha_raw?: any;
  criado_em?: string | null;
}

export interface AdminDashboardMetrics {
  alunos_ativos: number;
  matriculas_total: number;
  polos_ativos: number;
  escolas_ativas: number;
  professores_ativos: number;
  certificados_emitidos: number;
  licencas_em_estoque: number;
}
