import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';

interface EnderecoSchema {
  logradouro?: string;
  numero?: string;
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
    coordenador_nome: polo.coordenador_nome || '',
    coordenador_email: polo.coordenador_email || '',
    coordenador_cpf: '',
    coordenador_senha: '',
  });

  const [usuarios, setUsuarios] = useState<UsuarioVinculavel[]>([]);
  const [loadingUsuarios, setLoadingUsuarios] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    const fetchUsuarios = async () => {
      setLoadingUsuarios(true);
      try {
        const resp = await polosEscolasApi.listarUsuariosVinculaveis({
          perfil: 'coordenador_polo',
          limit: 200,
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
      if (form.coordenador_nome) payload.coordenador_nome = form.coordenador_nome;
      if (form.coordenador_email) payload.coordenador_email = form.coordenador_email;
      if (form.coordenador_cpf) payload.coordenador_cpf = form.coordenador_cpf;
      if (form.coordenador_senha) payload.coordenador_senha = form.coordenador_senha;

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
            {(['logradouro', 'numero', 'bairro', 'cidade', 'estado', 'cep'] as const).map((key) => (
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
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="mb-1 block text-sm font-medium text-slate-300">
                  Vincular Usuário Existente
                </label>
                <select
                  value={form.coordenador_usuario_id}
                  onChange={(e) => {
                    const userId = e.target.value;
                    const user = usuarios.find((u) => u.id === userId);
                    setForm((prev) => ({
                      ...prev,
                      coordenador_usuario_id: userId,
                      coordenador_nome: user?.nome || prev.coordenador_nome,
                      coordenador_email: user?.email || prev.coordenador_email,
                    }));
                  }}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  disabled={loadingUsuarios}
                >
                  <option value="">Selecione um usuário (coordenador_polo)</option>
                  {usuarios.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.nome} {user.sobrenome} ({user.email})
                    </option>
                  ))}
                </select>
                {loadingUsuarios && <p className="mt-1 text-xs text-slate-500">Carregando usuários...</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Nome do Coordenador</label>
                <input
                  type="text"
                  value={form.coordenador_nome}
                  onChange={(e) => handleChange('coordenador_nome', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">E-mail do Coordenador</label>
                <input
                  type="email"
                  value={form.coordenador_email}
                  onChange={(e) => handleChange('coordenador_email', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">CPF do Coordenador</label>
                <input
                  type="text"
                  value={form.coordenador_cpf}
                  onChange={(e) => handleChange('coordenador_cpf', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Nova Senha (opcional)</label>
                <input
                  type="password"
                  value={form.coordenador_senha}
                  onChange={(e) => handleChange('coordenador_senha', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  placeholder="Deixe em branco para manter"
                />
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