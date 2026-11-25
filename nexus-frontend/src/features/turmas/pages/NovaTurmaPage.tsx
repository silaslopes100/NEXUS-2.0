import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, ChevronRight } from 'lucide-react';
import { TurmaCargaHorariaPanel } from '@/features/carga_horaria/components/TurmaCargaHorariaPanel';
import { Turma, turmasApi } from '@/features/turmas/api';
import { TurmaAlunosPanel } from '@/features/turmas/components/TurmaAlunosPanel';
import { TurmaDadosForm, useOpcoesTurma } from '@/features/turmas/components/TurmaFormModal';
import { TurmaProfessoresPanel } from '@/features/turmas/components/TurmaProfessoresPanel';
import { baseTurmas } from '@/features/turmas/pages/TurmasPage';

const ETAPAS = [
  { titulo: 'Dados', descricao: 'Curso, unidade, turno, vagas e responsável' },
  { titulo: 'Professores', descricao: 'Um professor por disciplina do curso' },
  { titulo: 'Alunos', descricao: 'Matrícula na turma' },
  { titulo: 'Cronograma', descricao: 'Aulas previstas pelo calendário' },
];

/** Assistente de criação: a turma é criada na etapa 1; as demais podem ficar para depois. */
export const NovaTurmaPage: React.FC = () => {
  const navigate = useNavigate();
  const { role, isAdmin, isPolo, cursos, polos, escolas, erro } = useOpcoesTurma();
  const base = baseTurmas(role);
  const [etapa, setEtapa] = useState(0);
  const [turma, setTurma] = useState<Turma | null>(null);

  const recarregar = async () => {
    if (turma) setTurma(await turmasApi.obter(turma.id));
  };
  const irParaDetalhe = () => turma && navigate(`${base}/${turma.id}`);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="space-y-3">
        <Link to={base} className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-nexus-yellow">
          <ArrowLeft className="h-3.5 w-3.5" /> Voltar para as turmas
        </Link>
        <h1 className="text-2xl font-bold text-white">{turma ? turma.nome : 'Nova turma'}</h1>
        {turma && <p className="font-mono text-xs text-slate-400">{turma.codigo}</p>}
      </header>

      <ol className="grid gap-2 sm:grid-cols-4" aria-label="Etapas">
        {ETAPAS.map((e, i) => {
          const feita = i < etapa;
          const atual = i === etapa;
          return (
            <li
              key={e.titulo}
              aria-current={atual ? 'step' : undefined}
              className={`rounded-xl border p-3 ${atual ? 'border-blue-500 bg-blue-500/10' : feita ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-slate-800 bg-slate-900/60'}`}
            >
              <p className="flex items-center gap-2 text-xs font-bold text-white">
                <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${feita ? 'bg-emerald-500 text-ink' : atual ? 'bg-blue-500 text-on-accent' : 'bg-slate-800 text-slate-400'}`}>
                  {feita ? <Check className="h-3 w-3" aria-hidden /> : i + 1}
                </span>
                {e.titulo}
              </p>
              <p className="mt-1 text-[11px] text-slate-400">{e.descricao}</p>
            </li>
          );
        })}
      </ol>

      {erro && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}

      <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5 sm:p-6">
        {etapa === 0 && (
          <TurmaDadosForm
            turma={turma}
            cursos={cursos}
            polos={polos}
            escolas={escolas}
            mostrarPolo={isAdmin}
            mostrarEscola={isAdmin || isPolo}
            rotuloSalvar={turma ? 'Salvar e continuar' : 'Criar turma e continuar'}
            onCancel={() => (turma ? setEtapa(1) : navigate(base))}
            onSaved={(t) => {
              setTurma(t);
              setEtapa(1);
            }}
          />
        )}
        {etapa === 1 && turma && <TurmaProfessoresPanel turma={turma} embutido />}
        {etapa === 2 && turma && <TurmaAlunosPanel turma={turma} embutido onAlterado={() => void recarregar()} />}
        {etapa === 3 && turma && (
          <TurmaCargaHorariaPanel turma={turma} embutido podeGerar={isAdmin || isPolo} podeConcluir={false} />
        )}
      </section>

      {turma && etapa > 0 && (
        <footer className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setEtapa(etapa - 1)}
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800"
          >
            Voltar
          </button>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={irParaDetalhe}
              className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800"
            >
              Concluir depois
            </button>
            {etapa < ETAPAS.length - 1 ? (
              <button
                type="button"
                onClick={() => setEtapa(etapa + 1)}
                className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-blue-500"
              >
                Próxima etapa <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={irParaDetalhe}
                className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-emerald-500"
              >
                <Check className="h-4 w-4" /> Abrir a turma
              </button>
            )}
          </div>
        </footer>
      )}
    </div>
  );
};
