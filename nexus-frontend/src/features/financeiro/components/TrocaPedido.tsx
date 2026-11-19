import React, { useState } from 'react';
import { ArrowRight, Ban, CheckCircle2, Loader2, Repeat } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { MOTIVO_TROCA, Pedido, erroApi } from '@/features/financeiro/types';

interface Props {
  pedido: Pedido;
  /** Admin: "Troca efetuada" e "Recusar". */
  podeDecidir: boolean;
  onAtualizado: (pedido: Pedido) => void;
}

/** Detalhe da solicitação de troca de livro (itens, motivo) e as ações do Admin. */
export const TrocaPedido: React.FC<Props> = ({ pedido, podeDecidir, onAtualizado }) => {
  const [modo, setModo] = useState<'efetuar' | 'recusar' | null>(null);
  const [motivo, setMotivo] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const pendente = pedido.status === 'troca_solicitada';

  const executar = async (acao: () => Promise<Pedido>) => {
    setSalvando(true);
    setErro('');
    try {
      onAtualizado(await acao());
      setModo(null);
      setMotivo('');
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível concluir a ação.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <section className="space-y-3 rounded-xl border border-violet-500/30 bg-violet-500/5 p-4">
      <h3 className="flex items-center gap-2 text-xs font-bold uppercase text-violet-300">
        <Repeat size={14} /> Itens da troca
      </h3>
      <ul className="space-y-2">
        {(pedido.troca_itens || []).map((item, indice) => (
          <li key={item.id || indice} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-slate-300">Devolver</span>
            <strong className="text-white">{item.disciplina_devolver_nome || 'Disciplina'}</strong>
            <span className="text-slate-500">× {item.quantidade}</span>
            <ArrowRight size={14} className="text-slate-500" />
            <span className="text-slate-300">Receber</span>
            <strong className="text-white">{item.disciplina_receber_nome || 'Disciplina'}</strong>
          </li>
        ))}
      </ul>
      {(pedido.troca_motivo || pedido.troca_descricao) && (
        <div className="border-t border-slate-800 pt-3 text-sm">
          <p className="text-xs text-slate-500">Motivo</p>
          <p className="text-white">{pedido.troca_motivo ? MOTIVO_TROCA[pedido.troca_motivo] : '—'}</p>
          {pedido.troca_descricao && <p className="mt-1 text-slate-400">{pedido.troca_descricao}</p>}
        </div>
      )}

      {erro && <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-300">{erro}</p>}

      {podeDecidir && pendente && (
        <div className="border-t border-slate-800 pt-3">
          {modo === null && (
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setModo('efetuar')} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-3 py-2 text-xs font-semibold text-on-accent hover:bg-violet-500">
                <CheckCircle2 size={15} /> Troca efetuada
              </button>
              <button onClick={() => setModo('recusar')} className="inline-flex items-center gap-2 rounded-xl bg-red-600/80 px-3 py-2 text-xs font-semibold text-on-accent hover:bg-red-600">
                <Ban size={15} /> Recusar
              </button>
            </div>
          )}
          {modo === 'efetuar' && (
            <div className="space-y-3">
              <p className="text-sm text-slate-300">
                Confirmar a troca? As licenças novas entram no saldo da unidade e o Estoque Central é atualizado
                (livro devolvido entra, livro novo sai).
              </p>
              <div className="flex gap-2">
                <button disabled={salvando} onClick={() => executar(() => financeiroApi.efetuarTroca(pedido.id))} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-on-accent disabled:opacity-50">
                  {salvando && <Loader2 size={14} className="animate-spin" />} Confirmar troca efetuada
                </button>
                <button onClick={() => setModo(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-300">Voltar</button>
              </div>
            </div>
          )}
          {modo === 'recusar' && (
            <div className="space-y-3">
              <textarea
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                rows={2}
                placeholder="Motivo da recusa (obrigatório; a unidade recebe esse texto)"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              />
              <div className="flex gap-2">
                <button disabled={salvando || motivo.trim().length < 3} onClick={() => executar(() => financeiroApi.recusarTroca(pedido.id, motivo.trim()))} className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-xs font-semibold text-on-accent disabled:opacity-50">
                  {salvando && <Loader2 size={14} className="animate-spin" />} Recusar troca
                </button>
                <button onClick={() => setModo(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-300">Voltar</button>
              </div>
              <p className="text-xs text-slate-500">As licenças reservadas voltam ao saldo da unidade.</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
