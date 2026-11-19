import React from 'react';
import { PeriodoFiltros } from '@/components/filters/PeriodoFiltros';
import { BotoesExportar } from '@/features/financeiro/components/BotoesExportar';
import { PedidosTabela } from '@/features/financeiro/components/PedidosTabela';
import { useAcessoModulo } from '@/features/financeiro/acesso';
import { STATUS_PEDIDO, TIPO_PEDIDO } from '@/features/financeiro/types';

const STATUS_OPCOES = Object.entries(STATUS_PEDIDO).map(([value, meta]) => ({ value, label: meta.label }));
const TIPO_OPCOES = Object.entries(TIPO_PEDIDO).map(([value, label]) => ({ value, label }));

/** Visão administrativa de todos os pedidos (livros e licenças) com filtros. */
export const PedidosPage: React.FC = () => {
  const acesso = useAcessoModulo();
  return (
  <div className="max-w-7xl space-y-6">
    <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/30 p-6 shadow-xl sm:flex-row sm:items-start">
      <div>
        <h1 className="text-3xl font-extrabold text-white">Pedidos</h1>
        <p className="mt-1 text-sm text-slate-400">
          Todos os pedidos (licenças e livros) dos Polos e Escolas. Clique em um pedido para ver itens, cobrança,
          entrega e histórico.
        </p>
      </div>
      <BotoesExportar recurso="pedidos" />
    </header>
    <PeriodoFiltros statusOpcoes={STATUS_OPCOES} tipoOpcoes={TIPO_OPCOES} />
    <PedidosTabela podeAlterarStatus={acesso.financeiro} podeLogistica={acesso.logistica} />
  </div>
  );
};
