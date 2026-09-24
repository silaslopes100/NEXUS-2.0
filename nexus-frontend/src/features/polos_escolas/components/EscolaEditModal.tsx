import React, { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { adminApi } from '@/features/admin/api';
import { EscolaItem, EscolaUpdatePayload, EnderecoCompleto, PoloItem } from '@/types/polos';
import { UsuarioAdmin } from '@/types/admin';

interface EscolaEditModalProps {
  escola: EscolaItem;
  polos: PoloItem[]; // para permitir alterar o polo vinculado
  onClose: () => void;
  onSuccess: () => void;
}

const emptyAddress: EnderecoCompleto = {
  logradouro: '',
  numero: '',
  bairro: '',
  cidade: '',
  estado: 'SP',
  cep: '',
};

export const EscolaEditModal: React.FC<EscolaEditModalProps> = ({ escola, polos, onClose, onSuccess }) => {
  const [form, setForm] = useState<EscolaUpdatePayload>({
    polo_id: escola.polo_id,
    nome: escola.nome,
    endereco: escola.endereco || emptyAddress,
    secretario_id: escola.secretario_id || '',
    secretario_nome: escola.secretario_nome || '',
    secretario_email: escola.secretario_email || '',
    secretario_cpf: '',
    secretario_senha: '',
    status: escola.status,
  });

  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([]);
  const [loadingUsuarios, setLoadingUsuarios] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    const fetchUsuarios = async () => {
      setLoadingUsuarios(true);
      try {
        const response = await adminApi.listUsuarios({ perfil: 'Escola', limit: 100 });
        setUsuarios(response.items);
      } catch (error) {
        console.error('Erro ao buscar usuários:', error);
      } finally {
        setLoadingUsuarios(false);
      }
    };
    fetchUsuarios();
  }, []);

  const handleChange = (field: keyof EscolaUpdatePayload, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddressChange = (key: keyof EnderecoCompleto, value: string) => {
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
      await polosEscolasApi.updateEscola(escola.id, form);
      onSuccess();
      onClose();
    } catch (error: any) {
      setFeedback(error.response?.data?.detail || 'Erro ao atualizar escola.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Editar Escola</h2>
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
            <label className="mb-1 block text-sm font-medium text-slate-300">Polo Vinculado</label>
            <select
              value={form.polo_id || ''}
              onChange={(e) => handleChange('polo_id', e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              required
            >
              <option value="">Selecione um polo</option>
              {polos.map((polo) => (
                <option key={polo.id} value={polo.id}>
                  {polo.nome}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-300">Nome da Escola</label>
            <input
              type="text"
              value={form.nome || ''}
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
                  value={form.endereco?.[key] || ''}
                  onChange={(e) => handleAddressChange(key, e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
            ))}
          </div>

          <div className="border-t border-slate-800 pt-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">Secretário Responsável</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="mb-1 block text-sm font-medium text-slate-300">Vincular Usuário Existente</label>
                <select
                  value={form.secretario_id || ''}
                  onChange={(e) => {
                    const userId = e.target.value;
                    const user = usuarios.find((u) => u.id === userId);
                    setForm((prev) => ({
                      ...prev,
                      secretario_id: userId,
                      secretario_nome: user?.nome || '',
                      secretario_email: user?.email || '',
                    }));
                  }}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                  disabled={loadingUsuarios}
                >
                  <option value="">Selecione um usuário cadastrado como Escola</option>
                  {usuarios.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.nome} {user.sobrenome} ({user.email})
                    </option>
                  ))}
                </select>
                {loadingUsuarios && <p className="mt-1 text-xs text-slate-500">Carregando usuários...</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Nome do Secretário</label>
                <input
                  type="text"
                  value={form.secretario_nome || ''}
                  onChange={(e) => handleChange('secretario_nome', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">E-mail do Secretário</label>
                <input
                  type="email"
                  value={form.secretario_email || ''}
                  onChange={(e) => handleChange('secretario_email', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">CPF do Secretário</label>
                <input
                  type="text"
                  value={form.secretario_cpf || ''}
                  onChange={(e) => handleChange('secretario_cpf', e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Nova Senha (opcional)</label>
                <input
                  type="password"
                  value={form.secretario_senha || ''}
                  onChange={(e) => handleChange('secretario_senha', e.target.value)}
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