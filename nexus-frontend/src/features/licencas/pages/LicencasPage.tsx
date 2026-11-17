import React, { useCallback, useEffect, useState } from 'react';
import { ArrowUpFromLine, CheckCircle2, KeyRound, Loader2, Plus, RefreshCw, Shuffle, X } from 'lucide-react';
import {
  EstoqueDisciplina, licencasApi, LicencaKpis, MovimentacaoLicenca, nomeDisciplina,
} from '@/features/licencas/api';
import {
  DisciplinaSelect, paraDisciplinaId, TabelaEstoqueDisciplina, useDisciplinas, VALOR_SEM_DISCIPLINA,
} from '@/features/licencas/components/EstoqueDisciplina';
import { LicencasEscolaPage } from '@/features/licencas/pages/LicencasEscolaPage';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

type Acao = 'compra' | 'distribuir' | 'reclassificar';
interface Opcao { id: string; nome: string }

const listaDe = (data: unknown): Opcao[] => {
  const itens = Array.isArray(data) ? data : ((data as { items?: Opcao[] })?.items || []);
  return itens.map((i: Opcao) => ({ id: i.id, nome: i.nome }));
};

const FORM_INICIAL = {
  quantidade: 1, fornecedor: '', valor_unitario: 0, data: new Date().toISOString().slice(0, 10),
  escola_id: '', disciplina: '', destino: '',
};

/** Licenças do Polo: saldo por disciplina, compra externa, distribuição e reclassificação (admin). */
export const LicencasPage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome || user?.perfil?.nome);
  const isAdmin = role === 'admin';

  // Perfil escola usa a tela da própria escola.
  if (role === 'escola' && user?.escola_id) return <LicencasEscolaPage escolaIdFixo={user.escola_id} />;
  return <LicencasPolo isAdmin={isAdmin} poloDoUsuario={user?.polo_id || ''} />;
};

