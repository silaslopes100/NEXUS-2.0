import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ChevronRight, ClipboardList } from 'lucide-react';
import { AtividadeDocente } from '@/features/aulas/api';
import { formatarData } from '@/features/turmas/api';

export const DIAS_ATIVIDADE = 30;
export const DIAS_SEM_REGISTRO = 14;

/** Painel "Atividade docente": leva direto para a auditoria de aulas já filtrada. */
export const AtividadeDocentePainel: React.FC<{
  atividade: AtividadeDocente | null;
  erro: boolean;
  inicioPeriodo: string;
}> = ({ atividade, erro, inicioPeriodo }) => (
  <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
    <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-bold text-white">
          <ClipboardList className="h-5 w-5 text-cyan-400" />
          Disciplinas com mais aulas ({DIAS_ATIVIDADE} dias)
        </h2>
        <Link to={`/admin/aulas?de=${inicioPeriodo}`} className="text-xs font-semibold text-nexus-yellow hover:underline">
          Ver todas
        </Link>
      </div>
      {erro ? (
        <p className="text-sm text-slate-500">Dados indisponíveis no momento.</p>
      ) : !atividade ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : atividade.top_disciplinas.length === 0 ? (
        <p className="text-sm text-slate-500">Nenhuma aula registrada no período.</p>
      ) : (
        <ul className="divide-y divide-slate-800">
          {atividade.top_disciplinas.map((d) => (
            <li key={d.id}>
              <Link
                to={`/admin/aulas?disciplina=${d.id}&de=${inicioPeriodo}`}
                className="flex items-center justify-between gap-3 py-2.5 text-sm text-slate-300 hover:text-white"
              >
                <span className="truncate">{d.nome}</span>
                <span className="flex shrink-0 items-center gap-1 font-semibold text-white">
                  {d.total_aulas} aula(s)
                  <ChevronRight className="h-4 w-4 text-slate-500" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>

    <section className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
      <h2 className="mb-1 flex items-center gap-2 text-base font-bold text-white">
        <AlertTriangle className="h-5 w-5 text-amber-400" />
        Polos sem aula registrada há {DIAS_SEM_REGISTRO} dias
      </h2>
      <p className="mb-4 text-xs text-slate-500">Polos com turma e professor vinculados, mas sem registro recente.</p>
      {erro ? (
        <p className="text-sm text-slate-500">Dados indisponíveis no momento.</p>
      ) : !atividade ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : atividade.polos_sem_registro.length === 0 ? (
        <p className="text-sm text-emerald-300">Todos os polos com turma registraram aulas recentemente.</p>
      ) : (
        <ul className="divide-y divide-slate-800">
          {atividade.polos_sem_registro.map((p) => (
            <li key={p.id}>
              <Link
                to={`/admin/aulas?polo=${p.id}`}
                className="flex items-center justify-between gap-3 py-2.5 text-sm text-slate-300 hover:text-white"
              >
                <span className="truncate">{p.nome}</span>
                <span className="flex shrink-0 items-center gap-1 text-xs text-slate-500">
                  {p.ultima_aula ? `última em ${formatarData(p.ultima_aula)}` : 'nenhuma aula'}
                  <ChevronRight className="h-4 w-4" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  </div>
);
