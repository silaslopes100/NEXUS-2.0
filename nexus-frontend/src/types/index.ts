export interface User {
  id: string
  nome: string
  sobrenome: string
  email: string
  cpf: string
  telefone?: string
  celular?: string
  foto_url?: string
  perfil_id: string
  perfil_nome?: string
  polo_id?: string
  polo_nome?: string
  escola_id?: string
  escola_nome?: string
  status: 'ativo' | 'inativo' | 'bloqueado'
  ultimo_login_em?: string
  criado_em: string
  atualizado_em: string
  permissoes?: Permission[]
}

export interface Permission {
  id: string
  chave: string
  descricao: string
  modulo: string
}

export interface Profile {
  id: string
  nome: string
  descricao: string
  permissoes: string[]
}

export interface Polo {
  id: string
  nome: string
  responsavel: string
  cpf: string
  email: string
  endereco: string
  logradouro?: string
  numero?: string
  bairro?: string
  cidade?: string
  uf?: string
  cep?: string
  usuario_id: string
  usuario_nome?: string
  usuario_email?: string
  status: 'ativo' | 'inativo'
  criado_em: string
  atualizado_em: string
  total_alunos?: number
  total_escolas?: number
  total_licencas?: number
  escolas_vinculadas?: Escola[]
}

export interface Escola {
  id: string
  nome: string
  polo_id: string
  polo_nome?: string
  responsavel: string
  cpf: string
  email: string
  endereco: string
  logradouro?: string
  numero?: string
  bairro?: string
  cidade?: string
  uf?: string
  cep?: string
  usuario_id: string
  usuario_nome?: string
  usuario_email?: string
  status: 'ativo' | 'inativo'
  criado_em: string
  atualizado_em: string
  total_alunos?: number
}

export interface Curso {
  id: string
  nome: string
  descricao?: string
  carga_horaria: number
  grade_curricular?: string
  status: 'ativo' | 'inativo'
  criado_em: string
  atualizado_em: string
}

export interface Modulo {
  id: string
  curso_id: string
  curso_nome?: string
  nome: string
  ordem: number
  conteudo?: string
  carga_horaria: number
  criado_em: string
  atualizado_em: string
  materias?: Materia[]
}

export interface Materia {
  id: string
  curso_id?: string
  modulo_id?: string
  nome: string
  descricao?: string
  carga_horaria: number
  total_aulas_previstas: number
  ordem?: number
  tipo?: 'teoria' | 'pratica' | 'estagio'
  criado_em: string
  atualizado_em: string
}

export interface Aluno {
  id: string
  usuario_id: string
  nome: string
  sobrenome: string
  email?: string
  cpf?: string
  data_nascimento?: string
  pais?: string
  estado?: string
  polo_id?: string
  polo_nome?: string
  escola_id?: string
  escola_nome?: string
  modalidade: 'polo' | 'escola' | 'ead'
  numero_matricula?: string
  curso_id?: string
  curso_nome?: string
  semestre?: number
  ano?: number
  status: 'ativo' | 'inativo' | 'bloqueado' | 'desistente'
  quantidade_presencas: number
  percentual_presenca: number
  ultima_movimentacao_em?: string
  criado_em: string
  atualizado_em: string
  presencas_por_materia?: PresencaMateriaItem[]
  notas?: NotaHistoricoItem[]
  certificados?: CertificadoResumoItem[]
}

export interface Matricula {
  id: string
  aluno_id: string
  aluno_nome?: string
  polo_id?: string
  polo_nome?: string
  escola_id?: string
  escola_nome?: string
  curso_id: string
  curso_nome?: string
  semestre: number
  ano: number
  status: 'ativa' | 'trancada' | 'cancelada' | 'concluida'
  data_matricula: string
  criado_em: string
  atualizado_em: string
}

export interface MatriculaEad {
  id: string
  aluno_id: string
  aluno_nome?: string
  curso_id: string
  curso_nome?: string
  materia_atual_id?: string
  materia_atual_nome?: string
  progresso: number
  ultimo_acesso_em?: string
  status: 'ativa' | 'concluida' | 'reprovada' | 'cancelada'
  criado_em: string
  atualizado_em: string
}

export interface Nota {
  id: string
  aluno_id: string
  materia_id: string
  materia_nome?: string
  nota: number
  tipo: 'prova' | 'trabalho' | 'participacao' | 'final'
  semestre: number
  ano: number
  criado_em: string
  atualizado_em: string
}

export interface HistoricoItem {
  id: string
  aluno_id: string
  materia_id?: string
  materia_nome?: string
  descricao: string
  tipo: string
  semestre?: number
  ano?: number
  criado_em: string
}

export interface Presenca {
  id: string
  aula_id: string
  aula_titulo?: string
  aluno_id: string
  aluno_nome?: string
  presente: boolean
  registrado_por?: string
  criado_em: string
}

export interface PresencaMateriaItem {
  materia_id: string
  materia_nome: string
  total_aulas_previstas: number
  presencas: number
  percentual: number
}

export interface PresencaProfessorItem {
  aula_id: string
  aula_titulo: string
  materia_nome: string
  data_aula: string
  total_alunos: number
  presencas: number
  percentual: number
}

export interface Aula {
  id: string
  curso_id?: string
  modulo_id?: string
  materia_id: string
  materia_nome?: string
  professor_id: string
  professor_nome?: string
  titulo: string
  data_aula: string
  descricao?: string
  criado_em: string
  atualizado_em: string
}

export interface AnexoAula {
  id: string
  aula_id: string
  professor_id: string
  professor_nome?: string
  nome_arquivo: string
  url: string
  descricao?: string
  criado_em: string
}

