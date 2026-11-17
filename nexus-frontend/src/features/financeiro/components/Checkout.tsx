import React, { useEffect, useState } from 'react';
import { AlertTriangle, Barcode, CheckCircle2, QrCode } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { CobrancaPedido } from '@/features/financeiro/components/CobrancaPedido';
import {
  CheckoutOpcoes, CheckoutResposta, MeioCobranca, TipoPedido, formatBRL, formatData,
} from '@/features/financeiro/types';

const ROTULO_MEIO: Record<string, { label: string; icon: React.ReactNode }> = {
  BOLETO: { label: 'Boleto', icon: <Barcode size={15} /> },
  PIX: { label: 'PIX', icon: <QrCode size={15} /> },
};

/** Opções da regra de pagamento aplicável (recarrega quando o valor muda). */
export const useOpcoesCheckout = (tipo: TipoPedido, valor: number, poloId?: string) => {
  const [opcoes, setOpcoes] = useState<CheckoutOpcoes | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => {
      financeiroApi.opcoesCheckout({ tipo, valor: valor || undefined, polo_id: poloId || undefined })
        .then(setOpcoes)
        .catch(() => setOpcoes(null));
    }, 300);
    return () => clearTimeout(timer);
  }, [tipo, valor, poloId]);
  return opcoes;
};

/** Seleção do meio (boleto/PIX) com as condições da regra. */
export const MeioPagamentoCheckout: React.FC<{
  opcoes: CheckoutOpcoes | null;
  meio: MeioCobranca | '';
  onChange: (meio: MeioCobranca) => void;
}> = ({ opcoes, meio, onChange }) => {
  useEffect(() => {
    if (opcoes && (!meio || !opcoes.meios.includes(meio))) {
      const primeiro = opcoes.meios[0] as MeioCobranca | undefined;
      if (primeiro) onChange(primeiro);
    }
  }, [opcoes, meio, onChange]);

  if (!opcoes) return <p className="text-xs text-slate-500">Carregando condições de pagamento…</p>;
  const encargos = [
    opcoes.desconto_antecipado_pct ? `${opcoes.desconto_antecipado_pct}% de desconto até o vencimento` : '',
    opcoes.multa_pct ? `multa ${opcoes.multa_pct}%` : '',
    opcoes.juros_mes_pct ? `juros ${opcoes.juros_mes_pct}% a.m.` : '',
  ].filter(Boolean);

  return (
    <div className="space-y-2 text-sm">
      <p className="text-xs font-bold uppercase text-slate-500">Pagamento</p>
      <div className="flex flex-wrap gap-2">
        {opcoes.meios.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => onChange(m as MeioCobranca)}
            className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold ${meio === m ? 'border-blue-500 bg-blue-600/20 text-white' : 'border-slate-700 text-slate-300'}`}
          >
            {ROTULO_MEIO[m]?.icon} {ROTULO_MEIO[m]?.label || m}
          </button>
        ))}
        {!opcoes.meios.length && <p className="text-xs text-amber-300">Nenhum meio de pagamento disponível para este pedido.</p>}
      </div>
      <p className="text-[11px] text-slate-500">
        Vence em {formatData(opcoes.vencimento)} ({opcoes.dias_vencimento} dia(s)) · regra “{opcoes.regra_nome}”
        {encargos.length ? ` · boleto: ${encargos.join(', ')}` : ''}
      </p>
    </div>
  );
};

/** Resultado do checkout: pedido criado e cobrança (ou o motivo da falha). */
export const ResultadoCheckout: React.FC<{ resultado: CheckoutResposta; onFechar: () => void }> = ({ resultado, onFechar }) => (
  <section className="space-y-4 rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-5">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="flex items-center gap-2 font-bold text-white">
        <CheckCircle2 size={18} className="text-emerald-400" />
        Pedido <span className="font-mono">{resultado.pedido.numero}</span> criado · {formatBRL(resultado.pedido.valor_total)}
      </p>
      <button onClick={onFechar} className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300">Novo pedido</button>
    </div>
    {resultado.erro_cobranca && (
      <p className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
        <AlertTriangle size={16} className="mt-0.5 shrink-0" />
        <span>A cobrança não pôde ser gerada: {resultado.erro_cobranca}. O pedido ficou aguardando pagamento; gere o boleto/PIX abaixo quando resolver.</span>
      </p>
    )}
    <CobrancaPedido pedido={resultado.pedido} podeCancelar={false} onAlterado={() => undefined} />
  </section>
);
