import React, { useEffect, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { Academico, alunosGestaoApi, apiErrorMessage } from '@/features/alunos/api';
import { BarraProgresso } from '@/features/alunos/components/DisciplinasExpandidas';

const situacaoLabel: Record<string, string> = {
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
  cursando: 'Cursando',
};

interface Props {
  alunoId: string;
  onClose: () => void;
}

export const BoletimModal: React.FC<Props> = ({ alunoId, onClose }) => {
  const [dados, setDados] = useState<Academico | null>(null);
  const [cursoId, setCursoId] = useState('');
  const [erro, setErro] = useState('');

  useEffect(() => {
    let ativo = true;
    alunosGestaoApi
      .academico(alunoId)
      .then((resposta) => {
        if (!ativo) return;
        setDados(resposta);
        setCursoId(resposta.cursos[0]?.id ?? '');
      })
      .catch((err: unknown) => {
        if (ativo) setErro(apiErrorMessage(err, 'Não foi possível carregar o boletim.'));
      });
    return () => {
      ativo = false;
    };
  }, [alunoId]);

  const curso = dados?.cursos.find((item) => item.id === cursoId);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="boletim-titulo"
        className="my-auto max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-300">Histórico Escolar</p>
            <h2 id="boletim-titulo" className="mt-1 text-xl font-bold text-white">
              Boletim {dados ? `de ${dados.aluno_nome}` : ''}
            </h2>
            {dados && (
              <p className="mt-1 text-sm text-slate-400">
                Matrícula: {dados.numero_matricula || 'não informada'}
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Fechar boletim"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X size={20} />
          </button>
        </header>

        {erro && (
          <div role="alert" className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {erro}
          </div>
        )}
        {!dados && !erro && (
          <div className="flex justify-center py-12 text-blue-400">
            <Loader2 className="animate-spin" />
          </div>
        )}
        {dados && dados.cursos.length === 0 && (
          <p className="py-12 text-center text-sm text-slate-500">
            Nenhuma disciplina registrada para este aluno.
          </p>
        )}

        {dados && dados.cursos.length > 0 && (
          <div className="mt-5 space-y-4">
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Curso</span>
              <select
                value={cursoId}
                onChange={(event) => setCursoId(event.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
              >
                {dados.cursos.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nome}
                  </option>
                ))}
              </select>
            </label>

            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full min-w-[560px] text-left text-sm text-slate-300">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-3">Disciplina</th>
                    <th className="p-3">Semestre</th>
                    <th className="p-3">Nota</th>
                    <th className="p-3">Situação</th>
                    <th className="p-3">Progresso</th>
                  </tr>
                </thead>
                <tbody>
                  {curso?.disciplinas.map((disciplina) => (
                    <tr key={disciplina.id} className="border-b border-slate-800/60 last:border-0">
                      <td className="p-3 font-medium text-white">{disciplina.nome}</td>
                      <td className="p-3">{disciplina.semestre ?? '—'}</td>
                      <td className="p-3">
                        {disciplina.nota != null ? disciplina.nota.toFixed(1) : '—'}
                      </td>
                      <td className="p-3">
                        {situacaoLabel[disciplina.situacao] ?? disciplina.situacao}
                      </td>
                      <td className="p-3">
                        <BarraProgresso disciplina={disciplina} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
