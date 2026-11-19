import React from 'react';
import { PeriodoFiltros } from '@/components/filters/PeriodoFiltros';
import { PedidosTabela } from '@/features/financeiro/components/PedidosTabela';
import { useAcessoModulo } from '@/features/financeiro/acesso';
import { BotoesExportar } from '@/features/financeiro/components/BotoesExportar';
import { STATUS_PEDIDO } from '@/features/financeiro/types';

const STATUS_HISTORICO = (['aguardando_pagamento', 'pago_aguardando_envio', 'enviado', 'entregue', 'troca_solicitada', 'troca', 'cancelado'] as const)
  .map((value) => ({ value, label: STATUS_PEDIDO[value].label }));

/**
 * Logística de livros (Fase 3C).
 * - pendentes: pedidos pagos aguardando envio (marcar enviado, editar entrega, cancelar)
 * - historico: todos os pedidos de livro com filtros (data, mês, semestre, ano, polo, escola, status)
 */
export const LogisticaPage: React.FC<{ modo: 'pendentes' | 'historico' }> = ({ modo }) => {
  const pendentes = modo === 'pendentes';
  const acesso = useAcessoModulo();
  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/30 p-6 shadow-xl sm:flex-row sm:items-start">
        <div>
        <h1 className="text-3xl font-extrabold text-white">
          {pendentes ? 'Pendentes de envio' : 'Histórico de pedidos'}
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {pendentes
            ? 'Pedidos de livros já pagos pelos Polos. Abra um pedido para registrar o envio (transportadora e rastreio), editar a entrega ou cancelar.'
            : 'Todos os pedidos de livros. Filtre por período, Polo, Escola e status; abra um pedido para ver itens, envios e histórico.'}
        </p>
        </div>
        <BotoesExportar
          recurso="pedidos"
          filtrosFixos={pendentes ? { tipo: 'com_envio', status: 'fila_envio' } : { tipo: 'com_envio' }}
        />
      </header>
      {pendentes ? (
        <PeriodoFiltros />
      ) : (
        <PeriodoFiltros statusOpcoes={STATUS_HISTORICO} />
      )}
      <PedidosTabela
        titulo={pendentes ? 'Aguardando envio' : 'Pedidos de livros'}
        podeAlterarStatus={acesso.financeiro}
        podeLogistica={acesso.logistica}
        filtrosFixos={pendentes ? { tipo: 'com_envio', status: 'fila_envio' } : { tipo: 'com_envio' }}
      />
    </div>
  );
};
