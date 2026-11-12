import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, GraduationCap, Loader2, Search, UserRoundX, X } from 'lucide-react';
import { cursosApi, Disciplina } from '@/features/cursos/api';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { ProfessorDisponivel, ProfessorTurmaVinculo, rotuloLotacao } from '@/types/professor';
import { Turma } from '@/features/turmas/api';
import { inputCls } from '@/features/turmas/components/TurmaFormModal';

interface Props {
  turma: Turma;
  onClose: () => void;
}

export const TurmaProfessoresPanel: React.FC<Props> = ({ turma, onClose }) => {
  const [vinculos, setVinculos] = useState<ProfessorTurmaVinculo[]>([]);
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [professores, setProfessores] = useState<ProfessorDisponivel[]>([]);
  const [professorId, setProfessorId] = useState('');
  const [disciplinaId, setDisciplinaId] = useState('');
  const [buscaProfessor, setBuscaProfessor] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [buscandoProfessores, setBuscandoProfessores] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [arquivandoId, setArquivandoId] = useState<string | null>(null);
  const [erro, setErro] = useState('');
  const [erroBusca, setErroBusca] = useState('');
  const [feedback, setFeedback] = useState('');

  const disciplinasDoCurso = useMemo(
    () => disciplinas.filter((disciplina) => disciplina.curso_id === turma.curso_id),
    [disciplinas, turma.curso_id]
  );

  const carregarVinculos = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const [atuais, disciplinasDisponiveis] = await Promise.all([
        professoresApi.listarVinculosTurma(turma.id),
        cursosApi.listarDisciplinas(),
      ]);
      setVinculos(atuais);
      setDisciplinas(disciplinasDisponiveis);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar os vínculos desta turma.'));
    } finally {
      setCarregando(false);
    }
  }, [turma.id]);

  useEffect(() => {
    void carregarVinculos();
  }, [carregarVinculos]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setBuscandoProfessores(true);
      setErroBusca('');
      professoresApi
        .disponiveis(buscaProfessor.trim() || undefined)
        .then((items) => {
          if (active) setProfessores(items);
        })
        .catch((error: unknown) => {
          if (active) setErroBusca(apiErrorMessage(error, 'Não foi possível buscar professores.'));
        })
        .finally(() => {
          if (active) setBuscandoProfessores(false);
        });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [buscaProfessor]);

  const professorSelecionado = professores.find((professor) => professor.id === professorId);
  const atendeTurma = Boolean(
    professorSelecionado?.lotacoes.some(
      (lotacao) =>
        lotacao.polo_id === turma.polo_id &&
        (!lotacao.escola_id || lotacao.escola_id === turma.escola_id)
    )
  );

  const jaVinculado = vinculos.some(
    (vinculo) =>
      vinculo.professor_id === professorId && vinculo.disciplina_id === disciplinaId
  );

  const vincular = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!professorId || !disciplinaId) return;
    setSalvando(true);
    setErro('');
    setFeedback('');
    try {
      await professoresApi.vincularProfessorTurma(turma.id, professorId, disciplinaId);
      setProfessorId('');
      setDisciplinaId('');
      setFeedback('Professor vinculado à disciplina nesta turma.');
      await carregarVinculos();
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível vincular o professor.'));
    } finally {
      setSalvando(false);
    }
  };

  const arquivar = async (vinculo: ProfessorTurmaVinculo) => {
    if (!window.confirm(
      `Arquivar o vínculo de ${vinculo.professor_nome} com ${vinculo.disciplina_nome}? Materiais e atas serão preservados.`
    )) {
      return;
    }
    setErro('');
    setFeedback('');
    setArquivandoId(vinculo.id);
    try {
      const mensagem = await professoresApi.arquivarVinculoTurma(turma.id, vinculo.id);
      setFeedback(mensagem);
      await carregarVinculos();
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível arquivar o vínculo.'));
    } finally {
      setArquivandoId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/75 p-4 backdrop-blur-sm">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="turma-professores-titulo"
        className="my-auto max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-nexus-yellow">
              <GraduationCap className="h-4 w-4" /> Gestão de docentes
            </p>
            <h2 id="turma-professores-titulo" className="mt-1 text-xl font-bold text-white">
              {turma.nome}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Associe professores a disciplinas do curso desta turma.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar gestão de docentes"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {(erro || erroBusca) && (
          <div role="alert" className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {erro || erroBusca}
          </div>
        )}
        {feedback && (
          <p role="status" className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
            {feedback}
          </p>
        )}

        <form onSubmit={vincular} className="mt-5 grid gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <div className="space-y-1 text-xs font-semibold text-slate-300">
            <label htmlFor="buscar-professor-turma">Professor</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                id="buscar-professor-turma"
                type="search"
                value={buscaProfessor}
                onChange={(event) => setBuscaProfessor(event.target.value)}
                placeholder="Buscar por nome ou e-mail"
                className={`${inputCls} pl-9`}
              />
            </div>
            <select
              id="professor-vinculo-turma"
              aria-label="Selecionar professor"
              value={professorId}
              onChange={(event) => setProfessorId(event.target.value)}
              className={inputCls}
              required
            >
              <option value="">Selecione um professor</option>
              {professores.map((professor) => (
                <option key={professor.id} value={professor.id}>
                  {professor.nome || professor.email || professor.id}
                  {professor.lotacoes.length
                    ? ` — ${professor.lotacoes.map(rotuloLotacao).join(', ')}`
                    : ' — sem polo'}
                </option>
              ))}
            </select>
            {buscandoProfessores && <p className="text-slate-500">Buscando...</p>}
            {!buscandoProfessores && professores.length === 0 && (
              <p className="text-amber-300">Nenhum professor ativo encontrado.</p>
            )}
            {professorSelecionado && !atendeTurma && (
              <p className="font-normal text-sky-300">
                Ao vincular, {professorSelecionado.nome || 'o professor'} passa a atender também este
                polo/escola.
              </p>
            )}
          </div>

          <div className="space-y-1 text-xs font-semibold text-slate-300">
            <label htmlFor="disciplina-vinculo-turma">Disciplina do curso</label>
            <select
              id="disciplina-vinculo-turma"
              value={disciplinaId}
              onChange={(event) => setDisciplinaId(event.target.value)}
              className={inputCls}
              disabled={!turma.curso_id || carregando}
              required
            >
              <option value="">Selecione uma disciplina</option>
              {disciplinasDoCurso.map((disciplina) => (
                <option key={disciplina.id} value={disciplina.id}>
                  {disciplina.nome}
                </option>
              ))}
            </select>
            {!turma.curso_id && (
              <span className="text-amber-300">Esta turma não possui curso associado.</span>
            )}
            {turma.curso_id && !carregando && disciplinasDoCurso.length === 0 && (
              <span className="text-amber-300">O curso não possui disciplinas cadastradas.</span>
            )}
          </div>

          <button
            type="submit"
            disabled={salvando || carregando || !professores.length || !disciplinasDoCurso.length || jaVinculado}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2 text-xs font-bold text-slate-950 hover:bg-nexus-yellow-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {salvando && <Loader2 className="h-4 w-4 animate-spin" />}
            Vincular
          </button>
          {jaVinculado && (
            <p className="text-xs text-amber-300 md:col-span-3">
              Este professor já está vinculado a essa disciplina nesta turma.
            </p>
          )}
        </form>

        <section aria-label="Professores vinculados" className="mt-6">
          <h3 className="mb-3 text-sm font-bold text-white">Vínculos atuais</h3>
          {carregando ? (
            <div className="py-8 text-center text-sm text-slate-400">
              <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />
              Carregando vínculos...
            </div>
          ) : vinculos.length === 0 ? (
            <p className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-400">
              Nenhum professor está vinculado a esta turma.
            </p>
          ) : (
            <ul className="space-y-2">
              {vinculos.map((vinculo) => (
                <li key={vinculo.id} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-semibold text-white">{vinculo.professor_nome}</p>
                    <p className="text-sm text-slate-300">{vinculo.disciplina_nome}</p>
                    {vinculo.professor_email && (
                      <p className="text-xs text-slate-500">{vinculo.professor_email}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => void arquivar(vinculo)}
                    disabled={arquivandoId !== null || carregando}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-500/30 px-3 py-2 text-xs font-semibold text-red-200 hover:bg-red-500/10"
                  >
                    {arquivandoId === vinculo.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <UserRoundX className="h-4 w-4" />
                    )}
                    {arquivandoId === vinculo.id ? 'Arquivando...' : 'Arquivar vínculo'}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Arquivar um vínculo preserva materiais e atas associados.
          </p>
        </section>
      </section>
    </div>
  );
};
