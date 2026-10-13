import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, X } from 'lucide-react';
import { alunosApi, apiErrorMessage, AlunoItem, EscolaOption } from '@/features/alunos/api';
import { alunoFormSchema, AlunoFormValues } from '@/features/alunos/schemas';

interface Props {
  poloId: string;
  escolas: EscolaOption[];
  escolaFixaId?: string | null;
  onClose: () => void;
  onSuccess: (aluno: AlunoItem) => void;
}

const inputCls =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

const Field: React.FC<{ label: string; error?: string; children: React.ReactNode }> = ({ label, error, children }) => (
  <div>
    <label className="mb-1 block text-sm font-medium text-slate-300">{label}</label>
    {children}
    {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
  </div>
);

export const AlunoFormModal: React.FC<Props> = ({ poloId, escolas, escolaFixaId, onClose, onSuccess }) => {
  const [erro, setErro] = useState('');
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<AlunoFormValues>({
    resolver: zodResolver(alunoFormSchema),
    defaultValues: {
      modalidade: escolaFixaId ? 'escola' : 'polo',
      escola_id: escolaFixaId ?? '',
    },
  });

  const modalidade = watch('modalidade');

  const onSubmit = async (values: AlunoFormValues) => {
    setErro('');
    try {
      const aluno = await alunosApi.criar(poloId, {
        ...values,
        cpf: values.cpf.replace(/\D/g, ''),
        escola_id: values.modalidade === 'ead' ? null : values.escola_id || null,
      });
      onSuccess(aluno);
    } catch (err) {
      setErro(apiErrorMessage(err, 'Não foi possível cadastrar o aluno.'));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Cadastrar Aluno</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white" aria-label="Fechar">
            <X size={20} />
          </button>
        </div>

        {erro && (
          <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{erro}</div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nome" error={errors.nome?.message}>
              <input className={inputCls} {...register('nome')} />
            </Field>
            <Field label="Sobrenome" error={errors.sobrenome?.message}>
              <input className={inputCls} {...register('sobrenome')} />
            </Field>
            <Field label="CPF" error={errors.cpf?.message}>
              <input className={inputCls} placeholder="000.000.000-00" {...register('cpf')} />
            </Field>
            <Field label="Data de nascimento" error={errors.data_nascimento?.message}>
              <input type="date" className={inputCls} {...register('data_nascimento')} />
            </Field>
            <div className="col-span-2">
              <Field label="E-mail (o aluno receberá o convite para definir a senha)" error={errors.email?.message}>
                <input type="email" className={inputCls} {...register('email')} />
              </Field>
            </div>
            <Field label="Modalidade" error={errors.modalidade?.message}>
              <select className={inputCls} disabled={!!escolaFixaId} {...register('modalidade')}>
                <option value="polo">Presencial no polo</option>
                <option value="escola">Escola</option>
                <option value="ead">EAD</option>
              </select>
            </Field>
            {modalidade !== 'ead' && (
              <Field label="Escola" error={errors.escola_id?.message}>
                <select className={inputCls} disabled={!!escolaFixaId} {...register('escola_id')}>
                  <option value="">{modalidade === 'escola' ? 'Selecione a escola' : 'Nenhuma'}</option>
                  {escolas.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.nome}
                    </option>
                  ))}
                </select>
              </Field>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-sm text-slate-300 hover:text-white">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
            >
              {isSubmitting && <Loader2 size={16} className="animate-spin" />}
              Cadastrar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
