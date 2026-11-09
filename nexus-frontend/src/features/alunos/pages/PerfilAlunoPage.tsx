import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Loader2, Save, UserRound } from 'lucide-react';
import { apiErrorMessage } from '@/features/alunos/api';
import { perfilAlunoApi, PerfilAluno } from '@/features/alunos/profileApi';
import { perfilAlunoSchema, PerfilAlunoForm } from '@/features/alunos/profileSchema';
import { useAuthStore } from '@/stores/authStore';

const emptyForm: PerfilAlunoForm = {
  email: '',
  telefone: '',
  celular: '',
  cep: '',
  logradouro: '',
  numero: '',
  complemento: '',
  bairro: '',
  cidade: '',
  uf: '',
};

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-slate-600 focus:border-nexus-yellow';

function toForm(perfil: PerfilAluno): PerfilAlunoForm {
  return {
    email: perfil.email || '',
    telefone: perfil.telefone || '',
    celular: perfil.celular || '',
    cep: perfil.endereco.cep || '',
    logradouro: perfil.endereco.logradouro || '',
    numero: perfil.endereco.numero || '',
    complemento: perfil.endereco.complemento || '',
    bairro: perfil.endereco.bairro || '',
    cidade: perfil.endereco.cidade || '',
    uf: perfil.endereco.uf || '',
  };
}

export const PerfilAlunoPage: React.FC = () => {
  const { user, setUser } = useAuthStore();
  const [perfil, setPerfil] = useState<PerfilAluno | null>(null);
  const [form, setForm] = useState<PerfilAlunoForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [validationError, setValidationError] = useState('');

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await perfilAlunoApi.get();
      setPerfil(result);
      setForm(toForm(result));
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível carregar seu perfil.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  const handleChange = (field: keyof PerfilAlunoForm, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setSuccess('');
    setValidationError('');
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    const parsed = perfilAlunoSchema.safeParse(form);
    if (!parsed.success) {
      setValidationError(parsed.error.issues[0]?.message || 'Revise os dados informados.');
      return;
    }

    setSaving(true);
    setValidationError('');
    try {
      const updated = await perfilAlunoApi.update(parsed.data);
      setPerfil(updated);
      setForm(toForm(updated));
      if (user) {
        setUser({ ...user, email: updated.email, telefone: updated.telefone, celular: updated.celular });
      }
      setSuccess('Perfil atualizado com sucesso.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível salvar as alterações.'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Loader2 className="mr-3 h-6 w-6 animate-spin text-nexus-yellow" />
        Carregando perfil...
      </div>
    );
  }

  if (!perfil) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <h1 className="text-2xl font-bold text-white">Meu perfil</h1>
        <div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300">
          {error || 'Não foi possível carregar seu perfil.'}
        </div>
        <button
          type="button"
          onClick={() => void loadProfile()}
          className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  const field = (name: keyof PerfilAlunoForm, label: string, options?: { required?: boolean; autoComplete?: string }) => (
    <label className="block space-y-1.5" key={name}>
      <span className="text-xs font-semibold text-slate-300">{label}</span>
      <input
        className={inputClass}
        name={name}
        type={name === 'email' ? 'email' : 'text'}
        value={form[name]}
        required={options?.required}
        autoComplete={options?.autoComplete}
        maxLength={name === 'uf' ? 2 : undefined}
        onChange={(event) => handleChange(name, event.target.value)}
      />
    </label>
  );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Meu perfil</h1>
        <p className="mt-1 text-sm text-slate-400">Consulte seus dados e mantenha seus contatos atualizados.</p>
      </header>

      <section className="flex items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-sky-500/30 bg-sky-500/10 text-sky-300">
          <UserRound className="h-6 w-6" />
        </div>
        <div>
          <p className="font-semibold text-white">{[perfil.nome, perfil.sobrenome].filter(Boolean).join(' ')}</p>
          <p className="text-xs text-slate-400">Dados pessoais e de contato</p>
        </div>
      </section>

      <form onSubmit={handleSubmit} className="space-y-6 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 sm:p-7">
        <section className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Contato</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {field('email', 'E-mail', { required: true, autoComplete: 'email' })}
            {field('telefone', 'Telefone', { autoComplete: 'tel' })}
            {field('celular', 'Celular', { autoComplete: 'tel' })}
          </div>
        </section>

        <section className="space-y-4 border-t border-slate-800 pt-5">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Endereço residencial</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            {field('cep', 'CEP', { autoComplete: 'postal-code' })}
            {field('logradouro', 'Logradouro', { autoComplete: 'address-line1' })}
            {field('numero', 'Número')}
            {field('complemento', 'Complemento', { autoComplete: 'address-line2' })}
            {field('bairro', 'Bairro')}
            {field('cidade', 'Cidade', { autoComplete: 'address-level2' })}
            {field('uf', 'UF', { autoComplete: 'address-level1' })}
          </div>
        </section>

        {(error || validationError) && (
          <div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
            {error || validationError}
          </div>
        )}
        {success && (
          <div role="status" className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-300">
            <CheckCircle2 className="h-4 w-4" />
            {success}
          </div>
        )}

        <div className="flex justify-end border-t border-slate-800 pt-5">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-slate-950 transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saving ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </div>
      </form>
    </div>
  );
};
