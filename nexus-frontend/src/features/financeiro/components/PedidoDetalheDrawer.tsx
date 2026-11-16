import React, { useCallback, useEffect, useState } from 'react';
import { Ban, CheckCircle2, Loader2, MapPin, Wallet, X } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { CobrancaPedido } from '@/features/financeiro/components/CobrancaPedido';
import { StatusPedidoBadge } from '@/features/financeiro/components/StatusPedidoBadge';
import {
  ACOES_MANUAIS,
  Pedido,
  STATUS_PEDIDO,
  StatusManual,
  StatusPedido,
  TIPO_PEDIDO,
  erroApi,
  formatBRL,
  formatData,
} from '@/features/financeiro/types';

const ROTULO_ACAO: Record<StatusManual, { label: string; icon: React.ReactNode; className: string }> = {
  pago_aguardando_envio: { label: 'Marcar como pago', icon: <Wallet size={15} />, className: 'bg-blue-600 hover:bg-blue-500' },
  concluido: { label: 'Marcar como pago e concluir', icon: <CheckCircle2 size={15} />, className: 'bg-emerald-600 hover:bg-emerald-500' },
  cancelado: { label: 'Cancelar pedido', icon: <Ban size={15} />, className: 'bg-red-600/80 hover:bg-red-600' },
};

interface Props {
  pedidoId: string;
  podeAlterarStatus: boolean;
  onClose: () => void;
  onAlterado: () => void;
}

export const PedidoDetalheDrawer: React.FC<Props> = ({ pedidoId, podeAlterarStatus, onClose, onAlterado }) => {
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [erro, setErro] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [acao, setAcao] = useState<StatusManual | null>(null);
  const [texto, setTexto] = useState('');

  const load = useCallback(async () => {
    try {
      setPedido(await financeiroApi.getPedido(pedidoId));
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar o pedido.'));
    }
  }, [pedidoId]);

  useEffect(() => { load(); }, [load]);

  const confirmar = async () => {
    if (!acao || !pedido) return;
    setSalvando(true);
    setErro('');
    try {
      const atualizado = await financeiroApi.alterarStatus(pedido.id, {
        status: acao,
        ...(acao === 'cancelado' ? { motivo_cancelamento: texto } : { observacao: texto || undefined }),
      });
      setPedido(atualizado);
      setAcao(null);
      setTexto('');
      onAlterado();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível alterar o status.'));
    } finally {
      setSalvando(false);
    }
  };

  const acoes = pedido && podeAlterarStatus
    // Livro pago segue para a logística; licença paga é concluída na hora.
    ? (ACOES_MANUAIS[pedido.status] || []).filter((a) =>
      pedido.tipo === 'livro' ? a !== 'concluido' : a !== 'pago_aguardando_envio')
    : [];
  const end = pedido?.endereco;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onClose}>
      <aside onClick={(e) => e.stopPropagation()} className="h-full w-full max-w-xl overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-5 flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Pedido</p>
            <h2 className="font-mono text-xl font-bold text-white">{pedido?.numero || '...'}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X /></button>
        </div>

        {erro && <p className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
        {!pedido && !erro && <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>}

        {pedido && (
          <div className="space-y-5 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPedidoBadge status={pedido.status} />
              <span className="rounded-full border border-slate-700 px-2.5 py-0.5 text-[11px] text-slate-300">{TIPO_PEDIDO[pedido.tipo]}</span>
              <span className="text-xs text-slate-500">Criado em {formatData(pedido.criado_em, true)}</span>
            </div>

            <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <div><p className="text-xs text-slate-500">Polo</p><p className="text-white">{pedido.polo_nome || '-'}</p></div>
              <div><p className="text-xs text-slate-500">Escola</p><p className="text-white">{pedido.escola_nome || '-'}</p></div>
              {pedido.fornecedor && <div><p className="text-xs text-slate-500">Fornecedor</p><p className="text-white">{pedido.fornecedor}</p></div>}
              {pedido.pago_em && <div><p className="text-xs text-slate-500">Pago em</p><p className="text-white">{formatData(pedido.pago_em, true)}</p></div>}
              {pedido.motivo_cancelamento && (
                <div className="col-span-2"><p className="text-xs text-slate-500">Motivo do cancelamento</p><p className="text-red-300">{pedido.motivo_cancelamento}</p></div>
              )}
            </div>

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase text-slate-500">Itens</h3>
              <table className="w-full text-left text-sm">
                <tbody className="divide-y divide-slate-800">
                  {pedido.itens.map((i) => (
                    <tr key={i.id} className="text-slate-300">
                      <td className="py-2">{i.descricao || 'Item'}</td>
                      <td className="py-2 text-center text-xs">{i.quantidade} × {formatBRL(i.valor_unitario)}</td>
                      <td className="py-2 text-right text-white">{formatBRL(i.valor_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-2 space-y-1 border-t border-slate-800 pt-2 text-right text-xs text-slate-400">
                {Number(pedido.desconto) > 0 && <p>Desconto: −{formatBRL(pedido.desconto)}</p>}
                <p className="text-base font-bold text-white">Total {formatBRL(pedido.valor_total)}</p>
              </div>
            </div>

            <CobrancaPedido pedido={pedido} podeCancelar={podeAlterarStatus} onAlterado={() => { load(); onAlterado(); }} />

            {end && (end.logradouro || end.cidade) && (
              <div>
                <h3 className="mb-2 flex items-center gap-1 text-xs font-bold uppercase text-slate-500"><MapPin size={13} /> Entrega</h3>
                <p className="text-slate-300">
                  {end.nome && <><strong className="text-white">{end.nome}</strong><br /></>}
                  {end.logradouro}{end.numero ? `, ${end.numero}` : ''}{end.complemento ? ` - ${end.complemento}` : ''}<br />
                  {end.bairro ? `${end.bairro} · ` : ''}{end.cidade}/{end.uf} · CEP {end.cep}
                </p>
              </div>
            )}

            <div>
              <h3 className="mb-2 text-xs font-bold uppercase text-slate-500">Histórico</h3>
              <ol className="space-y-2 border-l border-slate-700 pl-4">
                {pedido.historico.map((h) => (
                  <li key={h.id} className="text-xs text-slate-400">
                    <span className="text-slate-200">{STATUS_PEDIDO[h.status_para as StatusPedido]?.label || h.status_para}</span>
                    {' · '}{formatData(h.criado_em, true)}{' · '}{h.origem}
                    {h.observacao && <p className="text-slate-500">{h.observacao}</p>}
                  </li>
                ))}
              </ol>
            </div>

            {acoes.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                <h3 className="mb-3 text-xs font-bold uppercase text-slate-500">Ações financeiras</h3>
                {!acao ? (
                  <div className="flex flex-wrap gap-2">
                    {acoes.map((a) => (
                      <button key={a} onClick={() => setAcao(a)} className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-white ${ROTULO_ACAO[a].className}`}>
                        {ROTULO_ACAO[a].icon} {ROTULO_ACAO[a].label}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-white">{ROTULO_ACAO[acao].label}</p>
                    <textarea
                      value={texto}
                      onChange={(e) => setTexto(e.target.value)}
                      rows={2}
                      placeholder={acao === 'cancelado' ? 'Motivo do cancelamento (obrigatório)' : 'Observação (ex.: PIX recebido manualmente)'}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={confirmar}
                        disabled={salvando || (acao === 'cancelado' && !texto.trim())}
                        className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
                      >
                        {salvando && <Loader2 size={14} className="animate-spin" />} Confirmar
                      </button>
                      <button onClick={() => { setAcao(null); setTexto(''); }} className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-300">Voltar</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
};
