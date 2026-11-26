import { PoloEditModal } from '@/features/polos_escolas/components/PoloEditModal';
import { EscolaEditModal } from '@/features/polos_escolas/components/EscolaEditModal';
import { SecretarioEscolaFields } from '@/features/polos_escolas/components/SecretarioEscolaFields';
import { IndicadoresEscola, IndicadoresPolo } from '@/features/polos_escolas/components/IndicadoresUnidade';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  ChevronRight,
  Edit2,
  LayoutGrid,
  List,
  Loader2,
  Mail,
  MapPin,
  Plus,
  RefreshCw,
  School,
  Search,
  UserCheck,
  X,
} from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { useCepAddress } from '@/features/polos_escolas/useCepAddress';
import { areaDoPerfil, formatarEndereco } from '@/features/polos_escolas/indicadores';
import {
  EnderecoCompleto,
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
const selectClass = 'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const LIMITE_POLOS = 200;
const DEBOUNCE_BUSCA_MS = 300;

type Visualizacao = 'cards' | 'tabela';
const CHAVE_VISUALIZACAO = 'nexus.polos.visualizacao';

const lerVisualizacao = (): Visualizacao => {
  try {
    return localStorage.getItem(CHAVE_VISUALIZACAO) === 'tabela' ? 'tabela' : 'cards';
  } catch {
    return 'cards';
  }
};

const salvarVisualizacao = (valor: Visualizacao) => {
  try {
    localStorage.setItem(CHAVE_VISUALIZACAO, valor);
  } catch {
    // Armazenamento indisponível (aba anônima, bloqueio): a escolha vale só nesta visita.
  }
};

const cidadeUf = (endereco?: EnderecoCompleto | null) =>
  [endereco?.cidade, endereco?.estado].filter(Boolean).join(' / ') || 'Cidade não informada';

type Feedback = { tipo: 'ok' | 'erro'; texto: string } | null;

const mensagemErro = (error: any, padrao: string) => {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail : padrao;
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
  <div className="min-w-0">
    <span className="block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
    <span className="mt-1 block break-words text-sm text-slate-200">{value || '—'}</span>
  </div>
);

const Endereco: React.FC<{ endereco?: EnderecoCompleto | null }> = ({ endereco }) => {
  const texto = formatarEndereco(endereco);
  return (
    <p className="flex items-start gap-2 text-sm text-slate-300">
      <MapPin size={16} className="mt-0.5 shrink-0 text-slate-500" />
      <span>{texto || 'Endereço não informado'}</span>
    </p>
  );
};

const BotaoVisualizacao: React.FC<{
  ativo: boolean;
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}> = ({ ativo, label, icon, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={ativo}
    title={label}
    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
      ativo ? 'bg-blue-600 text-on-accent' : 'text-slate-400 hover:text-white'
    }`}
  >
    {icon} {label}
  </button>
);

// =========================================================================
// Página
// =========================================================================

export const PolosEscolasPage: React.FC = () => {
  const { user } = useAuthStore();
  const role = user?.perfil?.nome?.toLowerCase() || '';
  const isAdmin = role === 'admin';
  const area = areaDoPerfil(role);

  // O polo aberto fica na URL (?polo=<id>): voltar de um indicador reabre o detalhe.
  const [params, setParams] = useSearchParams();
  const poloAberto = params.get('polo') || '';
  const view: 'lista' | 'detalhe' = poloAberto ? 'detalhe' : 'lista';

  // ---------- Estado: lista de polos ----------
  const [polos, setPolos] = useState<PoloItem[]>([]);
  const [totalPolos, setTotalPolos] = useState(0);
  const [query, setQuery] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('');
  const [ufFiltro, setUfFiltro] = useState('');
  const [visualizacao, setVisualizacao] = useState<Visualizacao>(lerVisualizacao);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const requisicaoListaRef = useRef(0);

  // ---------- Estado: detalhe do polo ----------
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
  const [erroModal, setErroModal] = useState('');
  const { changeAddress, lookup: cepLookup } = useCepAddress((update) => {
    if (modal === 'polo') {
      setPoloForm((form) => ({ ...form, endereco: update(form.endereco || {}) }));
    } else if (modal === 'escola') {
      setEscolaForm((form) => ({ ...form, endereco: update(form.endereco || {}) }));
    }
  }, modal);

  // Carrega usuários quando abre o modal de polo
  useEffect(() => {
    if (modal === 'polo') {
      carregarUsuarios();
    }
  }, [modal]);

  const carregarUsuarios = async () => {
    setLoadingUsuarios(true);
    try {
      const resp = await polosEscolasApi.listarUsuariosVinculaveis({ perfil: 'polo', limit: 500 });
      setUsuariosDisponiveis(resp.items || []);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
      setErroModal('Não foi possível carregar os coordenadores. Feche e abra o formulário para tentar novamente.');
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

  // ---------- Lista de polos ----------
  const loadPolos = useCallback(async (searchQuery = '') => {
    const requisicao = ++requisicaoListaRef.current;
    setLoading(true);
    try {
      const poloResponse = isAdmin
        ? await polosEscolasApi.listarPolos({ limit: LIMITE_POLOS, offset: 0, search: searchQuery || undefined })
        : user?.polo_id
          ? { total: 1, items: [await polosEscolasApi.obterPolo(user.polo_id)], limit: 1, offset: 0 }
          : await polosEscolasApi.listarPolos({ limit: LIMITE_POLOS, offset: 0, search: searchQuery || undefined });
      // Ignora respostas de buscas já substituídas por outra mais recente.
      if (requisicao !== requisicaoListaRef.current) return;
      const items: PoloItem[] = poloResponse.items || [];
      setPolos(items);
      setTotalPolos(poloResponse.total ?? items.length);
    } catch (error: any) {
      if (requisicao !== requisicaoListaRef.current) return;
      setFeedback({ tipo: 'erro', texto: mensagemErro(error, 'Não foi possível carregar os polos.') });
    } finally {
      if (requisicao === requisicaoListaRef.current) setLoading(false);
    }
  }, [isAdmin, user?.polo_id]);

  // Carrega ao abrir a tela e busca enquanto digita.
  useEffect(() => {
    const termo = query.trim();
    const timeoutId = setTimeout(() => void loadPolos(termo), termo ? DEBOUNCE_BUSCA_MS : 0);
    return () => clearTimeout(timeoutId);
  }, [query, loadPolos]);

  const trocarVisualizacao = (valor: Visualizacao) => {
    setVisualizacao(valor);
    salvarVisualizacao(valor);
  };

  const ufsDisponiveis = useMemo(
    () => Array.from(new Set(polos.map((polo) => polo.endereco?.estado).filter((uf): uf is string => Boolean(uf)))).sort(),
    [polos],
  );

  const polosFiltrados = useMemo(
    () => polos.filter((polo) =>
      (!statusFiltro || polo.status === statusFiltro)
      && (!ufFiltro || polo.endereco?.estado === ufFiltro)),
    [polos, statusFiltro, ufFiltro],
  );

  const temFiltroLista = Boolean(query.trim() || statusFiltro || ufFiltro);
  const limparFiltrosLista = () => {
    setQuery('');
    setStatusFiltro('');
    setUfFiltro('');
  };

  // ---------- Detalhe do polo ----------
  const carregarDetalhe = useCallback(async (poloId: string, limpar = true) => {
    setLoadingDetalhe(true);
    if (limpar) {
      setSelectedPolo(null);
      setResumoPolo(null);
      setEscolas([]);
      setEscolaFilter('');
    }
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
      setFeedback({ tipo: 'erro', texto: mensagemErro(error, 'Não foi possível carregar os detalhes do polo.') });
      setParams((atual) => {
        const proximo = new URLSearchParams(atual);
        proximo.delete('polo');
        return proximo;
      }, { replace: true });
    } finally {
      setLoadingDetalhe(false);
    }
  }, [setParams]);

  useEffect(() => {
    if (poloAberto) {
      void carregarDetalhe(poloAberto);
      return;
    }
    setSelectedPolo(null);
    setResumoPolo(null);
    setEscolas([]);
    setDrawerOpen(false);
    setEscolaSelecionada(null);
  }, [poloAberto, carregarDetalhe]);

  const abrirPolo = useCallback((poloId: string) => {
    setParams((atual) => {
      const proximo = new URLSearchParams(atual);
      proximo.set('polo', poloId);
      return proximo;
    });
  }, [setParams]);

  const voltarParaLista = useCallback(() => {
    setParams((atual) => {
      const proximo = new URLSearchParams(atual);
      proximo.delete('polo');
      return proximo;
    });
  }, [setParams]);

  const recarregarDetalhe = useCallback(() => {
    if (poloAberto) void carregarDetalhe(poloAberto, false);
  }, [carregarDetalhe, poloAberto]);

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
      .catch((error: any) => setFeedback({ tipo: 'erro', texto: mensagemErro(error, 'Não foi possível carregar os indicadores da escola.') }))
      .finally(() => {
        setLoadingEscola(false);
        setTimeout(() => setDrawerOpen(true), 10);
      });
  }, []);

  // ---------- Criação ----------
  const savePolo = async (event: React.FormEvent) => {
    event.preventDefault();
    setErroModal('');
    setSaving(true);
    try {
      await polosEscolasApi.criarPolo(poloForm);
      setFeedback({ tipo: 'ok', texto: 'Polo cadastrado e coordenador vinculado com sucesso.' });
      setModal(null);
      setPoloForm({ nome: '', endereco: emptyAddress, coordenador_usuario_id: '' });
      setBuscaUsuario('');
      setQuery('');
      await loadPolos('');
    } catch (error: any) {
      setErroModal(mensagemErro(error, 'Falha ao criar o polo. Confira os dados informados.'));
    } finally { setSaving(false); }
  };

  const saveEscola = async (event: React.FormEvent) => {
    event.preventDefault();
    setErroModal('');
    setSaving(true);
    try {
      await polosEscolasApi.criarEscola(escolaForm.polo_id, escolaForm);
      setFeedback({ tipo: 'ok', texto: 'Escola cadastrada com sucesso.' });
      setModal(null);
      setEscolaForm({ polo_id: user?.polo_id || '', nome: '', endereco: emptyAddress, secretario_nome: '', secretario_cpf: '', secretario_email: '', secretario_senha: '', secretario_usuario_id: '' });
      if (poloAberto) await carregarDetalhe(poloAberto, false);
      else await loadPolos(query.trim());
    } catch (error: any) {
      setErroModal(mensagemErro(error, 'Falha ao criar a escola. Confira os dados informados.'));
    } finally { setSaving(false); }
  };

  const aposEditar = () => {
    if (poloAberto) void carregarDetalhe(poloAberto, false);
    else void loadPolos(query.trim());
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
    <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
      <div>
        <h1 className="text-3xl font-extrabold text-white">Polos e escolas</h1>
        <p className="mt-1 text-sm text-slate-400">Cadastros, responsáveis e visão operacional por unidade.</p>
      </div>
      <div className="flex gap-2">
        {isAdmin && <button onClick={() => { setErroModal(''); setModal('polo'); }} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-blue-500"><Plus size={16} /> Novo polo</button>}
        <button onClick={() => {
          setErroModal('');
          setEscolaForm((form) => ({ ...form, polo_id: user?.polo_id || selectedPolo?.id || '', secretario_usuario_id: '' }));
          if (!polos.length) void loadPolos('');
          setModal('escola');
        }} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-indigo-500"><Plus size={16} /> Nova escola</button>
      </div>
    </header>

    {feedback && (
      <div
        role={feedback.tipo === 'erro' ? 'alert' : 'status'}
        className={`flex items-center justify-between rounded-xl border p-3 text-sm ${
          feedback.tipo === 'erro'
            ? 'border-red-500/30 bg-red-500/10 text-red-300'
            : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
        }`}
      >
        <span className="flex items-center gap-2">
          {feedback.tipo === 'erro' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />} {feedback.texto}
        </span>
        <button onClick={() => setFeedback(null)} aria-label="Fechar aviso"><X size={16} /></button>
      </div>
    )}

    {view === 'lista' ? (
      <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        {/* Barra de ferramentas */}
        <div className="flex flex-col gap-3 border-b border-slate-800 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative sm:w-72">
              <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
              <input
                className={`${inputClass} pl-9`}
                placeholder="Buscar polo por nome"
                aria-label="Buscar polo por nome"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
            <select aria-label="Filtrar por status" className={selectClass} value={statusFiltro} onChange={(event) => setStatusFiltro(event.target.value)}>
              <option value="">Todos os status</option>
              <option value="ativo">Ativos</option>
              <option value="inativo">Inativos</option>
            </select>
            <select aria-label="Filtrar por UF" className={selectClass} value={ufFiltro} onChange={(event) => setUfFiltro(event.target.value)}>
              <option value="">Todas as UFs</option>
              {ufsDisponiveis.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
            </select>
            {temFiltroLista && (
              <button type="button" onClick={limparFiltrosLista} className="text-xs font-semibold text-slate-400 hover:text-white">Limpar filtros</button>
            )}
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-slate-500">
              {polosFiltrados.length} {polosFiltrados.length === 1 ? 'polo' : 'polos'}
            </span>
            <div className="flex items-center gap-2">
              <div className="flex rounded-xl border border-slate-800 bg-slate-950 p-1" role="group" aria-label="Visualização">
                <BotaoVisualizacao ativo={visualizacao === 'cards'} label="Cards" icon={<LayoutGrid size={14} />} onClick={() => trocarVisualizacao('cards')} />
                <BotaoVisualizacao ativo={visualizacao === 'tabela'} label="Tabela" icon={<List size={14} />} onClick={() => trocarVisualizacao('tabela')} />
              </div>
              <button title="Recarregar" aria-label="Recarregar polos" onClick={() => void loadPolos(query.trim())} className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-300 hover:text-white">
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>
        </div>

        {totalPolos > polos.length && (
          <p className="border-b border-slate-800 bg-amber-500/5 px-4 py-2 text-xs text-amber-200">
            Mostrando {polos.length} de {totalPolos} polos. Refine a busca para encontrar os demais.
          </p>
        )}

        {loading && !polos.length ? (
          <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : !polosFiltrados.length ? (
          <div className="py-14 text-center text-sm text-slate-500">
            {polos.length || temFiltroLista ? 'Nenhum polo corresponde aos filtros.' : 'Nenhum polo cadastrado.'}
            {temFiltroLista && (
              <button type="button" onClick={limparFiltrosLista} className="ml-2 font-semibold text-blue-400 hover:text-blue-300">Limpar filtros</button>
            )}
          </div>
        ) : visualizacao === 'cards' ? (
          <div className={`grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-3 ${loading ? 'opacity-60' : ''}`}>
            {polosFiltrados.map((polo) => (
              <article key={polo.id} className="group relative rounded-2xl border border-slate-800 bg-slate-950/50 p-5 transition-colors hover:border-blue-500/40 hover:bg-slate-950/80">
                {/* Botão que cobre o card inteiro: o card todo abre o detalhe. */}
                <button
                  type="button"
                  onClick={() => abrirPolo(polo.id)}
                  aria-label={`Abrir polo ${polo.nome}`}
                  className="absolute inset-0 rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
                />
                <div className="pointer-events-none">
                  <div className="flex items-start gap-3 pr-8">
                    <span className="rounded-xl bg-blue-500/10 p-2 text-blue-400"><Building2 size={20} /></span>
                    <div className="min-w-0">
                      <h2 className="truncate font-bold text-white" title={polo.nome}>{polo.nome}</h2>
                      <p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><MapPin size={13} /> {cidadeUf(polo.endereco)}</p>
                    </div>
                  </div>
                  <div className="mt-3"><StatusBadge status={polo.status} /></div>
                  <div className="mt-4 border-t border-slate-800 pt-3">
                    <span className="block text-xs font-semibold uppercase tracking-wide text-slate-500">Coordenador</span>
                    <span className="mt-0.5 block truncate text-sm font-semibold text-white">{polo.coordenador_nome || 'Não informado'}</span>
                    {polo.coordenador_email && (
                      <span className="mt-0.5 flex items-center gap-1 truncate text-xs text-slate-400"><Mail size={12} className="shrink-0" /> {polo.coordenador_email}</span>
                    )}
                  </div>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-blue-400 group-hover:text-blue-300">
                    Ver detalhes, indicadores e escolas <ChevronRight size={14} />
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setEditPolo(polo)}
                  className="absolute right-3 top-3 z-10 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                  title="Editar polo"
                  aria-label={`Editar polo ${polo.nome}`}
                >
                  <Edit2 size={16} />
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className={`overflow-x-auto ${loading ? 'opacity-60' : ''}`}>
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="p-4">Polo</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Cidade / UF</th>
                  <th className="p-4">Coordenador</th>
                  <th className="p-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {polosFiltrados.map((polo) => (
                  <tr key={polo.id} onClick={() => abrirPolo(polo.id)} className="cursor-pointer text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4 font-semibold text-white"><Building2 className="mr-2 inline text-blue-400" size={16} />{polo.nome}</td>
                    <td className="p-4"><StatusBadge status={polo.status} /></td>
                    <td className="p-4">{cidadeUf(polo.endereco)}</td>
                    <td className="p-4">
                      <span className="block text-white">{polo.coordenador_nome || 'Não informado'}</span>
                      {polo.coordenador_email && <span className="block text-xs text-slate-500">{polo.coordenador_email}</span>}
                    </td>
                    <td className="whitespace-nowrap p-4 text-right">
                      <button type="button" onClick={(event) => { event.stopPropagation(); abrirPolo(polo.id); }} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-on-accent hover:bg-blue-500">Detalhes</button>
                      <button type="button" onClick={(event) => { event.stopPropagation(); setEditPolo(polo); }} className="ml-2 rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" title="Editar polo" aria-label={`Editar polo ${polo.nome}`}><Edit2 size={15} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    ) : (
      <>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav aria-label="Navegação" className="flex min-w-0 items-center gap-1.5 text-sm">
            <button onClick={voltarParaLista} className="font-semibold text-slate-400 hover:text-white">Polos</button>
            <ChevronRight size={14} className="shrink-0 text-slate-600" />
            <span className="truncate font-semibold text-white">{selectedPolo?.nome || 'Carregando...'}</span>
          </nav>
          {selectedPolo && (
            <div className="flex gap-2">
              <button type="button" onClick={recarregarDetalhe} title="Recarregar" aria-label="Recarregar detalhes do polo" className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-300 hover:text-white">
                <RefreshCw size={16} className={loadingDetalhe ? 'animate-spin' : ''} />
              </button>
              <button type="button" onClick={() => setEditPolo(selectedPolo)} className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-300 hover:text-white">
                <Edit2 size={14} /> Editar polo
              </button>
            </div>
          )}
        </div>
        {!selectedPolo ? (
          <div className="glass flex justify-center rounded-2xl border border-slate-800 bg-slate-900/80 py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="space-y-6">
            {/* 1. Dados do polo + Coordenador */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6 lg:col-span-2">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400"><Building2 size={22} /></span>
                  <h2 className="text-xl font-bold text-white">{selectedPolo.nome}</h2>
                  <StatusBadge status={selectedPolo.status} />
                </div>
                <div className="mt-4"><Endereco endereco={selectedPolo.endereco} /></div>
              </div>

              <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
                <div className="mb-4 flex items-center gap-2">
                  <UserCheck className="text-indigo-400" size={20} />
                  <h3 className="text-base font-bold text-white">Coordenador responsável</h3>
                </div>
                <div className="space-y-3">
                  <InfoField label="Nome" value={selectedPolo.coordenador_nome} />
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                    <InfoField label="E-mail" value={selectedPolo.coordenador_email} />
                    <InfoField label="CPF" value={selectedPolo.coordenador_cpf} />
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Indicadores do polo (clicáveis) */}
            <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
              <div className="mb-4">
                <h3 className="text-base font-bold text-white">Indicadores do polo</h3>
                <p className="text-xs text-slate-500">Clique em um indicador para abrir a lista correspondente.</p>
              </div>
              {resumoPolo ? (
                <IndicadoresPolo resumo={resumoPolo} poloId={selectedPolo.id} area={area} />
              ) : (
                <div className="flex justify-center py-10 text-blue-400"><Loader2 className="animate-spin" /></div>
              )}
            </div>

            {/* 3. Escolas do polo */}
            <div className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
              <div className="flex flex-col justify-between gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center">
                <div>
                  <h3 className="text-base font-bold text-white">
                    Escolas do polo ({escolaFilter.trim() ? `${escolasFiltradas.length} de ${escolas.length}` : escolas.length})
                  </h3>
                  <p className="text-xs text-slate-500">Clique em uma escola para ver dados completos e indicadores.</p>
                </div>
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
                  <input
                    className={`${inputClass} pl-9`}
                    placeholder="Filtrar escolas..."
                    aria-label="Filtrar escolas"
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
                      <td className="p-4">{cidadeUf(escola.endereco)}</td>
                      <td className="p-4">{escola.secretario_nome || 'Não informado'}</td>
                      <td className="whitespace-nowrap p-4 text-right">
                        <button type="button" onClick={(event) => { event.stopPropagation(); abrirEscola(escola); }} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-on-accent hover:bg-blue-500">Detalhes</button>
                        <button type="button" onClick={(event) => { event.stopPropagation(); setEditEscola(escola); }} className="ml-2 rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" title="Editar escola" aria-label={`Editar escola ${escola.nome}`}><Edit2 size={15} /></button>
                      </td>
                    </tr>)}
                    {!escolasFiltradas.length && <tr><td colSpan={5} className="p-12 text-center text-slate-500">{escolaFilter.trim() ? 'Nenhuma escola corresponde ao filtro.' : 'Nenhuma escola vinculada a este polo.'}</td></tr>}
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
              <span className="rounded-xl bg-indigo-500/10 p-2 text-indigo-400"><School size={22} /></span>
              <div>
                <h3 className="text-lg font-bold text-white">{escolaSelecionada.nome}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <StatusBadge status={escolaSelecionada.status} />
                  {selectedPolo && <span className="text-xs text-slate-500">Polo {selectedPolo.nome}</span>}
                </div>
              </div>
            </div>
            <button onClick={fecharEscola} aria-label="Fechar detalhes da escola" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"><X size={20} /></button>
          </div>

          <div className="flex-1 space-y-6 p-5">
            {/* Dados cadastrais + responsável */}
            <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
              <Endereco endereco={escolaSelecionada.endereco} />
              <div className="border-t border-slate-800 pt-4">
                <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"><UserCheck size={14} className="text-indigo-400" /> Responsável</h4>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <InfoField label="Nome" value={escolaSelecionada.secretario_nome} />
                  <InfoField label="E-mail" value={escolaSelecionada.secretario_email} />
                  <InfoField label="CPF" value={escolaSelecionada.secretario_cpf} />
                </div>
              </div>
            </section>

            {/* Indicadores da escola (clicáveis) */}
            <section>
              <div className="mb-3">
                <h4 className="text-sm font-bold text-white">Indicadores da escola</h4>
                <p className="text-xs text-slate-500">Clique em um indicador para abrir a lista correspondente.</p>
              </div>
              {loadingEscola || !resumoEscola ? (
                <div className="flex justify-center rounded-2xl border border-slate-800 bg-slate-950/50 py-10 text-blue-400"><Loader2 className="animate-spin" /></div>
              ) : (
                <IndicadoresEscola resumo={resumoEscola} escola={escolaSelecionada} area={area} />
              )}
            </section>
          </div>

          {/* Footer do drawer */}
          <div className="sticky bottom-0 flex justify-end gap-2 border-t border-slate-800 bg-slate-900/95 p-4 backdrop-blur">
            <button onClick={fecharEscola} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Fechar</button>
            <button onClick={() => { setEditEscola(escolaSelecionada); fecharEscola(); }} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-blue-500"><Edit2 size={14} /> Editar escola</button>
          </div>
        </div>
      </div>
    )}

    {/* Modal de criação (polo / escola) */}
    {modal && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <form onSubmit={modal === 'polo' ? savePolo : saveEscola} className="glass max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">{modal === 'polo' ? 'Novo polo' : 'Nova escola e secretário'}</h2>
          <button type="button" onClick={() => setModal(null)} className="text-slate-400"><X /></button>
        </div>
        {erroModal && <p role="alert" className="text-sm text-red-300">{erroModal}</p>}
        <input className={inputClass} required minLength={2} placeholder="Nome da unidade" value={modal === 'polo' ? poloForm.nome : escolaForm.nome} onChange={(event) => modal === 'polo' ? setPoloForm({ ...poloForm, nome: event.target.value }) : setEscolaForm({ ...escolaForm, nome: event.target.value })} />
        {modal === 'escola' && <select className={inputClass} required value={escolaForm.polo_id} onChange={(event) => setEscolaForm({ ...escolaForm, polo_id: event.target.value, secretario_usuario_id: '' })}><option value="">Selecione o polo</option>{polos.map((polo) => <option key={polo.id} value={polo.id}>{polo.nome}</option>)}</select>}
        <div className="grid gap-3 sm:grid-cols-2">
          {(['cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'] as const).map((key) => <input key={key} className={inputClass} required={key === 'cidade' || key === 'estado'} placeholder={key[0].toUpperCase() + key.slice(1)} value={(modal === 'polo' ? poloForm.endereco?.[key] : escolaForm.endereco?.[key]) || ''} onChange={(event) => changeAddress(key, event.target.value)} />)}
        </div>
        {cepLookup.message && <p role={cepLookup.status === 'error' ? 'alert' : 'status'} className={`text-xs ${cepLookup.status === 'error' ? 'text-red-300' : 'text-slate-400'}`}>{cepLookup.message}</p>}
        {modal === 'escola' && <SecretarioEscolaFields poloId={escolaForm.polo_id} values={escolaForm} onChange={(update) => setEscolaForm((form) => ({ ...form, ...update }))} />}
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
          <button type="submit" disabled={saving} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:opacity-50">{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </div>}

    {editPolo && <PoloEditModal polo={editPolo} onClose={() => setEditPolo(null)} onSuccess={() => { aposEditar(); setEditPolo(null); }} />}
    {editEscola && <EscolaEditModal escola={editEscola} polos={polos} onClose={() => setEditEscola(null)} onSuccess={() => { aposEditar(); setEditEscola(null); }} />}
  </div>;
};
