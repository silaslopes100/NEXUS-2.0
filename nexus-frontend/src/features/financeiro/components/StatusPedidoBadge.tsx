import React from 'react';
import { STATUS_PEDIDO, StatusPedido } from '@/features/financeiro/types';

export const StatusPedidoBadge: React.FC<{ status: StatusPedido | string }> = ({ status }) => {
  const meta = STATUS_PEDIDO[status as StatusPedido];
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${meta?.className || 'border-slate-600 text-slate-300'}`}>
      {meta?.label || status}
    </span>
  );
};
