// Tipos do módulo 2.4 Financeiro & Logística (espelham app/modules/financeiro/schemas.py).

export type TipoPedido = 'livro' | 'licenca';

export type StatusPedido =
  | 'aguardando_pagamento'
  | 'pago_aguardando_envio'
  | 'enviado'
  | 'entregue'
  | 'concluido'
  | 'cancelado';

export interface Produto {
  id: string;
  tipo: TipoPedido;
  sku: string;
  nome: string;
  descricao?: string | null;
  disciplina_id?: string | null;
  preco: number;
  peso_g?: number | null;
  altura_cm?: number | null;
  largura_cm?: number | null;
  comprimento_cm?: number | null;
  ativo: boolean;
  criado_em?: string | null;
}

export interface ProdutoPayload {
  tipo?: TipoPedido;
  sku?: string;
  nome?: string;
  descricao?: string | null;
  preco?: number;
  peso_g?: number | null;
  ativo?: boolean;
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
}

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
};

export const TIPO_PEDIDO: Record<TipoPedido, string> = { livro: 'Livro', licenca: 'Licença' };

// Transições manuais permitidas pela API (POST /financeiro/pedidos/{id}/status).
export const ACOES_MANUAIS: Partial<Record<StatusPedido, StatusManual[]>> = {
  aguardando_pagamento: ['pago_aguardando_envio', 'concluido', 'cancelado'],
  pago_aguardando_envio: ['cancelado'],
};

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

export type GatewayNome = 'asaas' | 'pagbank' | 'mercadopago';
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
};

export const COR_STATUS_PAGAMENTO: Record<string, string> = {
  pago: 'text-emerald-400',
  pendente: 'text-amber-300',
  vencido: 'text-red-400',
  cancelado: 'text-slate-500',
  estornado: 'text-purple-300',
  falhou: 'text-red-400',
};
