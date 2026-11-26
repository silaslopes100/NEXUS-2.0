// Tipos do módulo 2.4 Financeiro & Logística (espelham app/modules/financeiro/schemas.py).

/** 'kit' = Disciplina (1 livro + 1 licença), o produto vendido; 'livro' e 'licenca' ficam para o histórico. */
/** 'troca' = solicitação de troca de licença/livro feita pelo Polo/Escola. */
/** 'ead' / 'ead_livro' = disciplina comprada pelo aluno EAD na loja (com ou sem livro físico). */
export type TipoPedido = 'livro' | 'licenca' | 'kit' | 'troca' | 'ead' | 'ead_livro';
/** Tipos que passam pela logística (envio de livro). */
export const tipoComEnvio = (tipo: TipoPedido) =>
  tipo === 'livro' || tipo === 'kit' || tipo === 'troca' || tipo === 'ead_livro';

export type StatusPedido =
  | 'aguardando_pagamento'
  | 'pago_aguardando_envio'
  | 'enviado'
  | 'entregue'
  | 'concluido'
  | 'cancelado'
  | 'troca_solicitada'
  | 'troca';

export type MotivoTroca = 'disciplina_errada' | 'mudanca_turma' | 'livro_defeito' | 'outro';

export const MOTIVO_TROCA: Record<MotivoTroca, string> = {
  disciplina_errada: 'Disciplina comprada errada',
  mudanca_turma: 'Mudança de turma ou grade',
  livro_defeito: 'Livro com defeito',
  outro: 'Outro',
};

export interface TrocaItem {
  id?: string | null;
  disciplina_devolver_id: string;
  disciplina_devolver_nome?: string | null;
  disciplina_receber_id: string;
  disciplina_receber_nome?: string | null;
  quantidade: number;
}

export interface TrocaPayload {
  itens: { disciplina_devolver_id: string; disciplina_receber_id: string; quantidade: number }[];
  motivo: MotivoTroca;
  descricao?: string;
  endereco?: EnderecoEntrega;
}

/** Saldo de livros de uma Disciplina no Estoque Central (negativo = enviado sem estoque). */
export interface EstoqueItem {
  disciplina_id: string;
  disciplina_nome: string;
  sku?: string | null;
  curso_id?: string | null;
  curso_nome?: string | null;
  semestre?: number | null;
  disciplina_ativa: boolean;
  quantidade: number;
  atualizado_em?: string | null;
}

export type TipoMovimentacaoEstoque = 'entrada' | 'ajuste' | 'baixa_envio';

export interface EstoqueMovimentacao {
  id: string;
  disciplina_id: string;
  tipo: TipoMovimentacaoEstoque;
  /** Variação com sinal. */
  quantidade: number;
  saldo_apos: number;
  pedido_id?: string | null;
  pedido_numero?: string | null;
  usuario_nome?: string | null;
  observacao?: string | null;
  criado_em?: string | null;
}

export interface EnderecoEntrega {
  nome?: string | null;
  cep?: string | null;
  logradouro?: string | null;
  numero?: string | null;
  complemento?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  uf?: string | null;
  telefone?: string | null;
}

export interface PedidoItem {
  id: string;
  produto_id?: string | null;
  disciplina_id?: string | null;
  descricao?: string | null;
  quantidade: number;
  valor_unitario: number;
  valor_total: number;
}

export interface PedidoHistorico {
  id: string;
  status_de?: string | null;
  status_para: string;
  usuario_id?: string | null;
  origem: string;
  observacao?: string | null;
  criado_em?: string | null;
}

export interface Pedido {
  id: string;
  numero: string;
  tipo: TipoPedido;
  status: StatusPedido;
  polo_id?: string | null;
  polo_nome?: string | null;
  escola_id?: string | null;
  escola_nome?: string | null;
  valor_bruto: number;
  desconto: number;
  valor_total: number;
  fornecedor?: string | null;
  endereco: EnderecoEntrega;
  observacao?: string | null;
  pago_em?: string | null;
  cancelado_em?: string | null;
  motivo_cancelamento?: string | null;
  enviado_em?: string | null;
  entregue_em?: string | null;
  criado_em?: string | null;
  itens: PedidoItem[];
  historico: PedidoHistorico[];
  envios?: Envio[];
  troca_motivo?: MotivoTroca | null;
  troca_descricao?: string | null;
  troca_itens?: TrocaItem[];
  /** Pedido do aluno EAD (tipos ead / ead_livro). */
  aluno_id?: string | null;
  aluno_nome?: string | null;
  ead?: {
    disciplina_id?: string | null;
    disciplina_nome?: string | null;
    turma_nome?: string | null;
    status_pagamento?: string | null;
    liberada_em?: string | null;
    numero_matricula?: string | null;
    aluno_email?: string | null;
  } | null;
}

