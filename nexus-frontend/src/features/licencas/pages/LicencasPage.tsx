import React, { useState, useEffect, useCallback } from 'react';
import {
  Key,
  Plus,
  Share2,
  UserCheck,
  Search,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  RefreshCw,
  Layers,
  Building,
  School,
  Database,
} from 'lucide-react';
import { licencasApi } from '@/features/licencas/api';
import { EstoqueLicenca, LicencaAtribuida } from '@/types/licencas';
import { useAuthStore } from '@/stores/authStore';

export const LicencasPage: React.FC = () => {
  const { user } = useAuthStore();
  const perfil = user?.perfil?.nome?.toLowerCase() || '';

  const [activeTab, setActiveTab] = useState<'estoque' | 'atribuidas'>('estoque');
  const [estoqueList, setEstoqueList] = useState<EstoqueLicenca[]>([]);
  const [atribuidasList, setAtribuidasList] = useState<LicencaAtribuida[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEscola] = useState('');

  // Modais
  const [isAdicionarOpen, setIsAdicionarOpen] = useState(false);
  const [isDistribuirOpen, setIsDistribuirOpen] = useState(false);
  const [isAtribuirOpen, setIsAtribuirOpen] = useState(false);

  // Formulários
  const [adicionarForm, setAdicionarForm] = useState({
    disciplina_id: '',
    quantidade: 10,
  });

  const [distribuirForm, setDistribuirForm] = useState({
    disciplina_id: '',
    escola_id: '',
    quantidade: 5,
  });

  const [atribuirForm, setAtribuirForm] = useState({
    disciplina_id: '',
    escola_id: user?.escola_id || '',
    polo_id: user?.polo_id || '',
    aluno_id: '',
    quantidade: 1,
  });

  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [estRes, atribRes] = await Promise.all([
        licencasApi.listEstoque({
          escola_id: filtroEscola || (perfil === 'escola' ? user?.escola_id || undefined : undefined),
        }).catch(() => []),
        licencasApi.listLicencasAtribuidas({
          polo_id: perfil === 'polo' ? user?.polo_id || undefined : undefined,
          escola_id: filtroEscola || (perfil === 'escola' ? user?.escola_id || undefined : undefined),
        }).catch(() => []),
      ]);
      setEstoqueList(Array.isArray(estRes) ? estRes : []);
      setAtribuidasList(Array.isArray(atribRes) ? atribRes : []);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao carregar dados de estoque de licenças.',
      });
      setEstoqueList([]);
      setAtribuidasList([]);
    } finally {
      setIsLoading(false);
    }
  }, [filtroEscola, perfil, user?.escola_id, user?.polo_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Ações
  const handleAdicionarEstoque = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adicionarForm.disciplina_id || adicionarForm.quantidade <= 0) return;
    setIsSaving(true);
    try {
      await licencasApi.adicionarEstoque(adicionarForm.disciplina_id, Number(adicionarForm.quantidade));
      setFeedback({ type: 'success', message: 'Estoque adicionado com sucesso!' });
      setIsAdicionarOpen(false);
      setAdicionarForm({ disciplina_id: '', quantidade: 10 });
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Falha ao adicionar estoque de licença.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDistribuirEstoque = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!distribuirForm.disciplina_id || !distribuirForm.escola_id || distribuirForm.quantidade <= 0) return;
    setIsSaving(true);
    try {
      await licencasApi.distribuirEstoque({
        disciplina_id: distribuirForm.disciplina_id,
        escola_id: distribuirForm.escola_id,
        quantidade: Number(distribuirForm.quantidade),
      });
      setFeedback({ type: 'success', message: 'Licenças distribuídas para a escola com sucesso!' });
      setIsDistribuirOpen(false);
      setDistribuirForm({ disciplina_id: '', escola_id: '', quantidade: 5 });
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Falha ao distribuir licenças para a escola.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleAtribuirLicenca = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!atribuirForm.disciplina_id || !atribuirForm.aluno_id || atribuirForm.quantidade <= 0) return;
    setIsSaving(true);
    try {
      await licencasApi.atribuirLicenca({
        disciplina_id: atribuirForm.disciplina_id,
        escola_id: atribuirForm.escola_id || undefined,
        polo_id: atribuirForm.polo_id || undefined,
        aluno_id: atribuirForm.aluno_id,
        quantidade: Number(atribuirForm.quantidade),
      });
      setFeedback({ type: 'success', message: 'Licença atribuída ao aluno com sucesso!' });
      setIsAtribuirOpen(false);
      setAtribuirForm({
        disciplina_id: '',
        escola_id: user?.escola_id || '',
        polo_id: user?.polo_id || '',
        aluno_id: '',
        quantidade: 1,
      });
      await loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Falha ao atribuir licença (verifique o saldo disponível).',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const filteredEstoque = Array.isArray(estoqueList)
    ? estoqueList.filter((item) => {
        const matchDisc = item.disciplina_id?.toLowerCase().includes(searchTerm.toLowerCase()) ?? true;
        const matchEscola = item.escola_id?.toLowerCase().includes(searchTerm.toLowerCase()) ?? true;
        return matchDisc || matchEscola;
      })
    : [];

  const filteredAtribuidas = Array.isArray(atribuidasList)
    ? atribuidasList.filter((item) => {
        const matchDisc = item.disciplina_id?.toLowerCase().includes(searchTerm.toLowerCase()) ?? true;
        const matchAluno = item.aluno_id?.toLowerCase().includes(searchTerm.toLowerCase()) ?? true;
        return matchDisc || matchAluno;
      })
    : [];

  const totalEstoqueDisponivel = Array.isArray(estoqueList)
    ? estoqueList.reduce((acc, curr) => acc + (curr.quantidade_disponivel || 0), 0)
    : 0;
  const totalEstoqueGeral = Array.isArray(estoqueList)
    ? estoqueList.reduce((acc, curr) => acc + (curr.quantidade_total || 0), 0)
    : 0;
  const totalAtribuidasCount = Array.isArray(atribuidasList)
    ? atribuidasList.reduce((acc, curr) => acc + (curr.quantidade || 0), 0)
    : 0;

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-400 text-xs font-bold uppercase tracking-wider mb-2">
            <Key className="w-3.5 h-3.5" />
            Módulo de Licenças & Estoque
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Gestão de Licenças & Distribuição
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Controle de estoque global, alocação por escola e atribuição nominal a alunos.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {perfil === 'admin' && (
            <>
              <button
                onClick={() => setIsAdicionarOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 transition"
              >
                <Plus className="w-4 h-4" />
                Adicionar Estoque
              </button>
              <button
                onClick={() => setIsDistribuirOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-500/20 transition"
              >
                <Share2 className="w-4 h-4" />
                Distribuir p/ Escola
              </button>
            </>
          )}

          {(perfil === 'admin' || perfil === 'polo' || perfil === 'escola') && (
            <button
              onClick={() => setIsAtribuirOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 transition"
            >
              <UserCheck className="w-4 h-4" />
              Atribuir a Aluno
            </button>
          )}
        </div>
      </div>

      {/* Cards de Métricas */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Produzido/Geral</span>
            <Database className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">{totalEstoqueGeral}</div>
          <p className="text-xs text-slate-400 mt-1">Licenças registradas no sistema</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Disponível em Saldo</span>
            <Layers className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">{totalEstoqueDisponivel}</div>
          <p className="text-xs text-slate-400 mt-1">Prontas para alocação/uso</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-purple-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Licenças Atribuídas</span>
            <UserCheck className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-white mt-3">{totalAtribuidasCount}</div>
          <p className="text-xs text-slate-400 mt-1">Consumidas por discentes</p>
        </div>
      </div>

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
            onClick={() => setActiveTab('estoque')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
              activeTab === 'estoque'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Saldos de Estoque ({filteredEstoque.length})
          </button>
          <button
            onClick={() => setActiveTab('atribuidas')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
              activeTab === 'atribuidas'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Licenças Atribuídas ({filteredAtribuidas.length})
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Buscar por disciplina/aluno/escola..."
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

      {/* Conteúdo Principal */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-3" />
            <p className="text-sm">Carregando informações de licenças...</p>
          </div>
        ) : activeTab === 'estoque' ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Disciplina / Matéria</th>
                  <th className="py-3.5 px-4">Nível / Destino</th>
                  <th className="py-3.5 px-4 text-center">Quantidade Total</th>
                  <th className="py-3.5 px-4 text-center">Disponível em Saldo</th>
                  <th className="py-3.5 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredEstoque.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      Nenhum registro de estoque encontrado.
                    </td>
                  </tr>
                ) : (
                  filteredEstoque.map((item, idx) => (
                    <tr key={item.id || idx} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 text-white font-semibold">
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-blue-400" />
                          <span>{item.disciplina_id || 'Todas as Disciplinas'}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {item.escola_id ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-bold">
                            <School className="w-3 h-3" />
                            Escola: {item.escola_id}
                          </span>
                        ) : item.polo_id ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-bold">
                            <Building className="w-3 h-3" />
                            Polo: {item.polo_id}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-500/10 border border-slate-500/30 text-slate-300 text-xs font-bold">
                            <Database className="w-3 h-3" />
                            Estoque Central / Global
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center text-slate-200">
                        {item.quantidade_total}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2.5 py-1 rounded-lg text-xs font-extrabold ${
                          item.quantidade_disponivel > 0 
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        }`}>
                          {item.quantidade_disponivel} un.
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {item.quantidade_disponivel > 0 ? (
                          <span className="text-emerald-400 text-xs font-semibold">Ativo / Com Saldo</span>
                        ) : (
                          <span className="text-rose-400 text-xs font-semibold">Esgotado</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Disciplina</th>
                  <th className="py-3.5 px-4">Aluno / Discente</th>
                  <th className="py-3.5 px-4">Origem (Escola/Polo)</th>
                  <th className="py-3.5 px-4 text-center">Qtd Atribuída</th>
                  <th className="py-3.5 px-4 text-right">Data de Atribuição</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredAtribuidas.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      Nenhuma licença nominal atribuída no momento.
                    </td>
                  </tr>
                ) : (
                  filteredAtribuidas.map((item, idx) => (
                    <tr key={item.id || idx} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4 text-white font-semibold">
                        {item.disciplina_id || 'Geral'}
                      </td>
                      <td className="py-3 px-4 text-emerald-400 font-semibold">
                        {item.aluno_id || 'Não informado'}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-400">
                        {item.escola_id ? `Escola: ${item.escola_id}` : item.polo_id ? `Polo: ${item.polo_id}` : 'Central'}
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-white">
                        {item.quantidade}
                      </td>
                      <td className="py-3 px-4 text-right text-xs text-slate-400">
                        {item.atribuido_em ? new Date(item.atribuido_em).toLocaleString('pt-BR') : 'Recentemente'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Adicionar Estoque */}
      {isAdicionarOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-400" />
                Adicionar ao Estoque Central
              </h3>
              <button onClick={() => setIsAdicionarOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAdicionarEstoque} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  ID ou Código da Disciplina
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: disc-1, teologia-s1"
                  value={adicionarForm.disciplina_id}
                  onChange={(e) => setAdicionarForm({ ...adicionarForm, disciplina_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Quantidade a Injetar
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={adicionarForm.quantidade}
                  onChange={(e) => setAdicionarForm({ ...adicionarForm, quantidade: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAdicionarOpen(false)}
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
                  Confirmar Adição
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Distribuir Estoque para Escola */}
      {isDistribuirOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Share2 className="w-5 h-5 text-indigo-400" />
                Distribuir Licenças para Escola
              </h3>
              <button onClick={() => setIsDistribuirOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleDistribuirEstoque} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  ID da Disciplina
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: disc-1"
                  value={distribuirForm.disciplina_id}
                  onChange={(e) => setDistribuirForm({ ...distribuirForm, disciplina_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  ID da Escola Destinatária
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: escola-1"
                  value={distribuirForm.escola_id}
                  onChange={(e) => setDistribuirForm({ ...distribuirForm, escola_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Quantidade a Transferir
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={distribuirForm.quantidade}
                  onChange={(e) => setDistribuirForm({ ...distribuirForm, quantidade: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsDistribuirOpen(false)}
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
                  Distribuir Saldo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Atribuir Licença a Aluno */}
      {isAtribuirOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-emerald-400" />
                Atribuir Licença a Discente
              </h3>
              <button onClick={() => setIsAtribuirOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAtribuirLicenca} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  ID da Disciplina
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: disc-1"
                  value={atribuirForm.disciplina_id}
                  onChange={(e) => setAtribuirForm({ ...atribuirForm, disciplina_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  ID do Aluno
                </label>
                <input
                  type="text"
                  required
                  placeholder="ex: aluno-1"
                  value={atribuirForm.aluno_id}
                  onChange={(e) => setAtribuirForm({ ...atribuirForm, aluno_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Escola de Origem (Opcional se Central)
                </label>
                <input
                  type="text"
                  placeholder="ex: escola-1"
                  value={atribuirForm.escola_id}
                  onChange={(e) => setAtribuirForm({ ...atribuirForm, escola_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Quantidade
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={atribuirForm.quantidade}
                  onChange={(e) => setAtribuirForm({ ...atribuirForm, quantidade: Number(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAtribuirOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Confirmar Atribuição
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
