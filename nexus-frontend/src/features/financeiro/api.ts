import { apiClient } from '@/api/client';
import {
  FiltrosPeriodo,
  Pagamento,
  Paginado,
  Pedido,
  PedidoCreatePayload,
  Produto,
  ProdutoPayload,
  StatusManual,
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
};
