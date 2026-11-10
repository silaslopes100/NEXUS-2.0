import { create } from 'zustand';
import { Transferencia, transferenciasApi } from '@/features/transferencias/api';

interface TransferenciasState {
  total: number;
  itens: Transferencia[];
  carregar: () => Promise<void>;
}

export const useTransferenciasStore = create<TransferenciasState>((set) => ({
  total: 0,
  itens: [],
  carregar: async () => {
    try {
      const resumo = await transferenciasApi.resumoPendentes();
      set({ total: resumo.total, itens: resumo.items });
    } catch {
      // O sino é informativo: uma falha mantém o último valor conhecido.
    }
  },
}));
