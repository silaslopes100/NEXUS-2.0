import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowLeftRight, Ban, Loader2, X } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { Opcao, TipoTransferencia, tipoLabel, transferenciasApi } from '@/features/transferencias/api';
import { UsuarioFicha } from '@/types/admin';
import { Campo } from './SecaoEditavel';
import { inputCls, mensagemErro } from './fichaUtils';

const Modal: React.FC<{
  titulo: string; icone: React.ReactNode; aoFechar: () => void; children: React.ReactNode; idTitulo: string;
}> = ({ titulo, icone, aoFechar, children, idTitulo }) => {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && aoFechar();
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [aoFechar]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div role="dialog" aria-modal="true" aria-labelledby={idTitulo}
        className="glass bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 animate-fadeIn max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h2 id={idTitulo} className="flex items-center gap-2 text-white font-bold text-sm">{icone} {titulo}</h2>
          <button type="button" onClick={aoFechar} className="p-1 text-slate-400 hover:text-white" aria-label="Fechar">
            <X className="w-4 h-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

const Rodape: React.FC<{ aoFechar: () => void; salvando: boolean; rotulo: string; perigo?: boolean }> = ({
  aoFechar, salvando, rotulo, perigo,
}) => (
  <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-800">
    <button type="button" onClick={aoFechar} disabled={salvando} className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-xl font-medium">
      Cancelar
    </button>
    <button
      type="submit"
      disabled={salvando}
      className={`px-4 py-2 text-xs font-bold rounded-xl shadow flex items-center gap-1.5 disabled:opacity-60 ${
        perigo ? 'bg-red-500 hover:bg-red-600 text-on-accent' : 'bg-nexus-yellow hover:bg-nexus-yellow-hover text-ink'
      }`}
    >
      {salvando && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
      {rotulo}
    </button>
  </div>
);

const Erro: React.FC<{ msg: string | null }> = ({ msg }) =>
  msg ? (
    <p role="alert" className="flex items-start gap-2 text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
      <AlertCircle className="w-4 h-4 shrink-0" /> {msg}
    </p>
  ) : null;

// ---------- Inativar ----------

export const InativarModal: React.FC<{ ficha: UsuarioFicha; aoFechar: () => void; aoConcluir: (m: string) => void }> = ({
  ficha, aoFechar, aoConcluir,
}) => {
  const [motivo, setMotivo] = useState('');
  const [status, setStatus] = useState<'inativo' | 'bloqueado'>('inativo');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const nome = `${ficha.nome} ${ficha.sobrenome || ''}`.trim();

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (motivo.trim().length < 3) {
      setErro('Descreva o motivo (mínimo de 3 caracteres).');
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      await adminApi.inativarUsuario(ficha.id, motivo.trim(), status);
      aoConcluir(`${nome} foi ${status === 'bloqueado' ? 'bloqueado(a)' : 'inativado(a)'}. As sessões abertas foram encerradas.`);
    } catch (err) {
      setErro(mensagemErro(err, 'Não foi possível inativar o usuário.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Modal titulo="Inativar usuário" icone={<Ban className="w-4 h-4 text-red-400" />} aoFechar={aoFechar} idTitulo="titulo-inativar">
      <form onSubmit={enviar} className="space-y-4 mt-4">
        <p className="text-xs text-slate-400">
          <strong className="text-white">{nome}</strong> perde o acesso ao sistema e as sessões abertas são encerradas.
          O histórico (notas, presenças, cobranças) é mantido, e você pode reativar depois.
        </p>
        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold text-slate-300">Situação</legend>
          {([
            ['inativo', 'Inativo', 'Saiu da instituição, encerrou o curso, cadastro sem uso.'],
            ['bloqueado', 'Bloqueado', 'Acesso suspenso por segurança ou irregularidade.'],
          ] as const).map(([v, l, d]) => (
            <label key={v} className="flex items-start gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 cursor-pointer">
              <input type="radio" name="status-inativacao" className="mt-0.5 accent-yellow-400" checked={status === v} onChange={() => setStatus(v)} />
              <span>
                <span className="block text-xs font-semibold text-white">{l}</span>
                <span className="block text-[11px] text-slate-500">{d}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <Campo label="Motivo" obrigatorio>
          <textarea className={`${inputCls} min-h-[80px]`} maxLength={1000} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        </Campo>
        <Erro msg={erro} />
        <Rodape aoFechar={aoFechar} salvando={salvando} rotulo={status === 'bloqueado' ? 'Bloquear' : 'Inativar'} perigo />
      </form>
    </Modal>
  );
};

// ---------- Transferência ----------

export const TransferenciaModal: React.FC<{ ficha: UsuarioFicha; aoFechar: () => void; aoConcluir: (m: string) => void }> = ({
  ficha, aoFechar, aoConcluir,
}) => {
  const aluno = ficha.aluno!;
  const ead = aluno.modalidade === 'ead';
  const tipos: TipoTransferencia[] = ead ? ['ead_para_polo'] : ['troca_polo', 'polo_para_ead'];
  const [tipo, setTipo] = useState<TipoTransferencia>(tipos[0]);
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [polo, setPolo] = useState('');
  const [escola, setEscola] = useState('');
  const [observacao, setObservacao] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const comDestino = tipo !== 'polo_para_ead';

  useEffect(() => {
    transferenciasApi.polos().then(setPolos).catch(() => setErro('Não foi possível carregar os polos.'));
  }, []);
  useEffect(() => {
    setEscola('');
    if (!polo) {
      setEscolas([]);
      return;
    }
    transferenciasApi.escolas(polo).then(setEscolas).catch(() => setEscolas([]));
  }, [polo]);

  const polosDestino = tipo === 'troca_polo' ? polos.filter((p) => p.id !== aluno.polo_id) : polos;

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (comDestino && (!polo || !escola)) {
      setErro('Escolha o polo e a escola de destino.');
      return;
    }
    setSalvando(true);
    setErro(null);
    try {
      await transferenciasApi.solicitar({
        aluno_id: aluno.id,
        tipo,
        polo_destino_id: comDestino ? polo : undefined,
        escola_destino_id: comDestino ? escola : undefined,
        observacao: observacao.trim() || undefined,
      });
      aoConcluir('Solicitação de transferência aberta. Ela segue para análise em Transferências.');
    } catch (err) {
      setErro(mensagemErro(err, 'Não foi possível abrir a solicitação.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Modal titulo="Solicitar transferência" icone={<ArrowLeftRight className="w-4 h-4 text-nexus-yellow" />} aoFechar={aoFechar} idTitulo="titulo-transferencia">
      <form onSubmit={enviar} className="space-y-4 mt-4">
        <p className="text-xs text-slate-400">
          Hoje: {[aluno.polo_nome, aluno.escola_nome].filter(Boolean).join(' · ') || 'sem unidade'} ({ead ? 'EAD' : 'presencial'}).
          A solicitação passa pela análise normal antes de mudar o cadastro.
        </p>
        <Campo label="Tipo" obrigatorio>
          <select className={inputCls} value={tipo} onChange={(e) => setTipo(e.target.value as TipoTransferencia)}>
            {tipos.map((t) => <option key={t} value={t}>{tipoLabel[t]}</option>)}
          </select>
        </Campo>
        {comDestino && (
          <>
            <Campo label="Polo de destino" obrigatorio>
              <select className={inputCls} value={polo} onChange={(e) => setPolo(e.target.value)}>
                <option value="">Selecione</option>
                {polosDestino.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
              </select>
            </Campo>
            <Campo label="Escola de destino" obrigatorio>
              <select className={inputCls} value={escola} disabled={!polo} onChange={(e) => setEscola(e.target.value)}>
                <option value="">Selecione</option>
                {escolas.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
              </select>
            </Campo>
          </>
        )}
        <Campo label="Observação">
          <textarea className={`${inputCls} min-h-[70px]`} maxLength={1000} value={observacao} onChange={(e) => setObservacao(e.target.value)} />
        </Campo>
        <Erro msg={erro} />
        <Rodape aoFechar={aoFechar} salvando={salvando} rotulo="Abrir solicitação" />
      </form>
    </Modal>
  );
};
