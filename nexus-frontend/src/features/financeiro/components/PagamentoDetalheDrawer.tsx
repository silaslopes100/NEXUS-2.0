import React, { useCallback, useEffect, useState } from 'react';
import { Ban, Copy, CheckCircle2, ExternalLink, Loader2, RotateCcw, Webhook, X } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { SeloSimulado, SimuladorPagamento } from '@/features/financeiro/components/SimuladorPagamento';
import {
  COR_STATUS_PAGAMENTO, NOME_GATEWAY, Pagamento, WebhookEvento, erroApi, formatBRL, formatData, linkCobranca,
} from '@/features/financeiro/types';

const Copiar: React.FC<{ texto: string; rotulo: string }> = ({ texto, rotulo }) => {
  const [ok, setOk] = useState(false);
  return (
    <div>
      <p className="mb-1 text-[11px] font-semibold uppercase text-slate-500">{rotulo}</p>
      <div className="flex items-start gap-2">
        <code className="flex-1 break-all rounded-lg bg-slate-950 p-2 text-[11px] text-slate-200">{texto}</code>
        <button
          onClick={async () => {
            try { await navigator.clipboard.writeText(texto); setOk(true); setTimeout(() => setOk(false), 1500); } catch { setOk(false); }
          }}
          className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white"
          title="Copiar"
        >
          {ok ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
      </div>
    </div>
  );
};

interface Props {
  pagamento: Pagamento;
  podeOperar: boolean;
  onClose: () => void;
  onAlterado: () => void;
}

/** Detalhe da cobrança: dados de pagamento, eventos do gateway, cancelar e segunda via. */
export const PagamentoDetalheDrawer: React.FC<Props> = ({ pagamento, podeOperar, onClose, onAlterado }) => {
  const [pg, setPg] = useState(pagamento);
  const [eventos, setEventos] = useState<WebhookEvento[]>([]);
  const [acao, setAcao] = useState<string | null>(null);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  const carregar = useCallback(async () => {
    try {
      const [atual, evts] = await Promise.all([
        financeiroApi.getPagamento(pagamento.id),
        pagamento.gateway_payment_id && podeOperar
          ? financeiroApi.listWebhookEventos({ payment_id: pagamento.gateway_payment_id, limit: 50 }).then((r) => r.items)
          : Promise.resolve([] as WebhookEvento[]),
      ]);
      setPg(atual);
      setEventos(evts);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar o detalhe.'));
    }
  }, [pagamento, podeOperar]);

  useEffect(() => { carregar(); }, [carregar]);

  const executar = async (nome: string, fn: () => Promise<unknown>, msg: string) => {
    setAcao(nome);
    setErro('');
    try {
      await fn();
      setAviso(msg);
      onAlterado();
      await carregar();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível concluir a ação.'));
    } finally {
      setAcao(null);
    }
  };

  const link = linkCobranca(pg);
  const aberto = pg.status === 'pendente' || pg.status === 'vencido';

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onClose}>
      <aside onClick={(e) => e.stopPropagation()} className="h-full w-full max-w-xl space-y-5 overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 text-sm shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Cobrança {pg.billing_type || ''}</p>
            <h2 className="text-xl font-bold text-white">{formatBRL(pg.valor)}</h2>
            <p className={`text-xs font-semibold ${COR_STATUS_PAGAMENTO[pg.status || ''] || 'text-slate-300'}`}>{pg.status}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X /></button>
        </div>

        {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-300">{erro}</p>}
        {aviso && <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-emerald-200">{aviso}</p>}

        <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-xs">
          <div><p className="text-slate-500">Pedido</p><p className="font-mono text-white">{pg.pedido_numero || '-'}</p></div>
          <div><p className="text-slate-500">Polo</p><p className="text-white">{pg.polo_nome || '-'}</p></div>
          <div>
            <p className="text-slate-500">Gateway</p>
            <p className="text-white">{pg.gateway === 'fake' ? <SeloSimulado /> : `${NOME_GATEWAY[pg.gateway as keyof typeof NOME_GATEWAY] || pg.gateway || '-'} (${pg.ambiente || '-'})`}</p>
          </div>
          <div><p className="text-slate-500">ID no gateway</p><p className="break-all font-mono text-white">{pg.gateway_payment_id || '-'}</p></div>
          <div><p className="text-slate-500">Criado em</p><p className="text-white">{formatData(pg.criado_em, true)}</p></div>
          <div><p className="text-slate-500">Vencimento</p><p className="text-white">{formatData(pg.vencimento_em)}</p></div>
          {pg.pago_em && <div><p className="text-slate-500">Pago em</p><p className="text-white">{formatData(pg.pago_em, true)}</p></div>}
          {pg.valor_liquido != null && <div><p className="text-slate-500">Valor líquido</p><p className="text-white">{formatBRL(pg.valor_liquido)}</p></div>}
        </div>

        {aberto && pg.linha_digitavel && <Copiar texto={pg.linha_digitavel} rotulo="Linha digitável" />}
        {aberto && pg.pix_copia_cola && <Copiar texto={pg.pix_copia_cola} rotulo="PIX copia e cola" />}
        {aberto && pg.pix_qrcode_base64 && pg.gateway !== 'fake' && (
          <img src={`data:image/png;base64,${pg.pix_qrcode_base64}`} alt="QR Code PIX" className="h-40 w-40 rounded-lg bg-[#fff] p-2" />
        )}

        <div className="flex flex-wrap gap-2">
          {link && (
            <a href={link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:text-white">
              <ExternalLink size={13} /> {pg.boleto_url ? 'Abrir boleto' : 'Abrir fatura'}
            </a>
          )}
          {podeOperar && pg.status === 'vencido' && (
            <button
              disabled={!!acao}
              onClick={() => executar('segunda', () => financeiroApi.segundaVia(pg.id), 'Segunda via gerada: a cobrança antiga foi cancelada.')}
              className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-on-accent disabled:opacity-50"
            >
              {acao === 'segunda' ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />} Gerar segunda via
            </button>
          )}
          {podeOperar && aberto && pg.gateway && (
            <button
              disabled={!!acao}
              onClick={() => window.confirm('Cancelar esta cobrança no gateway?') && executar('cancelar', () => financeiroApi.cancelarPagamento(pg.id), 'Cobrança cancelada.')}
              className="inline-flex items-center gap-1 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs text-red-300 disabled:opacity-50"
            >
              {acao === 'cancelar' ? <Loader2 size={13} className="animate-spin" /> : <Ban size={13} />} Cancelar cobrança
            </button>
          )}
        </div>
        <SimuladorPagamento pagamento={pg} onAlterado={() => { onAlterado(); carregar(); }} />

        {podeOperar && (
          <div>
            <h3 className="mb-2 flex items-center gap-1 text-xs font-bold uppercase text-slate-500"><Webhook size={13} /> Eventos do gateway</h3>
            <ol className="space-y-2 border-l border-slate-700 pl-4">
              {eventos.map((e) => (
                <li key={e.id} className="text-xs text-slate-400">
                  <span className="font-mono text-slate-200">{e.tipo_evento || 'evento'}</span>
                  {' · '}{formatData(e.recebido_em, true)}{' · '}
                  <span className={e.status === 'erro' ? 'text-red-400' : e.status === 'processado' ? 'text-emerald-400' : ''}>{e.status}</span>
                  {e.erro && <p className="text-slate-500">{e.erro}</p>}
                </li>
              ))}
              {!eventos.length && <li className="text-xs text-slate-500">Nenhum evento recebido para esta cobrança.</li>}
            </ol>
          </div>
        )}
      </aside>
    </div>
  );
};
