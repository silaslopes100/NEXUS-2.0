import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import {
  Academico,
  alunosGestaoApi,
  apiErrorMessage,
  DisciplinaAcademica,
} from '@/features/alunos/api';

export const BarraProgresso: React.FC<{ disciplina: DisciplinaAcademica }> = ({ disciplina }) => {
  if (disciplina.progresso == null) {
    return <span className="text-xs text-slate-500">Sem conteúdo</span>;
  }
  return (
    <div
      className="flex items-center gap-2"
      title={`${disciplina.conteudos_concluidos} de ${disciplina.total_conteudos} conteúdos`}
    >
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-800">
        <div className="h-full bg-blue-500" style={{ width: `${disciplina.progresso}%` }} />
      </div>
      <span className="w-9 text-right text-xs text-slate-300">{disciplina.progresso}%</span>
    </div>
  );
};

export const DisciplinasExpandidas: React.FC<{ alunoId: string }> = ({ alunoId }) => {
  const [dados, setDados] = useState<Academico | null>(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    let ativo = true;
    alunosGestaoApi
      .academico(alunoId)
      .then((resposta) => {
        if (ativo) setDados(resposta);
      })
      .catch((err: unknown) => {
        if (ativo) setErro(apiErrorMessage(err, 'Não foi possível carregar as disciplinas.'));
      });
    return () => {
      ativo = false;
    };
  }, [alunoId]);

  if (erro) return <p className="text-sm text-red-300">{erro}</p>;
  if (!dados) return <Loader2 size={16} className="animate-spin text-blue-400" />;

  const cursos = dados.cursos
    .map((curso) => ({ ...curso, disciplinas: curso.disciplinas.filter((d) => d.em_curso) }))
    .filter((curso) => curso.disciplinas.length > 0);

  if (cursos.length === 0) {
    return <p className="text-sm text-slate-500">Nenhuma disciplina em curso.</p>;
  }

  return (
    <div className="space-y-3">
      {cursos.map((curso) => (
        <div key={curso.id}>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
            {curso.nome}
          </p>
          <ul className="space-y-1.5">
            {curso.disciplinas.map((disciplina) => (
              <li
                key={disciplina.id}
                className="flex max-w-xl items-center justify-between gap-4 text-sm text-slate-200"
              >
                <span className="min-w-0 truncate">{disciplina.nome}</span>
                <BarraProgresso disciplina={disciplina} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};
