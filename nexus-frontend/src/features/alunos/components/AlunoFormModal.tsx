import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, X } from 'lucide-react';
import { alunosApi, apiErrorMessage, AlunoItem, EscolaOption, Modalidade, UsuarioAlunoDisponivel } from '@/features/alunos/api';
import { alunoFormSchema, AlunoFormValues } from '@/features/alunos/schemas';

interface Props {
  poloId: string;
  escolas: EscolaOption[];
  escolaFixaId?: string | null;
  inicialExistente?: boolean;
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

export const AlunoFormModal: React.FC<Props> = ({ poloId, escolas, escolaFixaId, inicialExistente, onClose, onSuccess }) => {
  const [erro, setErro] = useState('');
  const [existente, setExistente] = useState(!!inicialExistente);
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
      <div className="glass max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Cadastrar Aluno</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white" aria-label="Fechar">
            <X size={20} />
          </button>
        </div>

        {erro && (
          <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{erro}</div>
        )}

        <div className="mb-4 flex gap-2">
          <button type="button" onClick={() => { setExistente(false); setErro(''); }} className={`rounded-lg px-3 py-2 text-sm ${!existente ? 'bg-blue-600 text-on-accent' : 'text-slate-300'}`}>Novo usuário</button>
          <button type="button" onClick={() => { setExistente(true); setErro(''); }} className={`rounded-lg px-3 py-2 text-sm ${existente ? 'bg-blue-600 text-on-accent' : 'text-slate-300'}`}>Usuário existente</button>
        </div>
        {existente ? (
          <VincularUsuarioForm poloId={poloId} escolas={escolas} escolaFixaId={escolaFixaId} onClose={onClose} onSuccess={onSuccess} />
        ) : <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
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
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:opacity-60"
            >
              {isSubmitting && <Loader2 size={16} className="animate-spin" />}
              Cadastrar
            </button>
          </div>
        </form>}
      </div>
    </div>
  );
};

const VincularUsuarioForm: React.FC<Props> = ({ poloId, escolas, escolaFixaId, onClose, onSuccess }) => {
  const [modalidade, setModalidade] = useState<Modalidade>(escolaFixaId ? 'escola' : 'polo');
  const [escolaId, setEscolaId] = useState(escolaFixaId || '');
  const [nascimento, setNascimento] = useState('');
  const [busca, setBusca] = useState('');
  const [pagina, setPagina] = useState(0);
  const [usuarios, setUsuarios] = useState<UsuarioAlunoDisponivel[]>([]);
  const [total, setTotal] = useState(0);
  const [selecionado, setSelecionado] = useState<UsuarioAlunoDisponivel | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [erroBusca, setErroBusca] = useState('');
  const escolaDestino = modalidade === 'ead' ? '' : escolaId;

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    const timer = window.setTimeout(() => {
      alunosApi.usuariosDisponiveis(poloId, { escola_id: escolaDestino || undefined, q: busca.trim() || undefined, limit: 20, offset: pagina * 20 })
        .then((resultado) => {
          if (!ativo) return;
          setUsuarios(resultado.items);
          setTotal(resultado.total);
          setErroBusca('');
        })
        .catch((e) => {
          if (ativo) {
            setUsuarios([]);
            setTotal(0);
            setErroBusca(apiErrorMessage(e, 'Não foi possível buscar usuários. Altere a busca para tentar novamente.'));
          }
        })
        .finally(() => { if (ativo) setCarregando(false); });
    }, 300);
    return () => { ativo = false; window.clearTimeout(timer); };
  }, [poloId, escolaDestino, busca, pagina]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErro('');
    if (!selecionado) { setErro('Selecione um usuário.'); return; }
    if (!nascimento || nascimento >= new Date().toISOString().slice(0, 10)) { setErro('Informe uma data de nascimento anterior a hoje.'); return; }
    if (modalidade === 'escola' && !escolaDestino) { setErro('Selecione a escola.'); return; }
    setSalvando(true);
    try {
      const aluno = await alunosApi.vincularUsuario(poloId, {
        usuario_id: selecionado.id, data_nascimento: nascimento, modalidade, escola_id: escolaDestino || null,
      });
      onSuccess(aluno);
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível vincular o usuário.'));
    } finally { setSalvando(false); }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      {erro && <div role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{erro}</div>}
      {erroBusca && <div role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{erroBusca}</div>}
      <p className="text-sm text-slate-300">Vincule uma conta ativa com perfil de aluno. A senha existente será mantida.</p>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Modalidade">
          <select aria-label="Modalidade" className={inputCls} value={modalidade} disabled={!!escolaFixaId} onChange={(e) => { setModalidade(e.target.value as Modalidade); setSelecionado(null); setPagina(0); }}>
            <option value="polo">Presencial no polo</option><option value="escola">Escola</option><option value="ead">EAD</option>
          </select>
        </Field>
        {modalidade !== 'ead' && <Field label="Escola">
          <select aria-label="Escola" className={inputCls} value={escolaId} disabled={!!escolaFixaId} onChange={(e) => { setEscolaId(e.target.value); setSelecionado(null); setPagina(0); }}>
            <option value="">Nenhuma</option>
            {escolaFixaId && !escolas.some((e) => e.id === escolaFixaId) && <option value={escolaFixaId}>Escola da turma</option>}
            {escolas.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
          </select>
        </Field>}
        <Field label="Data de nascimento"><input aria-label="Data de nascimento" className={inputCls} type="date" value={nascimento} onChange={(e) => setNascimento(e.target.value)} required /></Field>
      </div>
      <Field label="Buscar usuário aluno">
        <input aria-label="Buscar usuário aluno" className={inputCls} value={busca} onChange={(e) => { setBusca(e.target.value); setPagina(0); }} placeholder="Nome, e-mail ou CPF" />
      </Field>
      {selecionado && <p className="break-words text-sm text-blue-300">Selecionado: {selecionado.nome} {selecionado.sobrenome || ''} ({selecionado.email || 'sem e-mail'})</p>}
      <ul className="max-h-40 overflow-y-auto rounded-xl border border-slate-700">
        {carregando ? <li className="p-3 text-sm text-slate-400">Buscando...</li> : usuarios.length === 0 ? <li className="p-3 text-sm text-slate-400">Nenhum usuário disponível.</li> : usuarios.map((u) => (
          <li key={u.id}><button type="button" onClick={() => setSelecionado(u)} className="w-full p-3 text-left text-sm text-white hover:bg-slate-800">{u.nome} {u.sobrenome || ''} — {u.email || 'sem e-mail'}</button></li>
        ))}
      </ul>
      <div className="flex items-center justify-between text-sm text-slate-300">
        <button type="button" disabled={pagina === 0 || carregando} onClick={() => setPagina(pagina - 1)} className="disabled:opacity-40">Anterior</button>
        <span>{total} usuários encontrados</span>
        <button type="button" disabled={(pagina + 1) * 20 >= total || carregando} onClick={() => setPagina(pagina + 1)} className="disabled:opacity-40">Próxima</button>
      </div>
      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-sm text-slate-300">Cancelar</button>
        <button type="submit" disabled={salvando} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent disabled:opacity-60">{salvando ? 'Vinculando...' : 'Vincular aluno'}</button>
      </div>
    </form>
  );
};
