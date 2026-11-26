import React, { useCallback, useState } from 'react';
import { BookMarked, Check, Loader2, QrCode, Barcode, X } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { lookupAddressByCep } from '@/features/alunos/viacep';
import { DisciplinaLoja, Endereco, PedidoAluno, TurmaLoja, brl, lojaApi } from '../api';
import { PagamentoPainel } from './PagamentoPainel';

const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none';
const rotulo = 'mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-400';

interface Props {
  turma: TurmaLoja;
  disciplina: DisciplinaLoja;
  endereco: Endereco;
  /** Pedido em aberto já existente: abre direto no pagamento. */
  pedidoInicial?: PedidoAluno | null;
  onFechar: () => void;
  onMudou: () => void;
}

/** Checkout de uma disciplina EAD: upsell do livro, endereço, Pix ou boleto e o pagamento. */
export const CheckoutDrawer: React.FC<Props> = ({ turma, disciplina: d, endereco, pedidoInicial, onFechar, onMudou }) => {
  const [comLivro, setComLivro] = useState(false);
  const [meio, setMeio] = useState<'PIX' | 'BOLETO'>('PIX');
  const [end, setEnd] = useState<Endereco>({ ...endereco });
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [pedido, setPedido] = useState<PedidoAluno | null>(pedidoInicial ?? null);

  const total = d.valor_ead + (comLivro ? d.valor_livro_ead : 0);
  const enderecoOk = !!(end.cep && end.logradouro && end.numero && end.cidade && end.uf);

  const buscarCep = async (cep: string) => {
    const digitos = cep.replace(/\D/g, '');
    if (digitos.length !== 8) return;
    setBuscandoCep(true);
    try {
      const a = await lookupAddressByCep(digitos, new AbortController().signal);
      setEnd((e) => ({ ...e, logradouro: a.logradouro || e.logradouro, bairro: a.bairro || e.bairro, cidade: a.cidade || e.cidade, uf: a.uf || e.uf }));
    } catch {
      /* preenchimento manual */
    } finally {
      setBuscandoCep(false);
    }
  };

  const pagar = async () => {
    setEnviando(true);
    setErro(null);
    try {
      const p = await lojaApi.checkout({
        disciplina_id: d.id, turma_id: turma.id, com_livro: comLivro, meio,
        endereco: comLivro ? end : null,
      });
      setPedido(p);
      onMudou();
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível gerar o pagamento.'));
    } finally {
      setEnviando(false);
    }
  };

  const atualizado = useCallback((p: PedidoAluno) => { setPedido(p); onMudou(); }, [onMudou]);
  const setCampo = (k: keyof Endereco) => (e: React.ChangeEvent<HTMLInputElement>) => setEnd((x) => ({ ...x, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onMouseDown={onFechar}>
      <aside className="flex h-full w-full max-w-lg flex-col border-l border-slate-700 bg-slate-900 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-slate-800 px-4 py-4 sm:px-6">
          <h2 className="text-lg font-bold text-white">{pedido ? 'Pagamento' : 'Comprar disciplina'}</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"><X size={18} /></button>
        </header>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-5 sm:px-6">
          {pedido ? (
            <PagamentoPainel pedido={pedido} onAtualizado={atualizado} onFechar={onFechar} />
          ) : (
            <>
              <div className="flex gap-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="h-16 w-24 shrink-0 overflow-hidden rounded-xl bg-gradient-to-br from-blue-800 to-slate-950">
                  {d.capa_url && <img src={urlArquivo(d.capa_url)} alt="" className="h-full w-full object-cover" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] text-slate-400">{turma.nome} · {turma.curso_nome}</p>
                  <p className="font-bold text-white">{d.nome}</p>
                  <p className="text-xs text-slate-400">
                    {d.total_aulas} aulas{d.prazo_dias ? ` · ${d.prazo_dias} dias para concluir` : ''}
                  </p>
                </div>
                <p className="shrink-0 font-bold text-white">{brl(d.valor_ead)}</p>
              </div>

              {d.estado === 'recompra' && (
                <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                  O prazo anterior terminou. Com o novo pagamento, a disciplina reabre com um prazo novo.
                </p>
              )}

              <section className="space-y-2">
                <p className="text-sm font-bold text-white">Forma de pagamento</p>
                <div className="grid grid-cols-2 gap-3">
                  {([['PIX', 'Pix', 'Liberação em minutos', QrCode], ['BOLETO', 'Boleto', 'Até 3 dias úteis', Barcode]] as const).map(([v, r, a, Icone]) => (
                    <button key={v} type="button" onClick={() => setMeio(v)}
                      className={`rounded-2xl border-2 p-3 text-left transition ${meio === v ? 'border-nexus-yellow bg-nexus-yellow/10' : 'border-slate-800 hover:border-slate-600'}`}>
                      <span className="flex items-center gap-2 font-bold text-white"><Icone size={16} className="text-nexus-yellow" /> {r}</span>
                      <span className="text-[11px] text-slate-400">{a}</span>
                    </button>
                  ))}
                </div>
              </section>

              {comLivro && (
                <section className="space-y-3 rounded-2xl border border-slate-800 p-4">
                  <p className="text-sm font-bold text-white">Endereço de entrega</p>
                  <div className="grid grid-cols-3 gap-3">
                    <label className="col-span-1">
                      <span className={rotulo}>CEP</span>
                      <span className="relative block">
                        <input value={end.cep ?? ''} onChange={setCampo('cep')} onBlur={(e) => void buscarCep(e.target.value)} className={campo} inputMode="numeric" maxLength={9} />
                        {buscandoCep && <Loader2 size={14} className="absolute right-3 top-3 animate-spin text-slate-400" />}
                      </span>
                    </label>
                    <label className="col-span-2"><span className={rotulo}>Rua</span><input value={end.logradouro ?? ''} onChange={setCampo('logradouro')} className={campo} /></label>
                    <label><span className={rotulo}>Número</span><input value={end.numero ?? ''} onChange={setCampo('numero')} className={campo} /></label>
                    <label className="col-span-2"><span className={rotulo}>Complemento</span><input value={end.complemento ?? ''} onChange={setCampo('complemento')} className={campo} /></label>
                    <label className="col-span-3"><span className={rotulo}>Bairro</span><input value={end.bairro ?? ''} onChange={setCampo('bairro')} className={campo} /></label>
                    <label className="col-span-2"><span className={rotulo}>Cidade</span><input value={end.cidade ?? ''} onChange={setCampo('cidade')} className={campo} /></label>
                    <label><span className={rotulo}>UF</span><input value={end.uf ?? ''} onChange={(e) => setEnd((x) => ({ ...x, uf: e.target.value.toUpperCase() }))} maxLength={2} className={campo} /></label>
                  </div>
                </section>
              )}

              {erro && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}
            </>
          )}
        </div>

        {!pedido && (
          <footer className="space-y-3 border-t border-slate-800 px-4 pt-4 pb-safe-4 sm:px-6">
            {d.livro_disponivel && (
              <button type="button" onClick={() => setComLivro((v) => !v)}
                className={`flex w-full items-center gap-3 rounded-2xl border-2 p-3 text-left transition ${comLivro ? 'border-nexus-yellow bg-nexus-yellow/10' : 'border-dashed border-nexus-yellow/40 hover:border-nexus-yellow'}`}>
                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${comLivro ? 'border-nexus-yellow bg-nexus-yellow text-ink' : 'border-slate-600'}`}>
                  {comLivro && <Check size={13} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2 text-sm font-bold text-white"><BookMarked size={15} className="text-nexus-yellow" /> Incluir o livro físico</span>
                  <span className="block text-[11px] text-slate-400">
                    {comLivro ? 'Preencha o endereço de entrega acima.' : 'Material impresso da disciplina, entregue no seu endereço.'}
                  </span>
                </span>
                <span className="shrink-0 font-extrabold text-nexus-yellow">+ {brl(d.valor_livro_ead)}</span>
              </button>
            )}
            <div className="space-y-1 text-sm">
              <div className="flex justify-between text-slate-300"><span>Disciplina</span><span>{brl(d.valor_ead)}</span></div>
              {comLivro && <div className="flex justify-between text-slate-300"><span>Livro físico</span><span>{brl(d.valor_livro_ead)}</span></div>}
              <div className="flex justify-between border-t border-slate-800 pt-2 text-base font-extrabold text-white"><span>Total</span><span>{brl(total)}</span></div>
            </div>
            <button type="button" onClick={() => void pagar()} disabled={enviando || (comLivro && !enderecoOk)}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-nexus-yellow py-4 text-sm font-extrabold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
              {enviando && <Loader2 size={16} className="animate-spin" />} Gerar {meio === 'PIX' ? 'Pix' : 'boleto'} de {brl(total)}
            </button>
          </footer>
        )}
      </aside>
    </div>
  );
};