export interface Envio {
  id: string;
  transportadora?: string | null;
  codigo_rastreio?: string | null;
  volumes: number;
  peso_total_g?: number | null;
  enviado_em?: string | null;
  observacao?: string | null;
}

export interface EnvioPayload {
  transportadora: string;
  codigo_rastreio?: string;
  volumes: number;
  peso_total_g?: number | null;
  observacao?: string;
}

export interface PedidoUpdatePayload {
  endereco?: EnderecoEntrega;
  observacao?: string;
  itens?: { produto_id: string; quantidade: number }[];
}

// ---------------------------------------------------------------------------
// Fase 3: regras de pagamento, checkout e vendas
// ---------------------------------------------------------------------------

export interface RegraPagamento {
  id: string;
  nome: string;
  aplica_tipo_pedido?: TipoPedido | null;
  aplica_polo_id?: string | null;
  polo_nome?: string | null;
  meios_permitidos: string[];
  gateway_preferido?: string | null;
  dias_vencimento: number;
  multa_pct: number;
  juros_mes_pct: number;
  desconto_antecipado_pct: number;
  valor_minimo: number;
  prioridade: number;
  ativo: boolean;
  generica: boolean;
}

export type RegraPagamentoPayload = Partial<Omit<RegraPagamento, 'id' | 'polo_nome' | 'generica'>>;

export interface CheckoutOpcoes {
  regra_id?: string | null;
  regra_nome: string;
  meios: string[];
  dias_vencimento: number;
  vencimento: string;
  multa_pct: number;
  juros_mes_pct: number;
  desconto_antecipado_pct: number;
}

export interface CheckoutResposta {
  pedido: Pedido;
  pagamento?: Pagamento | null;
  erro_cobranca?: string | null;
}

export interface VendasKpis {
  pedidos: number;
  pedidos_pagos: number;
  receita_paga: number;
  a_receber: number;
  vencido: number;
  ticket_medio: number;
  receita_licencas: number;
  receita_livros: number;
  receita_kits?: number;
  receita_ead: number;
  vendas_ead: number;
  vendas_ead_livro: number;
  licencas_vendidas: number;
  livros_vendidos: number;
  por_status: { status: string; pedidos: number; valor: number }[];
  top_polos: { polo_id?: string | null; polo_nome?: string | null; pedidos_pagos: number; receita: number }[];
}

export interface CursoCatalogo {
  id: string;
  nome: string;
  modalidade?: string | null;
  /** Disciplinas ativas do curso. */
  disciplinas: number;
  /** Disciplinas ativas com preço (à venda). */
  disciplinas_a_venda: number;
  /** Preço do curso completo = soma das disciplinas ativas à venda. */
  preco_curso: number;
  preco_min?: number | null;
  preco_max?: number | null;
}

export interface DisciplinaCatalogo {
  disciplina_id: string;
  nome: string;
  semestre?: number | null;
  ordem?: number;
  /** Nulo quando a disciplina ainda não tem preço (não está à venda). */
  produto_id: string | null;
  preco: number | null;
  a_venda: boolean;
  saldo_polo: number;
}

export interface CursoCatalogoDetalhe {
  id: string;
  nome: string;
  modalidade?: string | null;
  disciplinas: DisciplinaCatalogo[];
}

export interface VendasSerieItem { mes: string; pedidos: number; pedidos_pagos: number; receita: number; }

export interface PedidoCreatePayload {
  tipo: TipoPedido;
  polo_id?: string;
  escola_id?: string;
  itens: { produto_id: string; quantidade: number }[];
  endereco?: EnderecoEntrega;
  observacao?: string;
}

export type StatusManual = 'pago_aguardando_envio' | 'concluido' | 'cancelado';

export interface Pagamento {
  id: string;
  pedido_id?: string | null;
  pedido_numero?: string | null;
  polo_id?: string | null;
  polo_nome?: string | null;
  gateway?: string | null;
  ambiente?: string | null;
  gateway_payment_id?: string | null;
  billing_type?: string | null;
  valor?: number | null;
  status?: string | null;
  boleto_url?: string | null;
  invoice_url?: string | null;
  linha_digitavel?: string | null;
  pix_copia_cola?: string | null;
  pix_qrcode_base64?: string | null;
  valor_liquido?: number | null;
  vencimento_em?: string | null;
  pago_em?: string | null;
  descricao?: string | null;
  criado_em?: string | null;
}

export interface Paginado<T> {
  total: number;
  items: T[];
  limit: number;
  offset: number;
}

/** Filtros aceitos pelas listagens (mesmos nomes dos query params da API). */
export interface FiltrosPeriodo {
  data_inicio?: string;
  data_fim?: string;
  mes?: string;
  semestre?: string;
  ano?: string;
  polo_id?: string;
  escola_id?: string;
  status?: string;
  tipo?: string;
  pedido_id?: string;
  gateway?: string;
  meio?: string;
  limit?: number;
  offset?: number;
}

