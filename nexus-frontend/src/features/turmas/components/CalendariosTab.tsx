import React, { useCallback, useEffect, useState } from 'react';
import { Edit2, Loader2, Plus, Trash2, X } from 'lucide-react';
import { apiErrorMessage } from '@/features/alunos/api';
import { Curso, cursosApi, Disciplina } from '@/features/cursos/api';
import { Calendario, CalendarioInput, formatarData, turmasApi } from '@/features/turmas/api';
import { inputCls } from '@/features/turmas/components/TurmaFormModal';

const formVazio = { curso_id: '', disciplina_id: '', data_liberacao: '', data_encerramento: '' };

export const CalendariosTab: React.FC<{ cursos: Curso[] }> = ({ cursos }) => {
  const [calendarios, setCalendarios] = useState<Calendario[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [editando, setEditando] = useState<Calendario | null>(null);
  const [formAberto, setFormAberto] = useState(false);
  const [form, setForm] = useState(formVazio);
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [saving, setSaving] = useState(false);
  const [formErro, setFormErro] = useState('');
  const [confirmandoId, setConfirmandoId] = useState<string | null>(null);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      setCalendarios(await turmasApi.listarCalendarios());
    } catch (e) {
      setErro(apiErrorMessage(e, 'Erro ao carregar calendários.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (!formAberto) return;
    let ativo = true;
    cursosApi
      .listarDisciplinas(form.curso_id || undefined)
      .then((itens) => ativo && setDisciplinas(itens))
      .catch((e) => ativo && setFormErro(apiErrorMessage(e, 'Erro ao carregar disciplinas.')));
    return () => {
      ativo = false;
    };
  }, [formAberto, form.curso_id]);

  const abrirForm = (calendario: Calendario | null) => {
    setEditando(calendario);
    setForm({
      curso_id: calendario?.curso_id ?? '',
      disciplina_id: calendario?.disciplina_id ?? '',
      data_liberacao: calendario?.data_liberacao ?? '',
      data_encerramento: calendario?.data_encerramento ?? '',
    });
    setFormErro('');
    setFormAberto(true);
  };

  const salvar = async (event: React.FormEvent) => {
    event.preventDefault();
    if (form.data_liberacao && form.data_encerramento && form.data_encerramento < form.data_liberacao) {
      setFormErro('O encerramento não pode ser anterior à liberação.');
      return;
    }
    const payload: CalendarioInput = {
      curso_id: form.curso_id || null,
      disciplina_id: form.disciplina_id || null,
      data_liberacao: form.data_liberacao || null,
      data_encerramento: form.data_encerramento || null,
    };
    setSaving(true);
    setFormErro('');
    try {
      if (editando) {
        await turmasApi.atualizarCalendario(editando.id, payload);
      } else {
        await turmasApi.criarCalendario(payload);
      }
      setFormAberto(false);
      await carregar();
    } catch (e) {
      setFormErro(apiErrorMessage(e, 'Não foi possível salvar o calendário.'));
    } finally {
      setSaving(false);
    }
  };

  const excluir = async (id: string) => {
    setExcluindoId(id);
    setErro('');
    try {
      await turmasApi.excluirCalendario(id);
      setConfirmandoId(null);
      await carregar();
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível excluir o calendário.'));
    } finally {
      setExcluindoId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => abrirForm(null)}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"
        >
          <Plus size={16} /> Cadastrar calendário
        </button>
      </div>

      {erro && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          {erro}
        </div>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-4">Curso</th>
              <th className="p-4">Disciplina</th>
              <th className="p-4">Liberação</th>
              <th className="p-4">Encerramento</th>
              <th className="p-4 text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="p-6 text-center">
                  <Loader2 className="mx-auto animate-spin" size={18} />
                </td>
              </tr>
            )}
            {!loading && calendarios.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-slate-500">
                  Nenhum calendário cadastrado.
                </td>
              </tr>
            )}
            {!loading &&
              calendarios.map((calendario) => (
                <tr key={calendario.id} className="border-b border-slate-800/60 last:border-0">
                  <td className="p-4 font-semibold text-white">{calendario.curso_nome || '—'}</td>
                  <td className="p-4">{calendario.disciplina_nome || '—'}</td>
                  <td className="p-4">{formatarData(calendario.data_liberacao)}</td>
                  <td className="p-4">{formatarData(calendario.data_encerramento)}</td>
                  <td className="p-4">
                    {confirmandoId === calendario.id ? (
                      <span className="flex justify-end gap-2">
                        <button
                          type="button"
                          disabled={excluindoId !== null}
                          onClick={() => void excluir(calendario.id)}
                          className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-60"
                        >
                          Confirmar
                        </button>
                        <button
                          type="button"
                          disabled={excluindoId !== null}
                          onClick={() => setConfirmandoId(null)}
                          className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-60"
                        >
                          Cancelar
                        </button>
                      </span>
                    ) : (
                      <span className="flex justify-end gap-2">
                        <button
                          type="button"
                          aria-label="Editar calendário"
                          onClick={() => abrirForm(calendario)}
                          className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          type="button"
                          aria-label="Excluir calendário"
                          onClick={() => setConfirmandoId(calendario.id)}
                          className="rounded-lg border border-red-500/30 p-2 text-red-300 hover:bg-red-500/10"
                        >
                          <Trash2 size={14} />
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {formAberto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !saving) setFormAberto(false);
          }}
        >
          <form
            role="dialog"
            aria-modal="true"
            aria-labelledby="calendario-form-titulo"
            onSubmit={salvar}
            className="my-auto w-full max-w-xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
          >
            <header className="flex items-start justify-between gap-4">
              <h2 id="calendario-form-titulo" className="text-xl font-bold text-white">
                {editando ? 'Editar calendário' : 'Cadastrar calendário'}
              </h2>
              <button
                type="button"
                aria-label="Fechar formulário"
                disabled={saving}
                onClick={() => setFormAberto(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
              >
                <X size={20} />
              </button>
            </header>

            {formErro && (
              <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                {formErro}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
                <span>Curso</span>
                <select
                  className={inputCls}
                  value={form.curso_id}
                  onChange={(e) => setForm({ ...form, curso_id: e.target.value, disciplina_id: '' })}
                >
                  <option value="">Sem curso</option>
                  {cursos.map((curso) => (
                    <option key={curso.id} value={curso.id}>
                      {curso.nome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
                <span>Disciplina</span>
                <select
                  className={inputCls}
                  value={form.disciplina_id}
                  onChange={(e) => setForm({ ...form, disciplina_id: e.target.value })}
                >
                  <option value="">Sem disciplina</option>
                  {disciplinas.map((disciplina) => (
                    <option key={disciplina.id} value={disciplina.id}>
                      {disciplina.nome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Liberação</span>
                <input
                  type="date"
                  className={inputCls}
                  value={form.data_liberacao}
                  onChange={(e) => setForm({ ...form, data_liberacao: e.target.value })}
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Encerramento</span>
                <input
                  type="date"
                  className={inputCls}
                  min={form.data_liberacao || undefined}
                  value={form.data_encerramento}
                  onChange={(e) => setForm({ ...form, data_encerramento: e.target.value })}
                />
              </label>
            </div>

            <footer className="flex justify-end gap-3">
              <button
                type="button"
                disabled={saving}
                onClick={() => setFormAberto(false)}
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
              >
                {saving && <Loader2 size={16} className="animate-spin" />}
                Salvar
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
};
