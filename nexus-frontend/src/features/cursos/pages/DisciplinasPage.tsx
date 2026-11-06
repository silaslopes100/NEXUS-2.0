import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Loader2,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import {
  Curso,
  cursosApi,
  cursosApiErrorMessage,
  Disciplina,
  DisciplinaInput,
} from '@/features/cursos/api';

type DisciplinaForm = {
  curso_id: string;
  semestre: string;
  nome: string;
  ordem: string;
  carga_horaria: string;
  qtd_aulas_prevista: string;
  tipo: string;
  eh_extra_grade: boolean;
};

const initialForm: DisciplinaForm = {
  curso_id: '',
  semestre: '',
  nome: '',
  ordem: '0',
  carga_horaria: '40',
  qtd_aulas_prevista: '10',
  tipo: 'presencial',
  eh_extra_grade: false,
};

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500';

const optionalNumber = (value: string): number | null =>
  value.trim() ? Number(value) : null;

export const DisciplinasPage: React.FC = () => {
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [cursoFilter, setCursoFilter] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editing, setEditing] = useState<Disciplina | null>(null);
  const [form, setForm] = useState<DisciplinaForm>(initialForm);
  const [formError, setFormError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null
  );

  const carregarDados = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [disciplinasItems, cursosItems] = await Promise.all([
        cursosApi.listarDisciplinas(),
        cursosApi.listar(),
      ]);
      setDisciplinas(disciplinasItems);
      setCursos(cursosItems);
    } catch (err) {
      setError(cursosApiErrorMessage(err, 'Não foi possível carregar as disciplinas.'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void carregarDados();
  }, []);

  const cursoPorId = useMemo(
    () => new Map(cursos.map((curso) => [curso.id, curso.nome])),
    [cursos]
  );

  const disciplinasFiltradas = useMemo(() => {
    const termo = search.trim().toLocaleLowerCase('pt-BR');
    return disciplinas.filter((disciplina) => {
      if (cursoFilter && disciplina.curso_id !== cursoFilter) return false;
      if (!termo) return true;
      const cursoNome = cursoPorId.get(disciplina.curso_id || '') || '';
      return `${disciplina.nome} ${cursoNome}`.toLocaleLowerCase('pt-BR').includes(termo);
    });
  }, [cursoFilter, cursoPorId, disciplinas, search]);

  const abrirCadastro = () => {
    setEditing(null);
    setForm(initialForm);
    setFormError('');
    setIsFormOpen(true);
  };

  const abrirEdicao = (disciplina: Disciplina) => {
    setEditing(disciplina);
    setForm({
      curso_id: disciplina.curso_id || '',
      semestre: disciplina.semestre == null ? '' : String(disciplina.semestre),
      nome: disciplina.nome,
      ordem: String(disciplina.ordem ?? 0),
      carga_horaria:
        disciplina.carga_horaria == null ? '' : String(disciplina.carga_horaria),
      qtd_aulas_prevista:
        disciplina.qtd_aulas_prevista == null ? '' : String(disciplina.qtd_aulas_prevista),
      tipo: disciplina.tipo || 'presencial',
      eh_extra_grade: disciplina.eh_extra_grade ?? false,
    });
    setFormError('');
    setIsFormOpen(true);
  };

  const salvarDisciplina = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setFormError('');
    setFeedback(null);

    const payload: DisciplinaInput = {
      curso_id: form.curso_id || null,
      semestre: optionalNumber(form.semestre),
      nome: form.nome.trim(),
      ordem: Number(form.ordem),
      carga_horaria: optionalNumber(form.carga_horaria),
      qtd_aulas_prevista: optionalNumber(form.qtd_aulas_prevista),
      tipo: form.tipo.trim(),
      eh_extra_grade: form.eh_extra_grade,
    };

    try {
      if (editing) {
        const updated = await cursosApi.atualizarDisciplina(editing.id, payload);
        setDisciplinas((items) =>
          items.map((item) => (item.id === updated.id ? updated : item))
        );
        setFeedback({ type: 'success', message: 'Disciplina atualizada com sucesso.' });
      } else {
        const created = await cursosApi.criarDisciplina(payload);
        setDisciplinas((items) => [...items, created]);
        setFeedback({ type: 'success', message: 'Disciplina cadastrada com sucesso.' });
      }
      setIsFormOpen(false);
    } catch (err) {
      setFormError(cursosApiErrorMessage(err, 'Não foi possível salvar a disciplina.'));
    } finally {
      setIsSaving(false);
    }
  };

  const excluirDisciplina = async (disciplina: Disciplina) => {
    if (!window.confirm(`Deseja excluir a disciplina "${disciplina.nome}"?`)) return;
    setDeletingId(disciplina.id);
    setFeedback(null);
    try {
      await cursosApi.excluirDisciplina(disciplina.id);
      setDisciplinas((items) => items.filter((item) => item.id !== disciplina.id));
      setFeedback({ type: 'success', message: 'Disciplina excluída com sucesso.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        message: cursosApiErrorMessage(
          err,
          'Não foi possível excluir a disciplina. Verifique se há vínculos acadêmicos.'
        ),
      });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300">
            <BookOpen size={16} />
            Gestão curricular
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Disciplinas
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Cadastre e organize as disciplinas e seus vínculos curriculares.
          </p>
        </div>
        <button
          type="button"
          disabled={isLoading}
          onClick={abrirCadastro}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Plus size={17} />
          Cadastrar disciplina
        </button>
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
            <h2 className="font-bold text-white">Lista de disciplinas</h2>
            <p className="text-xs text-slate-500">{disciplinasFiltradas.length} disciplinas</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                aria-label="Buscar disciplina"
                className={`${inputClass} pl-9`}
                placeholder="Buscar por disciplina ou curso"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <select
              aria-label="Filtrar por curso"
              className={inputClass}
              value={cursoFilter}
              onChange={(event) => setCursoFilter(event.target.value)}
            >
              <option value="">Todos os cursos</option>
              {cursos.map((curso) => (
                <option key={curso.id} value={curso.id}>
                  {curso.nome}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div
            role="alert"
            className="m-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"
          >
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-16 text-blue-400">
            <Loader2 className="animate-spin" />
          </div>
        ) : !error ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="p-4">Disciplina</th>
                  <th className="p-4">Curso / semestre</th>
                  <th className="p-4">Carga horária</th>
                  <th className="p-4">Aulas previstas</th>
                  <th className="p-4">Tipo</th>
                  <th className="p-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {disciplinasFiltradas.map((disciplina) => (
                  <tr key={disciplina.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4">
                      <p className="font-semibold text-white">{disciplina.nome}</p>
                      {disciplina.eh_extra_grade && (
                        <span className="text-xs text-amber-300">Extra-grade</span>
                      )}
                    </td>
                    <td className="p-4">
                      <p>{cursoPorId.get(disciplina.curso_id || '') || 'Sem curso'}</p>
                      <p className="text-xs text-slate-500">
                        {disciplina.semestre == null ? 'Sem semestre' : `Semestre ${disciplina.semestre}`}
                      </p>
                    </td>
                    <td className="p-4">
                      {disciplina.carga_horaria == null ? '—' : `${disciplina.carga_horaria} h`}
                    </td>
                    <td className="p-4">{disciplina.qtd_aulas_prevista ?? '—'}</td>
                    <td className="p-4 capitalize">{disciplina.tipo || '—'}</td>
                    <td className="p-4">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          aria-label={`Editar ${disciplina.nome}`}
                          onClick={() => abrirEdicao(disciplina)}
                          className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          type="button"
                          aria-label={`Excluir ${disciplina.nome}`}
                          disabled={deletingId === disciplina.id}
                          onClick={() => void excluirDisciplina(disciplina)}
                          className="rounded-lg border border-red-500/30 p-2 text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                        >
                          {deletingId === disciplina.id ? (
                            <Loader2 size={16} className="animate-spin" />
                          ) : (
                            <Trash2 size={16} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {disciplinasFiltradas.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-12 text-center text-slate-500">
                      {disciplinas.length
                        ? 'Nenhuma disciplina corresponde aos filtros.'
                        : 'Nenhuma disciplina cadastrada.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {isFormOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isSaving) setIsFormOpen(false);
          }}
        >
          <form
            role="dialog"
            aria-modal="true"
            aria-labelledby="disciplina-form-titulo"
            onSubmit={salvarDisciplina}
            className="my-auto w-full max-w-2xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
          >
            <header className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-blue-300">
                  Gestão curricular
                </p>
                <h2 id="disciplina-form-titulo" className="mt-1 text-xl font-bold text-white">
                  {editing ? 'Editar disciplina' : 'Cadastrar disciplina'}
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  Curso e semestre são opcionais.
                </p>
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
              <div
                role="alert"
                className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200"
              >
                {formError}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
                <span>Nome *</span>
                <input
                  autoFocus
                  required
                  minLength={1}
                  maxLength={255}
                  className={inputClass}
                  value={form.nome}
                  onChange={(event) => setForm({ ...form, nome: event.target.value })}
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Curso (opcional)</span>
                <select
                  className={inputClass}
                  value={form.curso_id}
                  onChange={(event) => setForm({ ...form, curso_id: event.target.value })}
                >
                  <option value="">Sem vínculo com curso</option>
                  {cursos.map((curso) => (
                    <option key={curso.id} value={curso.id}>
                      {curso.nome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Semestre (opcional)</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  className={inputClass}
                  value={form.semestre}
                  onChange={(event) => setForm({ ...form, semestre: event.target.value })}
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Ordem</span>
                <input
                  type="number"
                  step={1}
                  className={inputClass}
                  value={form.ordem}
                  onChange={(event) => setForm({ ...form, ordem: event.target.value })}
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Carga horária</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  className={inputClass}
                  value={form.carga_horaria}
                  onChange={(event) => setForm({ ...form, carga_horaria: event.target.value })}
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Aulas previstas</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  className={inputClass}
                  value={form.qtd_aulas_prevista}
                  onChange={(event) =>
                    setForm({ ...form, qtd_aulas_prevista: event.target.value })
                  }
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Tipo</span>
                <input
                  maxLength={16}
                  className={inputClass}
                  value={form.tipo}
                  onChange={(event) => setForm({ ...form, tipo: event.target.value })}
                />
              </label>
              <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={form.eh_extra_grade}
                  onChange={(event) => setForm({ ...form, eh_extra_grade: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-blue-600"
                />
                Disciplina extra-grade
              </label>
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
                {isSaving ? 'Salvando...' : 'Salvar disciplina'}
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
};