export const STATUS_PEDIDO: Record<StatusPedido, { label: string; className: string }> = {
  aguardando_pagamento: { label: 'Aguardando pagamento', className: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  pago_aguardando_envio: { label: 'Pago · aguardando envio', className: 'bg-blue-500/15 text-blue-300 border-blue-500/30' },
  enviado: { label: 'Enviado', className: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30' },
  entregue: { label: 'Entregue', className: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  concluido: { label: 'Concluído', className: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  cancelado: { label: 'Cancelado', className: 'bg-red-500/15 text-red-300 border-red-500/30' },
  troca_solicitada: { label: 'Troca solicitada', className: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  troca: { label: 'Troca', className: 'bg-violet-500/15 text-violet-300 border-violet-500/30' },
};

export const TIPO_PEDIDO: Record<TipoPedido, string> = {
  kit: 'Disciplina (livro + licença)', livro: 'Livro', licenca: 'Licença', troca: 'Troca de livro',
  ead: 'Disciplina EAD (aluno)', ead_livro: 'Disciplina EAD + livro (aluno)',
};

// Transições manuais permitidas pela API (POST /financeiro/pedidos/{id}/status).
export const ACOES_MANUAIS: Partial<Record<StatusPedido, StatusManual[]>> = {
  aguardando_pagamento: ['pago_aguardando_envio', 'concluido', 'cancelado'],
  pago_aguardando_envio: ['cancelado'],
};

/** Pedido criado pelo script de demonstração (scripts/demo_financeiro.py). */
export const ehDemo = (pedido?: { observacao?: string | null } | null) =>
  !!pedido?.observacao?.startsWith('[DEMO]');

export const formatBRL = (valor?: number | null) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0));

export const formatData = (valor?: string | null, comHora = false) => {
  if (!valor) return '-';
  const d = new Date(valor.length === 10 ? `${valor}T00:00:00` : valor);
  return comHora ? d.toLocaleString('pt-BR') : d.toLocaleDateString('pt-BR');
};

export const erroApi = (error: any, padrao: string): string => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => d.msg).join('; ');
  return padrao;
};

// ---------------------------------------------------------------------------
// Fase 2: gateways, cobrança e webhooks
// ---------------------------------------------------------------------------

/** 'fake' = Simulador (somente sandbox, sem credenciais). */
export type GatewayNome = 'asaas' | 'pagbank' | 'mercadopago' | 'fake';
export type StatusSimulado = 'pago' | 'vencido' | 'cancelado';
export type Ambiente = 'sandbox' | 'producao';
export type MeioCobranca = 'BOLETO' | 'PIX';

export interface CampoCredencial { campo: string; label: string; obrigatorio: boolean; }

export interface GatewayConfig {
  gateway: GatewayNome;
  ambiente: Ambiente;
  ativo: boolean;
  padrao: boolean;
  credenciais: Record<string, string>; // sempre mascaradas
  webhook_token: string; // mascarado
  campos: CampoCredencial[];
  rotulo_webhook_token: string | null;
  webhook_url: string | null;
  ultimo_teste_em?: string | null;
  ultimo_teste_ok?: boolean | null;
}

export interface GatewaysResposta {
  ambiente_ativo: Ambiente;
  public_api_url_configurada: boolean;
  chave_configurada: boolean;
  items: GatewayConfig[];
}

export interface GatewayConfigPayload {
  credenciais?: Record<string, string>;
  webhook_token?: string;
  ativo?: boolean;
  padrao?: boolean;
}

export interface WebhookEvento {
  id: string;
  gateway: string;
  ambiente: string;
  evento_id: string;
  tipo_evento?: string | null;
  gateway_payment_id?: string | null;
  payload: unknown;
  status: 'recebido' | 'processado' | 'erro' | 'ignorado';
  tentativas: number;
  erro?: string | null;
  recebido_em?: string | null;
  processado_em?: string | null;
}

export const NOME_GATEWAY: Record<GatewayNome, string> = {
  asaas: 'Asaas',
  pagbank: 'PagBank',
  mercadopago: 'Mercado Pago',
  fake: 'Simulador (sandbox)',
};

/** Links do Simulador (fake.local) não abrem: são ocultados na interface. */
export const linkCobranca = (pg: Pagamento): string | null =>
  pg.gateway === 'fake' ? null : (pg.boleto_url || pg.invoice_url || null);

export const COR_STATUS_PAGAMENTO: Record<string, string> = {
  pago: 'text-emerald-400',
  pendente: 'text-amber-300',
  vencido: 'text-red-400',
  cancelado: 'text-slate-500',
  estornado: 'text-purple-300',
  falhou: 'text-red-400',
};
