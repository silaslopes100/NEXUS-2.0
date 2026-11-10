import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, Search, X } from 'lucide-react';
import {
  AlunoElegivel,
  Opcao,
  TipoTransferencia,
  tipoLabel,
  transferenciasApi,
  transferenciasErro,
} from '@/features/transferencias/api';
import { useAuthStore } from '@/stores/authStore';

interface Props {
  modoAluno: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500';

const tiposDoAluno = (aluno: AlunoElegivel): TipoTransferencia[] =>
  aluno.modalidade === 'ead' ? ['ead_para_polo'] : ['troca_polo', 'polo_para_ead'];

export const SolicitarTransferenciaModal: React.FC<Props> = ({ modoAluno, onClose, onSuccess }) => {
  const { user } = useAuthStore();
  const [reingresso, setReingresso] = useState(false);
  const [aluno, setAluno] = useState<AlunoElegivel | null>(null);
  const [tipo, setTipo] = useState<TipoTransferencia | ''>('');
  const [busca, setBusca] = useState('');
  const [resultados, setResultados] = useState<AlunoElegivel[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [carregandoEscolas, setCarregandoEscolas] = useState(false);
  const [poloDestino, setPoloDestino] = useState('');
  const [escolaDestino, setEscolaDestino] = useState('');
  const [observacao, setObservacao] = useState('');
  const [erro, setErro] = useState('');
  const [salvando, setSalvando] = useState(false);

  const selecionarAluno = (selecionado: AlunoElegivel) => {
    setAluno(selecionado);
    setTipo(reingresso ? 'reingresso' : tiposDoAluno(selecionado)[0]);
    setPoloDestino('');
    setEscolaDestino('');
  };

  useEffect(() => {
    if (!modoAluno) return;
    transferenciasApi
      .meuCadastro()
      .then(selecionarAluno)
      .catch((err: unknown) =>
        setErro(transferenciasErro(err, 'Não foi possível carregar seu cadastro de aluno.'))
      );
  }, [modoAluno]);

  useEffect(() => {
    transferenciasApi
      .polos()
      .then(setPolos)
      .catch((err: unknown) =>
        setErro(transferenciasErro(err, 'Não foi possível carregar os polos.'))
      );
  }, []);

  useEffect(() => {
    const termo = busca.trim();
    if (termo.length < 3) {
      setResultados([]);
      setBuscando(false);
      return;
    }
    let ativo = true;
    setBuscando(true);
    const timeout = window.setTimeout(() => {
      transferenciasApi
        .buscarAlunos(termo, reingresso)
        .then((itens) => {
          if (ativo) setResultados(itens);
        })
        .catch((err: unknown) => {
          if (ativo) setErro(transferenciasErro(err, 'Não foi possível buscar os alunos.'));
        })
        .finally(() => {
          if (ativo) setBuscando(false);
        });
    }, 300);
    return () => {
      ativo = false;
      window.clearTimeout(timeout);
    };
  }, [busca, reingresso]);

  useEffect(() => {
    setEscolas([]);
    setEscolaDestino('');
    if (!poloDestino) return;
    let ativo = true;
    setCarregandoEscolas(true);
    transferenciasApi
      .escolas(poloDestino)
      .then((itens) => {
        if (!ativo) return;
        // No reingresso, o destino é a unidade de quem solicita.
        setEscolas(
          reingresso && user?.escola_id ? itens.filter((e) => e.id === user.escola_id) : itens
        );
      })
      .catch((err: unknown) => {
        if (ativo) setErro(transferenciasErro(err, 'Não foi possível carregar as escolas.'));
      })
      .finally(() => {
        if (ativo) setCarregandoEscolas(false);
      });
    return () => {
      ativo = false;
    };
  }, [poloDestino, reingresso, user?.escola_id]);

  const precisaDestino = tipo === 'troca_polo' || tipo === 'ead_para_polo' || tipo === 'reingresso';
  const polosDisponiveis = useMemo(
    () =>
      polos.filter((polo) =>
        tipo === 'reingresso'
          ? polo.id === user?.polo_id
          : tipo !== 'troca_polo' || polo.id !== aluno?.polo_id
      ),
    [aluno?.polo_id, polos, tipo, user?.polo_id]
  );
  const poloSemEscola = !!poloDestino && !carregandoEscolas && escolas.length === 0;

  const salvar = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!aluno || !tipo) return;
    setSalvando(true);
    setErro('');
    try {
      await transferenciasApi.solicitar(
        {
          aluno_id: modoAluno ? undefined : aluno.id,
          tipo,
          polo_destino_id: precisaDestino ? poloDestino : undefined,
          escola_destino_id: precisaDestino ? escolaDestino : undefined,
          observacao: observacao.trim() || undefined,
        },
        modoAluno ? 'aluno' : undefined
      );
      onSuccess();
    } catch (err) {
      setErro(transferenciasErro(err, 'Não foi possível registrar a solicitação.'));
    } finally {
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
        aria-labelledby="solicitar-transferencia-titulo"
        onSubmit={salvar}
        className="my-auto max-h-[90vh] w-full max-w-xl space-y-5 overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 id="solicitar-transferencia-titulo" className="text-xl font-bold text-white">
              Nova solicitação
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              A transferência é feita sem nova matrícula, após aprovação da Secretaria Geral.
            </p>
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
          <div
            role="alert"
            className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200"
          >
            {erro}
          </div>
        )}