const LicencasPolo: React.FC<{ isAdmin: boolean; poloDoUsuario: string }> = ({ isAdmin, poloDoUsuario }) => {
  const disciplinas = useDisciplinas();
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [poloId, setPoloId] = useState(poloDoUsuario);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [kpis, setKpis] = useState<LicencaKpis | null>(null);
  const [estoque, setEstoque] = useState<EstoqueDisciplina | null>(null);
  const [items, setItems] = useState<MovimentacaoLicenca[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [action, setAction] = useState<Acao | null>(null);
  const [form, setForm] = useState(FORM_INICIAL);

  useEffect(() => {
    if (!isAdmin) return;
    polosEscolasApi.listarPolos({ limit: 200 })
      .then((data) => {
        const lista = listaDe(data);
        setPolos(lista);
        setPoloId((atual) => atual || lista[0]?.id || '');
      })
      .catch(() => setPolos([]));
  }, [isAdmin]);

  const load = useCallback(async () => {
    if (!poloId) { setLoading(false); return; }
    setLoading(true);
    try {
      const [kpiResponse, estoqueResponse, movementResponse, escolasResponse] = await Promise.all([
        licencasApi.getKpis(poloId),
        licencasApi.estoquePolo(poloId),
        licencasApi.listMovimentacoes(poloId),
        polosEscolasApi.listarEscolasDoPolo(poloId),
      ]);
      setKpis(kpiResponse);
      setEstoque(estoqueResponse);
      setItems(movementResponse.items);
      setEscolas(listaDe(escolasResponse));
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Não foi possível carregar as licenças.');
    } finally {
      setLoading(false);
    }
  }, [poloId]);
  useEffect(() => { load(); }, [load]);

  const abrir = (acao: Acao) => { setForm(FORM_INICIAL); setAction(acao); };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const disciplina_id = paraDisciplinaId(form.disciplina);
      if (action === 'compra') {
        await licencasApi.comprar(poloId, {
          quantidade: form.quantidade, fornecedor: form.fornecedor, valor_unitario: form.valor_unitario,
          data: form.data, disciplina_id,
        });
      }
      if (action === 'distribuir') {
        await licencasApi.distribuir(poloId, { escola_id: form.escola_id, quantidade: form.quantidade, disciplina_id });
      }
      if (action === 'reclassificar') {
        await licencasApi.reclassificar(poloId, {
          de_disciplina_id: disciplina_id, para_disciplina_id: paraDisciplinaId(form.destino), quantidade: form.quantidade,
        });
      }
      setFeedback('Movimentação registrada com sucesso.');
      setAction(null);
      await load();
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'A movimentação não pôde ser concluída.');
    } finally {
      setSaving(false);
    }
  };

  const temSemDisciplina = (estoque?.items || []).some((i) => !i.materia_id && i.quantidade_disponivel > 0);
  const metricCards = kpis ? [
    ['Compradas', kpis.total_licencas_compradas, 'text-white'],
    ['Vendidas', kpis.total_licencas_vendidas_alunos, 'text-emerald-400'],
    ['Disponíveis', kpis.total_licencas_nao_vendidas, 'text-amber-300'],
    ['No polo', kpis.total_nao_vendidas_polo, 'text-blue-400'],
    ['Conversão', `${kpis.taxa_conversao_global}%`, 'text-indigo-300'],
  ] : [];

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-300"><KeyRound size={15} /> Fluxo de licenças</p>
          <h1 className="text-3xl font-extrabold text-white">Estoque e distribuição</h1>
          <p className="mt-1 text-sm text-slate-400">Saldo por disciplina, distribuição às escolas e registro de compras externas.</p>
          {isAdmin && (
            <select value={poloId} onChange={(e) => setPoloId(e.target.value)} className="mt-3 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              {!polos.length && <option value="">Nenhum polo</option>}
              {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {isAdmin && (
            <button onClick={() => abrir('compra')} disabled={!poloId} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
              <Plus size={16} /> Registrar compra externa
            </button>
          )}
          <button onClick={() => abrir('distribuir')} disabled={!poloId} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
            <ArrowUpFromLine size={16} /> Distribuir
          </button>
        </div>
      </header>

      {feedback && (
        <div className="flex items-center justify-between rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200">
          <span className="flex items-center gap-2"><CheckCircle2 size={16} /> {feedback}</span>
          <button onClick={() => setFeedback('')}><X size={16} /></button>
        </div>
      )}
      {!poloId && !loading && <p className="text-sm text-slate-400">Nenhum polo vinculado ao seu usuário.</p>}

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {metricCards.map(([label, value, color]) => (
          <div key={String(label)} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
            <strong className={`mt-2 block text-2xl font-black ${color}`}>{value}</strong>
          </div>
        ))}
      </section>

      <TabelaEstoqueDisciplina
        estoque={estoque}
        acao={isAdmin && temSemDisciplina ? (
          <button onClick={() => abrir('reclassificar')} className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 px-3 py-2 text-xs font-semibold text-amber-300">
            <Shuffle size={14} /> Reclassificar saldo
          </button>
        ) : undefined}
      />

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between border-b border-slate-800 p-4">
          <div><h2 className="font-bold text-white">Últimas movimentações</h2><p className="text-xs text-slate-500">{items.length} registros carregados</p></div>
          <button onClick={load} title="Recarregar" className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
        </div>
        {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr><th className="p-4">Tipo</th><th className="p-4">Disciplina</th><th className="p-4">Destino</th><th className="p-4 text-center">Qtd.</th><th className="p-4">Status</th><th className="p-4 text-right">Data</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {items.map((item) => (
                  <tr key={item.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4 font-semibold capitalize text-white">{item.tipo.split('_').join(' ')}</td>
                    <td className="p-4 text-xs">{nomeDisciplina(item)}</td>
                    <td className="p-4 text-xs text-slate-400">
                      {item.aluno_id ? 'Aluno' : item.escola_id ? (escolas.find((e) => e.id === item.escola_id)?.nome || 'Escola') : 'Polo'}
                    </td>
                    <td className="p-4 text-center font-bold">{item.quantidade}</td>
                    <td className="p-4 text-xs text-emerald-400">{item.status}</td>
                    <td className="p-4 text-right text-xs text-slate-500">{item.criado_em ? new Date(item.criado_em).toLocaleDateString('pt-BR') : '-'}</td>
                  </tr>
                ))}
                {!items.length && <tr><td colSpan={6} className="p-12 text-center text-slate-500">Nenhuma movimentação encontrada.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {action && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">
                {action === 'compra' ? 'Registrar compra externa' : action === 'distribuir' ? 'Distribuir para escola' : 'Reclassificar saldo'}
              </h2>
              <button type="button" onClick={() => setAction(null)} className="text-slate-400"><X /></button>
            </div>

            {action === 'compra' && (
              <>
                <p className="text-xs text-slate-500">Compra já paga fora do NEXUS. Compras com boleto/PIX são feitas pelo Polo em "Comprar Licenças".</p>
                <DisciplinaSelect value={form.disciplina} onChange={(v) => setForm({ ...form, disciplina: v })} disciplinas={disciplinas} />
                <input className={inputClass} required placeholder="Fornecedor" value={form.fornecedor} onChange={(e) => setForm({ ...form, fornecedor: e.target.value })} />
                <input className={inputClass} type="number" min={0} step="0.01" required placeholder="Valor unitário" value={form.valor_unitario} onChange={(e) => setForm({ ...form, valor_unitario: Number(e.target.value) })} />
                <input className={inputClass} type="date" required value={form.data} onChange={(e) => setForm({ ...form, data: e.target.value })} />
              </>
            )}

            {action === 'distribuir' && (
              <>
                <label className="block space-y-1 text-sm text-slate-300">
                  <span>Escola</span>
                  <select required className={inputClass} value={form.escola_id} onChange={(e) => setForm({ ...form, escola_id: e.target.value })}>
                    <option value="">Selecione</option>
                    {escolas.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
                  </select>
                </label>
                <DisciplinaSelect value={form.disciplina} onChange={(v) => setForm({ ...form, disciplina: v })} saldos={estoque?.items || []} />
              </>
            )}

            {action === 'reclassificar' && (
              <>
                <p className="text-xs text-slate-500">Move licenças do saldo "Sem disciplina" (anterior ao estoque por disciplina) para uma disciplina.</p>
                <DisciplinaSelect label="Origem" value={form.disciplina || VALOR_SEM_DISCIPLINA} onChange={(v) => setForm({ ...form, disciplina: v })} saldos={estoque?.items || []} />
                <DisciplinaSelect label="Destino" value={form.destino} onChange={(v) => setForm({ ...form, destino: v })} disciplinas={disciplinas} incluirSemDisciplina={false} />
              </>
            )}

            <label className="block space-y-1 text-sm text-slate-300">
              <span>Quantidade</span>
              <input className={inputClass} type="number" min={1} required value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: Number(e.target.value) })} />
            </label>
            <button disabled={saving} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-white disabled:opacity-50">
              {saving && <Loader2 className="animate-spin" size={16} />} Confirmar movimentação
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
