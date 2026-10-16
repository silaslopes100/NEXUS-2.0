import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserPlus,
  Search,
  Filter,
  Edit2,
  Trash2,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  Shield,
  RefreshCw,
  Eye,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Building2,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { UsuarioAdmin } from '@/types/admin';
import { UsuarioFormModal } from '@/features/admin/components/UsuarioFormModal';
import { useAuthStore } from '@/stores/authStore';

const PAGE_SIZE = 20;

const inputCls =
  'w-full pl-10 pr-4 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow transition-colors';

export const UsuariosInternosPage: React.FC = () => {
  const navigate = useNavigate();
  const { user: loggedAdmin } = useAuthStore();

  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [offset, setOffset] = useState(0);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [selectedPerfil, setSelectedPerfil] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // Modais
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UsuarioAdmin | null>(null);
  const [isResetPasswordOpen, setIsResetPasswordOpen] = useState(false);
  const [resetTargetUser, setResetTargetUser] = useState<UsuarioAdmin | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [deleteTargetUser, setDeleteTargetUser] = useState<UsuarioAdmin | null>(null);

  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await adminApi.listUsuarios({
        q: appliedSearch || undefined,
        perfil: selectedPerfil || undefined,
        status: selectedStatus || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setUsuarios(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao carregar usuários administrativos.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [appliedSearch, selectedPerfil, selectedStatus, offset]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSearch = () => {
    setOffset(0);
    setAppliedSearch(searchTerm.trim());
  };

  const handleOpenCreate = () => {
    setEditingUser(null);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (u: UsuarioAdmin) => {
    setEditingUser(u);
    setIsFormOpen(true);
  };

  const handleSaved = (message: string) => {
    setFeedback({ type: 'success', message });
    void loadData();
  };

  const handleOpenResetPassword = (u: UsuarioAdmin) => {
    setResetTargetUser(u);
    setNewPassword('');
    setIsResetPasswordOpen(true);
  };

  const handleConfirmResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetTargetUser || newPassword.length < 6) {
      setFeedback({ type: 'error', message: 'A nova senha deve ter no mínimo 6 caracteres.' });
      return;
    }
    try {
      await adminApi.resetUsuarioSenha(resetTargetUser.id, newPassword);
      setFeedback({
        type: 'success',
        message: `Senha de ${resetTargetUser.nome} redefinida com sucesso (Argon2id).`,
      });
      setIsResetPasswordOpen(false);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao redefinir a senha.',
      });
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetUser) return;
    try {
      await adminApi.deleteUsuario(deleteTargetUser.id);
      setFeedback({ type: 'success', message: `Usuário ${deleteTargetUser.nome} excluído com sucesso.` });
      setDeleteTargetUser(null);
      void loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao excluir usuário.',
      });
      setDeleteTargetUser(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ativo':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'inativo':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      case 'bloqueado':
        return 'bg-red-500/15 text-red-400 border-red-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-yellow/15 border border-nexus-yellow/30 text-nexus-yellow text-xs font-bold uppercase tracking-wider mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            Gestão de Contas & Permissões
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Consulta de Usuário
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Consulte fichas cadastrais, perfis de acesso e métricas operacionais de cada usuário do
            NEXUS 2.0.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="py-3 px-5 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all transform active:scale-95 cursor-pointer shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          <span>Novo Usuário</span>
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
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-3 shadow-md">
        <div className="w-full md:w-96 relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por nome, e-mail ou CPF..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSearch();
            }}
            className={inputCls}
          />
        </div>

        <div className="w-full md:w-auto flex items-center gap-2.5 overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Perfil:</span>
          </div>
          <select
            value={selectedPerfil}
            onChange={(e) => {
              setOffset(0);
              setSelectedPerfil(e.target.value);
            }}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
          >
            <option value="">Todos os perfis</option>
            <option value="admin">Admin / Staff</option>
            <option value="polo">Polo</option>
            <option value="escola">Escola</option>
            <option value="professor">Professor</option>
            <option value="aluno">Aluno</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => {
              setOffset(0);
              setSelectedStatus(e.target.value);
            }}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
          >
            <option value="">Todos os status</option>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
            <option value="bloqueado">Bloqueado</option>
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
            onClick={() => void loadData()}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors"
            title="Recarregar"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Usuário</th>
                <th className="py-3.5 px-4">E-mail & CPF</th>
                <th className="py-3.5 px-4">Polo / Escola</th>
                <th className="py-3.5 px-4">Perfil</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-nexus-yellow" />
                    Carregando usuários do NEXUS 2.0...
                  </td>
                </tr>
              ) : usuarios.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    Nenhum usuário encontrado com os filtros informados.
                  </td>
                </tr>
              ) : (
                usuarios.map((u) => (
                  <tr
                    key={u.id}
                    onClick={() => navigate(`/admin/usuarios/${u.id}`)}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    title="Ver ficha cadastral"
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        {u.foto_url ? (
                          <img
                            src={u.foto_url}
                            alt={u.nome}
                            className="w-8 h-8 rounded-lg object-cover shrink-0 border border-slate-700"
                          />
                        ) : (
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue flex items-center justify-center text-white font-bold text-xs shrink-0">
                            {u.nome.charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div>
                          <p className="font-semibold text-white">
                            {u.nome} {u.sobrenome || ''}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            {u.telefone || u.celular || 'Sem telefone'}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <p className="text-slate-200 font-medium">{u.email || '—'}</p>
                      <p className="text-[11px] text-slate-500">{u.cpf || 'Sem CPF cadastrado'}</p>
                    </td>

                    <td className="py-3.5 px-4">
                      {u.polo_nome || u.escola_nome ? (
                        <div className="space-y-0.5">
                          {u.polo_nome && (
                            <p className="flex items-center gap-1 text-slate-200">
                              <MapPin className="w-3 h-3 text-nexus-yellow shrink-0" />
                              {u.polo_nome}
                            </p>
                          )}
                          {u.escola_nome && (
                            <p className="flex items-center gap-1 text-[11px] text-slate-400">
                              <Building2 className="w-3 h-3 shrink-0" />
                              {u.escola_nome}
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-nexus-blue/15 border border-nexus-blue/30 text-blue-400">
                        <Shield className="w-3 h-3" />
                        {u.perfil_nome || 'Sem Perfil'}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getStatusBadge(u.status)}`}
                      >
                        {u.status}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div
                        className="flex items-center justify-end gap-1.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => navigate(`/admin/usuarios/${u.id}`)}
                          className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-emerald-400 border border-slate-800 transition-colors"
                          title="Ver Ficha"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => handleOpenResetPassword(u)}
                          className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-nexus-yellow border border-slate-800 transition-colors"
                          title="Redefinir Senha"
                        >
                          <KeyRound className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => handleOpenEdit(u)}
                          className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-blue-400 border border-slate-800 transition-colors"
                          title="Editar Usuário"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => {
                            if (loggedAdmin?.id === u.id) {
                              setFeedback({
                                type: 'error',
                                message: 'Você não pode excluir o próprio usuário administrador.',
                              });
                              return;
                            }
                            setDeleteTargetUser(u);
                          }}
                          className="p-1.5 rounded-lg bg-slate-950 hover:bg-red-500/10 text-slate-400 hover:text-red-400 border border-slate-800 transition-colors"
                          title="Excluir Usuário"
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

        {/* Paginação */}
        <div className="p-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span>
            Total: <strong>{total}</strong> usuários · Página <strong>{currentPage}</strong> de{' '}
            <strong>{totalPages}</strong>
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0 || isLoading}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Anterior
            </button>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total || isLoading}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
            >
              Próxima
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Modal de Criação / Edição */}
      <UsuarioFormModal
        open={isFormOpen}
        editingUser={editingUser}
        onClose={() => setIsFormOpen(false)}
        onSaved={handleSaved}
      />

      {/* Modal de Redefinição de Senha */}
      {isResetPasswordOpen && resetTargetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-white font-bold text-sm">
                <KeyRound className="w-4 h-4 text-nexus-yellow" />
                <span>Redefinir Senha do Usuário</span>
              </div>
              <button
                onClick={() => setIsResetPasswordOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleConfirmResetPassword} className="space-y-4 mt-4">
              <p className="text-xs text-slate-400">
                Você está alterando administrativamente a senha de{' '}
                <strong>{resetTargetUser.nome}</strong> ({resetTargetUser.email}). A nova senha será
                criptografada em <strong>Argon2id</strong>.
              </p>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Nova Senha *</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                  placeholder="Mínimo 6 caracteres"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsResetPasswordOpen(false)}
                  className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 text-xs font-bold rounded-xl shadow transition-colors cursor-pointer"
                >
                  Confirmar Redefinição
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Confirmação de Exclusão */}
      {deleteTargetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn">
            <div className="flex items-center gap-2 text-white font-bold text-sm pb-3 border-b border-slate-800">
              <Trash2 className="w-4 h-4 text-red-400" />
              <span>Confirmar Exclusão</span>
            </div>
            <p className="text-xs text-slate-400 mt-4">
              Tem certeza que deseja excluir o usuário{' '}
              <strong className="text-white">
                {deleteTargetUser.nome} {deleteTargetUser.sobrenome || ''}
              </strong>{' '}
              ({deleteTargetUser.email})? Esta ação será registrada em auditoria.
            </p>
            <div className="pt-4 flex items-center justify-end gap-2 border-t border-slate-800 mt-4">
              <button
                onClick={() => setDeleteTargetUser(null)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white text-xs font-bold rounded-xl shadow transition-colors cursor-pointer"
              >
                Excluir Definitivamente
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
