import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Pencil, Plus, Power, RefreshCw, Scale, X } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { NOME_GATEWAY, RegraPagamento, RegraPagamentoPayload, TIPO_PEDIDO, erroApi, formatBRL } from '@/features/financeiro/types';
import { polosEscolasApi } from '@/features/polos_escolas/api';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const labelCls = 'mb-1 block text-xs font-semibold text-slate-400';

interface FormState {
  nome: string;
  aplica_tipo_pedido: string;
  aplica_polo_id: string;
  boleto: boolean;
  pix: boolean;
  gateway_preferido: string;
  dias_vencimento: string;
  multa_pct: string;
  juros_mes_pct: string;
  desconto_antecipado_pct: string;
  valor_minimo: string;
  prioridade: string;
  ativo: boolean;
}

const VAZIO: FormState = {
  nome: '', aplica_tipo_pedido: '', aplica_polo_id: '', boleto: true, pix: true, gateway_preferido: '',
  dias_vencimento: '3', multa_pct: '0', juros_mes_pct: '0', desconto_antecipado_pct: '0', valor_minimo: '0',
  prioridade: '100', ativo: true,
};

const num = (v: string) => Number(String(v).replace(',', '.'));

/** CRUD das regras de pagamento usadas no checkout (meios, vencimento, encargos). */
export const RegrasPagamentoPage: React.FC = () => {
  const [items, setItems] = useState<RegraPagamento[]>([]);
  const [polos, setPolos] = useState<{ id: string; nome: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState('');
  const [editando, setEditando] = useState<RegraPagamento | 'nova' | null>(null);
  const [form, setForm] = useState<FormState>(VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await financeiroApi.listRegras());
    } catch (error) {
      setFeedback(erroApi(error, 'Não foi possível carregar as regras.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    polosEscolasApi.listarPolos({ limit: 200 }).then((d: any) => setPolos(d?.items || [])).catch(() => setPolos([]));
  }, [load]);

  const abrir = (r: RegraPagamento | 'nova') => {
    setErroForm('');
    setEditando(r);
    setForm(r === 'nova' ? VAZIO : {
      nome: r.nome,
      aplica_tipo_pedido: r.aplica_tipo_pedido || '',
      aplica_polo_id: r.aplica_polo_id || '',
      boleto: r.meios_permitidos.includes('BOLETO'),
      pix: r.meios_permitidos.includes('PIX'),
      gateway_preferido: r.gateway_preferido || '',
      dias_vencimento: String(r.dias_vencimento),
      multa_pct: String(r.multa_pct),
      juros_mes_pct: String(r.juros_mes_pct),
      desconto_antecipado_pct: String(r.desconto_antecipado_pct),
      valor_minimo: String(r.valor_minimo),
      prioridade: String(r.prioridade),
      ativo: r.ativo,
    });
  };

  const salvar = async (event: React.FormEvent) => {
    event.preventDefault();
    const meios = [form.boleto && 'BOLETO', form.pix && 'PIX'].filter(Boolean) as string[];
    if (!meios.length) { setErroForm('Escolha ao menos um meio de pagamento.'); return; }
    const numeros = [form.dias_vencimento, form.multa_pct, form.juros_mes_pct, form.desconto_antecipado_pct, form.valor_minimo, form.prioridade].map(num);
    if (numeros.some((n) => Number.isNaN(n) || n < 0)) { setErroForm('Revise os valores numéricos.'); return; }
    const payload: RegraPagamentoPayload = {
      nome: form.nome.trim(),
      aplica_tipo_pedido: (form.aplica_tipo_pedido || null) as RegraPagamento['aplica_tipo_pedido'],
      aplica_polo_id: form.aplica_polo_id || null,
      meios_permitidos: meios,
      gateway_preferido: form.gateway_preferido || null,
      dias_vencimento: numeros[0],
      multa_pct: numeros[1],
      juros_mes_pct: numeros[2],
      desconto_antecipado_pct: numeros[3],
      valor_minimo: numeros[4],
      prioridade: Math.round(numeros[5]),
      ativo: form.ativo,
    };
    setSalvando(true);
    setErroForm('');
    try {
      if (editando === 'nova') await financeiroApi.criarRegra(payload);
      else if (editando) await financeiroApi.atualizarRegra(editando.id, payload);
      setFeedback('Regra salva.');
      setEditando(null);
      await load();
    } catch (error) {
      setErroForm(erroApi(error, 'Não foi possível salvar a regra.'));
    } finally {
      setSalvando(false);
    }
  };

  const alternar = async (r: RegraPagamento) => {
    try {
      await financeiroApi.atualizarRegra(r.id, { ativo: !r.ativo });
      await load();
    } catch (error) {
      setFeedback(erroApi(error, 'Não foi possível alterar a regra.'));
    }
  };

  const escopo = (r: RegraPagamento) => [
    r.aplica_tipo_pedido ? TIPO_PEDIDO[r.aplica_tipo_pedido] : 'Todos os tipos',
    r.polo_nome || (r.aplica_polo_id ? 'Polo' : 'Todos os Polos'),
    r.valor_minimo ? `a partir de ${formatBRL(r.valor_minimo)}` : '',
  ].filter(Boolean).join(' · ');

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300"><Scale size={15} /> Financeiro</p>
          <h1 className="text-3xl font-extrabold text-white">Regras de Pagamento</h1>
          <p className="mt-1 text-sm text-slate-400">
            Definem meios (boleto/PIX), vencimento e encargos do checkout. Vale a regra mais específica (Polo › tipo); no empate, a de menor prioridade.
          </p>
        </div>
        <button onClick={() => abrir('nova')} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus size={16} /> Nova regra</button>
      </header>

      {feedback && (
        <div className="flex items-center justify-between rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200">
          <span>{feedback}</span><button onClick={() => setFeedback('')}><X size={16} /></button>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <p className="text-xs text-slate-500">{items.length} regra(s)</p>
          <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
        </div>
        {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr><th className="p-4">Regra</th><th className="p-4">Aplica a</th><th className="p-4">Meios</th><th className="p-4">Vencimento</th><th className="p-4">Encargos (boleto)</th><th className="p-4 text-center">Prioridade</th><th className="p-4" /></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {items.map((r) => (
                  <tr key={r.id} className={`text-slate-300 ${r.ativo ? '' : 'opacity-50'}`}>
                    <td className="p-4">
                      <p className="font-semibold text-white">{r.nome}</p>
                      <p className="text-xs">{r.generica && <span className="text-emerald-400">Padrão (sem filtros)</span>}{!r.ativo && <span className="text-slate-500"> Inativa</span>}</p>
                    </td>
                    <td className="p-4 text-xs">{escopo(r)}</td>
                    <td className="p-4 text-xs">{r.meios_permitidos.join(', ')}{r.gateway_preferido ? ` · ${NOME_GATEWAY[r.gateway_preferido as keyof typeof NOME_GATEWAY] || r.gateway_preferido}` : ''}</td>
                    <td className="p-4 text-xs">{r.dias_vencimento} dia(s)</td>
                    <td className="p-4 text-xs">
                      {[r.multa_pct ? `multa ${r.multa_pct}%` : '', r.juros_mes_pct ? `juros ${r.juros_mes_pct}% a.m.` : '', r.desconto_antecipado_pct ? `desc. ${r.desconto_antecipado_pct}%` : ''].filter(Boolean).join(' · ') || '—'}
                    </td>
                    <td className="p-4 text-center text-xs">{r.prioridade}</td>
                    <td className="p-4">
                      <div className="flex justify-end gap-1">
                        <button onClick={() => abrir(r)} title="Editar" className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white"><Pencil size={14} /></button>
                        <button onClick={() => alternar(r)} title={r.ativo ? 'Desativar' : 'Ativar'} className={`rounded-lg border p-1.5 ${r.ativo ? 'border-red-500/40 text-red-300' : 'border-emerald-500/40 text-emerald-300'}`}><Power size={14} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!items.length && <tr><td colSpan={7} className="p-12 text-center text-slate-500">Nenhuma regra cadastrada.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4">
          <form onSubmit={salvar} className="my-auto w-full max-w-2xl space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">{editando === 'nova' ? 'Nova regra' : 'Editar regra'}</h2>
              <button type="button" onClick={() => setEditando(null)} className="text-slate-400"><X /></button>
            </div>
            {erroForm && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erroForm}</p>}
            <div>
              <label className={labelCls}>Nome</label>
              <input className={inputClass} required minLength={2} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className={labelCls}>Tipo de pedido</label>
                <select className={inputClass} value={form.aplica_tipo_pedido} onChange={(e) => setForm({ ...form, aplica_tipo_pedido: e.target.value })}>
                  <option value="">Todos</option><option value="livro">Livro</option><option value="licenca">Licença</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Polo</label>
                <select className={inputClass} value={form.aplica_polo_id} onChange={(e) => setForm({ ...form, aplica_polo_id: e.target.value })}>
                  <option value="">Todos</option>
                  {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Valor mínimo do pedido (R$)</label>
                <input className={inputClass} inputMode="decimal" value={form.valor_minimo} onChange={(e) => setForm({ ...form, valor_minimo: e.target.value })} />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className={labelCls}>Meios permitidos</label>
                <div className="flex gap-4 pt-2 text-sm text-slate-300">
                  <label className="flex items-center gap-2"><input type="checkbox" checked={form.boleto} onChange={(e) => setForm({ ...form, boleto: e.target.checked })} /> Boleto</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={form.pix} onChange={(e) => setForm({ ...form, pix: e.target.checked })} /> PIX</label>
                </div>
              </div>
              <div>
                <label className={labelCls}>Gateway preferido</label>
                <select className={inputClass} value={form.gateway_preferido} onChange={(e) => setForm({ ...form, gateway_preferido: e.target.value })}>
                  <option value="">Padrão do ambiente</option>
                  {Object.entries(NOME_GATEWAY).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Vencimento (dias)</label>
                <input className={inputClass} type="number" min={1} max={60} value={form.dias_vencimento} onChange={(e) => setForm({ ...form, dias_vencimento: e.target.value })} />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-4">
              <div><label className={labelCls}>Multa (%)</label><input className={inputClass} inputMode="decimal" value={form.multa_pct} onChange={(e) => setForm({ ...form, multa_pct: e.target.value })} /></div>
              <div><label className={labelCls}>Juros ao mês (%)</label><input className={inputClass} inputMode="decimal" value={form.juros_mes_pct} onChange={(e) => setForm({ ...form, juros_mes_pct: e.target.value })} /></div>
              <div><label className={labelCls}>Desconto até o venc. (%)</label><input className={inputClass} inputMode="decimal" value={form.desconto_antecipado_pct} onChange={(e) => setForm({ ...form, desconto_antecipado_pct: e.target.value })} /></div>
              <div><label className={labelCls}>Prioridade (menor = 1ª)</label><input className={inputClass} type="number" min={0} value={form.prioridade} onChange={(e) => setForm({ ...form, prioridade: e.target.value })} /></div>
            </div>
            <p className="text-[11px] text-slate-500">Multa, juros e desconto são enviados no boleto do Asaas. PagBank e Mercado Pago ainda não recebem esses encargos.</p>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /> Ativa
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
