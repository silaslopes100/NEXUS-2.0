import React, { useEffect, useMemo, useState } from 'react';
import {
  UserPlus,
  Users,
  X,
  Loader2,
  Check,
  ShieldCheck,
  KeyRound,
  RefreshCw,
  Lock,
  Link2,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { UsuarioAdmin } from '@/types/admin';
import { PoloItem, EscolaItem } from '@/types/polos';

const inputCls =
  'w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow transition-colors';

const PERFIS_FALLBACK = [
  { value: 'admin', label: 'Administrador / Staff Central' },
  { value: 'polo', label: 'Polo Regional' },
  { value: 'escola', label: 'Unidade Escolar' },
  { value: 'professor', label: 'Professor / Docente' },
  { value: 'aluno', label: 'Aluno / Estudante' },
];

const PERMISSOES_LABELS: Record<string, { label: string; desc: string }> = {
  p_cadastro: { label: 'Cadastro Geral', desc: 'Permite criar novos registros no sistema' },
  p_edicao: { label: 'Edição de Dados', desc: 'Permite editar registros e cadastros existentes' },
  p_vendas: { label: 'Vendas & Licenças', desc: 'Acesso a checkout, pedidos e compra de licenças' },
  p_matriculas: { label: 'Matrículas', desc: 'Efetuar e regularizar matrículas de discentes' },
  p_financeiro: { label: 'Financeiro & Asaas', desc: 'Consulta a faturamentos, boletos e transações' },
  p_academico: { label: 'Gestão Acadêmica', desc: 'Controle de turmas, matrizes, notas e frequência' },
  p_chat: { label: 'Chat & Mensagens', desc: 'Comunicação interna e mensagens diretas' },
  p_ranking: { label: 'Ranking & Metas', desc: 'Visualização de métricas e ranking comercial' },
};

const DEFAULT_PERMISSOES = ['p_cadastro', 'p_edicao', 'p_matriculas', 'p_academico', 'p_chat'];

function mascaraCpf(valor: string): string {
  const d = valor.replace(/\D/g, '').slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d{1,2})$/, '.$1-$2');
}

function gerarSenhaForte(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789@#%&*';
  const arr = new Uint32Array(12);
  crypto.getRandomValues(arr);
  return Array.from(arr, (n) => chars[n % chars.length]).join('');
}

interface UsuarioFormModalProps {
  open: boolean;
  editingUser: UsuarioAdmin | null;
  onClose: () => void;
  onSaved: (message: string) => void;
}

