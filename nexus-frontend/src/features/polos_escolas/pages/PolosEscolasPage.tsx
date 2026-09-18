import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Building2, CheckCircle2, Loader2, MapPin, Plus, RefreshCw, Search, School, X } from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { DashboardPoloKpis, EscolaCreatePayload, EscolaItem, PoloCreatePayload, PoloItem } from '@/types/polos';
import { useAuthStore } from '@/stores/authStore';

const emptyAddress = { logradouro: '', numero: '', bairro: '', cidade: '', estado: 'SP', cep: '' };
const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

const debounce = <T extends (value: string) => void>(fn: T, ms: number) => {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (value: string) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(value), ms);
  };
};

export const PolosEscolasPage: React.FC = () => {
  const { user } = useAuthStore();
  const role = user?.perfil?.nome?.toLowerCase() || '';
  const isAdmin = role === 'admin';
  const [tab, setTab] = useState<'polos' | 'escolas'>('polos');
  const [polos, setPolos] = useState<PoloItem[]>([]);
  const [escolas, setEscolas] = useState<EscolaItem[]>([]);
  const [selectedPolo, setSelectedPolo] = useState('');
  const [kpis, setKpis] = useState<DashboardPoloKpis | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [modal, setModal] = useState<'polo' | 'escola' | null>(null);
  const [poloForm, setPoloForm] = useState<PoloCreatePayload>({ nome: '', endereco: emptyAddress, coordenador_nome: '', coordenador_cpf: '', coordenador_email: '', coordenador_senha: '' });
  const [escolaForm, setEscolaForm] = useState<EscolaCreatePayload>({ polo_id: user?.polo_id || '', nome: '', endereco: emptyAddress, secretario_nome: '', secretario_cpf: '', secretario_email: '', secretario_senha: '' });

  const loadPolos = useCallback(async (searchQuery = '') => {
    setLoading(true);
    try {
      const poloResponse = isAdmin
        ? await polosEscolasApi.listPolos({ limit: 50, offset: 0, q: searchQuery })
        : user?.polo_id
          ? { total: 1, items: [await polosEscolasApi.getPolo(user.polo_id)], limit: 1, offset: 0 }
          : await polosEscolasApi.listPolos({ limit: 50, offset: 0, q: searchQuery });
      setPolos(poloResponse.items);
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Não foi possível carregar os polos.');
    } finally { setLoading(false); }
  }, [isAdmin, user?.polo_id]);

  const loadEscolas = useCallback(async (poloId: string) => {
    try {
      const schoolResponse = await polosEscolasApi.listEscolas(poloId, { limit: 50, offset: 0 });
      setEscolas(schoolResponse.items);
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Não foi possível carregar as escolas.');
    }
  }, []);

  const debouncedLoadPolos = useMemo(() => debounce(loadPolos, 300), [loadPolos]);

  const handleSearch = useCallback((value: string) => {
    setQuery(value);
    debouncedLoadPolos(value);
  }, [debouncedLoadPolos]);

  useEffect(() => {
    if (!selectedPolo) {
      setKpis(null);
      return;
    }
    polosEscolasApi.getResumoPolo(selectedPolo).then(setKpis).catch(() => setKpis(null));
  }, [selectedPolo]);

  const savePolo = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await polosEscolasApi.createPolo(poloForm);
      setFeedback('Polo e coordenador criados com sucesso.');
      setModal(null);
      await loadPolos(query);
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Falha ao criar o polo.');
    } finally { setSaving(false); }
  };

  const saveEscola = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await polosEscolasApi.createEscola(escolaForm);
      setFeedback('Escola e secretário criados com sucesso.');
      setModal(null);
      await loadPolos(query);
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Falha ao criar a escola.');
    } finally { setSaving(false); }
  };

  const updateAddress = (type: 'polo' | 'escola', key: keyof typeof emptyAddress, value: string) => {
    if (type === 'polo') {
      setPoloForm((form) => ({ ...form, endereco: { ...form.endereco, [key]: value } }));
    } else {
      setEscolaForm((form) => ({ ...form, endereco: { ...form.endereco, [key]: value } }));
    }
  };

  return <div className="max-w-7xl space-y-6">
    <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
      <div>
        <p className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-400">Estrutura regional</p>
        <h1 className="text-3xl font-extrabold text-white">Polos e escolas</h1>
        <p className="mt-1 text-sm text-slate-400">Cadastros, responsáveis e visão operacional por unidade.</p>
      </div>
      <div className="flex gap-2">
        {isAdmin && <button onClick={() => setModal('polo')} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"><Plus size={16} /> Novo polo</button>}
        <button onClick={() => { setEscolaForm((form) => ({ ...form, polo_id: user?.polo_id || selectedPolo })); setModal('escola'); }} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"><Plus size={16} /> Nova escola</button>
      </div>
    </header>
    {kpis && <section className="grid grid-cols-2 gap-3 md:grid-cols-4">{[['Compradas', kpis.total_licencas_compradas, 'text-white'], ['Vendidas', kpis.total_licencas_vendidas_alunos, 'text-emerald-400'], ['Não vendidas', kpis.total_licencas_nao_vendidas, 'text-amber-300'], ['Conversão', `${kpis.taxa_conversao_global}%`, 'text-blue-400']].map(([label, value, color]) => <div key={String(label)} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4"><p className="text-xs font-semibold uppercase text-slate-500">{label}</p><strong className={`mt-2 block text-2xl font-black ${color}`}>{value}</strong></div>)}</section>}
    {feedback && <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300"><span className="flex items-center gap-2"><CheckCircle2 size={16} /> {feedback}</span><button onClick={() => setFeedback('')}><X size={16} /></button></div>}
    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900 p-1">
        <button onClick={() => setTab('polos')} className={`rounded-lg px-4 py-2 text-sm font-semibold ${tab === 'polos' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}>Polos ({polos.length})</button>
        <button onClick={() => setTab('escolas')} className={`rounded-lg px-4 py-2 text-sm font-semibold ${tab === 'escolas' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}>Escolas ({escolas.length})</button>
      </div>
      <div className="flex gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
          <input className={`${inputClass} pl-9`} placeholder="Buscar polo por nome" value={query} onChange={(event) => handleSearch(event.target.value)} />
        </div>
        <button title="Recarregar" onClick={() => loadPolos(query)} className="rounded-xl border border-slate-800 bg-slate-900 px-3 text-slate-300 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
      </div>
    </div>
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
      {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : tab === 'polos' ? (
        <div className="grid gap-4 p-4 md:grid-cols-2">
          {polos.map((polo) => <article key={polo.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
            <div className="flex items-start justify-between">
              <div className="flex gap-3">
                <Building2 className="mt-1 text-blue-400" />
                <div>
                  <h2 className="font-bold text-white">{polo.nome}</h2>
                  <p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><MapPin size={13} /> {polo.endereco?.cidade || 'Cidade não informada'} / {polo.endereco?.estado || '--'}</p>
                </div>
              </div>
              <span className="rounded-full border border-emerald-500/30 px-2 py-1 text-xs text-emerald-400">{polo.status}</span>
            </div>
            <p className="mt-5 border-t border-slate-800 pt-4 text-sm text-slate-300">Coordenador: <b className="text-white">{polo.coordenador_nome || 'Não informado'}</b></p>
            <button onClick={() => { setSelectedPolo(polo.id); setTab('escolas'); loadEscolas(polo.id); }} className="mt-4 text-sm font-semibold text-blue-400 hover:text-blue-300">Ver escolas e métricas →</button>
          </article>)}
          {!polos.length && <p className="col-span-full py-12 text-center text-slate-500">Nenhum polo encontrado. Use a busca ou cadastre um novo.</p>}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="p-4">Escola</th>
                <th className="p-4">Secretário</th>
                <th className="p-4">Localidade</th>
                <th className="p-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {escolas.map((escola) => <tr key={escola.id} className="text-slate-300 hover:bg-slate-800/40">
                <td className="p-4 font-semibold text-white"><School className="mr-2 inline text-indigo-400" size={16} />{escola.nome}</td>
                <td className="p-4">{escola.secretario_nome || 'Não informado'}</td>
                <td className="p-4">{escola.endereco?.cidade || 'Cidade não informada'} / {escola.endereco?.estado || '--'}</td>
                <td className="p-4 text-right"><span className={`rounded-full px-2 py-1 text-xs ${escola.status === 'ativo' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-500/20 text-slate-400'}`}>{escola.status}</span></td>
              </tr>)}
              {!escolas.length && <tr><td colSpan={4} className="p-12 text-center text-slate-500">Nenhuma escola encontrada para este polo.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </section>
    {modal && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <form onSubmit={modal === 'polo' ? savePolo : saveEscola} className="max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">{modal === 'polo' ? 'Novo polo e coordenador' : 'Nova escola e secretário'}</h2>
          <button type="button" onClick={() => setModal(null)} className="text-slate-400"><X /></button>
        </div>
        <input className={inputClass} required placeholder="Nome da unidade" value={modal === 'polo' ? poloForm.nome : escolaForm.nome} onChange={(event) => modal === 'polo' ? setPoloForm({ ...poloForm, nome: event.target.value }) : setEscolaForm({ ...escolaForm, nome: event.target.value })} />
        {modal === 'escola' && <select className={inputClass} required value={escolaForm.polo_id} onChange={(event) => setEscolaForm({ ...escolaForm, polo_id: event.target.value })}><option value="">Selecione o polo</option>{polos.map((polo) => <option key={polo.id} value={polo.id}>{polo.nome}</option>)}</select>}
        <div className="grid gap-3 sm:grid-cols-2">
          {(['logradouro', 'numero', 'bairro', 'cidade', 'estado', 'cep'] as const).map((key) => <input key={key} className={inputClass} required={key === 'cidade' || key === 'estado'} placeholder={key[0].toUpperCase() + key.slice(1)} value={(modal === 'polo' ? poloForm.endereco?.[key] : escolaForm.endereco?.[key]) || ''} onChange={(event) => updateAddress(modal, key, event.target.value)} />)}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {(['nome', 'cpf', 'email', 'senha'] as const).map((key) => {
            const prefix = modal === 'polo' ? 'coordenador' : 'secretario';
            const field = `${prefix}_${key}` as Exclude<keyof PoloCreatePayload, 'endereco'> & Exclude<keyof EscolaCreatePayload, 'endereco'>;
            const form = modal === 'polo' ? poloForm : escolaForm;
            return <input key={key} className={inputClass} required minLength={key === 'senha' ? 8 : undefined} type={key === 'senha' ? 'password' : 'text'} placeholder={key[0].toUpperCase() + key.slice(1)} value={form[field] || ''} onChange={(event) => modal === 'polo' ? setPoloForm({ ...poloForm, [field]: event.target.value }) : setEscolaForm({ ...escolaForm, [field]: event.target.value })} />
          })}
        </div>
        <div className="flex justify-end gap-2 pt-4">
          <button type="button" onClick={() => setModal(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Cancelar</button>
          <button type="submit" disabled={saving} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50">{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </div>}
  </div>;
};