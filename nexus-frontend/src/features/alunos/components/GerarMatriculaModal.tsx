import React, { useEffect, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import {
  AlunoGestao,
  alunosGestaoApi,
  apiErrorMessage,
  ReingressoResultado,
} from '@/features/alunos/api';
import { Opcao, transferenciasApi } from '@/features/transferencias/api';

interface Props {
  aluno: AlunoGestao;
  onClose: () => void;
  onSuccess: (resultado: ReingressoResultado) => void;
}

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500 disabled:opacity-60';

export const GerarMatriculaModal: React.FC<Props> = ({ aluno, onClose, onSuccess }) => {
  const [modalidade, setModalidade] = useState<'polo' | 'ead'>(
    aluno.reingresso_polo_destino_id || aluno.modalidade !== 'ead' ? 'polo' : 'ead'
  );
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [poloId, setPoloId] = useState(aluno.reingresso_polo_destino_id ?? '');
  const [escolaId, setEscolaId] = useState(aluno.reingresso_escola_destino_id ?? '');
  const [taxaConfirmada, setTaxaConfirmada] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    transferenciasApi
      .polos()
      .then(setPolos)
      .catch((err: unknown) => setErro(apiErrorMessage(err, 'Não foi possível carregar os polos.')));
  }, []);

  useEffect(() => {
    if (!poloId) {
      setEscolas([]);
      return;
    }
    let ativo = true;
    transferenciasApi
      .escolas(poloId)
      .then((itens) => {
        if (ativo) setEscolas(itens);
      })
      .catch((err: unknown) => {
        if (ativo) setErro(apiErrorMessage(err, 'Não foi possível carregar as escolas.'));
      });
    return () => {
      ativo = false;
    };
  }, [poloId]);

  const salvar = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSalvando(true);
    setErro('');
    try {
      const resultado = await alunosGestaoApi.reingressar(aluno.id, {
        modalidade,
        polo_destino_id: modalidade === 'polo' ? poloId : undefined,
        escola_destino_id: modalidade === 'polo' ? escolaId : undefined,
        taxa_confirmada: taxaConfirmada,
      });
      onSuccess(resultado);
    } catch (err) {
      setErro(apiErrorMessage(err, 'Não foi possível gerar a nova matrícula.'));
      setSalvando(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !salvando) onClose();
      }}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="gerar-matricula-titulo"
        onSubmit={salvar}
        className="my-auto w-full max-w-lg space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 id="gerar-matricula-titulo" className="text-xl font-bold text-white">
              Gerar nova matrícula
            </h2>
            <p className="mt-1 text-sm text-slate-400">{aluno.nome}</p>
          </div>
          <button
            type="button"
            aria-label="Fechar formulário"
            disabled={salvando}
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </header>

        {erro && (
          <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {erro}
          </div>
        )}

        <label className="block space-y-1.5 text-sm text-slate-300">
          <span>Modalidade *</span>
          <select
            className={inputClass}
            value={modalidade}
            onChange={(event) => setModalidade(event.target.value as 'polo' | 'ead')}
          >
            <option value="polo">Polo</option>
            <option value="ead">EAD</option>
          </select>
        </label>

        {modalidade === 'polo' && (
          <>
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Polo de destino *</span>
              <select
                required
                className={inputClass}
                value={poloId}
                onChange={(event) => {
                  setPoloId(event.target.value);
                  setEscolaId('');
                }}
              >
                <option value="">Selecione</option>
                {polos.map((polo) => (
                  <option key={polo.id} value={polo.id}>
                    {polo.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Escola de destino *</span>
              <select
                required
                disabled={!poloId}
                className={inputClass}
                value={escolaId}
                onChange={(event) => setEscolaId(event.target.value)}
              >
                <option value="">Selecione</option>
                {escolas.map((escola) => (
                  <option key={escola.id} value={escola.id}>
                    {escola.nome}
                  </option>
                ))}
              </select>
            </label>
            <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
              Serão debitadas 2 licenças do estoque do Polo de destino.
            </p>
          </>
        )}

        <label className="flex items-start gap-2 text-sm font-medium text-slate-200">
          <input
            type="checkbox"
            required
            checked={taxaConfirmada}
            onChange={(event) => setTaxaConfirmada(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-900"
          />
          Confirmo o recebimento da taxa de matrícula de R$ 100,00
        </label>

        <p className="text-xs text-slate-400">
          O aluno receberá a etiqueta "Revalidado" e só poderá entrar em turmas que comecem do zero.
        </p>

        <footer className="flex flex-col-reverse justify-end gap-2 border-t border-slate-800 pt-4 sm:flex-row">
          <button
            type="button"
            disabled={salvando}
            onClick={onClose}
            className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={salvando}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {salvando && <Loader2 size={16} className="animate-spin" />}
            {salvando ? 'Gerando...' : 'Gerar matrícula'}
          </button>
        </footer>
      </form>
    </div>
  );
};