export interface Ata {
  id: string
  aula_id: string
  professor_id: string
  professor_nome?: string
  conteudo: string
  data_ata: string
  criado_em: string
  atualizado_em: string
}

export interface Certificado {
  id: string
  aluno_id: string
  aluno_nome?: string
  titulo: string
  estagios_entregues: { nome: string; data_entrega: string }[]
  historico_completo: boolean
  data_emissao?: string
  status: 'pendente' | 'emitido' | 'cancelado'
  criado_em: string
  atualizado_em: string
}

export interface ChatConversa {
  id: string
  tipo: 'individual' | 'grupo'
  nome?: string
  criado_por: string
  criador_nome?: string
  status: 'ativa' | 'finalizada' | 'arquivada'
  participantes: ChatParticipante[]
  ultima_mensagem?: ChatMensagem
  nao_lidas: number
  criado_em: string
  atualizado_em: string
}

export interface ChatParticipante {
  usuario_id: string
  usuario_nome: string
  usuario_email: string
  perfil: string
  entrou_em: string
}

export interface ChatMensagem {
  id: string
  conversa_id: string
  remetente_id: string
  remetente_nome: string
  conteudo: string
  lida: boolean
  criado_em: string
}

export interface Venda {
  id: string
  polo_id?: string
  polo_nome?: string
  escola_id?: string
  escola_nome?: string
  aluno_id?: string
  aluno_nome?: string
  modalidade: 'polo' | 'escola' | 'ead'
  valor: number
  forma_pagamento?: string
  status: 'paga' | 'pendente' | 'cancelada' | 'estornada'
  criado_em: string
  atualizado_em: string
}

export interface Boleto {
  id: string
  venda_id?: string
  valor: number
  data_vencimento?: string
  status: 'gerado' | 'pago' | 'vencido' | 'cancelado'
  nosso_numero?: string
  asaas_id?: string
  link_pdf?: string
  criado_em: string
  atualizado_em: string
}

export interface PedidoLivro {
  id: string
  polo_id?: string
  polo_nome?: string
  escola_id?: string
  escola_nome?: string
  materia_id?: string
  materia_nome?: string
  quantidade: number
  status: 'pendente' | 'enviado' | 'entregue' | 'cancelado'
  solicitado_por?: string
  solicitado_por_nome?: string
  observacao?: string
  criado_em: string
  atualizado_em: string
}

export interface AlunoChurn {
  id: string
  aluno_id: string
  aluno_nome?: string
  polo_id?: string
  polo_nome?: string
  escola_id?: string
  escola_nome?: string
  ultima_movimentacao_em: string
  status: 'ativo' | 'desistente' | 'reativado'
  reingresso_em?: string
  reingresso_tipo?: 'taxa' | 'licencas'
  criado_em: string
  atualizado_em: string
}

export interface RequisicaoTroca {
  id: string
  aluno_id: string
  aluno_nome?: string
  polo_origem_id?: string
  polo_origem_nome?: string
  escola_origem_id?: string
  escola_origem_nome?: string
  polo_destino_id?: string
  polo_destino_nome?: string
  escola_destino_id?: string
  escola_destino_nome?: string
  tipo_troca: 'polo' | 'escola' | 'modalidade'
  justificativa: string
  status: 'pendente' | 'aprovada' | 'rejeitada' | 'processada'
  solicitado_por?: string
  solicitado_por_nome?: string
  criado_em: string
  atualizado_em: string
}

export interface FeedNoticia {
  id: string
  autor_id: string
  autor_nome: string
  autor_perfil: string
  titulo: string
  conteudo: string
  criado_em: string
  atualizado_em: string
}

export interface Lembrete {
  id: string
  titulo: string
  mensagem: string
  data_exibicao?: string
  criado_em: string
}

export interface LicencaEstoque {
  id: string
  materia_id: string
  materia_nome: string
  tipo: 'licenca' | 'livro'
  quantidade: number
  polo_destino_id?: string
  polo_destino_nome?: string
  criado_em: string
  atualizado_em: string
}

export interface LicencaMovimentacao {
  id: string
  materia_id: string
  materia_nome?: string
  estoque_id?: string
  tipo_movimento: 'entrada' | 'saida' | 'ajuste'
  quantidade: number
  polo_id?: string
  polo_nome?: string
  usuario_id?: string
  usuario_nome?: string
  observacao?: string
  criado_em: string
}

export interface EadCalendario {
  id: string
  curso_id?: string
  materia_id?: string
  titulo: string
  data_inicio: string
  data_fim: string
  status: 'programado' | 'aberto' | 'fechado'
  criado_em: string
  atualizado_em: string
}

export interface DashboardResumo {
  alunos_ativos: number
  matriculas: number
  polos_ativos: number
  escolas_ativas: number
  professores_ativos: number
  certificados_emitidos: number
}

export interface ContagemResponse {
  titulo: string
  total: number
  filtros?: Record<string, unknown>
}

export interface RankingPoloItem {
  polo_id: string
  polo_nome?: string
  total_licencas: number
  total_livros: number
  total_adquirido: number
}

export interface LogAuditoria {
  id: string
  usuario_id?: string
  usuario_nome?: string
  usuario_email?: string
  acao: string
  entidade?: string
  entidade_id?: string
  dados_antes?: Record<string, unknown>
  dados_depois?: Record<string, unknown>
  ip?: string
  criado_em: string
}

export interface Configuracao {
  id?: string
  chave: string
  valor: unknown
  criado_em?: string
  atualizado_em?: string
}

export interface PaginatedResponse<T> {
  total: number
  items: T[]
  limit: number
  offset: number
}

export interface ApiError {
  detail: string
}