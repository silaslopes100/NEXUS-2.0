import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  Building2,
  CalendarDays,
  Clock3,
  GraduationCap,
  Loader2,
  MapPin,
  RefreshCw,
} from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { ProfessorDisciplinaResumo } from '@/types/professor';
import { formatarData } from '@/features/turmas/api';

export const MinhasDisciplinasPage: React.FC = () => {
  const [disciplinas, setDisciplinas] = useState<ProfessorDisciplinaResumo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [erro, setErro] = useState('');

  const carregarDisciplinas = useCallback(async () => {
    setIsLoading(true);
    setErro('');
    try {
      const resposta = await professoresApi.minhasDisciplinas();
      setDisciplinas(resposta.items);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar suas disciplinas.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregarDisciplinas();
  }, [carregarDisciplinas]);

  const totalTurmas = disciplinas.reduce((total, disciplina) => total + disciplina.turmas.length, 0);

  return (
    <div className="space-y-6 max-w-7xl">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <GraduationCap className="h-3.5 w-3.5" />
            Espaço do Docente
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Minhas Disciplinas &amp; Turmas
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Consulte as disciplinas e turmas vinculadas ao seu perfil.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-300">
          <span className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2">
            {disciplinas.length} disciplina(s)
          </span>
          <span className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2">
            {totalTurmas} turma(s)
          </span>
          <button
            type="button"
            onClick={() => void carregarDisciplinas()}
            disabled={isLoading}
            className="rounded-xl border border-slate-700 bg-slate-800 p-2 text-slate-300 transition-colors hover:bg-slate-700 disabled:opacity-50"
            aria-label="Atualizar disciplinas"
            title="Atualizar"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {erro && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
            <span>{erro}</span>
          </div>
          <button
            type="button"
            onClick={() => void carregarDisciplinas()}
            className="rounded-lg px-3 py-1.5 font-semibold text-red-100 hover:bg-red-500/15"
          >
            Tentar novamente
          </button>
        </div>
      )}

      <section className="space-y-4" aria-label="Disciplinas vinculadas">
        {isLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 py-16 text-center text-sm text-slate-400">
            <Loader2 className="mx-auto mb-3 h-6 w-6 animate-spin text-nexus-yellow" />
            Carregando suas disciplinas...
          </div>
        ) : erro ? null : disciplinas.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-16 text-center">
            <BookOpen className="mx-auto mb-3 h-8 w-8 text-slate-500" />
            <h2 className="font-semibold text-white">Nenhuma disciplina vinculada</h2>
            <p className="mt-1 text-sm text-slate-400">
              Quando suas disciplinas forem vinculadas, elas aparecerão nesta página.
            </p>
          </div>
        ) : (
          disciplinas.map((disciplina) => (
            <article
              key={disciplina.id}
              className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80 shadow-md"
            >
              <div className="flex flex-col gap-3 border-b border-slate-800 p-5 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="rounded-xl border border-nexus-yellow/20 bg-nexus-yellow/10 p-2.5 text-nexus-yellow">
                    <BookOpen className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">{disciplina.nome}</h2>
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400">
                      {disciplina.curso_nome && (
                        <span className="inline-flex items-center gap-1">
                          <GraduationCap className="h-3.5 w-3.5" />
                          {disciplina.curso_nome}
                        </span>
                      )}
                      {disciplina.semestre != null && <span>{disciplina.semestre}º semestre</span>}
                      {disciplina.carga_horaria != null && (
                        <span className="inline-flex items-center gap-1">
                          <Clock3 className="h-3.5 w-3.5" />
                          {disciplina.carga_horaria}h
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <span className="self-start rounded-full border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300">
                  {disciplina.turmas.length} turma(s)
                </span>
              </div>

              <div className="p-5">
                {disciplina.turmas.length === 0 ? (
                  <p className="text-sm text-slate-400">Ainda não há turma vinculada a esta disciplina.</p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {disciplina.turmas.map((turma) => (
                      <div
                        key={turma.id}
                        className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"
                      >
                        <div className="flex items-center gap-2 font-semibold text-slate-100">
                          <CalendarDays className="h-4 w-4 text-blue-400" />
                          {turma.nome}
                        </div>
                        {(turma.data_inicio || turma.data_fim) && (
                          <p className="mt-2 text-xs text-slate-400">
                            Período: {formatarData(turma.data_inicio)} – {formatarData(turma.data_fim)}
                          </p>
                        )}
                        {(turma.polo_nome || turma.escola_nome) && (
                          <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-400">
                            {turma.escola_nome ? (
                              <Building2 className="h-3.5 w-3.5" />
                            ) : (
                              <MapPin className="h-3.5 w-3.5" />
                            )}
                            {[turma.polo_nome, turma.escola_nome].filter(Boolean).join(' · ')}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
};
