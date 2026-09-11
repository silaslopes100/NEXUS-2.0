export interface EstoqueLicenca {
  id?: string;
  disciplina_id?: string;
  escola_id?: string;
  polo_id?: string;
  quantidade_total: number;
  quantidade_disponivel: number;
}

export interface LicencaAtribuida {
  id?: string;
  disciplina_id?: string;
  polo_id?: string;
  escola_id?: string;
  aluno_id?: string;
  quantidade: number;
  atribuido_por?: string;
  atribuido_em?: string;
}

export interface AdicionarEstoquePayload {
  disciplina_id: string;
  quantidade: number;
}

export interface DistribuirEstoquePayload {
  disciplina_id: string;
  escola_id: string;
  quantidade: number;
}

export interface AtribuirLicencaPayload {
  disciplina_id: string;
  polo_id?: string;
  escola_id?: string;
  aluno_id?: string;
  quantidade: number;
}
