import React from 'react';
import { Truck } from 'lucide-react';
import { PeriodoFiltros } from '@/components/filters/PeriodoFiltros';
import { PedidosTabela } from '@/features/financeiro/components/PedidosTabela';
import { STATUS_PEDIDO, TIPO_PEDIDO } from '@/features/financeiro/types';

const STATUS_OPCOES = Object.entries(STATUS_PEDIDO).map(([value, meta]) => ({ value, label: meta.label }));
const TIPO_OPCOES = Object.entries(TIPO_PEDIDO).map(([value, label]) => ({ value, label }));

/** Visão administrativa de todos os pedidos (livros e licenças) com filtros. */
export const PedidosPage: React.FC = () => (
  <div className="max-w-7xl space-y-6">
    <header className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/30 p-6 shadow-xl">
      <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-300"><Truck size={15} /> Logística & Livros</p>
      <h1 className="text-3xl font-extrabold text-white">Pedidos</h1>
      <p className="mt-1 text-sm text-slate-400">
        Todos os pedidos dos Polos e Escolas. Clique em um pedido para ver itens, entrega e histórico.
        Envio e etiqueta chegam na Fase 3/4.
      </p>
    </header>
    <PeriodoFiltros statusOpcoes={STATUS_OPCOES} tipoOpcoes={TIPO_OPCOES} />
    <PedidosTabela podeAlterarStatus />
  </div>
);
