import React from 'react';
import { Link } from 'react-router-dom';
import { ShoppingCart } from 'lucide-react';
import { PeriodoFiltros } from '@/components/filters/PeriodoFiltros';
import { PedidosTabela } from '@/features/financeiro/components/PedidosTabela';
import { STATUS_PEDIDO } from '@/features/financeiro/types';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const STATUS_OPCOES = Object.entries(STATUS_PEDIDO).map(([value, meta]) => ({ value, label: meta.label }));

/** Acompanhamento dos pedidos da unidade (pagamento, envio dos livros e entrega). */
export const MeusPedidosPage: React.FC = () => {
  const { perfil } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome);
  const podeComprar = role === 'polo' || role === 'admin';
  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Meus pedidos</h1>
          <p className="mt-1 text-sm text-slate-400">Acompanhe pagamento, envio dos livros e entrega. Clique em um pedido para ver o boleto/PIX e o histórico.</p>
        </div>
        {podeComprar && (
          <Link to="/polo/comprar-licencas" className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent">
            <ShoppingCart size={16} /> Comprar disciplinas
          </Link>
        )}
      </header>
      <PeriodoFiltros mostrarUnidade={role === 'admin'} statusOpcoes={STATUS_OPCOES} />
      <PedidosTabela mostrarPolo={role === 'admin'} />
    </div>
  );
};
