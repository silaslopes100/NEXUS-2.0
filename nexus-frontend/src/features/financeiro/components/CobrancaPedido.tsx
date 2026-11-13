import React, { useCallback, useEffect, useState } from 'react';
import { Ban, Barcode, CheckCircle2, Copy, ExternalLink, Loader2, QrCode, RefreshCw } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { COR_STATUS_PAGAMENTO, MeioCobranca, Pagamento, Pedido, erroApi, formatBRL, formatData } from '@/features/financeiro/types';

const CopiarTexto: React.FC<{ texto: string; rotulo: string }> = ({ texto, rotulo }) => {
  const [ok, setOk] = useState(false);
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto);
      setOk(true);
      setTimeout(() => setOk(false), 1500);
    } catch {
      setOk(false);
    }
  };
  return (
    <div>
      <p className="mb-1 text-[11px] font-semibold uppercase text-slate-500">{rotulo}</p>
      <div className="flex items-start gap-2">
        <code className="flex-1 break-all rounded-lg bg-slate-950 p-2 text-[11px] text-slate-200">{texto}</code>
        <button onClick={copiar} className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white" title="Copiar">
          {ok ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
      </div>
    </div>
  );
};

interface Props {
  pedido: Pedido;
  /** Pode cancelar cobranças (área financeiro). */
  podeCancelar: boolean;
  /** Recarrega o pedido (status pode ter mudado). */
  onAlterado: () => void;
}

/** Cobrança do pedido: gerar boleto/PIX, exibir linha digitável/QR Code e cancelar. */
export const CobrancaPedido: React.FC<Props> = ({ pedido, podeCancelar, onAlterado }) => {
  const [pagamentos, setPagamentos] = useState<Pagamento[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [acao, setAcao] = useState<string | null>(null);
  const [erro, setErro] = useState('');

  const load = useCallback(async () => {
    setCarregando(true);
    try {
      setPagamentos((await financeiroApi.listPagamentos({ pedido_id: pedido.id, limit: 20 })).items);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar as cobranças.'));
    } finally {
      setCarregando(false);
    }
  }, [pedido.id]);

  useEffect(() => { load(); }, [load, pedido.status]);

  const pendente = pagamentos.find((p) => p.status === 'pendente');
  const podeGerar = pedido.status === 'aguardando_pagamento' && !pendente && Number(pedido.valor_total) > 0;

  const gerar = async (meio: MeioCobranca) => {
    setAcao(meio);
    setErro('');
    try {
      await financeiroApi.gerarCobranca(pedido.id, meio);
      await load();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível gerar a cobrança.'));
    } finally {
      setAcao(null);
    }
  };

  const cancelar = async (id: string) => {
    setAcao(`cancelar-${id}`);
    setErro('');
    try {
      await financeiroApi.cancelarPagamento(id);
      await load();
      onAlterado();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível cancelar a cobrança.'));
    } finally {
      setAcao(null);
    }
  };

  if (pedido.status === 'cancelado' && !pagamentos.length) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase text-slate-500">Cobrança</h3>
        <button onClick={() => { load(); onAlterado(); }} className="text-slate-500 hover:text-white" title="Atualizar status">
          <RefreshCw size={14} className={carregando ? 'animate-spin' : ''} />
        </button>
      </div>

      {erro && <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-300">{erro}</p>}

      {podeGerar && (
        <div className="mb-3 flex flex-wrap gap-2">
          <button onClick={() => gerar('BOLETO')} disabled={!!acao} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
            {acao === 'BOLETO' ? <Loader2 size={14} className="animate-spin" /> : <Barcode size={14} />} Gerar boleto
          </button>
          <button onClick={() => gerar('PIX')} disabled={!!acao} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
            {acao === 'PIX' ? <Loader2 size={14} className="animate-spin" /> : <QrCode size={14} />} Gerar PIX
          </button>
        </div>
      )}

      <div className="space-y-3">
        {pagamentos.map((pg) => (
          <div key={pg.id} className="space-y-3 rounded-lg border border-slate-800 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="text-slate-300">
                {pg.billing_type || '-'} · {pg.gateway}{pg.ambiente ? ` (${pg.ambiente})` : ''} · vence {formatData(pg.vencimento_em)}
              </span>
              <span className={`font-semibold ${COR_STATUS_PAGAMENTO[pg.status || ''] || 'text-slate-300'}`}>
                {pg.status} · {formatBRL(pg.valor)}
              </span>
            </div>
            {pg.status === 'pendente' && (
              <>
                {pg.linha_digitavel && <CopiarTexto texto={pg.linha_digitavel} rotulo="Linha digitável" />}
                {pg.pix_qrcode_base64 && (
                  <img
                    src={`data:image/png;base64,${pg.pix_qrcode_base64}`}
                    alt="QR Code PIX"
                    className="h-40 w-40 rounded-lg bg-white p-2"
                  />
                )}
                {pg.pix_copia_cola && <CopiarTexto texto={pg.pix_copia_cola} rotulo="PIX copia e cola" />}
              </>
            )}
            <div className="flex flex-wrap gap-2">
              {(pg.boleto_url || pg.invoice_url) && (
                <a href={pg.boleto_url || pg.invoice_url || '#'} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs text-slate-200 hover:text-white">
                  <ExternalLink size={13} /> {pg.boleto_url ? 'Abrir boleto' : 'Abrir fatura'}
                </a>
              )}
              {podeCancelar && (pg.status === 'pendente' || pg.status === 'vencido') && (
                <button onClick={() => cancelar(pg.id)} disabled={!!acao} className="inline-flex items-center gap-1 rounded-lg border border-red-500/40 px-2.5 py-1.5 text-xs text-red-300 disabled:opacity-50">
                  {acao === `cancelar-${pg.id}` ? <Loader2 size={13} className="animate-spin" /> : <Ban size={13} />} Cancelar cobrança
                </button>
              )}
            </div>
          </div>
        ))}
        {!pagamentos.length && !carregando && !podeGerar && <p className="text-xs text-slate-500">Nenhuma cobrança registrada.</p>}
      </div>
    </div>
  );
};
