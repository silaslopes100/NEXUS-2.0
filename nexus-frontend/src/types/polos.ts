export interface EnderecoCompleto {
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
}

export interface PoloItem {
  id: string;
  nome: string;
  responsavel_nome?: string;
  responsavel_cpf?: string;
  responsavel_email?: string;
  coordenador_id?: string;
  coordenador_nome?: string;
  coordenador_email?: string;
  endereco: EnderecoCompleto;
  status: string;
  criado_em?: string;
  atualizado_em?: string;
}

export interface EscolaItem {
  id: string;
  polo_id: string;
  nome: string;
  secretario_id?: string;
  secretario_nome?: string;
  secretario_email?: string;
  responsavel_nome?: string;
  responsavel_cpf?: string;
  responsavel_email?: string;
  endereco: EnderecoCompleto;
  status: string;
  total_turmas?: number;
  criado_em?: string;
  atualizado_em?: string;
}

export interface PaginacaoResponse<T> {
  total: number;
  items: T[];
  limit: number;
  offset: number;
}

export interface PoloCreatePayload {
  nome: string;
  endereco?: EnderecoCompleto;
  coordenador_nome: string;
  coordenador_cpf: string;
  coordenador_email: string;
  coordenador_senha: string;
}

export interface EscolaCreatePayload {
  polo_id: string;
  nome: string;
  endereco?: EnderecoCompleto;
  secretario_nome: string;
  secretario_cpf: string;
  secretario_email: string;
  secretario_senha: string;
}

export interface ResumoPoloResponse {
  polo_id: string;
  escolas_vinculadas: number;
  alunos_ativos: number;
  professores_alocados: number;
  materias_em_estoque: number;
  detalhes_estoque: {
    licencas_no_polo: number;
    licencas_nas_escolas: number;
  };
}

export interface DashboardPoloKpis {
  total_licencas_compradas: number;
  total_licencas_vendidas_alunos: number;
  total_licencas_nao_vendidas: number;
  total_nao_vendidas_escolas: number;
  total_nao_vendidas_polo: number;
  taxa_conversao_global: number;
  taxa_distribuicao: number;
}

// Contagens operacionais do Polo (tela de detalhe)
export interface ResumoOperacionalPolo {
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

// Contagens operacionais da Escola (drawer de detalhe)
export interface ResumoOperacionalEscola {
  alunos: number;
  aulas: number;
  licencas_estoque: number;
  licencas_alunos: number;
  licencas_atribuidas: number;
  licencas_movimentacoes: number;
  pedidos_licencas: number;
  pedidos_livros: number;
  professores: number;
  turmas: number;
}

export interface DashboardEscolaKpis {
  licencas_recebidas: number;
  licencas_vendidas: number;
  licencas_nao_vendidas: number;
  taxa_conversao: number;
  taxa_ociosidade: number;
}

export interface AlertaItem {
  nivel: string;
  escopo: string;
  referencia_id: string;
  referencia_nome: string;
  mensagem: string;
}

// Payload para atualização de um Polo (inclui vínculo com usuário)
export interface PoloUpdatePayload {
  nome?: string;
  endereco?: EnderecoCompleto;
  coordenador_id?: string;        // ID do usuário (perfil Polo) a ser vinculado
  coordenador_nome?: string;      // Nome manual (fallback)
  coordenador_cpf?: string;       // CPF manual (fallback)
  coordenador_email?: string;     // E-mail manual (fallback)
  coordenador_senha?: string;     // Nova senha (opcional)
  status?: string;
}

// Payload para atualização de uma Escola (inclui vínculo com usuário)
export interface EscolaUpdatePayload {
  polo_id?: string;               // Permite alterar o polo vinculado
  nome?: string;
  endereco?: EnderecoCompleto;
  secretario_id?: string;         // ID do usuário (perfil Escola) a ser vinculado
  secretario_nome?: string;
  secretario_cpf?: string;
  secretario_email?: string;
  secretario_senha?: string;
  status?: string;
}