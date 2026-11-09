import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Trash2, X } from 'lucide-react';
import { apiErrorMessage } from '@/features/alunos/api';
import { AlunoTurma, Turma, turmasApi } from '@/features/turmas/api';
import { inputCls } from '@/features/turmas/components/TurmaFormModal';

interface TurmaAlunosPanelProps {
  turma: Turma;
  onClose: (houveAlteracao: boolean) => void;
}

export const TurmaAlunosPanel: React.FC<TurmaAlunosPanelProps> = ({ turma, onClose }) => {
  const [alunos, setAlunos] = useState<AlunoTurma[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [disponiveis, setDisponiveis] = useState<AlunoTurma[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [versao, setVersao] = useState(0);
  const [processandoId, setProcessandoId] = useState<string | null>(null);
  const [confirmandoId, setConfirmandoId] = useState<string | null>(null);
  const [alterado, setAlterado] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    turmasApi
      .listarAlunos(turma.id)
      .then((pagina) => {
        if (!ativo) return;
        setAlunos(pagina.items);
        setTotal(pagina.total);
      })
      .catch((e) => ativo && setErro(apiErrorMessage(e, 'Erro ao carregar alunos da turma.')))
      .finally(() => ativo && setLoading(false));
    return () => {
      ativo = false;
    };
  }, [turma.id, versao]);

  useEffect(() => {
    let ativo = true;
    setBuscando(true);
    const timer = window.setTimeout(() => {
      turmasApi
        .buscarAlunosDisponiveis(turma.id, busca.trim())
        .then((itens) => ativo && setDisponiveis(itens))
        .catch((e) => ativo && setErro(apiErrorMessage(e, 'Erro ao buscar alunos.')))
        .finally(() => ativo && setBuscando(false));
    }, 300);
    return () => {
      ativo = false;
      window.clearTimeout(timer);
    };
  }, [turma.id, busca, versao]);

  const executar = useCallback(
    async (alunoId: string, acao: () => Promise<void>, mensagemErro: string) => {
      setProcessandoId(alunoId);
      setErro('');
      try {
        await acao();
        setAlterado(true);
        setConfirmandoId(null);
        setVersao((atual) => atual + 1);
      } catch (e) {
        setErro(apiErrorMessage(e, mensagemErro));
      } finally {
        setProcessandoId(null);
      }
    },
    []
  );

  const matricular = (alunoId: string) =>
    void executar(alunoId, () => turmasApi.matricularAluno(turma.id, alunoId), 'Não foi possível matricular o aluno.');

  const remover = (alunoId: string) =>
    void executar(alunoId, () => turmasApi.removerAluno(turma.id, alunoId), 'Não foi possível remover o aluno.');

  const fechar = () => onClose(alterado);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) fechar();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="turma-alunos-titulo"
        className="my-auto w-full max-w-3xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-300">Alunos da turma</p>
            <h2 id="turma-alunos-titulo" className="mt-1 text-xl font-bold text-white">
              {turma.nome}
            </h2>
          </div>
          <button
            type="button"
            aria-label="Fechar"
            onClick={fechar}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X size={20} />
          </button>
        </header>

        {erro && (
          <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {erro}
          </div>
        )}

        <div className="space-y-2">
          <label className="block space-y-1.5 text-sm text-slate-300">
            <span>Matricular aluno</span>
            <input
              className={inputCls}
              placeholder="Buscar por nome ou matrícula"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </label>
          <ul className="max-h-48 divide-y divide-slate-800 overflow-y-auto rounded-xl border border-slate-800">
            {buscando && (
              <li className="p-3 text-center">
                <Loader2 className="mx-auto animate-spin text-slate-400" size={16} />
              </li>
            )}
            {!buscando && disponiveis.length === 0 && (
              <li className="p-3 text-center text-sm text-slate-500">Nenhum aluno disponível.</li>
            )}
            {!buscando &&
              disponiveis.map((aluno) => (
                <li key={aluno.aluno_id} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <span className="min-w-0">
                    <span className="block truncate font-semibold text-white">{aluno.nome || aluno.email}</span>
                    <span className="block truncate text-xs text-slate-500">{aluno.numero_matricula || 'Sem matrícula'}</span>
                  </span>
                  <button
                    type="button"
                    disabled={processandoId !== null}
                    onClick={() => matricular(aluno.aluno_id)}
                    className="flex shrink-0 items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
                  >
                    {processandoId === aluno.aluno_id ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                    Matricular
                  </button>
                </li>
              ))}
          </ul>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-300">Matriculados ({total})</h3>
          <ul className="max-h-72 divide-y divide-slate-800 overflow-y-auto rounded-xl border border-slate-800">
            {loading && (
              <li className="p-4 text-center">
                <Loader2 className="mx-auto animate-spin text-slate-400" size={18} />
              </li>
            )}
            {!loading && alunos.length === 0 && (
              <li className="p-4 text-center text-sm text-slate-500">Nenhum aluno matriculado.</li>
            )}
            {!loading &&
              alunos.map((aluno) => (
                <li key={aluno.aluno_id} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <span className="min-w-0">
                    <span className="block truncate font-semibold text-white">{aluno.nome || aluno.email || aluno.aluno_id}</span>
                    <span className="block truncate text-xs text-slate-500">{aluno.numero_matricula || 'Sem matrícula'}</span>
                  </span>
                  {confirmandoId === aluno.aluno_id ? (
                    <span className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        disabled={processandoId !== null}
                        onClick={() => remover(aluno.aluno_id)}
                        className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-60"
                      >
                        Confirmar
                      </button>
                      <button
                        type="button"
                        disabled={processandoId !== null}
                        onClick={() => setConfirmandoId(null)}
                        className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-60"
                      >
                        Cancelar
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      aria-label={`Remover ${aluno.nome || 'aluno'} da turma`}
                      onClick={() => setConfirmandoId(aluno.aluno_id)}
                      className="shrink-0 rounded-lg border border-red-500/30 p-2 text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </li>
              ))}
          </ul>
          {total > alunos.length && !loading && (
            <p className="text-xs text-slate-500">Exibindo os primeiros {alunos.length} alunos.</p>
          )}
        </div>
      </section>
    </div>
  );
};
