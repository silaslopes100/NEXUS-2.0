export interface EnderecoCompleto {
  logradouro?: string;
  numero?: string;
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
  endereco_completo?: EnderecoCompleto;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface EscolaItem {
  id: string;
  polo_id: string;
  nome: string;
  responsavel_nome?: string;
  responsavel_cpf?: string;
  responsavel_email?: string;
  endereco_completo?: EnderecoCompleto;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface PoloCreatePayload {
  nome: string;
  responsavel_nome?: string;
  responsavel_cpf?: string;
  responsavel_email?: string;
  logradouro?: string;
  numero?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
}

export interface EscolaCreatePayload {
  polo_id: string;
  nome: string;
  responsavel_nome?: string;
  responsavel_cpf?: string;
  responsavel_email?: string;
  logradouro?: string;
  numero?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
}

export interface CoordenadorCreatePayload {
  nome: string;
  cpf: string;
  email: string;
  senha: string;
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
