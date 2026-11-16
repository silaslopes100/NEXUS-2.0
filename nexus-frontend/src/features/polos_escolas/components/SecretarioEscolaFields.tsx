import React, { useEffect, useState } from 'react';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { EscolaCreatePayload } from '@/types/polos';

type SecretarioFields = Pick<EscolaCreatePayload,
  'secretario_usuario_id' | 'secretario_nome' | 'secretario_cpf' | 'secretario_email' | 'secretario_senha'>;

interface UsuarioEscola {
  id: string;
  nome: string;
  sobrenome?: string | null;
  email?: string | null;
  polo_id?: string | null;
  escola_id?: string | null;
  status?: string | null;
}

interface Props {
  poloId: string;
  values: SecretarioFields;
  onChange: (update: Partial<SecretarioFields>) => void;
}

const PAGE_SIZE = 200;
const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white';

export const SecretarioEscolaFields: React.FC<Props> = ({ poloId, values, onChange }) => {
  const [mode, setMode] = useState<'existente' | 'novo'>('existente');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [usuarios, setUsuarios] = useState<UsuarioEscola[]>([]);
  const [selected, setSelected] = useState<UsuarioEscola | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (mode !== 'existente') return;
    let active = true;
    setLoading(true);
    setError('');
    const timer = window.setTimeout(() => {
      void polosEscolasApi.listarUsuariosVinculaveis({
        perfil: 'escola',
        q: query.trim() || undefined,
        limit: PAGE_SIZE,
        offset,
      }).then((result) => {
        if (!active) return;
        setUsuarios(result.items);
        setTotal(result.total);
      }).catch(() => {
        if (!active) return;
        setUsuarios([]);
        setError('Não foi possível consultar os usuários. Tente novamente.');
      }).finally(() => {
        if (active) setLoading(false);
      });
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [mode, query, offset, retry]);

  const motivoIndisponivel = (usuario: UsuarioEscola) => {
    if (usuario.status !== 'ativo') return 'usuário inativo';
    if (usuario.escola_id) return 'já vinculado a uma escola';
    if (usuario.polo_id && usuario.polo_id !== poloId) return 'vinculado a outro polo';
    return '';
  };
  const options = selected && !usuarios.some((u) => u.id === selected.id) ? [selected, ...usuarios] : usuarios;

  return (
    <div className="space-y-3 border-t border-slate-800 pt-4">
      <h3 className="text-sm font-semibold text-slate-200">Responsável da escola</h3>
      <div className="flex flex-wrap gap-4 text-sm text-slate-300">
        <label><input type="radio" checked={mode === 'existente'} onChange={() => { setMode('existente'); onChange({ secretario_usuario_id: '' }); setSelected(null); }} /> Usuário existente</label>
        <label><input type="radio" checked={mode === 'novo'} onChange={() => { setMode('novo'); onChange({ secretario_usuario_id: '' }); setSelected(null); }} /> Criar usuário</label>
      </div>
      {mode === 'existente' ? (
        <div className="space-y-2">
          <input
            type="search"
            aria-label="Buscar usuário de escola"
            placeholder="Buscar por nome, sobrenome, e-mail ou CPF"
            className={inputClass}
            value={query}
            onChange={(event) => { setQuery(event.target.value); setOffset(0); }}
          />
          <select
            aria-label="Usuário responsável da escola"
            required
            className={inputClass}
            value={values.secretario_usuario_id || ''}
            onChange={(event) => {
              const usuario = options.find((item) => item.id === event.target.value) || null;
              setSelected(usuario);
              onChange({ secretario_usuario_id: usuario?.id || '' });
            }}
          >
            <option value="">{loading ? 'Carregando usuários...' : 'Selecione um usuário com perfil de escola'}</option>
            {options.map((usuario) => {
              const motivo = motivoIndisponivel(usuario);
              return <option key={usuario.id} value={usuario.id} disabled={!!motivo}>{usuario.nome} {usuario.sobrenome || ''} — {usuario.email || 'sem e-mail'}{motivo ? ` (${motivo})` : ''}</option>;
            })}
          </select>
          {error ? (
            <p role="alert" className="text-xs text-red-300">{error} <button type="button" className="underline" onClick={() => setRetry((value) => value + 1)}>Tentar novamente</button></p>
          ) : !loading && (
            <div className="flex items-center justify-between gap-2 text-xs text-slate-400">
              <span>{total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} de ${total}` : 'Nenhum usuário encontrado.'}</span>
              <div className="flex gap-2">
                <button type="button" disabled={offset === 0} onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))} className="disabled:opacity-40">Anterior</button>
                <button type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset((value) => value + PAGE_SIZE)} className="disabled:opacity-40">Próxima</button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <input required className={inputClass} placeholder="Nome" value={values.secretario_nome} onChange={(event) => onChange({ secretario_nome: event.target.value })} />
          <input required minLength={11} className={inputClass} placeholder="CPF" value={values.secretario_cpf} onChange={(event) => onChange({ secretario_cpf: event.target.value })} />
          <input required type="email" className={inputClass} placeholder="E-mail" value={values.secretario_email} onChange={(event) => onChange({ secretario_email: event.target.value })} />
          <input required minLength={8} type="password" className={inputClass} placeholder="Senha inicial" value={values.secretario_senha} onChange={(event) => onChange({ secretario_senha: event.target.value })} />
        </div>
      )}
    </div>
  );
};
