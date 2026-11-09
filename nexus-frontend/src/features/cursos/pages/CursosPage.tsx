import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  GraduationCap,
  Loader2,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import {
  Curso,
  CursoCreate,
  CursoUpdate,
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
  curso_livre: 'Curso livre',
  mestrado: 'Mestrado',
};

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500';
const PAGE_SIZE = 10;

// Cursos do legado podem não ter nível; o campo vazio obriga a escolha ao editar.
type CursoForm = Omit<CursoCreate, 'nivel_academico'> & { nivel_academico: NivelAcademico | '' };

const initialForm: CursoForm = {
  nome: '',
  descricao: '',
  nivel_academico: 'bacharelado',
  modalidade: 'hibrido',
  carga_horaria_total: 1,
  semestres: 1,
  status: 'ativo',
  disciplina_ids: [],
};

export const CursosPage: React.FC = () => {
  const { perfil } = useAuthStore();
  const isAdmin = perfil?.nome?.toLowerCase() === 'admin';
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [totalCursos, setTotalCursos] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [offset, setOffset] = useState(0);
  const [selectedCurso, setSelectedCurso] = useState<Curso | null>(null);
  const [activeTab, setActiveTab] = useState<'disciplinas' | 'turmas'>('disciplinas');
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editing, setEditing] = useState<Curso | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [form, setForm] = useState<CursoForm>(initialForm);
  const [disciplinasDisponiveis, setDisciplinasDisponiveis] = useState<Disciplina[]>([]);
  const [disciplinasCarregadas, setDisciplinasCarregadas] = useState(false);
  const [disciplinasLoading, setDisciplinasLoading] = useState(false);
  const [disciplinasError, setDisciplinasError] = useState('');
  const [buscaDisciplina, setBuscaDisciplina] = useState('');
  const [formError, setFormError] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null
  );

  useEffect(() => {
    const busca = search.trim();
    if (busca === buscaAplicada) return;
    const timeout = window.setTimeout(() => {
      setOffset(0);
      setBuscaAplicada(busca);
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [buscaAplicada, search]);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError('');
    cursosApi
      .listarPaginado({ q: buscaAplicada || undefined, limit: PAGE_SIZE, offset })
      .then((page) => {
        if (active) {
          setCursos(page.items);
          setTotalCursos(page.total);
        }
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
  }, [buscaAplicada, offset, reloadKey]);

  useEffect(() => {
    if (!isFormOpen) return;
    if (disciplinasCarregadas) return;
    let active = true;
    setDisciplinasLoading(true);
    setDisciplinasError('');
    cursosApi
      .listarDisciplinas()
      .then((items) => {
        if (active) {
          setDisciplinasDisponiveis(items);
          setDisciplinasCarregadas(true);
          if (editing) {
            setForm((current) => ({
              ...current,
              disciplina_ids: items
                .filter((item) => item.curso_id === editing.id)
                .map((item) => item.id),
            }));
          }
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setDisciplinasError(
            cursosApiErrorMessage(err, 'Não foi possível carregar as disciplinas.')
          );
        }
      })
      .finally(() => {
        if (active) setDisciplinasLoading(false);
      });
    return () => {
      active = false;
    };
  }, [disciplinasCarregadas, editing, isFormOpen]);

  useEffect(() => {
    if (!selectedCurso) return;
    let active = true;
    setDetailsLoading(true);
    setDetailsError('');
    cursosApi
      .detalhesCurso(selectedCurso.id)
      .then(({ disciplinas: disciplinasItems, turmas: turmasItems }) => {
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

  const disciplinasFiltradas = useMemo(() => {
    const termo = buscaDisciplina.trim().toLocaleLowerCase('pt-BR');
    return disciplinasDisponiveis.filter((disciplina) =>
      disciplina.nome.toLocaleLowerCase('pt-BR').includes(termo)
    );
  }, [buscaDisciplina, disciplinasDisponiveis]);

  const abrirDetalhes = (curso: Curso, tab: 'disciplinas' | 'turmas') => {
    setDisciplinas([]);
    setTurmas([]);
    setActiveTab(tab);
    setSelectedCurso(curso);
  };

  const abrirCadastro = () => {
    setEditing(null);
    setForm(initialForm);
    setFormError('');
    setBuscaDisciplina('');
    setIsFormOpen(true);
  };

  const abrirEdicao = (curso: Curso) => {
    setEditing(curso);
    setForm({
      nome: curso.nome,
      descricao: curso.descricao ?? '',
      nivel_academico: curso.nivel_academico ?? '',
      modalidade: curso.modalidade ?? 'hibrido',
      carga_horaria_total: curso.carga_horaria_total ?? 0,
      semestres: curso.semestres ?? 3,
      status: curso.status ?? 'ativo',
      disciplina_ids: [],
    });
    setFormError('');
    setBuscaDisciplina('');
    // Recarrega para marcar os vínculos atuais do curso a partir de dados atualizados.
    setDisciplinasCarregadas(false);
    setIsFormOpen(true);
  };

  const excluirCurso = async (curso: Curso) => {
    if (!window.confirm(`Deseja excluir o curso "${curso.nome}"?`)) return;
    setDeletingId(curso.id);
    setFeedback(null);
    try {
      await cursosApi.excluir(curso.id);
      if (cursos.length === 1 && offset > 0) {
        setOffset((current) => Math.max(0, current - PAGE_SIZE));
      } else {
        setReloadKey((current) => current + 1);
      }
      setFeedback({ type: 'success', message: 'Curso excluído com sucesso.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        message: cursosApiErrorMessage(
          err,
          'Não foi possível excluir o curso. Verifique se há vínculos acadêmicos.'
        ),
      });
    } finally {
      setDeletingId(null);
    }
  };

  const salvarCurso = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setFormError('');
    setFeedback(null);
    const dados = {
      ...form,
      nome: form.nome.trim(),
      descricao: form.descricao.trim(),
      nivel_academico: form.nivel_academico as NivelAcademico,
    };
    try {
      if (editing) {
        // Sem a lista carregada, omitir os ids evita desvincular as disciplinas do curso.
        const payload: CursoUpdate = disciplinasCarregadas
          ? dados
          : { ...dados, disciplina_ids: undefined };
        await cursosApi.atualizar(editing.id, payload);
        setDisciplinasCarregadas(false);
        setReloadKey((current) => current + 1);
        setIsFormOpen(false);
        setFeedback({ type: 'success', message: 'Curso atualizado com sucesso.' });
        return;
      }
      const cursoCriado = await cursosApi.criar(dados);
      setDisciplinasDisponiveis((items) =>
        items.map((item) =>
          form.disciplina_ids.includes(item.id) ? { ...item, curso_id: cursoCriado.id } : item
        )
      );
      setSearch(cursoCriado.nome);
      setBuscaAplicada(cursoCriado.nome);
      setOffset(0);
      setForm(initialForm);
      setIsFormOpen(false);
      setFeedback({
        type: 'success',
        message:
          form.disciplina_ids.length > 0
            ? `Curso cadastrado com ${form.disciplina_ids.length} disciplina(s) vinculada(s).`
            : 'Curso cadastrado com sucesso.',
      });
    } catch (err) {
      setFormError(
        cursosApiErrorMessage(
          err,
          editing ? 'Não foi possível atualizar o curso.' : 'Não foi possível cadastrar o curso.'
        )
      );
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
            onClick={abrirCadastro}
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
              <p className="text-xs text-slate-500">{totalCursos} cursos</p>
          </div>
          <div className="relative w-full sm:max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              aria-label="Buscar curso"
              className={inputClass}
              placeholder="Buscar por nome ou descrição"
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
                  {isAdmin && <th className="p-4 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {cursos.map((curso) => (
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
                    {isAdmin && (
                      <td className="p-4">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            aria-label={`Editar ${curso.nome}`}
                            onClick={() => abrirEdicao(curso)}
                            className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
                          >
                            <Pencil size={16} />
                          </button>
                          <button
                            type="button"
                            aria-label={`Excluir ${curso.nome}`}
                            disabled={deletingId === curso.id}
                            onClick={() => void excluirCurso(curso)}
                            className="rounded-lg border border-red-500/30 p-2 text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                          >
                            {deletingId === curso.id ? (
                              <Loader2 size={16} className="animate-spin" />
                            ) : (
                              <Trash2 size={16} />
                            )}
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
                {cursos.length === 0 && (
                  <tr>
                    <td colSpan={isAdmin ? 6 : 5} className="p-12 text-center text-slate-500">
                      {buscaAplicada
                        ? 'Nenhum curso corresponde à busca.'
                        : 'Nenhum curso cadastrado.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : null}
        {!isLoading && !error && totalCursos > 0 && (
          <footer className="flex flex-col gap-3 border-t border-slate-800 px-4 py-3 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Exibindo {offset + 1}–{Math.min(offset + cursos.length, totalCursos)} de {totalCursos}
            </span>
            <div className="flex items-center justify-between gap-3 sm:justify-end">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Anterior
              </button>
              <span>
                Página {Math.floor(offset / PAGE_SIZE) + 1} de {Math.ceil(totalCursos / PAGE_SIZE)}
              </span>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= totalCursos}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Próxima
              </button>
            </div>
          </footer>
        )}
      </section>

      {isFormOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isSaving) setIsFormOpen(false);
          }}
        >
          <form
            onSubmit={salvarCurso}
            className="my-auto max-h-[90vh] w-full max-w-2xl space-y-5 overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
          >
            <header className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-blue-300">
                  Gestão curricular
                </p>
                <h2 className="mt-1 text-xl font-bold text-white">
                  {editing ? 'Editar curso' : 'Cadastrar curso'}
                </h2>
                <p className="mt-1 text-sm text-slate-400">Preencha os dados obrigatórios do curso.</p>
              </div>
              <button
                type="button"
                aria-label="Fechar formulário"
                disabled={isSaving}
                onClick={() => setIsFormOpen(false)}
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
                  {form.nivel_academico === '' && (
                    <option value="" disabled>
                      Selecione
                    </option>
                  )}
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
                  {editing?.modalidade === 'polo' && <option value="polo">Polo (legado)</option>}
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
                  value={form.carga_horaria_total || ''}
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
                  {editing?.status === 'inativo' && <option value="inativo">Inativo (legado)</option>}
                </select>
              </label>

              <div className="space-y-3 sm:col-span-2">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200">Disciplinas</h3>
                    <p className="text-xs text-slate-500">
                      Opcional · {form.disciplina_ids.length} selecionada(s)
                    </p>
                  </div>
                  <input
                    aria-label="Buscar disciplina para vincular"
                    className={`${inputClass} max-w-xs`}
                    placeholder="Buscar disciplina"
                    value={buscaDisciplina}
                    onChange={(event) => setBuscaDisciplina(event.target.value)}
                  />
                </div>
                <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
                  Uma disciplina vinculada a outro curso será transferida para este curso ao salvar.
                  {editing && ' Desmarcar uma disciplina remove o vínculo dela com este curso.'}
                </p>
                {disciplinasError && (
                  <div
                    role="alert"
                    className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200"
                  >
                    {disciplinasError}
                    {editing && ' Os vínculos atuais serão mantidos ao salvar.'}
                  </div>
                )}
                {disciplinasLoading ? (
                  <div className="flex justify-center rounded-xl border border-slate-800 py-6 text-blue-400">
                    <Loader2 className="animate-spin" />
                  </div>
                ) : (
                  <div className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60 p-2">
                    {disciplinasFiltradas.map((disciplina) => {
                      const selected = form.disciplina_ids.includes(disciplina.id);
                      const cursoAtual = cursos.find((curso) => curso.id === disciplina.curso_id);
                      return (
                        <label
                          key={disciplina.id}
                          className="flex cursor-pointer items-start gap-3 rounded-lg p-2.5 hover:bg-slate-800/70"
                        >
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={() =>
                              setForm((current) => ({
                                ...current,
                                disciplina_ids: selected
                                  ? current.disciplina_ids.filter((id) => id !== disciplina.id)
                                  : [...current.disciplina_ids, disciplina.id],
                              }))
                            }
                            className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-900 text-blue-600"
                          />
                          <span className="min-w-0 text-sm text-slate-200">
                            <span className="block font-medium">{disciplina.nome}</span>
                            <span className="block text-xs text-slate-500">
                              {cursoAtual ? `Vinculada a: ${cursoAtual.nome}` : 'Sem curso vinculado'}
                              {disciplina.semestre != null
                                ? ` · Semestre ${disciplina.semestre}`
                                : ''}
                            </span>
                          </span>
                        </label>
                      );
                    })}
                    {disciplinasFiltradas.length === 0 && (
                      <p className="p-4 text-center text-sm text-slate-500">
                        {disciplinasDisponiveis.length
                          ? 'Nenhuma disciplina corresponde à busca.'
                          : 'Nenhuma disciplina cadastrada.'}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <footer className="flex flex-col-reverse justify-end gap-2 border-t border-slate-800 pt-4 sm:flex-row">
              <button
                type="button"
                disabled={isSaving}
                onClick={() => setIsFormOpen(false)}
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
