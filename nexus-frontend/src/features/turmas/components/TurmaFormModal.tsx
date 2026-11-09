import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { apiErrorMessage, EscolaOption } from '@/features/alunos/api';
import { Curso } from '@/features/cursos/api';
import { Calendario, formatarData, Turma, turmasApi, TurmaInput } from '@/features/turmas/api';

export type EscolaOpcao = EscolaOption & { polo_id?: string };

export const inputCls =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500 disabled:opacity-60';

interface TurmaFormModalProps {
  turma: Turma | null;
  cursos: Curso[];
  polos: EscolaOption[];
  escolas: EscolaOpcao[];
  mostrarPolo: boolean;
  mostrarEscola: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const TurmaFormModal: React.FC<TurmaFormModalProps> = ({
  turma,
  cursos,
  polos,
  escolas,
  mostrarPolo,
  mostrarEscola,
  onClose,
  onSaved,
}) => {
  const [form, setForm] = useState({
    nome: turma?.nome ?? '',
    curso_id: turma?.curso_id ?? '',
    polo_id: turma?.polo_id ?? '',
    escola_id: turma?.escola_id ?? '',
    data_inicio: turma?.data_inicio ?? '',
    data_fim: turma?.data_fim ?? '',
    calendario_oficial_id: turma?.calendario_oficial_id ?? '',
  });
  const [calendarios, setCalendarios] = useState<Calendario[]>([]);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    turmasApi
      .listarCalendarios()
      .then(setCalendarios)
      .catch((e) => setErro(apiErrorMessage(e, 'Erro ao carregar calendários.')));
  }, []);

  const atualizar = (campo: keyof typeof form, valor: string) =>
    setForm((atual) => ({ ...atual, [campo]: valor }));

  const escolasVisiveis = useMemo(() => {
    const doPolo = escolas.filter((e) => !form.polo_id || !e.polo_id || e.polo_id === form.polo_id);
    // A escola atual pode não estar na lista (ex.: consulta de escolas negada ao perfil).
    if (turma?.escola_id && !doPolo.some((e) => e.id === turma.escola_id)) {
      return [...doPolo, { id: turma.escola_id, nome: turma.escola_nome ?? 'Escola atual' }];
    }
    return doPolo;
  }, [escolas, form.polo_id, turma]);

  const calendariosVisiveis = calendarios.filter(
    (c) => !c.curso_id || !form.curso_id || c.curso_id === form.curso_id
  );

  const selecionarPolo = (poloId: string) =>
    setForm((atual) => {
      const escola = escolas.find((e) => e.id === atual.escola_id);
      const manterEscola = !poloId || !escola?.polo_id || escola.polo_id === poloId;
      return { ...atual, polo_id: poloId, escola_id: manterEscola ? atual.escola_id : '' };
    });

  const selecionarEscola = (escolaId: string) =>
    setForm((atual) => ({
      ...atual,
      escola_id: escolaId,
      polo_id: escolas.find((e) => e.id === escolaId)?.polo_id ?? atual.polo_id,
    }));

  const salvar = async (event: React.FormEvent) => {
    event.preventDefault();
    if (form.data_inicio && form.data_fim && form.data_fim < form.data_inicio) {
      setErro('A data de fim não pode ser anterior à data de início.');
      return;
    }
    const payload: TurmaInput = {
      nome: form.nome.trim(),
      curso_id: form.curso_id || null,
      polo_id: form.polo_id || null,
      escola_id: form.escola_id || null,
      data_inicio: form.data_inicio || null,
      data_fim: form.data_fim || null,
      calendario_oficial_id: form.calendario_oficial_id || null,
    };
    setSaving(true);
    setErro('');
    try {
      if (turma) {
        await turmasApi.atualizar(turma.id, payload);
      } else {
        await turmasApi.criar(payload);
      }
      onSaved();
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível salvar a turma.'));
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !saving) onClose();
      }}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="turma-form-titulo"
        onSubmit={salvar}
        className="my-auto w-full max-w-2xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <h2 id="turma-form-titulo" className="text-xl font-bold text-white">
            {turma ? 'Editar turma' : 'Cadastrar turma'}
          </h2>
          <button
            type="button"
            aria-label="Fechar formulário"
            disabled={saving}
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </header>

        {erro && (
          <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {erro}
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
              className={inputCls}
              value={form.nome}
              onChange={(e) => atualizar('nome', e.target.value)}
            />
          </label>

          <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
            <span>Curso</span>
            <select className={inputCls} value={form.curso_id} onChange={(e) => atualizar('curso_id', e.target.value)}>
              <option value="">Sem curso</option>
              {cursos.map((curso) => (
                <option key={curso.id} value={curso.id}>
                  {curso.nome}
                </option>
              ))}
            </select>
          </label>

          {mostrarPolo && (
            <label className="space-y-1.5 text-sm text-slate-300">
              <span>Polo</span>
              <select className={inputCls} value={form.polo_id} onChange={(e) => selecionarPolo(e.target.value)}>
                <option value="">Sem polo</option>
                {polos.map((polo) => (
                  <option key={polo.id} value={polo.id}>
                    {polo.nome}
                  </option>
                ))}
              </select>
            </label>
          )}

          {mostrarEscola && (
            <label className={`space-y-1.5 text-sm text-slate-300 ${mostrarPolo ? '' : 'sm:col-span-2'}`}>
              <span>Escola</span>
              <select className={inputCls} value={form.escola_id} onChange={(e) => selecionarEscola(e.target.value)}>
                <option value="">Sem escola</option>
                {escolasVisiveis.map((escola) => (
                  <option key={escola.id} value={escola.id}>
                    {escola.nome}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="space-y-1.5 text-sm text-slate-300">
            <span>Início</span>
            <input
              type="date"
              className={inputCls}
              value={form.data_inicio}
              onChange={(e) => atualizar('data_inicio', e.target.value)}
            />
          </label>

          <label className="space-y-1.5 text-sm text-slate-300">
            <span>Fim</span>
            <input
              type="date"
              className={inputCls}
              min={form.data_inicio || undefined}
              value={form.data_fim}
              onChange={(e) => atualizar('data_fim', e.target.value)}
            />
          </label>

          <label className="space-y-1.5 text-sm text-slate-300 sm:col-span-2">
            <span>Calendário oficial</span>
            <select
              className={inputCls}
              value={form.calendario_oficial_id}
              onChange={(e) => atualizar('calendario_oficial_id', e.target.value)}
            >
              <option value="">Sem calendário</option>
              {calendariosVisiveis.map((c) => (
                <option key={c.id} value={c.id}>
                  {[c.curso_nome, c.disciplina_nome].filter(Boolean).join(' · ') || 'Calendário geral'} (
                  {formatarData(c.data_liberacao)} a {formatarData(c.data_encerramento)})
                </option>
              ))}
            </select>
          </label>
        </div>

        <footer className="flex justify-end gap-3">
          <button
            type="button"
            disabled={saving}
            onClick={onClose}
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
  );
};
