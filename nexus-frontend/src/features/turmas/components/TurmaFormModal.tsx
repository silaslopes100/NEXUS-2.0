import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, Loader2, X } from 'lucide-react';
import { alunosApi, apiErrorMessage, EscolaOption } from '@/features/alunos/api';
import { Curso, cursosApi } from '@/features/cursos/api';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  formatarData,
  formatarHora,
  ModalidadeTurma,
  ResponsavelTurma,
  ROTULO_TURNO,
  SugestaoTurma,
  Turma,
  TurmaInput,
  turmasApi,
  TurnoTurma,
} from '@/features/turmas/api';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

export type EscolaOpcao = EscolaOption & { polo_id?: string };

export const inputCls =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500 disabled:opacity-60';

/** Perfil do usuário e listas de cursos, polos e escolas para os formulários e filtros de turma. */
export function useOpcoesTurma() {
  const { user, perfil } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome ?? user?.perfil?.nome);
  const isAdmin = role === 'admin';
  const isPolo = role === 'polo';
  const poloUsuario = user?.polo_id ?? '';
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [polos, setPolos] = useState<EscolaOption[]>([]);
  const [escolas, setEscolas] = useState<EscolaOpcao[]>([]);
  const [erro, setErro] = useState('');

  useEffect(() => {
    cursosApi.listar().then(setCursos).catch((e) => setErro(apiErrorMessage(e, 'Erro ao carregar cursos.')));
  }, []);

  useEffect(() => {
    // Sem as listas, a tela segue funcionando: apenas os seletores de polo e escola ficam vazios.
    if (isAdmin) {
      alunosApi.listarPolos().then(setPolos).catch(() => setPolos([]));
      polosEscolasApi
        .listarEscolas({ limit: 200 })
        .then((data: { items?: EscolaOpcao[] }) => setEscolas(data.items ?? []))
        .catch(() => setEscolas([]));
    } else if (isPolo && poloUsuario) {
      alunosApi.listarEscolas(poloUsuario).then(setEscolas).catch(() => setEscolas([]));
    }
  }, [isAdmin, isPolo, poloUsuario]);

  return { role, isAdmin, isPolo, isEscola: role === 'escola', cursos, polos, escolas, erro };
}

interface TurmaDadosFormProps {
  turma: Turma | null;
  cursos: Curso[];
  polos: EscolaOption[];
  escolas: EscolaOpcao[];
  mostrarPolo: boolean;
  mostrarEscola: boolean;
  onSaved: (turma: Turma) => void;
  onCancel?: () => void;
  rotuloSalvar?: string;
}

const Campo: React.FC<{ label: string; obrigatorio?: boolean; className?: string; children: React.ReactNode; dica?: string }> = ({
  label, obrigatorio, className = '', children, dica,
}) => (
  <label className={`block space-y-1.5 text-sm text-slate-300 ${className}`}>
    <span>
      {label}
      {obrigatorio && ' *'}
    </span>
    {children}
    {dica && <span className="block text-xs text-slate-500">{dica}</span>}
  </label>
);