        {!aluno && !modoAluno && (
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={reingresso}
                onChange={(event) => {
                  setReingresso(event.target.checked);
                  setResultados([]);
                }}
                className="h-4 w-4 rounded border-slate-600 bg-slate-950"
              />
              Reingresso de aluno em Churn
            </label>
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Aluno *</span>
              <span className="relative block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  autoFocus
                  className={`${inputClass} pl-9`}
                  placeholder="Digite ao menos 3 letras do nome, matrícula ou e-mail"
                  value={busca}
                  onChange={(event) => setBusca(event.target.value)}
                />
              </span>
            </label>
            {buscando && (
              <div className="flex justify-center py-4 text-blue-400">
                <Loader2 className="animate-spin" />
              </div>
            )}
            {!buscando && resultados.length > 0 && (
              <div className="max-h-52 space-y-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60 p-2">
                {resultados.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selecionarAluno(item)}
                    className="block w-full rounded-lg p-2.5 text-left hover:bg-slate-800/70"
                  >
                    <span className="block text-sm font-medium text-slate-200">{item.nome}</span>
                    <span className="block text-xs text-slate-500">
                      {item.numero_matricula || 'Sem matrícula'} ·{' '}
                      {item.modalidade === 'ead' ? 'EAD' : item.polo_nome || 'Sem polo'}
                    </span>
                  </button>
                ))}
              </div>
            )}
            {!buscando && busca.trim().length >= 3 && resultados.length === 0 && (
              <p className="py-3 text-center text-sm text-slate-500">Nenhum aluno encontrado.</p>
            )}
          </div>
        )}

        {aluno && (
          <div className="flex items-start justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="min-w-0 text-sm">
              <p className="font-semibold text-white">{aluno.nome}</p>
              <p className="text-xs text-slate-400">
                {aluno.modalidade === 'ead'
                  ? 'Modalidade EAD'
                  : [aluno.polo_nome, aluno.escola_nome].filter(Boolean).join(' · ') || 'Sem polo'}
              </p>
            </div>
            {!modoAluno && (
              <button
                type="button"
                onClick={() => {
                  setAluno(null);
                  setTipo('');
                }}
                className="shrink-0 text-xs font-semibold text-blue-300 hover:text-blue-200"
              >
                Trocar aluno
              </button>
            )}
          </div>
        )}

        {aluno && (
          <div className="space-y-4">
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Tipo de solicitação *</span>
              <select
                required
                className={inputClass}
                value={tipo}
                onChange={(event) => {
                  setTipo(event.target.value as TipoTransferencia);
                  setPoloDestino('');
                }}
              >
                {(reingresso ? (['reingresso'] as TipoTransferencia[]) : tiposDoAluno(aluno)).map((valor) => (
                  <option key={valor} value={valor}>
                    {tipoLabel[valor]}
                  </option>
                ))}
              </select>
            </label>

            {precisaDestino && (
              <>
                <label className="block space-y-1.5 text-sm text-slate-300">
                  <span>Polo de destino *</span>
                  <select
                    required
                    className={inputClass}
                    value={poloDestino}
                    onChange={(event) => setPoloDestino(event.target.value)}
                  >
                    <option value="">Selecione</option>
                    {polosDisponiveis.map((polo) => (
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
                    className={inputClass}
                    disabled={!poloDestino || carregandoEscolas}
                    value={escolaDestino}
                    onChange={(event) => setEscolaDestino(event.target.value)}
                  >
                    <option value="">
                      {carregandoEscolas ? 'Carregando escolas...' : 'Selecione'}
                    </option>
                    {escolas.map((escola) => (
                      <option key={escola.id} value={escola.id}>
                        {escola.nome}
                      </option>
                    ))}
                  </select>
                  {poloSemEscola && (
                    <span className="block text-xs text-amber-300">
                      Este polo não tem escolas ativas e não pode receber alunos.
                    </span>
                  )}
                </label>
              </>
            )}

            {reingresso && (
              <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                O aluno pagará a taxa de matrícula de R$ 100,00, e 2 licenças serão debitadas do
                Polo de destino quando a Secretaria Geral gerar a nova matrícula.
              </p>
            )}

            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Observação</span>
              <textarea
                rows={3}
                maxLength={1000}
                className={inputClass}
                value={observacao}
                onChange={(event) => setObservacao(event.target.value)}
              />
            </label>
          </div>
        )}

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
            disabled={salvando || !aluno || !tipo}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {salvando && <Loader2 size={16} className="animate-spin" />}
            {salvando ? 'Enviando...' : 'Enviar solicitação'}
          </button>
        </footer>
      </form>
    </div>
  );
};
