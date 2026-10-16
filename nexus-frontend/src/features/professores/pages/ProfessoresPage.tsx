import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Edit2,
  Filter,
  GraduationCap,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { ProfessorModal } from '@/features/professores/components/ProfessorModal';
import { Professor, UnidadeOption } from '@/types/professor';

const PAGE_SIZE = 20;

const inputCls =
  'w-full pl-10 pr-4 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow transition-colors';

const getStatusBadge = (status?: string) => {
  switch (status) {
    case 'ativo':
      return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    case 'inativo':
      return 'bg-slate-800 text-slate-400 border-slate-700';
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700';
  }
};

export const ProfessoresPage: React.FC = () => {
  const [professores, setProfessores] = useState<Professor[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [offset, setOffset] = useState(0);

  // Indica se o usuário já acionou a busca (nenhum dado é carregado antes disso)
  const [searchTriggered, setSearchTriggered] = useState(false);
  const searchTriggeredRef = useRef(false);

  // Filtros digitados (staged) e filtros efetivamente aplicados (após Buscar/Enter)
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPolo, setSelectedPolo] = useState('');
  const [selectedEscola, setSelectedEscola] = useState('');
  const [disciplina, setDisciplina] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [applied, setApplied] = useState({
    search: '',
    polo_id: '',
    escola_id: '',
    disciplina: '',
    status: '',
  });

  // Opções de filtro
  const [polos, setPolos] = useState<UnidadeOption[]>([]);
  const [escolasFiltro, setEscolasFiltro] = useState<UnidadeOption[]>([]);

  // Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProfessor, setEditingProfessor] = useState<Professor | null>(null);

  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null
  );

  useEffect(() => {
    professoresApi
      .listarPolos()
      .then(setPolos)
      .catch(() => setPolos([]));
  }, []);

  useEffect(() => {
    if (!selectedPolo) {
      setEscolasFiltro([]);
      return;
    }
    professoresApi
      .listarEscolasDoPolo(selectedPolo)
      .then(setEscolasFiltro)
      .catch(() => setEscolasFiltro([]));
  }, [selectedPolo]);

  const loadData = useCallback(async () => {
    // Só consulta a API após o usuário acionar a busca
    if (!searchTriggeredRef.current) return;
    setIsLoading(true);
    try {
      const resposta = await professoresApi.listar({
        search: applied.search || undefined,
        polo_id: applied.polo_id || undefined,
        escola_id: applied.escola_id || undefined,
        disciplina: applied.disciplina || undefined,
        status: applied.status || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setProfessores(resposta.items || []);
      setTotal(resposta.total || 0);
    } catch (err) {
      setFeedback({ type: 'error', message: apiErrorMessage(err, 'Erro ao carregar professores.') });
    } finally {
      setIsLoading(false);
    }
  }, [applied, offset]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSearch = () => {
    searchTriggeredRef.current = true;
    setSearchTriggered(true);
    setApplied({
      search: searchTerm.trim(),
      polo_id: selectedPolo,
      escola_id: selectedEscola,
      disciplina: disciplina.trim(),
      status: selectedStatus,
    });
    setOffset(0);
  };

  const handleOpenCreate = () => {
    setEditingProfessor(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (professor: Professor) => {
    setEditingProfessor(professor);
    setIsModalOpen(true);
  };

  const handleDelete = async (professor: Professor) => {
    const nome = professor.nome || 'Professor';
    if (!window.confirm(`Tem certeza que deseja desativar o professor "${nome}"? O cadastro será mantido com status inativo.`)) {
      return;
    }
    try {
      await professoresApi.excluir(professor.id);
      setFeedback({ type: 'success', message: `Professor ${nome} desativado com sucesso.` });
      void loadData();
    } catch (err) {
      setFeedback({ type: 'error', message: apiErrorMessage(err, 'Erro ao desativar o professor.') });
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-yellow/15 border border-nexus-yellow/30 text-nexus-yellow text-xs font-bold uppercase tracking-wider mb-2">
            <GraduationCap className="w-3.5 h-3.5" />
            Corpo Docente
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Professores & Docentes
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Gestão de docentes: vínculos com polo/escola, disciplinas ministradas, carga horária e contraprestação.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="py-3 px-5 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all transform active:scale-95 cursor-pointer shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          <span>Novo Professor</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-sm animate-fadeIn ${
            feedback.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200'
              : 'bg-red-500/15 border-red-500/30 text-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="p-1 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Filters */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col lg:flex-row items-center justify-between gap-3 shadow-md">
        <div className="w-full lg:w-72 relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por nome ou e-mail..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSearch();
            }}
            className={inputCls}
          />
        </div>

        <div className="w-full lg:w-auto flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Filtros:</span>
          </div>

          <select
            value={selectedPolo}
            onChange={(e) => {
              setSelectedPolo(e.target.value);
              setSelectedEscola('');
            }}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
          >
            <option value="">Todos os polos</option>
            {polos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>

          <select
            value={selectedEscola}
            onChange={(e) => setSelectedEscola(e.target.value)}
            disabled={!selectedPolo}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow disabled:opacity-50"
            title={selectedPolo ? 'Filtrar por escola' : 'Selecione um polo para filtrar por escola'}
          >
            <option value="">
              {selectedPolo ? 'Todas as escolas' : 'Selecione um polo'}
            </option>
            {escolasFiltro.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nome}
              </option>
            ))}
          </select>

          <input
            type="text"
            placeholder="Disciplina"
            value={disciplina}
            onChange={(e) => setDisciplina(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSearch();
            }}
            className="w-36 bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-nexus-yellow"
          />

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
          >
            <option value="">Todos os status</option>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
          </select>

          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-xs rounded-xl transition-colors flex items-center gap-1.5 shrink-0"
            title="Buscar"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Buscar</span>
          </button>

          <button
            onClick={handleSearch}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
            title="Recarregar"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Tabela */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Docente</th>
                <th className="py-3.5 px-4">Polo</th>
                <th className="py-3.5 px-4">Escola</th>
                <th className="py-3.5 px-4">Disciplinas</th>
                <th className="py-3.5 px-4">Carga Horária</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-nexus-yellow" />
                    Carregando professores do NEXUS 2.0...
                  </td>
                </tr>
              ) : !searchTriggered ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    Preencha a busca ou selecione um filtro e clique em{' '}
                    <strong className="text-nexus-yellow">Buscar</strong> para carregar os
                    professores.
                  </td>
                </tr>
              ) : professores.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    Nenhum professor encontrado com os filtros informados.
                  </td>
                </tr>
              ) : (
                professores.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue flex items-center justify-center text-white font-bold text-xs shrink-0">
                          {(p.nome || '?').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-white">{p.nome || 'Sem vínculo'}</p>
                          <p className="text-[11px] text-slate-400">{p.email || '—'}</p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">{p.polo_nome || '—'}</td>
                    <td className="py-3.5 px-4">{p.escola_nome || '—'}</td>

                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {p.materias && p.materias.length > 0 ? (
                          p.materias.map((materia) => (
                            <span
                              key={materia}
                              className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-[10px] text-nexus-yellow font-mono"
                            >
                              {materia}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-500 text-[11px]">—</span>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <p className="text-slate-200 font-medium">
                        {p.quantidade_aulas || 0} aulas · {p.horas_totais || 0}h
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {p.valor_hora_aula ? `R$ ${p.valor_hora_aula.toFixed(2)}/hora` : 'Sem valor/hora'}
                      </p>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getStatusBadge(
                          p.status
                        )}`}
                      >
                        {p.status || 'ativo'}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenEdit(p)}
                          className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-blue-400 border border-slate-800 transition-colors"
                          title="Editar Professor"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => handleDelete(p)}
                          disabled={p.status === 'inativo'}
                          className="p-1.5 rounded-lg bg-slate-950 hover:bg-red-500/10 text-slate-400 hover:text-red-400 border border-slate-800 transition-colors disabled:opacity-40 disabled:pointer-events-none"
                          title="Desativar Professor"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span>
            Total: <strong>{total}</strong> professor(es) cadastrado(s)
          </span>
          <div className="flex items-center gap-3">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="rounded-lg px-3 py-1 hover:text-white disabled:opacity-40"
            >
              Anterior
            </button>
            <span>
              {total === 0 ? 0 : offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
            </span>
            <button
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="rounded-lg px-3 py-1 hover:text-white disabled:opacity-40"
            >
              Próxima
            </button>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <ProfessorModal
          polos={polos}
          professor={editingProfessor}
          onClose={() => setIsModalOpen(false)}
          onSuccess={(mensagem) => {
            setIsModalOpen(false);
            setFeedback({ type: 'success', message: mensagem });
            void loadData();
          }}
        />
      )}
    </div>
  );
};
