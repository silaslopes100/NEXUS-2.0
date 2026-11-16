import React, { useEffect, useMemo, useState } from 'react';
import { BookMarked, CheckCircle2, Loader2, MapPin, Minus, Plus, ShoppingCart, X } from 'lucide-react';
import { PeriodoFiltros } from '@/components/filters/PeriodoFiltros';
import { financeiroApi } from '@/features/financeiro/api';
import { PedidosTabela } from '@/features/financeiro/components/PedidosTabela';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { EnderecoEntrega, Produto, STATUS_PEDIDO, erroApi, formatBRL } from '@/features/financeiro/types';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const STATUS_OPCOES = Object.entries(STATUS_PEDIDO).map(([value, meta]) => ({ value, label: meta.label }));
const CAMPOS_ENDERECO: { key: keyof EnderecoEntrega; label: string; span?: string }[] = [
  { key: 'nome', label: 'Destinatário', span: 'col-span-2' },
  { key: 'cep', label: 'CEP' },
  { key: 'uf', label: 'UF' },
  { key: 'logradouro', label: 'Logradouro', span: 'col-span-2' },
  { key: 'numero', label: 'Número' },
  { key: 'complemento', label: 'Complemento' },
  { key: 'bairro', label: 'Bairro' },
  { key: 'cidade', label: 'Cidade' },
  { key: 'telefone', label: 'Telefone', span: 'col-span-2' },
];

