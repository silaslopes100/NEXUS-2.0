import { apiClient } from '@/api/client';
import {
  Ambiente,
  CheckoutOpcoes,
  CheckoutResposta,
  EnvioPayload,
  PedidoUpdatePayload,
  RegraPagamento,
  RegraPagamentoPayload,
  VendasKpis,
  VendasSerieItem,
  FiltrosPeriodo,
  GatewayConfig,
  GatewayConfigPayload,
  GatewayNome,
  GatewaysResposta,
  MeioCobranca,
  WebhookEvento,
  Pagamento,
  Paginado,
  Pedido,
  PedidoCreatePayload,
  Produto,
  ProdutoPayload,
  StatusManual,
  StatusSimulado,
  TipoPedido,
} from '@/features/financeiro/types';

/** Remove filtros vazios para não enviar `?mes=` à API. */
const limpar = (filtros: FiltrosPeriodo = {}) =>
  Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '' && v !== undefined && v !== null));

export const financeiroApi = {
  // Produtos (catálogo)
  async listProdutos(params?: { tipo?: TipoPedido; incluir_inativos?: boolean }) {
    return (await apiClient.get<{ total: number; items: Produto[] }>('/financeiro/produtos', { params })).data;
  },
  async createProduto(payload: ProdutoPayload) {
    return (await apiClient.post<Produto>('/financeiro/produtos', payload)).data;
  },
  async updateProduto(id: string, payload: ProdutoPayload) {
    return (await apiClient.put<Produto>(`/financeiro/produtos/${id}`, payload)).data;
  },

  // Pedidos
  async listPedidos(filtros?: FiltrosPeriodo) {
    return (await apiClient.get<Paginado<Pedido>>('/financeiro/pedidos', { params: limpar(filtros) })).data;
  },
  async getPedido(id: string) {
    return (await apiClient.get<Pedido>(`/financeiro/pedidos/${id}`)).data;
  },
  async createPedido(payload: PedidoCreatePayload) {
    return (await apiClient.post<Pedido>('/financeiro/pedidos', payload)).data;
  },
  async alterarStatus(id: string, payload: { status: StatusManual; observacao?: string; motivo_cancelamento?: string }) {
    return (await apiClient.post<Pedido>(`/financeiro/pedidos/${id}/status`, payload)).data;
  },

  // Pagamentos
  async listPagamentos(filtros?: FiltrosPeriodo) {
    return (await apiClient.get<Paginado<Pagamento>>('/financeiro/pagamentos', { params: limpar(filtros) })).data;
  },

  // Cobrança (Fase 2)
  async gerarCobranca(pedidoId: string, meio: MeioCobranca) {
    return (await apiClient.post<Pagamento>(`/financeiro/pedidos/${pedidoId}/cobranca`, { meio })).data;
  },
  async cancelarPagamento(id: string) {
    return (await apiClient.post<Pagamento>(`/financeiro/pagamentos/${id}/cancelar`)).data;
  },
  /** Simulador (sandbox, admin): confirma/vence/cancela como se fosse o webhook do gateway. */
  async simularPagamento(id: string, status: StatusSimulado) {
    return (await apiClient.post<{ status: string; pagamento?: Pagamento }>(
      `/financeiro/pagamentos/${id}/simular`, { status },
    )).data;
  },

  // Gateways
  async listGateways() {
    return (await apiClient.get<GatewaysResposta>('/financeiro/gateways')).data;
  },
  async salvarGateway(gateway: GatewayNome, ambiente: Ambiente, payload: GatewayConfigPayload) {
    return (await apiClient.put<GatewayConfig>(`/financeiro/gateways/${gateway}/${ambiente}`, payload)).data;
  },
  async testarGateway(gateway: GatewayNome, ambiente: Ambiente) {
    return (await apiClient.post<{ ok: boolean; mensagem: string }>(`/financeiro/gateways/${gateway}/${ambiente}/testar`)).data;
  },
  async listWebhookEventos(params?: { gateway?: string; status?: string; payment_id?: string; limit?: number; offset?: number }) {
    return (await apiClient.get<Paginado<WebhookEvento>>('/financeiro/webhooks/eventos', { params })).data;
  },

  // Fase 3B: checkout e regras de pagamento
  async opcoesCheckout(params: { tipo: TipoPedido; valor?: number; polo_id?: string }) {
    return (await apiClient.get<CheckoutOpcoes>('/financeiro/checkout/opcoes', { params })).data;
  },
  async checkout(payload: PedidoCreatePayload & { meio: MeioCobranca }) {
    return (await apiClient.post<CheckoutResposta>('/financeiro/checkout', payload)).data;
  },
  async listRegras() {
    return (await apiClient.get<RegraPagamento[]>('/financeiro/regras')).data;
  },
  async criarRegra(payload: RegraPagamentoPayload) {
    return (await apiClient.post<RegraPagamento>('/financeiro/regras', payload)).data;
  },
  async atualizarRegra(id: string, payload: RegraPagamentoPayload) {
    return (await apiClient.put<RegraPagamento>(`/financeiro/regras/${id}`, payload)).data;
  },

  // Fase 3C: logística
  async marcarEnviado(pedidoId: string, payload: EnvioPayload) {
    return (await apiClient.post<Pedido>(`/financeiro/pedidos/${pedidoId}/envio`, payload)).data;
  },
  async marcarEntregue(pedidoId: string, observacao?: string) {
    return (await apiClient.post<Pedido>(`/financeiro/pedidos/${pedidoId}/entregue`, { observacao })).data;
  },
  async editarPedido(pedidoId: string, payload: PedidoUpdatePayload) {
    return (await apiClient.put<Pedido>(`/financeiro/pedidos/${pedidoId}`, payload)).data;
  },

  // Fase 3D: vendas e boletos
  async vendasKpis(filtros?: FiltrosPeriodo) {
    return (await apiClient.get<VendasKpis>('/financeiro/vendas/kpis', { params: limpar(filtros) })).data;
  },
  async vendasSerie(filtros?: FiltrosPeriodo) {
    return (await apiClient.get<VendasSerieItem[]>('/financeiro/vendas/serie', { params: limpar(filtros) })).data;
  },
  // Fase 4: exportações e etiqueta (respostas binárias)
  async exportar(recurso: 'vendas' | 'pagamentos' | 'pedidos', formato: 'pdf' | 'xlsx', filtros?: FiltrosPeriodo) {
    const res = await apiClient.get<Blob>(`/financeiro/${recurso}/exportar`, {
      params: { ...limpar(filtros), formato }, responseType: 'blob',
    });
    return { blob: res.data, disposition: res.headers['content-disposition'] as string | undefined };
  },
  async etiqueta(pedidoId: string) {
    const res = await apiClient.get<Blob>(`/financeiro/pedidos/${pedidoId}/etiqueta`, { responseType: 'blob' });
    return { blob: res.data, disposition: res.headers['content-disposition'] as string | undefined };
  },
  async getPagamento(id: string) {
    return (await apiClient.get<Pagamento>(`/financeiro/pagamentos/${id}`)).data;
  },
  async segundaVia(pagamentoId: string) {
    return (await apiClient.post<Pagamento>(`/financeiro/pagamentos/${pagamentoId}/segunda-via`)).data;
  },
};
