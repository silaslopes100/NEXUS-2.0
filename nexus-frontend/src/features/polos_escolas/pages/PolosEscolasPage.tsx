import { PoloEditModal } from '@/features/polos_escolas/components/PoloEditModal';
import { EscolaEditModal } from '@/features/polos_escolas/components/EscolaEditModal';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowLeftRight,
  BadgeCheck,
  BookOpen,
  Building2,
  CheckCircle2,
  Edit2,
  FileText,
  Library,
  Loader2,
  MapPin,
  Package,
  Plus,
  RefreshCw,
  School,
  Search,
  ShoppingCart,
  UserCheck,
  Users,
  X,
} from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  EscolaCreatePayload,
  EscolaItem,
  PoloCreatePayload,
  PoloItem,
  ResumoOperacionalEscola,
  ResumoOperacionalPolo,
} from '@/types/polos';
import { useAuthStore } from '@/stores/authStore';

const emptyAddress = { logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', estado: 'SP', cep: '' };
const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

const debounce = <T extends (value: string) => void>(fn: T, ms: number) => {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (value: string) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(value), ms);
  };
};

// =========================================================================
// Componentes auxiliares (tema dark do NEXUS)
// =========================================================================

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const ativo = status === 'ativo';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
        ativo ? 'bg-emerald-500/15 text-emerald-400' : 'bg-slate-500/20 text-slate-400'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${ativo ? 'bg-emerald-400' : 'bg-slate-500'}`} />
      {ativo ? 'Ativo' : 'Inativo'}
    </span>
  );
};

const InfoField: React.FC<{ label: string; value?: string | null }> = ({ label, value }) => (
  <div>
    <span className="block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
    <span className="mt-1 block text-sm text-slate-200">{value || '—'}</span>
  </div>
);

interface KpiCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  accent?: 'blue' | 'emerald' | 'amber' | 'indigo';
}

const kpiAccent = {
  blue: 'text-blue-400',
  emerald: 'text-emerald-400',
  amber: 'text-amber-300',
  indigo: 'text-indigo-400',
};

const KpiCard: React.FC<KpiCardProps> = ({ label, value, icon, accent = 'blue' }) => (
  <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 transition-colors hover:bg-slate-900">
    <div className="flex items-center justify-between text-slate-500">
      <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
      <span className={kpiAccent[accent]}>{icon}</span>
    </div>
    <strong className={`mt-2 block text-2xl font-black text-white ${kpiAccent[accent]}`}>{value}</strong>
  </div>
);

// =========================================================================
// Página
// =========================================================================

export const PolosEscolasPage: React.FC = () => {
  const { user } = useAuthStore();
  const role = user?.perfil?.nome?.toLowerCase() || '';
  const isAdmin = role === 'admin';

  // ---------- Estado: lista de polos ----------
  const [polos, setPolos] = useState<PoloItem[]>([]);
  const [query, setQuery] = useState('');
  const [searchTriggered, setSearchTriggered] = useState(false);
  const searchTriggeredRef = useRef(false);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState('');

  // ---------- Estado: detalhe do polo ----------
  const [view, setView] = useState<'lista' | 'detalhe'>('lista');
  const [selectedPolo, setSelectedPolo] = useState<PoloItem | null>(null);
  const [resumoPolo, setResumoPolo] = useState<ResumoOperacionalPolo | null>(null);
  const [escolas, setEscolas] = useState<EscolaItem[]>([]);
  const [escolaFilter, setEscolaFilter] = useState('');
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);

  // ---------- Estado: drawer da escola ----------
  const [escolaSelecionada, setEscolaSelecionada] = useState<EscolaItem | null>(null);
  const [resumoEscola, setResumoEscola] = useState<ResumoOperacionalEscola | null>(null);
  const [loadingEscola, setLoadingEscola] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // ---------- Estado: modais ----------
  const [saving, setSaving] = useState(false);
  const [editPolo, setEditPolo] = useState<PoloItem | null>(null);
  const [editEscola, setEditEscola] = useState<EscolaItem | null>(null);
  const [modal, setModal] = useState<'polo' | 'escola' | null>(null);
  const [poloForm, setPoloForm] = useState<PoloCreatePayload>({ nome: '', endereco: emptyAddress, coordenador_usuario_id: '' });
  const [escolaForm, setEscolaForm] = useState<EscolaCreatePayload>({ polo_id: user?.polo_id || '', nome: '', endereco: emptyAddress, secretario_nome: '', secretario_cpf: '', secretario_email: '', secretario_senha: '' });
  const [usuariosDisponiveis, setUsuariosDisponiveis] = useState<Array<{ id: string; nome: string; email?: string; cpf?: string; perfil_nome?: string }>>([]);
  const [buscaUsuario, setBuscaUsuario] = useState('');
  const [loadingUsuarios, setLoadingUsuarios] = useState(false);

  // Carrega usuários quando abre o modal de polo
  useEffect(() => {
    if (modal === 'polo') {
      carregarUsuarios();
    }
  }, [modal]);

  const carregarUsuarios = async () => {
    setLoadingUsuarios(true);
    try {
      const resp = await polosEscolasApi.listarUsuariosVinculaveis({ limit: 500 });
      setUsuariosDisponiveis(resp.items || []);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
    } finally {
      setLoadingUsuarios(false);
    }
  };

  const usuariosFiltrados = useMemo(() => {
    if (!buscaUsuario.trim()) return usuariosDisponiveis;
    const termo = buscaUsuario.toLowerCase();
    return usuariosDisponiveis.filter(u =>
      u.nome.toLowerCase().includes(termo) ||
      (u.email || '').toLowerCase().includes(termo) ||
      (u.perfil_nome || '').toLowerCase().includes(termo) ||
      (u.cpf || '').includes(termo)
    );
  }, [usuariosDisponiveis, buscaUsuario]);

  const loadPolos = useCallback(async (searchQuery = '') => {
    if (!searchTriggeredRef.current) return;
    setLoading(true);
    try {
      const poloResponse = isAdmin
        ? await polosEscolasApi.listarPolos({ limit: 50, offset: 0, search: searchQuery })
        : user?.polo_id
          ? { total: 1, items: [await polosEscolasApi.obterPolo(user.polo_id)], limit: 1, offset: 0 }
          : await polosEscolasApi.listarPolos({ limit: 50, offset: 0, search: searchQuery });
      setPolos(poloResponse.items);
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Não foi possível carregar os polos.');
    } finally { setLoading(false); }
  }, [isAdmin, user?.polo_id]);

  const debouncedLoadPolos = useMemo(() => debounce(loadPolos, 300), [loadPolos]);

  const handleSearch = useCallback(() => {
    searchTriggeredRef.current = true;
    setSearchTriggered(true);
    debouncedLoadPolos(query);
  }, [debouncedLoadPolos, query]);

  // ---------- Detalhe do polo ----------
  const abrirPolo = useCallback(async (poloId: string) => {
    setView('detalhe');
    setLoadingDetalhe(true);
    setSelectedPolo(null);
    setResumoPolo(null);
    setEscolas([]);
    setEscolaFilter('');
    try {
      const [polo, resumo, escolasResp] = await Promise.all([
        polosEscolasApi.obterPolo(poloId),
        polosEscolasApi.getResumoOperacionalPolo(poloId),
        polosEscolasApi.listarEscolasDoPolo(poloId),
      ]);
      setSelectedPolo(polo);
      setResumoPolo(resumo);
      setEscolas(escolasResp.items || []);
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Não foi possível carregar os detalhes do polo.');
      setView('lista');
    } finally {
      setLoadingDetalhe(false);
    }
  }, []);

  const voltarParaLista = useCallback(() => {
    setView('lista');
    setSelectedPolo(null);
    setResumoPolo(null);
    setEscolas([]);
    setDrawerOpen(false);
    setEscolaSelecionada(null);
  }, []);

  // ---------- Drawer da escola ----------
  const fecharEscola = useCallback(() => {
    setDrawerOpen(false);
    setTimeout(() => setEscolaSelecionada(null), 300);
  }, []);

  const abrirEscola = useCallback((escola: EscolaItem) => {
    setEscolaSelecionada(escola);
    setResumoEscola(null);
    setDrawerOpen(false);
    setLoadingEscola(true);
    polosEscolasApi.getResumoOperacionalEscola(escola.id)
      .then(setResumoEscola)
      .catch((error: any) => setFeedback(error.response?.data?.detail || 'Não foi possível carregar os indicadores da escola.'))
      .finally(() => {
        setLoadingEscola(false);
        setTimeout(() => setDrawerOpen(true), 10);
      });
  }, []);

  // ---------- Criação ----------
  const savePolo = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await polosEscolasApi.criarPolo(poloForm);
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
      await polosEscolasApi.criarEscola(escolaForm.polo_id, escolaForm);
      setFeedback('Escola e secretário criados com sucesso.');
      setModal(null);
      if (selectedPolo) await abrirPolo(selectedPolo.id);
      else await loadPolos(query);
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

  const escolasFiltradas = useMemo(() => {
    const term = escolaFilter.trim().toLowerCase();
    if (!term) return escolas;
    return escolas.filter((escola) =>
      escola.nome.toLowerCase().includes(term)
      || (escola.endereco?.cidade || '').toLowerCase().includes(term)
      || (escola.secretario_nome || '').toLowerCase().includes(term)
    );
  }, [escolas, escolaFilter]);

  // ---------- Render ----------
  return <div className="max-w-7xl space-y-6">
    <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
      <div>
        <p className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-400">Estrutura regional</p>
        <h1 className="text-3xl font-extrabold text-white">Polos e escolas</h1>
        <p className="mt-1 text-sm text-slate-400">Cadastros, responsáveis e visão operacional por unidade.</p>
      </div>
      <div className="flex gap-2">
        {isAdmin && <button onClick={() => setModal('polo')} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"><Plus size={16} /> Novo polo</button>}
        <button onClick={() => { setEscolaForm((form) => ({ ...form, polo_id: user?.polo_id || selectedPolo?.id || '' })); setModal('escola'); }} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"><Plus size={16} /> Nova escola</button>
      </div>
    </header>

    {feedback && <div className="flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300"><span className="flex items-center gap-2"><CheckCircle2 size={16} /> {feedback}</span><button onClick={() => setFeedback('')}><X size={16} /></button></div>}

    {view === 'lista' ? (
      <>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <p className="text-sm text-slate-400">Selecione um polo para ver dados, indicadores e escolas vinculadas.</p>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
              <input
                className={`${inputClass} pl-9`}
                placeholder="Buscar polo por nome"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') handleSearch();
                }}
              />
            </div>
            <button onClick={handleSearch} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500">Buscar</button>
            <button title="Recarregar" onClick={() => loadPolos(query)} className="rounded-xl border border-slate-800 bg-slate-900 px-3 text-slate-300 hover:text-white"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /></button>
          </div>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
          {loading ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
            <div className="grid gap-4 p-4 md:grid-cols-2">
              {polos.map((polo) => <article key={polo.id} className="relative rounded-2xl border border-slate-800 bg-slate-950/50 p-5 transition-colors hover:border-blue-500/40">
                <div className="flex items-start justify-between">
                  <div className="flex gap-3">
                    <Building2 className="mt-1 text-blue-400" />
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-bold text-white">{polo.nome}</h2>
                        <StatusBadge status={polo.status} />
                      </div>
                      <p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><MapPin size={13} /> {polo.endereco?.cidade || 'Cidade não informada'} / {polo.endereco?.estado || '--'}</p>
                    </div>
                  </div>
                </div>
                <p className="mt-5 border-t border-slate-800 pt-4 text-sm text-slate-300">Coordenador: <b className="text-white">{polo.coordenador_nome || 'Não informado'}</b></p>
                <button type="button" onClick={(e) => { e.stopPropagation(); setEditPolo(polo); }} className="absolute right-4 top-4 rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" title="Editar Polo"> <Edit2 size={16} /></button>
                <button onClick={() => void abrirPolo(polo.id)} className="mt-4 text-sm font-semibold text-blue-400 hover:text-blue-300">Ver detalhes, indicadores e escolas →</button>
              </article>)}
              {!polos.length && <p className="col-span-full py-12 text-center text-slate-500">{searchTriggered ? 'Nenhum polo encontrado. Use a busca ou cadastre um novo.' : 'Preencha a busca e clique em "Buscar" para carregar os polos.'}</p>}
            </div>
          )}
        </section>
      </>
    ) : (
      <>
        <div className="flex items-center justify-between">
          <button onClick={voltarParaLista} className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-300 hover:text-white">
            <ArrowLeft size={16} /> Voltar para a lista
          </button>
          {selectedPolo && <button type="button" onClick={() => setEditPolo(selectedPolo)} className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-300 hover:text-white">
            <Edit2 size={14} /> Editar polo
          </button>}
        </div>

        {loadingDetalhe || !selectedPolo ? (
          <div className="flex justify-center rounded-2xl border border-slate-800 bg-slate-900/80 py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="space-y-6">
            {/* 1. Dados do polo + Coordenador */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 lg:col-span-2">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Building2 className="text-blue-400" size={22} />
                    <h2 className="text-xl font-bold text-white">{selectedPolo.nome}</h2>
                  </div>
                  <StatusBadge status={selectedPolo.status} />
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
                  <InfoField label="Logradouro" value={selectedPolo.endereco?.logradouro} />
                  <InfoField label="Número" value={selectedPolo.endereco?.numero} />
                  <InfoField label="Complemento" value={selectedPolo.endereco?.complemento} />
                  <InfoField label="Bairro" value={selectedPolo.endereco?.bairro} />
                  <InfoField label="Cidade" value={selectedPolo.endereco?.cidade} />
                  <InfoField label="UF" value={selectedPolo.endereco?.estado} />
                  <InfoField label="CEP" value={selectedPolo.endereco?.cep} />
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
                <div className="mb-4 flex items-center gap-2">
                  <UserCheck className="text-indigo-400" size={22} />
                  <h3 className="text-base font-bold text-white">Coordenador Responsável</h3>
                </div>
                <div className="space-y-4">
                  <InfoField label="Nome" value={selectedPolo.coordenador_nome} />
                  <InfoField label="CPF" value={selectedPolo.coordenador_cpf} />
                  <InfoField label="E-mail" value={selectedPolo.coordenador_email} />
                </div>
              </div>
            </div>

            {/* 2. Dashboard do polo (10 KPIs) */}
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-bold text-white">Indicadores do polo</h3>
                <span className="text-xs text-slate-500">Atualizado em tempo real</span>
              </div>
              {resumoPolo ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
                  <KpiCard label="Escolas" value={resumoPolo.escolas} icon={<School size={18} />} />
                  <KpiCard label="Turmas" value={resumoPolo.turmas} icon={<Users size={18} />} />
                  <KpiCard label="Professores" value={resumoPolo.professores} icon={<UserCheck size={18} />} />
                  <KpiCard label="Alunos" value={resumoPolo.alunos} icon={<Users size={18} />} accent="emerald" />
                  <KpiCard label="Aulas" value={resumoPolo.aulas} icon={<BookOpen size={18} />} />
                  <KpiCard label="Licenças estoque" value={resumoPolo.licencas_estoque} icon={<Package size={18} />} accent="indigo" />
                  <KpiCard label="Licenças atribuídas" value={resumoPolo.licencas_atribuidas} icon={<BadgeCheck size={18} />} accent="indigo" />
                  <KpiCard label="Licenças movimentações" value={resumoPolo.licencas_movimentacoes} icon={<ArrowLeftRight size={18} />} accent="indigo" />
                  <KpiCard label="Pedidos de licenças" value={resumoPolo.pedidos_licencas} icon={<ShoppingCart size={18} />} accent="amber" />
                  <KpiCard label="Pedidos de livros" value={resumoPolo.pedidos_livros} icon={<Library size={18} />} accent="amber" />
                </div>
              ) : (
                <div className="flex justify-center rounded-2xl border border-slate-800 bg-slate-900/80 py-10 text-blue-400"><Loader2 className="animate-spin" /></div>
              )}
            </div>

            {/* 3. Escolas do polo */}
            <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
              <div className="flex flex-col justify-between gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center">
                <div>
                  <h3 className="text-base font-bold text-white">Escolas do polo ({escolas.length})</h3>
                  <p className="text-xs text-slate-500">Clique em uma escola para ver dados completos e indicadores.</p>
                </div>
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
                  <input
                    className={`${inputClass} pl-9`}
                    placeholder="Filtrar escolas..."
                    value={escolaFilter}
                    onChange={(event) => setEscolaFilter(event.target.value)}
                  />
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="p-4">Escola</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Cidade</th>
                      <th className="p-4">Responsável</th>
                      <th className="p-4 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {escolasFiltradas.map((escola) => <tr key={escola.id} onClick={() => abrirEscola(escola)} className="cursor-pointer text-slate-300 hover:bg-slate-800/40">
                      <td className="p-4 font-semibold text-white"><School className="mr-2 inline text-indigo-400" size={16} />{escola.nome}</td>
                      <td className="p-4"><StatusBadge status={escola.status} /></td>
                      <td className="p-4">{escola.endereco?.cidade || '—'} / {escola.endereco?.estado || '--'}</td>
                      <td className="p-4">{escola.secretario_nome || 'Não informado'}</td>
                      <td className="p-4 text-right">
                        <button type="button" onClick={(event) => { event.stopPropagation(); abrirEscola(escola); }} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500">Detalhes</button>
                        <button type="button" onClick={(event) => { event.stopPropagation(); setEditEscola(escola); }} className="ml-2 rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" title="Editar Escola"><Edit2 size={15} /></button>
                      </td>
                    </tr>)}
                    {!escolasFiltradas.length && <tr><td colSpan={5} className="p-12 text-center text-slate-500">Nenhuma escola encontrada para este polo.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </>
    )}

    {/* =========================================================================
        Drawer de detalhe da escola
        ========================================================================= */}
    {escolaSelecionada && (
      <div className="fixed inset-0 z-50 flex justify-end bg-black/70" onClick={fecharEscola}>
        <div
          className={`flex h-full w-full max-w-2xl flex-col overflow-y-auto border-l border-slate-800 bg-slate-900 shadow-2xl transition-transform duration-300 ${drawerOpen ? 'translate-x-0' : 'translate-x-full'}`}
          onClick={(event) => event.stopPropagation()}
        >
          {/* Header do drawer */}
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 bg-slate-900/95 p-5 backdrop-blur">
            <div className="flex items-center gap-3">
              <School className="text-indigo-400" size={22} />
              <div>
                <h3 className="text-lg font-bold text-white">{escolaSelecionada.nome}</h3>
                <div className="mt-1"><StatusBadge status={escolaSelecionada.status} /></div>
              </div>
            </div>
            <button onClick={fecharEscola} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"><X size={20} /></button>
          </div>

          <div className="flex-1 space-y-6 p-5">
            {/* Dados cadastrais */}
            <section>
              <h4 className="mb-3 flex items-center gap-2 text-sm font-bold text-white"><FileText size={16} className="text-blue-400" /> Dados da escola</h4>
              <div className="grid grid-cols-1 gap-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-2 md:grid-cols-3">
                <InfoField label="Logradouro" value={escolaSelecionada.endereco?.logradouro} />
                <InfoField label="Número" value={escolaSelecionada.endereco?.numero} />
                <InfoField label="Complemento" value={escolaSelecionada.endereco?.complemento} />
                <InfoField label="Bairro" value={escolaSelecionada.endereco?.bairro} />
                <InfoField label="Cidade" value={escolaSelecionada.endereco?.cidade} />
                <InfoField label="UF" value={escolaSelecionada.endereco?.estado} />
                <InfoField label="CEP" value={escolaSelecionada.endereco?.cep} />
              </div>
            </section>

            {/* Responsável */}
            <section>
              <h4 className="mb-3 flex items-center gap-2 text-sm font-bold text-white"><UserCheck size={16} className="text-indigo-400" /> Responsável</h4>
              <div className="grid grid-cols-1 gap-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-3">
                <InfoField label="Nome" value={escolaSelecionada.secretario_nome} />
                <InfoField label="CPF" value={escolaSelecionada.secretario_cpf} />
                <InfoField label="E-mail" value={escolaSelecionada.secretario_email} />
              </div>
            </section>

            {/* Indicadores da escola (10 KPIs) */}
            <section>
              <h4 className="mb-3 flex items-center gap-2 text-sm font-bold text-white"><Package size={16} className="text-emerald-400" /> Indicadores da escola</h4>
              {loadingEscola || !resumoEscola ? (
                <div className="flex justify-center rounded-2xl border border-slate-800 bg-slate-950/50 py-10 text-blue-400"><Loader2 className="animate-spin" /></div>
              ) : (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
                  <KpiCard label="Alunos" value={resumoEscola.alunos} icon={<Users size={18} />} accent="emerald" />
                  <KpiCard label="Aulas" value={resumoEscola.aulas} icon={<BookOpen size={18} />} />
                  <KpiCard label="Licenças estoque" value={resumoEscola.licencas_estoque} icon={<Package size={18} />} accent="indigo" />
                  <KpiCard label="Licenças alunos" value={resumoEscola.licencas_alunos} icon={<Users size={18} />} accent="indigo" />
                  <KpiCard label="Licenças atribuídas" value={resumoEscola.licencas_atribuidas} icon={<BadgeCheck size={18} />} accent="indigo" />
                  <KpiCard label="Licenças movimentações" value={resumoEscola.licencas_movimentacoes} icon={<ArrowLeftRight size={18} />} accent="indigo" />
                  <KpiCard label="Pedidos de licenças" value={resumoEscola.pedidos_licencas} icon={<ShoppingCart size={18} />} accent="amber" />
                  <KpiCard label="Pedidos de livros" value={resumoEscola.pedidos_livros} icon={<Library size={18} />} accent="amber" />
                  <KpiCard label="Professores" value={resumoEscola.professores} icon={<UserCheck size={18} />} />
                  <KpiCard label="Turmas" value={resumoEscola.turmas} icon={<Users size={18} />} />
                </div>
              )}
            </section>
          </div>

          {/* Footer do drawer */}
          <div className="sticky bottom-0 flex justify-end gap-2 border-t border-slate-800 bg-slate-900/95 p-4 backdrop-blur">
            <button onClick={fecharEscola} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Fechar</button>
            <button onClick={() => { setEditEscola(escolaSelecionada); fecharEscola(); }} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"><Edit2 size={14} /> Editar escola</button>
          </div>
        </div>
      </div>
    )}

    {/* Modal de criação (polo / escola) */}
    {modal && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <form onSubmit={modal === 'polo' ? savePolo : saveEscola} className="max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">{modal === 'polo' ? 'Novo polo e coordenador' : 'Nova escola e secretário'}</h2>
          <button type="button" onClick={() => setModal(null)} className="text-slate-400"><X /></button>
        </div>
        <input className={inputClass} required placeholder="Nome da unidade" value={modal === 'polo' ? poloForm.nome : escolaForm.nome} onChange={(event) => modal === 'polo' ? setPoloForm({ ...poloForm, nome: event.target.value }) : setEscolaForm({ ...escolaForm, nome: event.target.value })} />
        {modal === 'escola' && <select className={inputClass} required value={escolaForm.polo_id} onChange={(event) => setEscolaForm({ ...escolaForm, polo_id: event.target.value })}><option value="">Selecione o polo</option>{polos.map((polo) => <option key={polo.id} value={polo.id}>{polo.nome}</option>)}</select>}
        <div className="grid gap-3 sm:grid-cols-2">
          {(['logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep'] as const).map((key) => <input key={key} className={inputClass} required={key === 'cidade' || key === 'estado'} placeholder={key[0].toUpperCase() + key.slice(1)} value={(modal === 'polo' ? poloForm.endereco?.[key] : escolaForm.endereco?.[key]) || ''} onChange={(event) => updateAddress(modal, key, event.target.value)} />)}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {modal === 'escola' && (['nome', 'cpf', 'email', 'senha'] as const).map((key) => {
            const prefix = 'secretario';
            const field = `${prefix}_${key}` as Exclude<keyof EscolaCreatePayload, 'endereco'>;
            return <input key={key} className={inputClass} required minLength={key === 'senha' ? 8 : undefined} type={key === 'senha' ? 'password' : 'text'} placeholder={key[0].toUpperCase() + key.slice(1)} value={escolaForm[field] || ''} onChange={(event) => setEscolaForm({ ...escolaForm, [field]: event.target.value })} />;
          })}
        </div>
        {modal === 'polo' && (
          <div className="border-t border-slate-800 pt-4">
            <label className="mb-1 block text-sm font-medium text-slate-300">Vincular Usuário Coordenador</label>
            <input
              className={inputClass}
              placeholder="Buscar por nome, e-mail ou CPF..."
              value={buscaUsuario}
              onChange={(event) => setBuscaUsuario(event.target.value)}
              disabled={loadingUsuarios}
            />
            <select
              className={`${inputClass} mt-2`}
              required
              value={poloForm.coordenador_usuario_id || ''}
              onChange={(event) => setPoloForm({ ...poloForm, coordenador_usuario_id: event.target.value })}
              disabled={loadingUsuarios}
              size={Math.min(usuariosFiltrados.length + 1, 8)}
            >
              <option value="">
                {loadingUsuarios ? 'Carregando usuários...' : 'Selecione um usuário'}
              </option>
              {usuariosFiltrados.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome} — {u.email || 'sem e-mail'}{u.perfil_nome ? ` (${u.perfil_nome})` : ''}
                </option>
              ))}
            </select>
            {buscaUsuario && usuariosFiltrados.length === 0 && !loadingUsuarios && (
              <p className="mt-2 text-xs text-slate-500">Nenhum usuário encontrado para "{buscaUsuario}".</p>
            )}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-4">
          <button type="button" onClick={() => setModal(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Cancelar</button>
          <button type="submit" disabled={saving} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50">{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </div>}

    {editPolo && <PoloEditModal polo={editPolo} onClose={() => setEditPolo(null)} onSuccess={() => { if (selectedPolo && view === 'detalhe') void abrirPolo(selectedPolo.id); else void loadPolos(query); setEditPolo(null); }} />}
    {editEscola && <EscolaEditModal escola={editEscola} polos={polos} onClose={() => setEditEscola(null)} onSuccess={() => { if (selectedPolo && view === 'detalhe') void abrirPolo(selectedPolo.id); else void loadPolos(query); setEditEscola(null); }} />}
  </div>;
};