/** Pedidos de livros didáticos feitos pelo Polo/Escola: novo pedido + acompanhamento. */
export const PedidosLivrosUnidadePage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const isAdmin = normalizeUserRole(perfil?.nome) === 'admin';
  const [aba, setAba] = useState<'novo' | 'meus'>('novo');
  const [catalogo, setCatalogo] = useState<Produto[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [quantidades, setQuantidades] = useState<Record<string, number>>({});
  const [poloId, setPoloId] = useState(user?.polo_id || '');
  const [polos, setPolos] = useState<{ id: string; nome: string }[]>([]);
  const [enderecoPolo, setEnderecoPolo] = useState<EnderecoEntrega | null>(null);
  const [outroEndereco, setOutroEndereco] = useState(false);
  const [endereco, setEndereco] = useState<EnderecoEntrega>({});
  const [observacao, setObservacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [recarregar, setRecarregar] = useState(0);

  useEffect(() => {
    financeiroApi.listProdutos({ tipo: 'livro' })
      .then((res) => setCatalogo(res.items))
      .catch((error) => setErro(erroApi(error, 'Não foi possível carregar o catálogo.')))
      .finally(() => setCarregando(false));
    if (isAdmin) {
      polosEscolasApi.listarPolos({ limit: 200 })
        .then((data: any) => setPolos(data?.items || []))
        .catch(() => setPolos([]));
    }
  }, [isAdmin]);

  useEffect(() => {
    if (!poloId) { setEnderecoPolo(null); return; }
    polosEscolasApi.obterPolo(poloId)
      .then((p: any) => setEnderecoPolo({
        nome: p.nome, cep: p.cep, logradouro: p.logradouro, numero: p.numero,
        complemento: p.complemento, bairro: p.bairro, cidade: p.cidade, uf: p.uf,
      }))
      .catch(() => setEnderecoPolo(null));
  }, [poloId]);

  const itens = useMemo(
    () => catalogo.filter((p) => (quantidades[p.id] || 0) > 0).map((p) => ({ produto: p, quantidade: quantidades[p.id] })),
    [catalogo, quantidades],
  );
  const total = itens.reduce((s, i) => s + i.produto.preco * i.quantidade, 0);

  const setQtd = (id: string, valor: number) =>
    setQuantidades((q) => ({ ...q, [id]: Math.max(0, Math.min(100000, Math.floor(valor) || 0)) }));

  const enviar = async () => {
    setErro('');
    setSucesso('');
    if (!itens.length) { setErro('Adicione ao menos um livro.'); return; }
    if (isAdmin && !poloId) { setErro('Selecione o Polo do pedido.'); return; }
    setEnviando(true);
    try {
      const pedido = await financeiroApi.createPedido({
        tipo: 'livro',
        polo_id: isAdmin ? poloId : undefined,
        itens: itens.map((i) => ({ produto_id: i.produto.id, quantidade: i.quantidade })),
        endereco: outroEndereco ? endereco : undefined,
        observacao: observacao.trim() || undefined,
      });
      setSucesso(`Pedido ${pedido.numero} criado (${formatBRL(pedido.valor_total)}). Status: aguardando pagamento.`);
      setQuantidades({});
      setObservacao('');
      setRecarregar((n) => n + 1);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível criar o pedido.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl">
        <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300"><BookMarked size={15} /> Livros didáticos</p>
        <h1 className="text-3xl font-extrabold text-white">Pedidos de Livros</h1>
        <p className="mt-1 text-sm text-slate-400">Monte o pedido a partir do catálogo e acompanhe o status até a entrega.</p>
        <div className="mt-4 inline-flex rounded-xl border border-slate-700 p-1">
          {(['novo', 'meus'] as const).map((a) => (
            <button key={a} onClick={() => setAba(a)} className={`rounded-lg px-4 py-1.5 text-sm font-semibold ${aba === a ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}>
              {a === 'novo' ? 'Novo pedido' : 'Meus pedidos'}
            </button>
          ))}
        </div>
      </header>

      {sucesso && (
        <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
          <span className="flex items-center gap-2"><CheckCircle2 size={16} /> {sucesso}</span>
          <button onClick={() => setSucesso('')}><X size={16} /></button>
        </div>
      )}

      {aba === 'meus' ? (
        <>
          <PeriodoFiltros mostrarUnidade={isAdmin} statusOpcoes={STATUS_OPCOES} />
          <PedidosTabela mostrarPolo={isAdmin} recarregarChave={recarregar} />
        </>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 lg:col-span-2">
            <div className="border-b border-slate-800 p-4">
              <h2 className="font-bold text-white">Catálogo</h2>
              <p className="text-xs text-slate-500">Preços definidos pela coordenação.</p>
            </div>
            {carregando ? (
              <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
            ) : (
              <ul className="divide-y divide-slate-800">
                {catalogo.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-4 p-4">
                    <div>
                      <p className="font-semibold text-white">{p.nome}</p>
                      <p className="text-xs text-slate-500">{p.sku}{p.descricao ? ` · ${p.descricao}` : ''}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-200">{formatBRL(p.preco)}</span>
                      <div className="flex items-center rounded-xl border border-slate-700">
                        <button onClick={() => setQtd(p.id, (quantidades[p.id] || 0) - 1)} className="p-2 text-slate-400 hover:text-white"><Minus size={14} /></button>
                        <input
                          type="number"
                          min={0}
                          value={quantidades[p.id] || 0}
                          onChange={(e) => setQtd(p.id, Number(e.target.value))}
                          className="w-16 bg-transparent text-center text-sm text-white outline-none"
                        />
                        <button onClick={() => setQtd(p.id, (quantidades[p.id] || 0) + 1)} className="p-2 text-slate-400 hover:text-white"><Plus size={14} /></button>
                      </div>
                    </div>
                  </li>
                ))}
                {!catalogo.length && <li className="p-12 text-center text-slate-500">Nenhum livro disponível no catálogo.</li>}
              </ul>
            )}
          </section>

          <aside className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <h2 className="flex items-center gap-2 font-bold text-white"><ShoppingCart size={16} /> Resumo</h2>
            {isAdmin && (
              <select className={inputClass} value={poloId} onChange={(e) => setPoloId(e.target.value)}>
                <option value="">Selecione o Polo…</option>
                {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
              </select>
            )}
            <ul className="space-y-1 text-sm">
              {itens.map((i) => (
                <li key={i.produto.id} className="flex justify-between text-slate-300">
                  <span>{i.quantidade} × {i.produto.nome}</span>
                  <span>{formatBRL(i.produto.preco * i.quantidade)}</span>
                </li>
              ))}
              {!itens.length && <li className="text-xs text-slate-500">Nenhum item selecionado.</li>}
            </ul>
            <p className="flex justify-between border-t border-slate-800 pt-3 text-lg font-bold text-white"><span>Total</span><span>{formatBRL(total)}</span></p>

            <div className="space-y-2 text-sm">
              <p className="flex items-center gap-1 text-xs font-bold uppercase text-slate-500"><MapPin size={13} /> Entrega</p>
              <label className="flex items-center gap-2 text-slate-300">
                <input type="radio" checked={!outroEndereco} onChange={() => setOutroEndereco(false)} /> Endereço do Polo
              </label>
              {!outroEndereco && (
                <p className="rounded-xl bg-slate-950/60 p-3 text-xs text-slate-400">
                  {enderecoPolo?.logradouro
                    ? `${enderecoPolo.logradouro}${enderecoPolo.numero ? `, ${enderecoPolo.numero}` : ''} · ${enderecoPolo.cidade}/${enderecoPolo.uf} · CEP ${enderecoPolo.cep}`
                    : 'Endereço cadastrado no Polo (se estiver incompleto, o pedido será recusado — use "Outro endereço").'}
                </p>
              )}
              <label className="flex items-center gap-2 text-slate-300">
                <input
                  type="radio"
                  checked={outroEndereco}
                  onChange={() => { setOutroEndereco(true); setEndereco(enderecoPolo || {}); }}
                /> Outro endereço
              </label>
              {outroEndereco && (
                <div className="grid grid-cols-2 gap-2">
                  {CAMPOS_ENDERECO.map((c) => (
                    <input
                      key={c.key}
                      className={`${inputClass} ${c.span || ''}`}
                      placeholder={c.label}
                      maxLength={c.key === 'uf' ? 2 : undefined}
                      value={endereco[c.key] || ''}
                      onChange={(e) => setEndereco({ ...endereco, [c.key]: c.key === 'uf' ? e.target.value.toUpperCase() : e.target.value })}
                    />
                  ))}
                </div>
              )}
            </div>

            <textarea className={inputClass} rows={2} placeholder="Observação (opcional)" value={observacao} onChange={(e) => setObservacao(e.target.value)} />
            {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
            <button
              onClick={enviar}
              disabled={enviando || !itens.length}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-white disabled:opacity-50"
            >
              {enviando && <Loader2 className="animate-spin" size={16} />} Enviar pedido
            </button>
            <p className="text-[11px] text-slate-500">O pagamento (boleto/PIX) será gerado automaticamente a partir da Fase 3. Até lá, a baixa é feita manualmente pelo financeiro.</p>
          </aside>
        </div>
      )}
    </div>
  );
};
