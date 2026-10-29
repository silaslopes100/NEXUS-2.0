import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';

interface EnderecoSchema {
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
}

export interface PoloItem {
  id: string;
  nome: string;
  endereco: EnderecoSchema;
  status: string;
  coordenador_id?: string | null;
  coordenador_nome?: string | null;
  coordenador_cpf?: string | null;
  coordenador_email?: string | null;
}

interface UsuarioVinculavel {
  id: string;
  nome: string;
  sobrenome?: string;
  email?: string;
  cpf?: string;
  perfil_nome?: string;
}

interface PoloEditModalProps {
  polo: PoloItem;
  onClose: () => void;
  onSuccess: () => void;
}

const emptyAddress: EnderecoSchema = {
  logradouro: '',
  numero: '',
  complemento: '',
  bairro: '',
  cidade: '',
  estado: '',
  cep: '',
};

export const PoloEditModal: React.FC<PoloEditModalProps> = ({ polo, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    nome: polo.nome || '',
    endereco: polo.endereco || emptyAddress,
    status: polo.status || 'ativo',
    coordenador_usuario_id: polo.coordenador_id || '',
  });

  const [usuarios, setUsuarios] = useState<UsuarioVinculavel[]>([]);
  const [loadingUsuarios, setLoadingUsuarios] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [buscaUsuario, setBuscaUsuario] = useState('');

  const usuariosFiltrados = React.useMemo(() => {
    if (!buscaUsuario.trim()) return usuarios;
    const termo = buscaUsuario.toLowerCase();
    return usuarios.filter(u =>
      u.nome.toLowerCase().includes(termo) ||
      (u.sobrenome || '').toLowerCase().includes(termo) ||
      (u.email || '').toLowerCase().includes(termo) ||
      (u.cpf || '').includes(termo)
    );
  }, [usuarios, buscaUsuario]);

  useEffect(() => {
    const fetchUsuarios = async () => {
      setLoadingUsuarios(true);
      try {
        const resp = await polosEscolasApi.listarUsuariosVinculaveis({
          limit: 500,
        });
        setUsuarios(resp.items || []);
      } catch (err) {
        console.error('Erro ao listar usuários:', err);
      } finally {
        setLoadingUsuarios(false);
      }
    };
    fetchUsuarios();
  }, []);

  const handleChange = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddressChange = (key: keyof EnderecoSchema, value: string) => {
    setForm((prev) => ({
      ...prev,
      endereco: { ...prev.endereco, [key]: value },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFeedback('');
    try {
      const payload: any = {
        nome: form.nome,
        endereco: form.endereco,
        status: form.status,
      };
      if (form.coordenador_usuario_id) {
        payload.coordenador_usuario_id = form.coordenador_usuario_id;
      }

      await polosEscolasApi.atualizarPolo(polo.id, payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      setFeedback(err.response?.data?.detail || 'Erro ao atualizar polo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Editar Polo</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        {feedback && (
          <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
            {feedback}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-300">Nome do Polo</label>
            <input
              type="text"
              value={form.nome}
              onChange={(e) => handleChange('nome', e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {(['logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep'] as const).map((key) => (
              <div key={key}>
                <label className="mb-1 block text-sm font-medium text-slate-300 capitalize">{key}</label>
                <input
                  type="text"
                  value={form.endereco[key] || ''}
                  onChange={(e) => handleAddressChange(key, e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Status</label>
              <select
                value={form.status}
                onChange={(e) => handleChange('status', e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              >
                <option value="ativo">Ativo</option>
                <option value="inativo">Inativo</option>
              </select>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">Coordenador Responsável</h3>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Vincular Usuário Existente</label>
                <input
                  type="text"
                  placeholder="Buscar por nome, e-mail ou CPF..."
                  value={buscaUsuario}
                  onChange={(e) => setBuscaUsuario(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  disabled={loadingUsuarios}
                />
                <select
                  value={form.coordenador_usuario_id}
                  onChange={(e) => {
                    const userId = e.target.value;
                    setForm((prev) => ({ ...prev, coordenador_usuario_id: userId }));
                  }}
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  disabled={loadingUsuarios}
                  size={Math.min(usuariosFiltrados.length + 1, 8)}
                >
                  <option value="">
                    {loadingUsuarios ? 'Carregando usuários...' : 'Selecione um usuário'}
                  </option>
                  {usuariosFiltrados.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.nome} {user.sobrenome} — {user.email || 'sem e-mail'}{user.perfil_nome ? ` (${user.perfil_nome})` : ''}
                    </option>
                  ))}
                </select>
                {buscaUsuario && usuariosFiltrados.length === 0 && !loadingUsuarios && (
                  <p className="mt-2 text-xs text-slate-500">Nenhum usuário encontrado para "{buscaUsuario}".</p>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {saving ? <Loader2 className="animate-spin" size={16} /> : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};