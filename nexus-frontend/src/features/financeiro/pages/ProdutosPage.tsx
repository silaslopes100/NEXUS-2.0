import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Package, Pencil, Plus, RefreshCw, X } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { Produto, TIPO_PEDIDO, TipoPedido, erroApi, formatBRL } from '@/features/financeiro/types';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const labelCls = 'mb-1 block text-xs font-semibold text-slate-400';

interface FormState {
  tipo: TipoPedido;
  sku: string;
  nome: string;
  descricao: string;
  preco: string;
  peso_g: string;
  ativo: boolean;
}

const VAZIO: FormState = { tipo: 'livro', sku: '', nome: '', descricao: '', preco: '', peso_g: '', ativo: true };

/** Catálogo de livros e licenças vendidos aos Polos (preço usado nos pedidos). */
export const ProdutosPage: React.FC = () => {
  const [items, setItems] = useState<Produto[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState('');
  const [editando, setEditando] = useState<Produto | 'novo' | null>(null);
  const [form, setForm] = useState<FormState>(VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await financeiroApi.listProdutos({ incluir_inativos: true })).items);
    } catch (error) {
      setFeedback(erroApi(error, 'Não foi possível carregar os produtos.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const abrir = (produto: Produto | 'novo') => {
    setErroForm('');
    setEditando(produto);
    setForm(produto === 'novo' ? VAZIO : {
      tipo: produto.tipo,
      sku: produto.sku,
      nome: produto.nome,
      descricao: produto.descricao || '',
      preco: String(produto.preco),
      peso_g: produto.peso_g != null ? String(produto.peso_g) : '',
      ativo: produto.ativo,
    });
  };

  const salvar = async (event: React.FormEvent) => {
    event.preventDefault();
    const preco = Number(form.preco.replace(',', '.'));
    if (Number.isNaN(preco) || preco < 0) { setErroForm('Preço inválido.'); return; }
    setSalvando(true);
    setErroForm('');
    const payload = {
      nome: form.nome.trim(),
      descricao: form.descricao.trim() || null,
      preco,
      peso_g: form.peso_g ? Number(form.peso_g) : null,
      ativo: form.ativo,
    };
    try {
      if (editando === 'novo') {
        await financeiroApi.createProduto({ ...payload, tipo: form.tipo, sku: form.sku.trim() });
        setFeedback('Produto cadastrado.');
      } else if (editando) {
        await financeiroApi.updateProduto(editando.id, payload);
        setFeedback('Produto atualizado.');
      }
      setEditando(null);
      await load();
    } catch (error) {
      setErroForm(erroApi(error, 'Não foi possível salvar o produto.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300"><Package size={15} /> Catálogo</p>
          <h1 className="text-3xl font-extrabold text-white">Produtos & Preços</h1>
          <p className="mt-1 text-sm text-slate-400">Livros e licenças disponíveis para os pedidos dos Polos. O preço do pedido vem sempre daqui.</p>
        </div>
        <button onClick={() => abrir('novo')} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus size={16} /> Novo produto</button>
      </header>

      {feedback && (
        <div className="flex items-center justify-between rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200">
          <span>{feedback}</span><button onClick={() => setFeedback('')}><X size={16} /></button>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <p className="text-xs text-slate-500">{items.length} produto(s)</p>
          <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
        {loading ? (
          <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr><th className="p-4">SKU</th><th className="p-4">Nome</th><th className="p-4">Tipo</th><th className="p-4 text-right">Preço</th><th className="p-4">Situação</th><th className="p-4" /></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {items.map((p) => (
                  <tr key={p.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4 font-mono text-xs text-white">{p.sku}</td>
                    <td className="p-4">{p.nome}</td>
                    <td className="p-4 text-xs">{TIPO_PEDIDO[p.tipo]}</td>
                    <td className="p-4 text-right font-semibold text-white">{formatBRL(p.preco)}</td>
                    <td className="p-4 text-xs">{p.ativo ? <span className="text-emerald-400">Ativo</span> : <span className="text-slate-500">Inativo</span>}</td>
                    <td className="p-4 text-right">
                      <button onClick={() => abrir(p)} className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white" title="Editar"><Pencil size={14} /></button>
                    </td>
                  </tr>
                ))}
                {!items.length && <tr><td colSpan={6} className="p-12 text-center text-slate-500">Nenhum produto cadastrado ainda.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form onSubmit={salvar} className="w-full max-w-lg space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">{editando === 'novo' ? 'Novo produto' : 'Editar produto'}</h2>
              <button type="button" onClick={() => setEditando(null)} className="text-slate-400"><X /></button>
            </div>
            {erroForm && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erroForm}</p>}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Tipo</label>
                <select className={inputClass} disabled={editando !== 'novo'} value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as TipoPedido })}>
                  <option value="livro">Livro</option>
                  <option value="licenca">Licença</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>SKU (código único)</label>
                <input className={inputClass} required minLength={2} disabled={editando !== 'novo'} value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} placeholder="LIV-MAT-01" />
              </div>
            </div>
            <div>
              <label className={labelCls}>Nome</label>
              <input className={inputClass} required minLength={2} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            </div>
            <div>
              <label className={labelCls}>Descrição</label>
              <textarea className={inputClass} rows={2} value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Preço (R$)</label>
                <input className={inputClass} required inputMode="decimal" value={form.preco} onChange={(e) => setForm({ ...form, preco: e.target.value })} placeholder="59,90" />
              </div>
              <div>
                <label className={labelCls}>Peso (g) — usado na etiqueta</label>
                <input className={inputClass} type="number" min={0} value={form.peso_g} onChange={(e) => setForm({ ...form, peso_g: e.target.value })} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /> Ativo (aparece no catálogo dos Polos)
            </label>
            <button disabled={salvando} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-white disabled:opacity-50">
              {salvando && <Loader2 className="animate-spin" size={16} />} Salvar
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
