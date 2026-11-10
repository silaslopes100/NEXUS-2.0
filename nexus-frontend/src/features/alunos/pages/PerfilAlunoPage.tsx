import React, { useCallback, useEffect, useRef, useState } from 'react';
import { CheckCircle2, ImagePlus, Loader2, Save, Upload, UserRound } from 'lucide-react';
import { apiErrorMessage } from '@/features/alunos/api';
import { perfilAlunoApi, PerfilAluno } from '@/features/alunos/profileApi';
import {
  formatCep,
  formatPhone,
  onlyDigits,
  perfilAlunoSchema,
  PerfilAlunoForm,
} from '@/features/alunos/profileSchema';
import { lookupAddressByCep } from '@/features/alunos/viacep';
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
    telefone: formatPhone(perfil.telefone || ''),
    celular: formatPhone(perfil.celular || ''),
    cep: formatCep(perfil.endereco.cep || ''),
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
  const [selectedPhoto, setSelectedPhoto] = useState<File | null>(null);
  const [selectedPhotoUrl, setSelectedPhotoUrl] = useState<string | null>(null);
  const [savedPhotoUrl, setSavedPhotoUrl] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState('');
  const [photoSuccess, setPhotoSuccess] = useState('');
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [cepLookup, setCepLookup] = useState<{
    status: 'idle' | 'loading' | 'success' | 'error';
    message: string;
  }>({ status: 'idle', message: '' });
  const cepLookupController = useRef<AbortController | null>(null);
  const cepLookupRequest = useRef(0);

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

  useEffect(
    () => () => {
      cepLookupController.current?.abort();
    },
    []
  );

  useEffect(() => {
    if (!selectedPhoto) {
      setSelectedPhotoUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(selectedPhoto);
    setSelectedPhotoUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedPhoto]);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setSavedPhotoUrl(null);
    if (!perfil?.foto_url) {
      return () => {
        active = false;
      };
    }

    perfilAlunoApi
      .getFoto(perfil.foto_url)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setSavedPhotoUrl(objectUrl);
      })
      .catch((err: unknown) => {
        if (active) {
          setPhotoError(apiErrorMessage(err, 'Não foi possível carregar a foto atual.'));
        }
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [perfil?.foto_url]);

  const handleChange = (field: keyof PerfilAlunoForm, value: string) => {
    const formattedValue = field === 'telefone' || field === 'celular'
      ? formatPhone(value)
      : field === 'cep'
        ? formatCep(value)
        : value;
    setForm((current) => ({ ...current, [field]: formattedValue }));
    setSuccess('');
    setValidationError('');

    if (field !== 'cep') return;

    const requestId = ++cepLookupRequest.current;
    cepLookupController.current?.abort();
    cepLookupController.current = null;
    setCepLookup({ status: 'idle', message: '' });

    const cep = onlyDigits(formattedValue);
    if (cep.length !== 8) return;

    const controller = new AbortController();
    cepLookupController.current = controller;
    setCepLookup({ status: 'loading', message: 'Consultando CEP...' });

    void lookupAddressByCep(cep, controller.signal)
      .then((address) => {
        if (controller.signal.aborted || requestId !== cepLookupRequest.current) return;
        setForm((current) => {
          if (onlyDigits(current.cep) !== cep) return current;
          return {
            ...current,
            logradouro: address.logradouro,
            bairro: address.bairro,
            cidade: address.cidade,
            uf: address.uf,
          };
        });
        setCepLookup({
          status: 'success',
          message: 'Endereço preenchido pelo ViaCEP. Informe o número e o complemento.',
        });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted || requestId !== cepLookupRequest.current) return;
        setCepLookup({
          status: 'error',
          message: err instanceof Error
            ? err.message
            : 'Não foi possível consultar o ViaCEP. Preencha o endereço manualmente.',
        });
      })
      .finally(() => {
        if (requestId === cepLookupRequest.current) {
          cepLookupController.current = null;
        }
      });
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

  const handlePhotoSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    event.target.value = '';
    setPhotoError('');
    setPhotoSuccess('');
    if (!file) return;

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setSelectedPhoto(null);
      setPhotoError('Escolha uma imagem JPEG, PNG ou WebP.');
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      setSelectedPhoto(null);
      setPhotoError('A imagem deve ter no máximo 4 MB.');
      return;
    }
    setSelectedPhoto(file);
  };

  const handlePhotoUpload = async () => {
    if (!selectedPhoto || !perfil) return;
    setUploadingPhoto(true);
    setPhotoError('');
    setPhotoSuccess('');
    try {
      const result = await perfilAlunoApi.uploadFoto(selectedPhoto);
      setPerfil({ ...perfil, foto_url: result.foto_url });
      if (user) {
        setUser({ ...user, foto_url: result.foto_url });
      }
      setSelectedPhoto(null);
      setPhotoSuccess('Foto de perfil atualizada.');
    } catch (err) {
      setPhotoError(apiErrorMessage(err, 'Não foi possível enviar a foto.'));
    } finally {
      setUploadingPhoto(false);
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
        type={name === 'email' ? 'email' : name === 'telefone' || name === 'celular' ? 'tel' : 'text'}
        inputMode={name === 'telefone' || name === 'celular' || name === 'cep' ? 'numeric' : undefined}
        value={form[name]}
        required={options?.required}
        autoComplete={options?.autoComplete}
        maxLength={
          name === 'telefone' || name === 'celular'
            ? 18
            : name === 'cep'
              ? 9
              : name === 'uf'
                ? 2
                : undefined
        }
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
        <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-700 bg-slate-950 text-sky-300">
          {selectedPhotoUrl || savedPhotoUrl ? (
            <img
              src={selectedPhotoUrl || savedPhotoUrl || ''}
              alt="Foto de perfil"
              className="h-full w-full object-cover"
            />
          ) : (
            <UserRound className="h-8 w-8" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-white">{[perfil.nome, perfil.sobrenome].filter(Boolean).join(' ')}</p>
          <p className="mt-1 text-xs text-slate-400">Foto de perfil · JPEG, PNG ou WebP · máximo 4 MB</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800">
              <ImagePlus className="h-4 w-4" />
              Escolher imagem
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                disabled={uploadingPhoto}
                onChange={handlePhotoSelection}
              />
            </label>
            {selectedPhoto && (
              <button
                type="button"
                onClick={() => void handlePhotoUpload()}
                disabled={uploadingPhoto}
                className="inline-flex items-center gap-2 rounded-lg bg-nexus-yellow px-3 py-2 text-xs font-bold text-slate-950 hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {uploadingPhoto ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                {uploadingPhoto ? 'Enviando...' : 'Enviar foto'}
              </button>
            )}
          </div>
          {(photoError || photoSuccess) && (
            <p
              role={photoError ? 'alert' : 'status'}
              className={`mt-2 text-xs ${photoError ? 'text-red-300' : 'text-emerald-300'}`}
            >
              {photoError || photoSuccess}
            </p>
          )}
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
            <div>
              {field('cep', 'CEP', { autoComplete: 'postal-code' })}
              {cepLookup.message && (
                <p
                  className={`mt-1 text-xs ${
                    cepLookup.status === 'error' ? 'text-red-300' : 'text-slate-400'
                  }`}
                  role={cepLookup.status === 'error' ? 'alert' : 'status'}
                  aria-live="polite"
                >
                  {cepLookup.message}
                </p>
              )}
            </div>
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
