import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  GraduationCap,
  Loader2,
  Plus,
  Search,
  X,
} from 'lucide-react';
import {
  Curso,
  CursoCreate,
  cursosApi,
  cursosApiErrorMessage,
  Disciplina,
  ModalidadeCurso,
  NivelAcademico,
  StatusCurso,
  Turma,
} from '@/features/cursos/api';
import { useAuthStore } from '@/stores/authStore';

const nivelLabel: Record<NivelAcademico, string> = {
  bacharelado: 'Bacharelado',
  licenciatura: 'Licenciatura',
  tecnologo: 'Tecnólogo',
  pos_graduacao: 'Pós-graduação',
  mestrado: 'Mestrado',
};

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500';

const initialForm: CursoCreate = {
  nome: '',
  descricao: '',
  nivel_academico: 'bacharelado',
  modalidade: 'hibrido',
  carga_horaria_total: 1,
  semestres: 1,
  status: 'ativo',
};

export const CursosPage: React.FC = () => {
  const { perfil } = useAuthStore();
  const isAdmin = perfil?.nome?.toLowerCase() === 'admin';
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [selectedCurso, setSelectedCurso] = useState<Curso | null>(null);
  const [activeTab, setActiveTab] = useState<'disciplinas' | 'turmas'>('disciplinas');
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState<CursoCreate>(initialForm);
  const [formError, setFormError] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null
  );

  useEffect(() => {
    let active = true;
    cursosApi
      .listar()
      .then((items) => {
        if (active) setCursos(items);
      })
      .catch((err: unknown) => {
        if (active) setError(cursosApiErrorMessage(err, 'Não foi possível carregar os cursos.'));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedCurso) return;
    let active = true;
    setDetailsLoading(true);
    setDetailsError('');
    Promise.all([
      cursosApi.listarDisciplinas(selectedCurso.id),
      cursosApi.listarTurmas(selectedCurso.id),
    ])
      .then(([disciplinasItems, turmasItems]) => {
        if (active) {
          setDisciplinas(disciplinasItems);
          setTurmas(turmasItems);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setDetailsError(
            cursosApiErrorMessage(err, 'Não foi possível carregar as disciplinas e turmas.')
          );
        }
      })
      .finally(() => {
        if (active) setDetailsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedCurso]);

  const cursosFiltrados = useMemo(() => {
    const termo = search.trim().toLocaleLowerCase('pt-BR');
    if (!termo) return cursos;
    return cursos.filter(
      (curso) =>
        curso.nome.toLocaleLowerCase('pt-BR').includes(termo) ||
        (curso.descricao || '').toLocaleLowerCase('pt-BR').includes(termo) ||
        (curso.nivel_academico ? nivelLabel[curso.nivel_academico] : '')
          .toLocaleLowerCase('pt-BR')
          .includes(termo)
    );
  }, [cursos, search]);

  const abrirDetalhes = (curso: Curso, tab: 'disciplinas' | 'turmas') => {
    setDisciplinas([]);
    setTurmas([]);
    setActiveTab(tab);
    setSelectedCurso(curso);
  };

  const salvarCurso = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setFormError('');
    setFeedback(null);
    try {
      const cursoCriado = await cursosApi.criar({
        ...form,
        nome: form.nome.trim(),
        descricao: form.descricao.trim(),
      });
      setCursos((atuais) =>
        [...atuais, cursoCriado].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
      );
      setForm(initialForm);
      setIsCreateOpen(false);
      setFeedback({ type: 'success', message: 'Curso cadastrado com sucesso.' });
    } catch (err) {
      setFormError(cursosApiErrorMessage(err, 'Não foi possível cadastrar o curso.'));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300">
            <GraduationCap size={16} />
            Gestão curricular
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">Cursos</h1>
          <p className="mt-1 text-sm text-slate-400">
            Consulte os cursos, seus níveis acadêmicos, disciplinas e turmas vinculadas.
          </p>
        </div>
        {isAdmin && (
          <button
            type="button"
            disabled={isLoading}
            onClick={() => {
              setForm(initialForm);
              setFormError('');
              setIsCreateOpen(true);
            }}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Plus size={17} />
            Cadastrar curso
          </button>
        )}
      </header>

      {feedback && (
        <div
          role={feedback.type === 'error' ? 'alert' : 'status'}
          className={`flex items-center justify-between gap-3 rounded-xl border p-3 text-sm ${
            feedback.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
              : 'border-red-500/30 bg-red-500/10 text-red-200'
          }`}
        >
          <span className="flex items-center gap-2">
            {feedback.type === 'success' ? <CheckCircle2 size={17} /> : <AlertCircle size={17} />}
            {feedback.message}
          </span>
          <button type="button" aria-label="Fechar mensagem" onClick={() => setFeedback(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex flex-col gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-bold text-white">Lista de cursos</h2>
            <p className="text-xs text-slate-500">{cursosFiltrados.length} cursos</p>
          </div>
          <div className="relative w-full sm:max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              aria-label="Buscar curso"
              className={inputClass}
              placeholder="Buscar por nome, descrição ou nível"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {error && (
          <div role="alert" className="m-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-16 text-blue-400">
            <Loader2 className="animate-spin" />
          </div>
        ) : !error ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="p-4">Nome</th>
                  <th className="p-4">Descrição</th>
                  <th className="p-4">Nível Acadêmico</th>
                  <th className="p-4 text-center">Disciplinas</th>
                  <th className="p-4 text-center">Turmas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {cursosFiltrados.map((curso) => (
                  <tr key={curso.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4 font-semibold text-white">{curso.nome}</td>
                    <td className="max-w-sm p-4 text-slate-400">
                      <span className="line-clamp-2">{curso.descricao || '—'}</span>
                    </td>
                    <td className="p-4">
                      {curso.nivel_academico ? nivelLabel[curso.nivel_academico] : 'Não informado'}
                    </td>
                    <td className="p-4 text-center">
                      <button
                        type="button"
                        onClick={() => abrirDetalhes(curso, 'disciplinas')}
                        className="inline-flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-semibold text-blue-200 hover:bg-blue-500/20"
                      >
                        <BookOpen size={14} />
                        Ver disciplinas
                      </button>
                    </td>
                    <td className="p-4 text-center">
                      <button
                        type="button"
                        onClick={() => abrirDetalhes(curso, 'turmas')}
                        className="inline-flex items-center gap-2 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-200 hover:bg-indigo-500/20"
                      >
                        <CalendarDays size={14} />
                        Ver turmas
                      </button>
                    </td>
                  </tr>
                ))}
                {cursosFiltrados.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-slate-500">
                      {cursos.length ? 'Nenhum curso corresponde à busca.' : 'Nenhum curso cadastrado.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {isCreateOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isSaving) setIsCreateOpen(false);
          }}
        >
          <form
            onSubmit={salvarCurso}
            className="my-auto w-full max-w-2xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
          >
            <header className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-blue-300">
                  Gestão curricular
                </p>
                <h2 className="mt-1 text-xl font-bold text-white">Cadastrar curso</h2>
                <p className="mt-1 text-sm text-slate-400">Preencha os dados obrigatórios do curso.</p>
              </div>
              <button
                type="button"
                aria-label="Fechar cadastro"
                disabled={isSaving}
                onClick={() => setIsCreateOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
              >
                <X size={20} />
              </button>
            </header>

            {formError && (
              <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                {formError}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
                <span>Nome *</span>
                <input
                  autoFocus
                  required
                  minLength={2}
                  maxLength={255}
                  className={inputClass}
                  value={form.nome}
                  onChange={(event) => setForm({ ...form, nome: event.target.value })}
                />
              </label>

              <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
                <span>Descrição *</span>
                <textarea
                  required
                  rows={3}
                  className={inputClass}
                  value={form.descricao}
                  onChange={(event) => setForm({ ...form, descricao: event.target.value })}
                />
              </label>

              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Nível acadêmico *</span>
                <select
                  required
                  className={inputClass}
                  value={form.nivel_academico}
                  onChange={(event) =>
                    setForm({ ...form, nivel_academico: event.target.value as NivelAcademico })
                  }
                >
                  {Object.entries(nivelLabel).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>

              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Modalidade *</span>
                <select
                  required
                  className={inputClass}
                  value={form.modalidade}
                  onChange={(event) =>
                    setForm({ ...form, modalidade: event.target.value as ModalidadeCurso })
                  }
                >
                  <option value="hibrido">Híbrido</option>
                  <option value="presencial">Presencial</option>
                  <option value="ead">EAD (Online)</option>
                </select>
              </label>

              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Carga horária total *</span>
                <input
                  required
                  type="number"
                  min={1}
                  step={1}
                  className={inputClass}
                  value={form.carga_horaria_total}
                  onChange={(event) =>
                    setForm({ ...form, carga_horaria_total: Number(event.target.value) })
                  }
                />
              </label>

              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Semestres *</span>
                <input
                  required
                  type="number"
                  min={1}
                  step={1}
                  className={inputClass}
                  value={form.semestres}
                  onChange={(event) => setForm({ ...form, semestres: Number(event.target.value) })}
                />
              </label>

              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Status *</span>
                <select
                  required
                  className={inputClass}
                  value={form.status}
                  onChange={(event) =>
                    setForm({ ...form, status: event.target.value as StatusCurso })
                  }
                >
                  <option value="ativo">Ativo</option>
                  <option value="cancelado">Cancelado</option>
                </select>
              </label>
            </div>

            <footer className="flex flex-col-reverse justify-end gap-2 border-t border-slate-800 pt-4 sm:flex-row">
              <button
                type="button"
                disabled={isSaving}
                onClick={() => setIsCreateOpen(false)}
                className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isSaving}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving && <Loader2 size={16} className="animate-spin" />}
                {isSaving ? 'Salvando...' : 'Salvar curso'}
              </button>
            </footer>
          </form>
        </div>
      )}

      {selectedCurso && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelectedCurso(null);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="curso-detalhes-titulo"
            className="max-h-[85vh] w-full max-w-3xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-800 p-5 sm:p-6">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-blue-300">Detalhes do curso</p>
                <h2 id="curso-detalhes-titulo" className="mt-1 text-xl font-bold text-white">
                  {selectedCurso.nome}
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  {selectedCurso.nivel_academico ? nivelLabel[selectedCurso.nivel_academico] : 'Nível não informado'}
                </p>
              </div>
              <button
                type="button"
                aria-label="Fechar detalhes"
                onClick={() => setSelectedCurso(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X size={20} />
              </button>
            </header>

            <div className="flex gap-2 border-b border-slate-800 px-5 pt-4 sm:px-6">
              <button
                type="button"
                onClick={() => setActiveTab('disciplinas')}
                className={`rounded-t-lg px-4 py-2 text-sm font-semibold ${
                  activeTab === 'disciplinas'
                    ? 'border-b-2 border-blue-400 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Disciplinas ({disciplinas.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('turmas')}
                className={`rounded-t-lg px-4 py-2 text-sm font-semibold ${
                  activeTab === 'turmas'
                    ? 'border-b-2 border-indigo-400 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Turmas ({turmas.length})
              </button>
            </div>

            <div className="max-h-[55vh] overflow-y-auto p-5 sm:p-6">
              {detailsError && (
                <div role="alert" className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                  {detailsError}
                </div>
              )}
              {detailsLoading ? (
                <div className="flex justify-center py-12 text-blue-400">
                  <Loader2 className="animate-spin" />
                </div>
              ) : activeTab === 'disciplinas' ? (
                <div className="space-y-3">
                  {disciplinas.map((disciplina) => (
                    <article key={disciplina.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <h3 className="font-semibold text-white">{disciplina.nome}</h3>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                        {disciplina.semestre != null && <span>Semestre {disciplina.semestre}</span>}
                        {disciplina.carga_horaria != null && <span>{disciplina.carga_horaria} horas</span>}
                        {disciplina.qtd_aulas_prevista != null && (
                          <span>{disciplina.qtd_aulas_prevista} aulas previstas</span>
                        )}
                      </div>
                    </article>
                  ))}
                  {!detailsError && disciplinas.length === 0 && (
                    <p className="py-10 text-center text-sm text-slate-500">Nenhuma disciplina vinculada ao curso.</p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {turmas.map((turma) => (
                    <article key={turma.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <h3 className="font-semibold text-white">{turma.nome}</h3>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                        <span>Início: {turma.data_inicio || 'Não informado'}</span>
                        <span>Fim: {turma.data_fim || 'Não informado'}</span>
                      </div>
                    </article>
                  ))}
                  {!detailsError && turmas.length === 0 && (
                    <p className="py-10 text-center text-sm text-slate-500">Nenhuma turma vinculada ao curso.</p>
                  )}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
