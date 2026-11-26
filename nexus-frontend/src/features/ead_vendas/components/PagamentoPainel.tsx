import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Barcode, Check, CheckCircle2, Copy, ExternalLink, Loader2, QrCode, XCircle } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { soltarConfete } from '@/features/ava/utils/confete';
import { PedidoAluno, brl, dataBr, lojaApi } from '../api';

const BotaoCopiar: React.FC<{ texto: string; rotulo: string }> = ({ texto, rotulo }) => {
  const [ok, setOk] = useState(false);
  return (
    <button type="button"
      onClick={() => { void navigator.clipboard?.writeText(texto).then(() => { setOk(true); window.setTimeout(() => setOk(false), 2000); }); }}
      className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-nexus-yellow py-3 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
      {ok ? <><Check size={16} /> Copiado!</> : <><Copy size={16} /> {rotulo}</>}
    </button>
  );
};

interface Props {
  pedido: PedidoAluno;
  onAtualizado: (p: PedidoAluno) => void;
  onFechar: () => void;
}

/** Pix (QR + copia e cola) ou boleto do pedido, com conferência automática do pagamento. */
export const PagamentoPainel: React.FC<Props> = ({ pedido, onAtualizado, onFechar }) => {
  const [cancelando, setCancelando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const aguardando = pedido.status === 'aguardando_pagamento';
  const pago = !!pedido.pago_em || ['concluido', 'pago_aguardando_envio', 'enviado', 'entregue'].includes(pedido.status);

  // Confere o pagamento a cada 5 s enquanto a cobrança está em aberto.
  useEffect(() => {
    if (!aguardando) return;
    const t = window.setInterval(() => {
      lojaApi.pedido(pedido.id).then((p) => {
        if (p.status !== pedido.status || p.pagamento_status !== pedido.pagamento_status) onAtualizado(p);
      }).catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(t);
  }, [aguardando, pedido.id, pedido.status, pedido.pagamento_status, onAtualizado]);

  useEffect(() => {
    if (pago) soltarConfete(2400);
  }, [pago]);

  const cancelar = async () => {
    if (!window.confirm('Cancelar este pedido? A cobrança em aberto será cancelada.')) return;
    setCancelando(true);
    setErro(null);
    try {
      onAtualizado(await lojaApi.cancelar(pedido.id));
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setCancelando(false);
    }
  };

  if (pago) {
    return (
      <div className="space-y-5 py-6 text-center">
        <CheckCircle2 className="mx-auto text-emerald-400" size={56} />
        <div>
          <h3 className="text-xl font-extrabold text-white">Pagamento confirmado!</h3>
          <p className="mt-1 text-sm text-slate-300">
            {pedido.disciplina_nome} já está liberada na sua Sala de Aula Virtual.
            {pedido.com_livro ? ' O livro físico será enviado para o seu endereço.' : ''}
          </p>
        </div>
        {pedido.disciplina_id && (
          <Link to={`/aluno/ava/disciplinas/${pedido.disciplina_id}`}
            className="inline-flex items-center justify-center rounded-2xl bg-nexus-yellow px-6 py-3.5 text-sm font-extrabold text-ink hover:bg-nexus-yellow-hover">
            Ir para a disciplina
          </Link>
        )}
      </div>
    );
  }

  if (pedido.status === 'cancelado') {
    return (
      <div className="space-y-4 py-6 text-center">
        <XCircle className="mx-auto text-slate-500" size={48} />
        <p className="text-sm text-slate-300">Pedido cancelado. Você pode comprar a disciplina novamente quando quiser.</p>
        <button type="button" onClick={onFechar} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800">Fechar</button>
      </div>
    );
  }

  const vencido = pedido.pagamento_status === 'vencido' || pedido.pagamento_status === 'cancelado';
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        <div>
          <p className="text-xs text-slate-400">Pedido {pedido.numero}</p>
          <p className="font-semibold text-white">{pedido.disciplina_nome}{pedido.com_livro ? ' + livro físico' : ''}</p>
        </div>
        <p className="text-xl font-extrabold text-white">{brl(pedido.valor_total)}</p>
      </div>

      {vencido ? (
        <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
          Esta cobrança venceu. Feche e compre a disciplina novamente para gerar um novo pagamento.
        </p>
      ) : pedido.billing_type === 'PIX' ? (
        <div className="space-y-4 text-center">
          <p className="flex items-center justify-center gap-2 text-sm font-bold text-white"><QrCode size={16} className="text-nexus-yellow" /> Pague com Pix</p>
          {pedido.pix_qrcode_base64 ? (
            <img src={pedido.pix_qrcode_base64.startsWith('data:') ? pedido.pix_qrcode_base64 : `data:image/png;base64,${pedido.pix_qrcode_base64}`}
              alt="QR Code Pix" className="mx-auto h-52 w-52 rounded-2xl bg-white p-3" />
          ) : null}
          {pedido.pix_copia_cola && (
            <>
              <p className="break-all rounded-xl border border-slate-800 bg-slate-950 p-3 text-left font-mono text-[11px] text-slate-300">{pedido.pix_copia_cola}</p>
              <BotaoCopiar texto={pedido.pix_copia_cola} rotulo="Copiar código Pix" />
            </>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="flex items-center gap-2 text-sm font-bold text-white"><Barcode size={16} className="text-nexus-yellow" /> Boleto bancário</p>
          {pedido.linha_digitavel && (
            <>
              <p className="break-all rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-300">{pedido.linha_digitavel}</p>
              <BotaoCopiar texto={pedido.linha_digitavel} rotulo="Copiar linha digitável" />
            </>
          )}
          {(pedido.boleto_url || pedido.invoice_url) && (
            <a href={pedido.boleto_url || pedido.invoice_url || '#'} target="_blank" rel="noreferrer"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-800">
              <ExternalLink size={15} /> Abrir boleto
            </a>
          )}
          <p className="text-xs text-slate-500">O boleto pode levar até 3 dias úteis para ser compensado.</p>
        </div>
      )}

      {!vencido && (
        <p className="flex items-center justify-center gap-2 text-xs text-slate-400">
          <Loader2 size={13} className="animate-spin" /> Aguardando a confirmação do pagamento…
          {pedido.vencimento_em ? ` Vence em ${dataBr(pedido.vencimento_em)}.` : ''}
        </p>
      )}
      {erro && <p role="alert" className="text-center text-sm text-red-300">{erro}</p>}
      <div className="flex justify-between gap-2 border-t border-slate-800 pt-4">
        <button type="button" onClick={() => void cancelar()} disabled={cancelando}
          className="text-xs font-semibold text-slate-400 hover:text-red-300 disabled:opacity-50">
          {cancelando ? 'Cancelando…' : 'Cancelar pedido'}
        </button>
        <button type="button" onClick={onFechar} className="text-xs font-semibold text-slate-300 hover:text-white">Pagar depois</button>
      </div>
    </div>
  );
};
