import React, { useState, useEffect, useCallback } from 'react';
import {
  Building,
  School,
  Plus,
  Search,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  RefreshCw,
  UserCheck,
  MapPin,
  Mail,
  User,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { PoloItem, EscolaItem, ResumoPoloResponse } from '@/types/polos';
import { useAuthStore } from '@/stores/authStore';

export const PolosEscolasPage: React.FC = () => {
  const { user } = useAuthStore();
  const perfil = user?.perfil?.nome?.toLowerCase() || '';

  const [activeTab, setActiveTab] = useState<'polos' | 'escolas'>('polos');
  const [polos, setPolos] = useState<PoloItem[]>([]);
  const [escolas, setEscolas] = useState<EscolaItem[]>([]);
  const [selectedPoloId, setSelectedPoloId] = useState<string>('');
  const [resumoPolo, setResumoPolo] = useState<ResumoPoloResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');

  // Modais
  const [isCreatePoloOpen, setIsCreatePoloOpen] = useState(false);
  const [isCreateEscolaOpen, setIsCreateEscolaOpen] = useState(false);
  const [isCoordenadorOpen, setIsCoordenadorOpen] = useState(false);

  // Formulários
  const [poloForm, setPoloForm] = useState({
    nome: '',
    responsavel_nome: '',
    responsavel_cpf: '',
    responsavel_email: '',
    logradouro: '',
    numero: '',
    bairro: '',
    cidade: '',
    estado: 'SP',
    cep: '',
  });

  const [escolaForm, setEscolaForm] = useState({
    polo_id: '',
    nome: '',
    responsavel_nome: '',
    responsavel_cpf: '',
    responsavel_email: '',
    logradouro: '',
    numero: '',
    bairro: '',
    cidade: '',
    estado: 'SP',
    cep: '',
  });

  const [coordenadorForm, setCoordenadorForm] = useState({
    polo_id: '',
    nome: '',
    cpf: '',
    email: '',
    senha: '',
  });

  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [polosRes, escolasRes] = await Promise.all([
        polosEscolasApi.listPolos().catch(() => []),
        polosEscolasApi.listEscolas(selectedPoloId ? { polo_id: selectedPoloId } : undefined).catch(() => []),
      ]);
      setPolos(Array.isArray(polosRes) ? polosRes : []);
      setEscolas(Array.isArray(escolasRes) ? escolasRes : []);

      if (selectedPoloId || (perfil === 'polo' && user?.polo_id)) {
        const targetId = selectedPoloId || user?.polo_id || '';
        if (targetId) {
          try {
            const resumo = await polosEscolasApi.getResumoPolo(targetId);
            setResumoPolo(resumo);
          } catch {
            setResumoPolo(null);
          }
        }
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao carregar dados de polos e escolas.',
      });
      setPolos([]);
      setEscolas([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedPoloId, perfil, user?.polo_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreatePolo = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await polosEscolasApi.createPolo(poloForm);
      setFeedback({ type: 'success', message: 'Polo Regional cadastrado com sucesso!' });
      setIsCreatePoloOpen(false);
      setPoloForm({
        nome: '',
        responsavel_nome: '',
        responsavel_cpf: '',
        responsavel_email: '',
        logradouro: '',
        numero: '',
        bairro: '',
        cidade: '',
        estado: 'SP',
        cep: '',
      });
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Falha ao cadastrar polo.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateEscola = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!escolaForm.polo_id) {
      setFeedback({ type: 'error', message: 'Selecione o polo associado.' });
      return;
    }
    setIsSaving(true);
    try {
      await polosEscolasApi.createEscola(escolaForm);
      setFeedback({ type: 'success', message: 'Escola / Unidade associada cadastrada com sucesso!' });
      setIsCreateEscolaOpen(false);
      setEscolaForm({
        polo_id: '',
        nome: '',
        responsavel_nome: '',
        responsavel_cpf: '',
        responsavel_email: '',
        logradouro: '',
        numero: '',
        bairro: '',
        cidade: '',
        estado: 'SP',
        cep: '',
      });
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Falha ao cadastrar escola.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateCoordenador = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!coordenadorForm.polo_id) return;
    setIsSaving(true);
    try {
      await polosEscolasApi.createCoordenador(coordenadorForm.polo_id, {
        nome: coordenadorForm.nome,
        cpf: coordenadorForm.cpf,
        email: coordenadorForm.email,
        senha: coordenadorForm.senha,
      });
      setFeedback({ type: 'success', message: 'Coordenador do polo criado com sucesso!' });
      setIsCoordenadorOpen(false);
      setCoordenadorForm({ polo_id: '', nome: '', cpf: '', email: '', senha: '' });
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Falha ao criar coordenador.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const filteredPolos = Array.isArray(polos)
    ? polos.filter((p) =>
        (p.nome || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.responsavel_nome || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.endereco_completo?.cidade || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : [];

  const filteredEscolas = Array.isArray(escolas)
    ? escolas.filter((esc) =>
        (esc.nome || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (esc.responsavel_nome || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (esc.endereco_completo?.cidade || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : [];

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-400 text-xs font-bold uppercase tracking-wider mb-2">
            <Building className="w-3.5 h-3.5" />
            Estrutura Regional & Unidades
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Polos Regionais & Escolas
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Gestão hierárquica, dados cadastrais, coordenadores e resumo de operação.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {perfil === 'admin' && (
            <button
              onClick={() => setIsCreatePoloOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 transition"
            >
              <Plus className="w-4 h-4" />
              Novo Polo
            </button>
          )}

          {(perfil === 'admin' || perfil === 'polo') && (
            <button
              onClick={() => {
                setEscolaForm({ ...escolaForm, polo_id: user?.polo_id || '' });
                setIsCreateEscolaOpen(true);
              }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-500/20 transition"
            >
              <Plus className="w-4 h-4" />
              Nova Escola
            </button>
          )}
        </div>
      </div>

      {/* Resumo do Polo Selecionado (se houver) */}
      {resumoPolo && (
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-blue-500/30 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              Métricas Operacionais do Polo
            </h3>
            <span className="text-xs text-blue-300 font-bold px-3 py-1 bg-blue-500/10 rounded-full border border-blue-500/30">
              ID: {resumoPolo.polo_id}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold uppercase text-slate-400">Escolas Vinculadas</div>
              <div className="text-2xl font-black text-white mt-2">{resumoPolo.escolas_vinculadas}</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold uppercase text-slate-400">Alunos Ativos</div>
              <div className="text-2xl font-black text-emerald-400 mt-2">{resumoPolo.alunos_ativos}</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold uppercase text-slate-400">Professores</div>
              <div className="text-2xl font-black text-indigo-400 mt-2">{resumoPolo.professores_alocados}</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="text-xs font-semibold uppercase text-slate-400">Estoque de Licenças</div>
              <div className="text-2xl font-black text-nexus-yellow mt-2">{resumoPolo.materias_em_estoque}</div>
              <div className="text-[11px] text-slate-500 mt-1">
                Polo: {resumoPolo.detalhes_estoque.licencas_no_polo} | Escolas: {resumoPolo.detalhes_estoque.licencas_nas_escolas}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Alert */}
      {feedback && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between gap-3 text-sm ${
            feedback.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="hover:opacity-70">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Navegação por Abas e Filtros */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2 p-1 bg-slate-900/80 rounded-xl border border-slate-800 self-start">
          <button
            onClick={() => setActiveTab('polos')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
              activeTab === 'polos'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Polos Regionais ({filteredPolos.length})
          </button>
          <button
            onClick={() => setActiveTab('escolas')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
              activeTab === 'escolas'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Escolas / Unidades ({filteredEscolas.length})
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Buscar por nome, responsável ou cidade..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            onClick={loadData}
            title="Recarregar dados"
            className="p-2 bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white rounded-xl transition"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-blue-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Listagem */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-3" />
            <p className="text-sm">Carregando polos e escolas...</p>
          </div>
        ) : activeTab === 'polos' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
            {filteredPolos.length === 0 ? (
              <div className="col-span-full py-12 text-center text-slate-500">
                Nenhum polo regional encontrado.
              </div>
            ) : (
              filteredPolos.map((polo) => (
                <div
                  key={polo.id}
                  className="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition space-y-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400">
                        <Building className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="text-base font-bold text-white">{polo.nome}</h4>
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                          <MapPin className="w-3.5 h-3.5 text-slate-500" />
                          <span>
                            {polo.endereco_completo?.cidade || 'Cidade não inf.'} - {polo.endereco_completo?.estado || 'UF'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <span className="px-2.5 py-1 rounded-full text-xs font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      {polo.status}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-300 pt-2 border-t border-slate-900">
                    <div className="flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      <span>Responsável: <strong className="text-white">{polo.responsavel_nome || 'Não definido'}</strong></span>
                    </div>
                    {polo.responsavel_email && (
                      <div className="flex items-center gap-2">
                        <Mail className="w-3.5 h-3.5 text-slate-500" />
                        <span>{polo.responsavel_email}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-900">
                    <button
                      onClick={() => setSelectedPoloId(polo.id)}
                      className="text-xs font-bold text-blue-400 hover:text-blue-300 inline-flex items-center gap-1"
                    >
                      Ver Métricas <ChevronRight className="w-3.5 h-3.5" />
                    </button>

                    {perfil === 'admin' && (
                      <button
                        onClick={() => {
                          setCoordenadorForm({ ...coordenadorForm, polo_id: polo.id });
                          setIsCoordenadorOpen(true);
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition"
                      >
                        + Coordenador
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Escola / Unidade</th>
                  <th className="py-3.5 px-4">Polo Vinculado</th>
                  <th className="py-3.5 px-4">Responsável</th>
                  <th className="py-3.5 px-4">Cidade / UF</th>
                  <th className="py-3.5 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredEscolas.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      Nenhuma escola encontrada.
                    </td>
                  </tr>
                ) : (
                  filteredEscolas.map((esc) => (
                    <tr key={esc.id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 text-white font-semibold">
                        <div className="flex items-center gap-2">
                          <School className="w-4 h-4 text-indigo-400" />
                          <span>{esc.nome}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-blue-400 text-xs">
                        ID: {esc.polo_id}
                      </td>
                      <td className="py-3 px-4 text-xs">
                        {esc.responsavel_nome || 'Não informado'}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-400">
                        {esc.endereco_completo?.cidade || '-'} / {esc.endereco_completo?.estado || '-'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="px-2 py-0.5 rounded-full text-xs font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          {esc.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Criar Polo */}
      {isCreatePoloOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Building className="w-5 h-5 text-blue-400" />
                Cadastrar Novo Polo Regional
              </h3>
              <button onClick={() => setIsCreatePoloOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreatePolo} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Nome do Polo
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: Polo Central SP"
                  value={poloForm.nome}
                  onChange={(e) => setPoloForm({ ...poloForm, nome: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Nome do Responsável
                  </label>
                  <input
                    type="text"
                    placeholder="Nome completo"
                    value={poloForm.responsavel_nome}
                    onChange={(e) => setPoloForm({ ...poloForm, responsavel_nome: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    CPF do Responsável
                  </label>
                  <input
                    type="text"
                    placeholder="000.000.000-00"
                    value={poloForm.responsavel_cpf}
                    onChange={(e) => setPoloForm({ ...poloForm, responsavel_cpf: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  E-mail do Responsável
                </label>
                <input
                  type="email"
                  placeholder="responsavel@polo.com.br"
                  value={poloForm.responsavel_email}
                  onChange={(e) => setPoloForm({ ...poloForm, responsavel_email: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Logradouro
                  </label>
                  <input
                    type="text"
                    placeholder="Rua / Avenida"
                    value={poloForm.logradouro}
                    onChange={(e) => setPoloForm({ ...poloForm, logradouro: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Número
                  </label>
                  <input
                    type="text"
                    placeholder="123"
                    value={poloForm.numero}
                    onChange={(e) => setPoloForm({ ...poloForm, numero: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Cidade
                  </label>
                  <input
                    type="text"
                    placeholder="São Paulo"
                    value={poloForm.cidade}
                    onChange={(e) => setPoloForm({ ...poloForm, cidade: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Estado (UF)
                  </label>
                  <input
                    type="text"
                    maxLength={2}
                    placeholder="SP"
                    value={poloForm.estado}
                    onChange={(e) => setPoloForm({ ...poloForm, estado: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    CEP
                  </label>
                  <input
                    type="text"
                    placeholder="00000-000"
                    value={poloForm.cep}
                    onChange={(e) => setPoloForm({ ...poloForm, cep: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreatePoloOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Salvar Polo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Criar Escola */}
      {isCreateEscolaOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <School className="w-5 h-5 text-indigo-400" />
                Cadastrar Nova Escola / Unidade
              </h3>
              <button onClick={() => setIsCreateEscolaOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateEscola} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Polo Regional Vinculado
                </label>
                <select
                  required
                  value={escolaForm.polo_id}
                  onChange={(e) => setEscolaForm({ ...escolaForm, polo_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Selecione um Polo...</option>
                  {polos.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome} (ID: {p.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Nome da Escola
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: Escola Teológica Zona Sul"
                  value={escolaForm.nome}
                  onChange={(e) => setEscolaForm({ ...escolaForm, nome: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Nome do Responsável
                  </label>
                  <input
                    type="text"
                    placeholder="Nome completo"
                    value={escolaForm.responsavel_nome}
                    onChange={(e) => setEscolaForm({ ...escolaForm, responsavel_nome: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    CPF do Responsável
                  </label>
                  <input
                    type="text"
                    placeholder="000.000.000-00"
                    value={escolaForm.responsavel_cpf}
                    onChange={(e) => setEscolaForm({ ...escolaForm, responsavel_cpf: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  E-mail da Escola / Responsável
                </label>
                <input
                  type="email"
                  placeholder="escola@dominio.com.br"
                  value={escolaForm.responsavel_email}
                  onChange={(e) => setEscolaForm({ ...escolaForm, responsavel_email: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateEscolaOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Salvar Escola
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Criar Coordenador */}
      {isCoordenadorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-blue-400" />
                Criar Acesso de Coordenador
              </h3>
              <button onClick={() => setIsCoordenadorOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCoordenador} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Nome Completo
                </label>
                <input
                  type="text"
                  required
                  placeholder="Nome do coordenador"
                  value={coordenadorForm.nome}
                  onChange={(e) => setCoordenadorForm({ ...coordenadorForm, nome: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  CPF
                </label>
                <input
                  type="text"
                  required
                  placeholder="000.000.000-00"
                  value={coordenadorForm.cpf}
                  onChange={(e) => setCoordenadorForm({ ...coordenadorForm, cpf: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  E-mail de Login
                </label>
                <input
                  type="email"
                  required
                  placeholder="coordenador@polo.com.br"
                  value={coordenadorForm.email}
                  onChange={(e) => setCoordenadorForm({ ...coordenadorForm, email: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Senha Temporária
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Mínimo 8 caracteres"
                  value={coordenadorForm.senha}
                  onChange={(e) => setCoordenadorForm({ ...coordenadorForm, senha: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCoordenadorOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Gerar Acesso
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
