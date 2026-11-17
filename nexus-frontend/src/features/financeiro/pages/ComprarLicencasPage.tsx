import React, { useEffect, useMemo, useState } from 'react';
import { KeyRound, Loader2, Minus, Plus, ShoppingCart } from 'lucide-react';
import { useDisciplinas } from '@/features/licencas/components/EstoqueDisciplina';
import { financeiroApi } from '@/features/financeiro/api';
import { MeioPagamentoCheckout, ResultadoCheckout, useOpcoesCheckout } from '@/features/financeiro/components/Checkout';
import { CheckoutResposta, MeioCobranca, Produto, erroApi, formatBRL } from '@/features/financeiro/types';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

/** Checkout de licenças por disciplina: o pagamento confirmado credita o estoque daquela disciplina no Polo. */
export const ComprarLicencasPage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const isAdmin = normalizeUserRole(perfil?.nome) === 'admin';
  const disciplinas = useDisciplinas();
  const [catalogo, setCatalogo] = useState<Produto[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [quantidades, setQuantidades] = useState<Record<string, number>>({});
  const [poloId, setPoloId] = useState(user?.polo_id || '');
  const [polos, setPolos] = useState<{ id: string; nome: string }[]>([]);
  const [busca, setBusca] = useState('');
  const [meio, setMeio] = useState<MeioCobranca | ''>('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const [resultado, setResultado] = useState<CheckoutResposta | null>(null);

  useEffect(() => {
    financeiroApi.listProdutos({ tipo: 'licenca' })
      .then((res) => setCatalogo(res.items))
      .catch((error) => setErro(erroApi(error, 'Não foi possível carregar o catálogo de licenças.')))
      .finally(() => setCarregando(false));
    if (isAdmin) {
      polosEscolasApi.listarPolos({ limit: 200 })
        .then((data: any) => setPolos(data?.items || []))
        .catch(() => setPolos([]));
    }
  }, [isAdmin]);

  const nomeDisciplina = (id?: string | null) => disciplinas.find((d) => d.id === id)?.nome || 'Disciplina';
  const visiveis = catalogo.filter((p) =>
    `${p.nome} ${nomeDisciplina(p.disciplina_id)}`.toLocaleLowerCase('pt-BR').includes(busca.trim().toLocaleLowerCase('pt-BR')));
  const itens = useMemo(
    () => catalogo.filter((p) => (quantidades[p.id] || 0) > 0).map((p) => ({ produto: p, quantidade: quantidades[p.id] })),
    [catalogo, quantidades],
  );
  const total = itens.reduce((s, i) => s + i.produto.preco * i.quantidade, 0);
  const totalLicencas = itens.reduce((s, i) => s + i.quantidade, 0);
  const opcoes = useOpcoesCheckout('licenca', total, poloId);

  const setQtd = (id: string, valor: number) =>
    setQuantidades((q) => ({ ...q, [id]: Math.max(0, Math.min(100000, Math.floor(valor) || 0)) }));

  const comprar = async () => {
    setErro('');
    if (!itens.length) { setErro('Informe a quantidade de ao menos uma disciplina.'); return; }
    if (isAdmin && !poloId) { setErro('Selecione o Polo.'); return; }
    if (!meio) { setErro('Escolha a forma de pagamento.'); return; }
    setEnviando(true);
    try {
      const res = await financeiroApi.checkout({
        tipo: 'licenca',
        polo_id: isAdmin ? poloId : undefined,
        itens: itens.map((i) => ({ produto_id: i.produto.id, quantidade: i.quantidade })),
        meio,
      });
      setResultado(res);
      setQuantidades({});
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível concluir a compra.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl">
        <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300"><KeyRound size={15} /> Licenças</p>
        <h1 className="text-3xl font-extrabold text-white">Comprar Licenças</h1>
        <p className="mt-1 text-sm text-slate-400">Escolha as disciplinas e quantidades. Após a confirmação do pagamento, as licenças entram no estoque do Polo, separadas por disciplina.</p>
      </header>

      {resultado ? (
        <ResultadoCheckout resultado={resultado} onFechar={() => setResultado(null)} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
              <div><h2 className="font-bold text-white">Licenças por disciplina</h2><p className="text-xs text-slate-500">Preços definidos pela coordenação.</p></div>
              <input className="w-56 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" placeholder="Buscar disciplina…" value={busca} onChange={(e) => setBusca(e.target.value)} />
            </div>
            {carregando ? (
              <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
            ) : (
              <ul className="divide-y divide-slate-800">
                {visiveis.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-4 p-4">
                    <div>
                      <p className="font-semibold text-white">{nomeDisciplina(p.disciplina_id)}</p>
                      <p className="text-xs text-slate-500">{p.nome} · {p.sku}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-200">{formatBRL(p.preco)} <span className="text-xs text-slate-500">/ licença</span></span>
                      <div className="flex items-center rounded-xl border border-slate-700">
                        <button onClick={() => setQtd(p.id, (quantidades[p.id] || 0) - 1)} className="p-2 text-slate-400 hover:text-white"><Minus size={14} /></button>
                        <input type="number" min={0} value={quantidades[p.id] || 0} onChange={(e) => setQtd(p.id, Number(e.target.value))} className="w-16 bg-transparent text-center text-sm text-white outline-none" />
                        <button onClick={() => setQtd(p.id, (quantidades[p.id] || 0) + 1)} className="p-2 text-slate-400 hover:text-white"><Plus size={14} /></button>
                      </div>
                    </div>
                  </li>
                ))}
                {!visiveis.length && <li className="p-12 text-center text-slate-500">Nenhuma licença disponível no catálogo.</li>}
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
                  <span>{i.quantidade} × {nomeDisciplina(i.produto.disciplina_id)}</span>
                  <span>{formatBRL(i.produto.preco * i.quantidade)}</span>
                </li>
              ))}
              {!itens.length && <li className="text-xs text-slate-500">Nenhuma disciplina selecionada.</li>}
            </ul>
            <p className="flex justify-between border-t border-slate-800 pt-3 text-lg font-bold text-white">
              <span>Total <span className="text-xs font-normal text-slate-500">({totalLicencas} licenças)</span></span><span>{formatBRL(total)}</span>
            </p>
            <MeioPagamentoCheckout opcoes={opcoes} meio={meio} onChange={setMeio} />
            {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
            <button onClick={comprar} disabled={enviando || !itens.length || !meio} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-white disabled:opacity-50">
              {enviando && <Loader2 className="animate-spin" size={16} />} Finalizar e gerar pagamento
            </button>
          </aside>
        </div>
      )}
    </div>
  );
};