/** Dados da turma (curso, modalidade, unidade, turno, horário, vagas, local e responsável). */
export const TurmaDadosForm: React.FC<TurmaDadosFormProps> = ({
  turma, cursos, polos, escolas, mostrarPolo, mostrarEscola, onSaved, onCancel, rotuloSalvar = 'Salvar',
}) => {
  const [form, setForm] = useState({
    nome: turma?.nome ?? '',
    curso_id: turma?.curso_id ?? '',
    modalidade: (turma?.modalidade ?? 'presencial') as ModalidadeTurma,
    polo_id: turma?.polo_id ?? '',
    escola_id: turma?.escola_id ?? '',
    turno: (turma?.turno ?? '') as TurnoTurma | '',
    horario_inicio: formatarHora(turma?.horario_inicio),
    horario_fim: formatarHora(turma?.horario_fim),
    vagas: turma?.vagas ? String(turma.vagas) : '',
    local_aulas: turma?.local_aulas ?? '',
    responsavel_id: turma?.responsavel_id ?? '',
  });
  const [sugestao, setSugestao] = useState<SugestaoTurma | null>(null);
  const [erroSugestao, setErroSugestao] = useState('');
  const [responsaveis, setResponsaveis] = useState<ResponsavelTurma[]>([]);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState('');
  const nomeSugerido = useRef<string>('');

  const atualizar = <K extends keyof typeof form>(campo: K, valor: (typeof form)[K]) =>
    setForm((atual) => ({ ...atual, [campo]: valor }));

  const ead = form.modalidade === 'ead';

  const escolasVisiveis = useMemo(() => {
    const doPolo = escolas.filter((e) => !form.polo_id || !e.polo_id || e.polo_id === form.polo_id);
    // A escola atual pode não estar na lista (ex.: consulta de escolas negada ao perfil).
    if (turma?.escola_id && !doPolo.some((e) => e.id === turma.escola_id)) {
      return [...doPolo, { id: turma.escola_id, nome: turma.escola_nome ?? 'Escola atual' }];
    }
    return doPolo;
  }, [escolas, form.polo_id, turma]);

  // Período (vigência do calendário do curso), código previsto e nome sugerido.
  useEffect(() => {
    if (!form.curso_id) {
      setSugestao(null);
      return;
    }
    let ativo = true;
    setErroSugestao('');
    turmasApi
      .sugestao({
        curso_id: form.curso_id, modalidade: form.modalidade,
        polo_id: form.polo_id || undefined, escola_id: form.escola_id || undefined,
      })
      .then((s) => {
        if (!ativo) return;
        setSugestao(s);
        if (!turma) {
          setForm((atual) =>
            !atual.nome.trim() || atual.nome === nomeSugerido.current ? { ...atual, nome: s.nome } : atual,
          );
          nomeSugerido.current = s.nome;
        }
      })
      .catch((e) => {
        if (!ativo) return;
        setSugestao(null);
        setErroSugestao(apiErrorMessage(e, 'Não foi possível ler o calendário do curso.'));
      });
    return () => {
      ativo = false;
    };
  }, [form.curso_id, form.modalidade, form.polo_id, form.escola_id, turma]);

  useEffect(() => {
    if (!form.polo_id && !form.escola_id) {
      setResponsaveis([]);
      return;
    }
    let ativo = true;
    turmasApi
      .responsaveis({ polo_id: form.polo_id || undefined, escola_id: form.escola_id || undefined })
      .then((r) => ativo && setResponsaveis(r))
      .catch(() => ativo && setResponsaveis([]));
    return () => {
      ativo = false;
    };
  }, [form.polo_id, form.escola_id]);

  const selecionarPolo = (poloId: string) =>
    setForm((atual) => {
      const escola = escolas.find((e) => e.id === atual.escola_id);
      const manterEscola = !poloId || !escola?.polo_id || escola.polo_id === poloId;
      return { ...atual, polo_id: poloId, escola_id: manterEscola ? atual.escola_id : '', responsavel_id: '' };
    });

  const selecionarEscola = (escolaId: string) =>
    setForm((atual) => ({
      ...atual,
      escola_id: escolaId,
      polo_id: escolas.find((e) => e.id === escolaId)?.polo_id ?? atual.polo_id,
      responsavel_id: '',
    }));

  const salvar = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.curso_id) {
      setErro('Escolha o curso: as datas da turma vêm do calendário dele.');
      return;
    }
    if (!ead && mostrarPolo && !form.polo_id && !form.escola_id) {
      setErro('Turma presencial precisa de um polo.');
      return;
    }
    if (form.horario_inicio && form.horario_fim && form.horario_fim <= form.horario_inicio) {
      setErro('O horário de término deve ser depois do início.');
      return;
    }
    const vagas = form.vagas.trim() ? Number(form.vagas) : null;
    if (vagas !== null && (!Number.isInteger(vagas) || vagas < 1)) {
      setErro('Vagas deve ser um número inteiro maior que zero.');
      return;
    }
    const payload: TurmaInput = {
      nome: form.nome.trim(),
      curso_id: form.curso_id,
      modalidade: form.modalidade,
      polo_id: form.polo_id || null,
      escola_id: form.escola_id || null,
      turno: form.turno || null,
      horario_inicio: form.horario_inicio || null,
      horario_fim: form.horario_fim || null,
      vagas,
      local_aulas: form.local_aulas.trim() || null,
      responsavel_id: form.responsavel_id || null,
    };
    setSaving(true);
    setErro('');
    try {
      const salva = turma ? await turmasApi.atualizar(turma.id, payload) : await turmasApi.criar(payload);
      onSaved(salva);
    } catch (e) {
      setErro(apiErrorMessage(e, 'Não foi possível salvar a turma.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={salvar} className="space-y-5" noValidate>
      {erro && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          {erro}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo label="Curso" obrigatorio className="sm:col-span-2">
          <select
            className={inputCls}
            required
            value={form.curso_id}
            onChange={(e) => atualizar('curso_id', e.target.value)}
          >
            <option value="">Selecione o curso</option>
            {cursos.map((curso) => (
              <option key={curso.id} value={curso.id}>
                {curso.nome}
              </option>
            ))}
          </select>
        </Campo>

        <div className="sm:col-span-2 flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-300">
          <CalendarDays className="h-4 w-4 text-nexus-yellow" aria-hidden />
          {sugestao ? (
            <span>
              Período: <strong className="text-white">{formatarData(sugestao.data_inicio)} a {formatarData(sugestao.data_fim)}</strong>
              {sugestao.calendario_nome ? ` (${sugestao.calendario_nome})` : ''} — vem do calendário do curso.
              {!turma && <> Código previsto: <strong className="text-white">{sugestao.codigo}</strong>.</>}
            </span>
          ) : erroSugestao ? (
            <span className="text-amber-300">{erroSugestao}</span>
          ) : turma ? (
            <span>Período: {formatarData(turma.data_inicio)} a {formatarData(turma.data_fim)} · Código {turma.codigo || '—'}</span>
          ) : (
            <span className="text-slate-500">Escolha o curso para ver o período e o código da turma.</span>
          )}
        </div>

        <fieldset className="sm:col-span-2">
          <legend className="mb-1.5 text-sm text-slate-300">Modalidade *</legend>
          <div className="flex flex-wrap gap-2">
            {(['presencial', 'ead'] as ModalidadeTurma[]).map((m) => (
              <label
                key={m}
                className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                  form.modalidade === m ? 'border-blue-500 bg-blue-500/10 text-white' : 'border-slate-700 text-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="modalidade-turma"
                  className="accent-blue-500"
                  checked={form.modalidade === m}
                  onChange={() => atualizar('modalidade', m)}
                />
                {m === 'ead' ? 'EAD (prazos por disciplina)' : 'Presencial'}
              </label>
            ))}
          </div>
        </fieldset>

        {mostrarPolo && (
          <Campo label="Polo" obrigatorio={!ead}>
            <select className={inputCls} value={form.polo_id} onChange={(e) => selecionarPolo(e.target.value)}>
              <option value="">Sem polo</option>
              {polos.map((polo) => (
                <option key={polo.id} value={polo.id}>
                  {polo.nome}
                </option>
              ))}
            </select>
          </Campo>
        )}

        {mostrarEscola && (
          <Campo label="Escola" className={mostrarPolo ? '' : 'sm:col-span-2'}>
            <select className={inputCls} value={form.escola_id} onChange={(e) => selecionarEscola(e.target.value)}>
              <option value="">Sem escola</option>
              {escolasVisiveis.map((escola) => (
                <option key={escola.id} value={escola.id}>
                  {escola.nome}
                </option>
              ))}
            </select>
          </Campo>
        )}

        <Campo label="Nome" obrigatorio className="sm:col-span-2" dica={!turma ? 'Sugerido pelo sistema; pode ser alterado.' : undefined}>
          <input
            required
            minLength={2}
            maxLength={255}
            className={inputCls}
            value={form.nome}
            onChange={(e) => atualizar('nome', e.target.value)}
          />
        </Campo>

        <Campo label="Turno">
          <select className={inputCls} value={form.turno} onChange={(e) => atualizar('turno', e.target.value as TurnoTurma | '')}>
            <option value="">—</option>
            {(Object.keys(ROTULO_TURNO) as TurnoTurma[]).map((t) => (
              <option key={t} value={t}>{ROTULO_TURNO[t]}</option>
            ))}
          </select>
        </Campo>

        <div className="grid grid-cols-2 gap-3">
          <Campo label="Início das aulas">
            <input type="time" className={inputCls} value={form.horario_inicio} onChange={(e) => atualizar('horario_inicio', e.target.value)} />
          </Campo>
          <Campo label="Término">
            <input type="time" className={inputCls} value={form.horario_fim} onChange={(e) => atualizar('horario_fim', e.target.value)} />
          </Campo>
        </div>

        <Campo label="Vagas" dica="Vazio = sem limite. A matrícula é bloqueada quando lotar.">
          <input
            type="number"
            min={1}
            step={1}
            inputMode="numeric"
            className={inputCls}
            value={form.vagas}
            onChange={(e) => atualizar('vagas', e.target.value)}
          />
        </Campo>

        <Campo label="Responsável" dica={form.polo_id || form.escola_id ? 'Usuários ativos do polo ou da escola da turma.' : 'Escolha o polo ou a escola primeiro.'}>
          <select
            className={inputCls}
            value={form.responsavel_id}
            disabled={!form.polo_id && !form.escola_id}
            onChange={(e) => atualizar('responsavel_id', e.target.value)}
          >
            <option value="">Sem responsável</option>
            {form.responsavel_id && !responsaveis.some((r) => r.id === form.responsavel_id) && (
              <option value={form.responsavel_id}>{turma?.responsavel_nome ?? 'Responsável atual'}</option>
            )}
            {responsaveis.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nome} ({r.perfil === 'polo' ? 'Polo' : 'Escola'})
              </option>
            ))}
          </select>
        </Campo>

        <Campo label={ead ? 'Local / link dos encontros' : 'Local das aulas'} className="sm:col-span-2">
          <input
            className={inputCls}
            maxLength={500}
            placeholder={ead ? 'Opcional' : 'Sala, endereço ou ponto de encontro'}
            value={form.local_aulas}
            onChange={(e) => atualizar('local_aulas', e.target.value)}
          />
        </Campo>
      </div>

      <footer className="flex justify-end gap-3">
        {onCancel && (
          <button
            type="button"
            disabled={saving}
            onClick={onCancel}
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            Cancelar
          </button>
        )}
        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:opacity-60"
        >
          {saving && <Loader2 size={16} className="animate-spin" />}
          {rotuloSalvar}
        </button>
      </footer>
    </form>
  );
};

interface TurmaFormModalProps extends Omit<TurmaDadosFormProps, 'onCancel'> {
  onClose: () => void;
}

/** Edição dos dados da turma em modal (página de detalhe). */
export const TurmaFormModal: React.FC<TurmaFormModalProps> = ({ onClose, ...props }) => (
  <div
    className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
    onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}
  >
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="turma-form-titulo"
      className="glass my-auto w-full max-w-2xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
    >
      <header className="flex items-start justify-between gap-4">
        <h2 id="turma-form-titulo" className="text-xl font-bold text-white">
          {props.turma ? 'Editar dados da turma' : 'Cadastrar turma'}
        </h2>
        <button
          type="button"
          aria-label="Fechar formulário"
          onClick={onClose}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
        >
          <X size={20} />
        </button>
      </header>
      <TurmaDadosForm {...props} onCancel={onClose} />
    </section>
  </div>
);
