import React, { useState } from 'react';
import { Ban, CheckCircle2, Clock, FlaskConical, Loader2 } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { Pagamento, StatusSimulado, erroApi } from '@/features/financeiro/types';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

export const SeloSimulado: React.FC = () => (
  <span className="inline-flex items-center gap-1 rounded-full bg-fuchsia-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-fuchsia-300">
    <FlaskConical size={11} /> Simulado
  </span>
);

export const SeloDemonstracao: React.FC = () => (
  <span title="Dado de demonstração (pode ser removido pelo script de limpeza)" className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300">
    <FlaskConical size={11} /> Demonstração
  </span>
);

const ACOES: { status: StatusSimulado; label: string; icon: React.ReactNode; className: string }[] = [
  { status: 'pago', label: 'Simular pagamento', icon: <CheckCircle2 size={13} />, className: 'border-emerald-500/40 text-emerald-300' },
  { status: 'vencido', label: 'Simular vencimento', icon: <Clock size={13} />, className: 'border-amber-500/40 text-amber-300' },
  { status: 'cancelado', label: 'Simular cancelamento', icon: <Ban size={13} />, className: 'border-slate-600 text-slate-300' },
];

/**
 * Botões do Simulador (gateway 'fake', sandbox). Visíveis só para o admin e só em
 * cobranças pendentes/vencidas. O backend processa como um webhook real.
 */
export const SimuladorPagamento: React.FC<{ pagamento: Pagamento; compacto?: boolean; onAlterado: () => void }> = ({
  pagamento, compacto, onAlterado,
}) => {
  const { perfil } = useAuthStore();
  const [acao, setAcao] = useState<StatusSimulado | null>(null);
  const [erro, setErro] = useState('');

  const ehAdmin = normalizeUserRole(perfil?.nome) === 'admin';
  const aberto = pagamento.status === 'pendente' || pagamento.status === 'vencido';
  if (pagamento.gateway !== 'fake' || !ehAdmin || !aberto) return null;

  const simular = async (status: StatusSimulado) => {
    setAcao(status);
    setErro('');
    try {
      await financeiroApi.simularPagamento(pagamento.id, status);
      onAlterado();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível simular.'));
    } finally {
      setAcao(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {ACOES.filter((a) => !(a.status === 'vencido' && pagamento.status === 'vencido')).map((a) => (
        <button
          key={a.status}
          onClick={() => simular(a.status)}
          disabled={!!acao}
          title={a.label}
          className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[11px] font-semibold disabled:opacity-50 ${a.className}`}
        >
          {acao === a.status ? <Loader2 size={13} className="animate-spin" /> : a.icon}
          {!compacto && a.label}
        </button>
      ))}
      {erro && <span className="text-[11px] text-red-300">{erro}</span>}
    </div>
  );
};