export const UsuarioFormModal: React.FC<UsuarioFormModalProps> = ({
  open,
  editingUser,
  onClose,
  onSaved,
}) => {
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
    polo_id: '',
    escola_id: '',
    permissoes: [] as string[],
  });

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [perfis, setPerfis] = useState<{ value: string; label: string }[]>(PERFIS_FALLBACK);
  const [permissoesDisponiveis, setPermissoesDisponiveis] = useState<string[]>(
    Object.keys(PERMISSOES_LABELS)
  );
  const [polos, setPolos] = useState<PoloItem[]>([]);
  const [escolas, setEscolas] = useState<EscolaItem[]>([]);
  const [isLoadingDependencias, setIsLoadingDependencias] = useState(false);

  // Preenche o formulário ao abrir (criação ou edição)
  useEffect(() => {
    if (!open) return;
    setError(null);
    if (editingUser) {
      setFormData({
        nome: editingUser.nome || '',
        sobrenome: editingUser.sobrenome || '',
        email: editingUser.email || '',
        cpf: mascaraCpf(editingUser.cpf || ''),
        senha: '',
        perfil_nome: editingUser.perfil_nome || 'admin',
        status: editingUser.status || 'ativo',
        telefone: editingUser.telefone || '',
        celular: editingUser.celular || '',
        polo_id: editingUser.polo_id || '',
        escola_id: editingUser.escola_id || '',
        permissoes: editingUser.permissoes || [],
      });
    } else {
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
        polo_id: '',
        escola_id: '',
        permissoes: [...DEFAULT_PERMISSOES],
      });
    }
  }, [open, editingUser]);

  // Carrega perfis, permissões e polos
  useEffect(() => {
    if (!open) return;
    let mounted = true;
    (async () => {
      try {
        const [perfisRes, permsRes, polosRes] = await Promise.all([
          adminApi.listPerfis().catch(() => null),
          adminApi.listPermissoes().catch(() => null),
          polosEscolasApi.listarPolos({ limit: 200 }).catch(() => null),
        ]);
        if (!mounted) return;
        if (perfisRes && perfisRes.length > 0) {
          setPerfis(perfisRes.map((p) => ({ value: p.nome, label: p.nome.charAt(0).toUpperCase() + p.nome.slice(1) })));
        }
        if (permsRes && permsRes.length > 0) {
          setPermissoesDisponiveis(permsRes.map((p) => p.chave));
        }
        if (polosRes?.items) {
          setPolos(polosRes.items);
        }
      } catch {
        // mantém fallbacks
      }
    })();
    return () => {
      mounted = false;
    };
  }, [open]);

  // Carrega escolas do polo selecionado
  useEffect(() => {
    if (!open || !formData.polo_id) {
      setEscolas([]);
      return;
    }
    let mounted = true;
    setIsLoadingDependencias(true);
    polosEscolasApi
      .listarEscolasDoPolo(formData.polo_id)
      .then((res) => {
        if (mounted && res?.items) setEscolas(res.items);
      })
      .catch(() => {
        if (mounted) setEscolas([]);
      })
      .finally(() => {
        if (mounted) setIsLoadingDependencias(false);
      });
    return () => {
      mounted = false;
    };
  }, [open, formData.polo_id]);

  const permissoesOrdenadas = useMemo(
    () => [...permissoesDisponiveis].sort(),
    [permissoesDisponiveis]
  );

  const handleTogglePermission = (chave: string) => {
    setFormData((prev) => ({
      ...prev,
      permissoes: prev.permissoes.includes(chave)
        ? prev.permissoes.filter((p) => p !== chave)
        : [...prev.permissoes, chave],
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    const cpfDigits = formData.cpf.replace(/\D/g, '');

    try {
      if (editingUser) {
        await adminApi.updateUsuario(editingUser.id, {
          nome: formData.nome,
          sobrenome: formData.sobrenome,
          email: formData.email,
          cpf: cpfDigits || undefined,
          perfil_nome: formData.perfil_nome,
          status: formData.status,
          telefone: formData.telefone || undefined,
          celular: formData.celular || undefined,
          polo_id: formData.polo_id,
          escola_id: formData.escola_id,
          permissoes: formData.permissoes,
        });
        onSaved(`Usuário ${formData.nome} atualizado com sucesso!`);
      } else {
        if (!formData.senha || formData.senha.length < 6) {
          setError('A senha inicial deve possuir no mínimo 6 caracteres.');
          setIsSaving(false);
          return;
        }
        await adminApi.createUsuario({
          nome: formData.nome,
          sobrenome: formData.sobrenome,
          email: formData.email,
          cpf: cpfDigits || undefined,
          senha: formData.senha,
          perfil_nome: formData.perfil_nome,
          status: formData.status,
          telefone: formData.telefone || undefined,
          celular: formData.celular || undefined,
          polo_id: formData.polo_id || undefined,
          escola_id: formData.escola_id || undefined,
          permissoes: formData.permissoes,
        });
        onSaved(`Novo usuário ${formData.nome} cadastrado com sucesso!`);
      }
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ocorreu um erro ao salvar o usuário.');
    } finally {
      setIsSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl animate-fadeIn my-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 pb-4 border-b border-slate-800 sticky top-0 bg-slate-900 rounded-t-2xl z-10">
          <div className="flex items-center gap-2 text-white font-bold text-lg">
            {editingUser ? (
              <Users className="w-5 h-5 text-nexus-yellow" />
            ) : (
              <UserPlus className="w-5 h-5 text-nexus-yellow" />
            )}
            <span>{editingUser ? 'Editar Usuário' : 'Cadastro de Usuário'}</span>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="flex flex-col">
          <div className="p-6 space-y-6 overflow-y-auto">
            {error && (
              <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/15 text-red-200 text-xs animate-fadeIn">
                {error}
              </div>
            )}

            {/* Seção 1: Dados Pessoais */}
            <section>
              <h3 className="text-xs font-bold uppercase tracking-wider text-nexus-yellow mb-3 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" />
                Dados Pessoais
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Nome Completo *</label>
                  <input
                    type="text"
                    required
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    className={inputCls}
                    placeholder="Ex: Fernanda"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Sobrenome</label>
                  <input
                    type="text"
                    value={formData.sobrenome}
                    onChange={(e) => setFormData({ ...formData, sobrenome: e.target.value })}
                    className={inputCls}
                    placeholder="Ex: Silva"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">E-mail *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className={inputCls}
                    placeholder="exemplo@nexus.com.br"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">CPF</label>
                  <input
                    type="text"
                    value={formData.cpf}
                    onChange={(e) => setFormData({ ...formData, cpf: mascaraCpf(e.target.value) })}
                    className={inputCls}
                    placeholder="000.000.000-00"
                    maxLength={14}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Telefone</label>
                  <input
                    type="tel"
                    value={formData.telefone}
                    onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                    className={inputCls}
                    placeholder="(00) 0000-0000"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Celular</label>
                  <input
                    type="tel"
                    value={formData.celular}
                    onChange={(e) => setFormData({ ...formData, celular: e.target.value })}
                    className={inputCls}
                    placeholder="(00) 00000-0000"
                  />
                </div>
              </div>
            </section>

            {/* Seção 2: Perfil de Acesso */}
            <section>
              <h3 className="text-xs font-bold uppercase tracking-wider text-nexus-yellow mb-3 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                Perfil de Acesso
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Perfil</label>
                  <select
                    value={formData.perfil_nome}
                    onChange={(e) => setFormData({ ...formData, perfil_nome: e.target.value })}
                    className={`${inputCls} capitalize`}
                  >
                    {perfis.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Status da Conta</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className={`${inputCls} capitalize`}
                  >
                    <option value="ativo">Ativo</option>
                    <option value="inativo">Inativo</option>
                    <option value="bloqueado">Bloqueado</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300 flex items-center gap-1">
                    <Link2 className="w-3 h-3 text-slate-500" />
                    Polo Vinculado
                  </label>
                  <select
                    value={formData.polo_id}
                    onChange={(e) =>
                      setFormData({ ...formData, polo_id: e.target.value, escola_id: '' })
                    }
                    className={inputCls}
                  >
                    <option value="">Sem polo vinculado</option>
                    {polos.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.nome}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Escola Vinculada</label>
                  <select
                    value={formData.escola_id}
                    onChange={(e) => setFormData({ ...formData, escola_id: e.target.value })}
                    disabled={!formData.polo_id || isLoadingDependencias}
                    className={`${inputCls} disabled:opacity-50`}
                  >
                    <option value="">
                      {isLoadingDependencias
                        ? 'Carregando escolas...'
                        : formData.polo_id
                          ? 'Selecione a escola'
                          : 'Selecione um polo primeiro'}
                    </option>
                    {escolas.map((es) => (
                      <option key={es.id} value={es.id}>
                        {es.nome}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            {/* Seção 3: Segurança */}
            <section>
              <h3 className="text-xs font-bold uppercase tracking-wider text-nexus-yellow mb-3 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5" />
                Segurança
              </h3>
              <div className="space-y-4">
                {!editingUser && (
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-300">
                      Senha Inicial (Argon2id) *
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        required
                        value={formData.senha}
                        onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                        className={inputCls}
                        placeholder="Mínimo 6 caracteres"
                      />
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, senha: gerarSenhaForte() })}
                        className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl transition-colors flex items-center gap-1.5 shrink-0"
                        title="Gerar senha forte automaticamente"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Gerar
                      </button>
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Permissões Granulares
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                    {permissoesOrdenadas.map((chave) => {
                      const meta = PERMISSOES_LABELS[chave];
                      const label = meta?.label ?? chave;
                      const desc = meta?.desc ?? 'Permissão granular do sistema';
                      const isChecked = formData.permissoes.includes(chave);
                      return (
                        <div
                          key={chave}
                          onClick={() => handleTogglePermission(chave)}
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
                            <p className="text-xs font-semibold text-white leading-tight">{label}</p>
                            <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">{desc}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Footer sticky */}
          <div className="p-4 sm:p-6 pt-4 flex items-center justify-end gap-3 border-t border-slate-800 sticky bottom-0 bg-slate-900 rounded-b-2xl">
            <button
              type="button"
              onClick={onClose}
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
              <span>
                {editingUser ? (
                  'Salvar Alterações'
                ) : (
                  <>
                    <KeyRound className="w-3.5 h-3.5 inline -mt-0.5 mr-1" />
                    Cadastrar Usuário
                  </>
                )}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
