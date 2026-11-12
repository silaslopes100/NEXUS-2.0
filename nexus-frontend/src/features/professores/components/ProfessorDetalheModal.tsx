import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { ProfessorDetalhe } from '@/types/professor';

interface Props {
  professorId: string;
  onClose: () => void;
}

export const ProfessorDetalheModal: React.FC<Props> = ({ professorId, onClose }) => {
  const [detalhe, setDetalhe] = useState<ProfessorDetalhe | null>(null);
  const [erro, setErro] = useState('');
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let active = true;
    setDetalhe(null);
    setErro('');
    professoresApi.detalhe(professorId)
      .then((data) => { if (active) setDetalhe(data); })
      .catch((error: unknown) => {
        if (active) setErro(apiErrorMessage(error, 'Não foi possível carregar o detalhe do professor.'));
      });
    return () => { active = false; };
  }, [professorId, tentativa]);

  const grupos = useMemo(() => {
    const polos = new Map<string, {
      nome: string;
      escolas: Map<string, { nome: string; turmas: ProfessorDetalhe['turmas'] }>;
    }>();
    for (const turma of detalhe?.turmas ?? []) {
      const poloId = turma.polo_id ?? '';
      const escolaId = turma.escola_id ?? '';
      if (!polos.has(poloId)) polos.set(poloId, { nome: turma.polo_nome || 'Sem polo', escolas: new Map() });
      const polo = polos.get(poloId)!;
      if (!polo.escolas.has(escolaId)) polo.escolas.set(escolaId, { nome: turma.escola_nome || 'Sem escola', turmas: [] });
      polo.escolas.get(escolaId)!.turmas.push(turma);
    }
    return Array.from(polos.entries());
  }, [detalhe]);

  const cursos = useMemo(() => {
    const itens = new Map<string, string>();
    for (const disciplina of detalhe?.disciplinas ?? []) {
      if (disciplina.curso_id) itens.set(disciplina.curso_id, disciplina.curso_nome || 'Curso sem nome');
    }
    return Array.from(itens.entries());
  }, [detalhe]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section role="dialog" aria-modal="true" aria-labelledby="detalhe-professor-titulo"
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 id="detalhe-professor-titulo" className="text-xl font-bold text-white">Detalhe do professor</h2>
            {detalhe && <p className="mt-1 text-sm text-slate-400">{detalhe.professor.nome || 'Sem nome'} · {detalhe.professor.email || 'Sem e-mail'}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar detalhe" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </header>

        {erro ? (
          <div role="alert" className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            {erro} <button type="button" onClick={() => setTentativa(tentativa + 1)} className="ml-2 underline">Tentar novamente</button>
          </div>
        ) : !detalhe ? (
          <div className="py-12 text-center text-sm text-slate-400"><Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin" />Carregando detalhe...</div>
        ) : (
          <div className="mt-6 space-y-6">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-200">
              <strong>{detalhe.professor.horas_totais ?? 0}h</strong> · {detalhe.professor.quantidade_aulas ?? 0} aulas previstas
              <p className="mt-1 text-xs text-slate-400">Soma das disciplinas vinculadas no cadastro.</p>
            </div>
            <section aria-label="Cursos">
              <h3 className="mb-2 font-semibold text-white">Cursos</h3>
              {cursos.length ? <ul className="flex flex-wrap gap-2">{cursos.map(([id, nome]) => <li key={id} className="rounded-lg bg-slate-800 px-3 py-1 text-sm text-slate-200">{nome}</li>)}</ul> : <p className="text-sm text-slate-400">Nenhum curso vinculado.</p>}
            </section>
            <section aria-label="Disciplinas">
              <h3 className="mb-2 font-semibold text-white">Disciplinas</h3>
              {detalhe.disciplinas.length ? (
                <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800">
                  {detalhe.disciplinas.map((disciplina) => (
                    <li key={disciplina.id} className="flex flex-wrap justify-between gap-2 p-3 text-sm text-slate-200">
                      <span>{disciplina.nome} <span className="text-slate-500">· {disciplina.curso_nome || 'Sem curso'}</span></span>
                      <span>{disciplina.carga_horaria ?? 0}h · {disciplina.qtd_aulas_prevista ?? 0} aulas</span>
                    </li>
                  ))}
                </ul>
              ) : <p className="text-sm text-slate-400">Nenhuma disciplina vinculada no cadastro.</p>}
            </section>
            <section aria-label="Alunos por polo, escola e turma">
              <h3 className="mb-2 font-semibold text-white">Alunos por polo, escola e turma</h3>
              {grupos.length ? grupos.map(([poloId, polo]) => (
                <div key={poloId} className="mt-3 rounded-xl border border-slate-800 p-4">
                  <h4 className="font-semibold text-nexus-yellow">{polo.nome}</h4>
                  {Array.from(polo.escolas.entries()).map(([escolaId, escola]) => (
                    <div key={escolaId} className="mt-3">
                      <h5 className="text-sm font-semibold text-white">{escola.nome}</h5>
                      {escola.turmas.map((turma) => (
                        <div key={turma.id} className="mt-2 rounded-lg bg-slate-950 p-3">
                          <p className="text-sm font-semibold text-slate-200">{turma.nome}</p>
                          {turma.alunos.length ? <ul className="mt-2 space-y-1 text-xs text-slate-400">{turma.alunos.map((aluno) => (
                            <li key={aluno.id}>{aluno.nome || 'Sem nome'} · {aluno.numero_matricula || 'Sem matrícula'} · {aluno.email || 'Sem e-mail'}</li>
                          ))}</ul> : <p className="mt-2 text-xs text-slate-400">Nenhum aluno ativo nesta turma.</p>}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )) : <p className="text-sm text-slate-400">Nenhuma turma vinculada às disciplinas do cadastro.</p>}
            </section>
          </div>
        )}
      </section>
    </div>
  );
};
