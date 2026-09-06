import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
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
  Check,
  Shield,
  RefreshCw,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { UsuarioAdmin } from '@/types/admin';
import { useAuthStore } from '@/stores/authStore';

const AVAILABLE_PERMISSIONS = [
  { chave: 'p_cadastro', label: 'Cadastro Geral', desc: 'Permite criar novos registros no sistema' },
  { chave: 'p_edicao', label: 'Edição de Dados', desc: 'Permite editar registros e cadastros existentes' },
  { chave: 'p_vendas', label: 'Vendas & Licenças', desc: 'Acesso a checkout, pedidos e compra de licenças' },
  { chave: 'p_matriculas', label: 'Matrículas', desc: 'Efetuar e regularizar matrículas de discentes' },
  { chave: 'p_financeiro', label: 'Financeiro & Asaas', desc: 'Consulta a faturamentos, boletos e transações' },
  { chave: 'p_academico', label: 'Gestão Acadêmica', desc: 'Controle de turmas, matrizes, notas e frequência' },
  { chave: 'p_chat', label: 'Chat & Mensagens', desc: 'Comunicação interna e mensagens diretas' },
  { chave: 'p_ranking', label: 'Ranking & Metas', desc: 'Visualização de métricas e ranking comercial' },
];

export const UsuariosInternosPage: React.FC = () => {
  const { user: loggedAdmin } = useAuthStore();

  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPerfil, setSelectedPerfil] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // Modais
  const [isCreateEditOpen, setIsCreateEditOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UsuarioAdmin | null>(null);
  const [isResetPasswordOpen, setIsResetPasswordOpen] = useState(false);
  const [resetTargetUser, setResetTargetUser] = useState<UsuarioAdmin | null>(null);
  const [newPassword, setNewPassword] = useState('');

  // Estados de formulário
  const [formData, setFormData] = useState({
    nome: '',
    sobrenome: '',
    email: '',
    cpf: '',
    senha: '',
    perfil_nome: 'admin',
    status: 'ativo',
    telefone: '',
    celular: '',
    permissoes: [] as string[],
  });

  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [usersRes] = await Promise.all([
        adminApi.listUsuarios({
          q: searchTerm || undefined,
          perfil: selectedPerfil || undefined,
          status: selectedStatus || undefined,
          limit: 100,
        }),
      ]);

      setUsuarios(usersRes.items || []);
      setTotal(usersRes.total || 0);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao carregar usuários administrativos.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [searchTerm, selectedPerfil, selectedStatus]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingUser(null);
    setFormData({
      nome: '',
      sobrenome: '',
      email: '',
      cpf: '',
      senha: '',
      perfil_nome: 'admin',
      status: 'ativo',
      telefone: '',
      celular: '',
      permissoes: ['p_cadastro', 'p_edicao', 'p_matriculas', 'p_academico', 'p_chat'],
    });
    setIsCreateEditOpen(true);
  };

  const handleOpenEdit = (u: UsuarioAdmin) => {
    setEditingUser(u);
    setFormData({
      nome: u.nome,
      sobrenome: u.sobrenome || '',
      email: u.email || '',
      cpf: u.cpf || '',
      senha: '',
      perfil_nome: u.perfil_nome || 'admin',
      status: u.status || 'ativo',
      telefone: u.telefone || '',
      celular: u.celular || '',
      permissoes: u.permissoes || [],
    });
    setIsCreateEditOpen(true);
  };

  const handleTogglePermission = (chave: string) => {
    setFormData((prev) => {
      const exists = prev.permissoes.includes(chave);
      if (exists) {
        return { ...prev, permissoes: prev.permissoes.filter((p) => p !== chave) };
      } else {
        return { ...prev, permissoes: [...prev.permissoes, chave] };
      }
    });
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setFeedback(null);

    try {
      if (editingUser) {
        // Atualiza usuário existente
        await adminApi.updateUsuario(editingUser.id, {
          nome: formData.nome,
          sobrenome: formData.sobrenome,
          email: formData.email,
          cpf: formData.cpf,
          perfil_nome: formData.perfil_nome,
          status: formData.status,
          telefone: formData.telefone,
          celular: formData.celular,
          permissoes: formData.permissoes,
        });
        setFeedback({ type: 'success', message: `Usuário ${formData.nome} atualizado com sucesso!` });
      } else {
        // Cria novo usuário
        if (!formData.senha || formData.senha.length < 6) {
          setFeedback({ type: 'error', message: 'A senha inicial deve possuir no mínimo 6 caracteres.' });
          setIsSaving(false);
          return;
        }

        await adminApi.createUsuario({
          nome: formData.nome,
          sobrenome: formData.sobrenome,
          email: formData.email,
          cpf: formData.cpf,
          senha: formData.senha,
          perfil_nome: formData.perfil_nome,
          status: formData.status,
          telefone: formData.telefone,
          celular: formData.celular,
          permissoes: formData.permissoes,
        });
        setFeedback({ type: 'success', message: `Novo usuário ${formData.nome} cadastrado com sucesso!` });
      }

      setIsCreateEditOpen(false);
      loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Ocorreu um erro ao salvar o usuário.',
      });
    } finally {
      setIsSaving(false);
    }
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
        message: `Senha do usuário ${resetTargetUser.nome} redefinida com sucesso para Argon2id!`,
      });
      setIsResetPasswordOpen(false);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao redefinir a senha.',
      });
    }
  };

  const handleDeleteUser = async (u: UsuarioAdmin) => {
    if (loggedAdmin?.id === u.id) {
      setFeedback({ type: 'error', message: 'Você não pode excluir o seu próprio usuário administrador.' });
      return;
    }

    if (
      !window.confirm(
        `Tem certeza que deseja excluir o usuário "${u.nome} ${u.sobrenome || ''}" (${u.email})? Esta ação será registrada em auditoria.`
      )
    ) {
      return;
    }

    try {
      await adminApi.deleteUsuario(u.id);
      setFeedback({ type: 'success', message: `Usuário ${u.nome} excluído com sucesso.` });
      loadData();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao excluir usuário.',
      });
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
            Usuários Administrativos & Staff
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Gerencie colaboradores da Secretaria, Coordenação Pedagógica e Diretoria com controle granular de acesso.
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
            placeholder="Buscar por nome, email ou CPF..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow transition-colors"
          />
        </div>

        <div className="w-full md:w-auto flex items-center gap-2.5 overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Perfil:</span>
          </div>
          <select
            value={selectedPerfil}
            onChange={(e) => setSelectedPerfil(e.target.value)}
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
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
          >
            <option value="">Todos os status</option>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
            <option value="bloqueado">Bloqueado</option>
          </select>

          <button
            onClick={loadData}
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
                <th className="py-3.5 px-4">Perfil</th>
                <th className="py-3.5 px-4">Permissões Granulares</th>
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
                  <tr key={u.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-nexus-blue-deep to-nexus-blue flex items-center justify-center text-white font-bold text-xs shrink-0">
                          {u.nome.charAt(0).toUpperCase()}
                        </div>
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
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-nexus-blue/15 border border-nexus-blue/30 text-blue-400">
                        <Shield className="w-3 h-3" />
                        {u.perfil_nome || 'Sem Perfil'}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {u.permissoes && u.permissoes.length > 0 ? (
                          u.permissoes.map((p) => (
                            <span
                              key={p}
                              className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-[10px] text-nexus-yellow font-mono"
                            >
                              {p}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-500 text-[11px]">Básicas do perfil</span>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${getStatusBadge(u.status)}`}>
                        {u.status}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
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
                          onClick={() => handleDeleteUser(u)}
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

        <div className="p-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span>Total: <strong>{total}</strong> usuários cadastrados</span>
          <span>Exibindo até 100 por página</span>
        </div>
      </div>

      {/* Modal de Criação / Edição */}
      {isCreateEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 sm:p-8 animate-fadeIn">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2 text-white font-bold text-lg">
                <Users className="w-5 h-5 text-nexus-yellow" />
                <span>{editingUser ? 'Editar Usuário' : 'Novo Usuário Administrativo'}</span>
              </div>
              <button
                onClick={() => setIsCreateEditOpen(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4 mt-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Nome *</label>
                  <input
                    type="text"
                    required
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                    placeholder="Ex: Fernanda"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Sobrenome</label>
                  <input
                    type="text"
                    value={formData.sobrenome}
                    onChange={(e) => setFormData({ ...formData, sobrenome: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                    placeholder="Ex: Silva (Secretaria)"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">E-mail *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                    placeholder="exemplo@nexus.com.br"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">CPF</label>
                  <input
                    type="text"
                    value={formData.cpf}
                    onChange={(e) => setFormData({ ...formData, cpf: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                    placeholder="000.000.000-00"
                  />
                </div>
              </div>

              {!editingUser && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Senha Inicial (Argon2id) *</label>
                  <input
                    type="password"
                    required
                    value={formData.senha}
                    onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow"
                    placeholder="Mínimo 6 caracteres"
                  />
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Perfil de Acesso</label>
                  <select
                    value={formData.perfil_nome}
                    onChange={(e) => setFormData({ ...formData, perfil_nome: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow capitalize"
                  >
                    <option value="admin">Administrador / Staff Central</option>
                    <option value="polo">Polo Regional</option>
                    <option value="escola">Unidade Escolar</option>
                    <option value="professor">Professor / Docente</option>
                    <option value="aluno">Aluno / Estudante</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Status da Conta</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-nexus-yellow capitalize"
                  >
                    <option value="ativo">Ativo</option>
                    <option value="inativo">Inativo</option>
                    <option value="bloqueado">Bloqueado</option>
                  </select>
                </div>
              </div>

              {/* Checkboxes de Permissões Granulares */}
              <div className="pt-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-nexus-yellow mb-2">
                  Permissões Granulares (Campos Legado p_*)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  {AVAILABLE_PERMISSIONS.map((p) => {
                    const isChecked = formData.permissoes.includes(p.chave);
                    return (
                      <div
                        key={p.chave}
                        onClick={() => handleTogglePermission(p.chave)}
                        className={`flex items-start gap-2.5 p-2 rounded-lg cursor-pointer transition-all ${
                          isChecked
                            ? 'bg-nexus-yellow/10 border border-nexus-yellow/30'
                            : 'hover:bg-slate-900 border border-transparent'
                        }`}
                      >
                        <div
                          className={`w-4 h-4 mt-0.5 rounded flex items-center justify-center shrink-0 border ${
                            isChecked
                              ? 'bg-nexus-yellow border-nexus-yellow text-slate-950'
                              : 'border-slate-700 bg-slate-900'
                          }`}
                        >
                          {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-white leading-tight">{p.label}</p>
                          <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">{p.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateEditOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2.5 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-xs rounded-xl shadow-lg transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{editingUser ? 'Salvar Alterações' : 'Cadastrar Usuário'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
                Você está alterando administrativamente a senha de <strong>{resetTargetUser.nome}</strong> ({resetTargetUser.email}). A nova senha será criptografada em <strong>Argon2id</strong>.
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
    </div>
  );
};
