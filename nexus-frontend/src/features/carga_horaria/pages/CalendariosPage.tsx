import React, { useCallback, useEffect, useState } from 'react';
import { CalendarDays, Loader2, Pencil, Plus, Trash2, X } from 'lucide-react';
import {
  Calendario,
  CalendarioInput,
  DIAS_SEMANA,
  DatasLetivas,
  MESES,
  RegrasCalendario,
  cargaHorariaApi,
  erroApi,
} from '@/features/carga_horaria/api';

const inputCls = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const labelCls = 'mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-500';

const fmtData = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString('pt-BR');
const anoAtual = new Date().getFullYear();

type Opcao = { value: string; label: string };
interface CampoRegra {
  chave: keyof RegrasCalendario;
  rotulo: string;
  ajuda: string;
  origem: string;
  tipo: 'numero' | 'opcoes' | 'bool';
  opcoes?: Opcao[];
  min?: number;
  max?: number;
  passo?: number;
}

/** Cada regra traz a explicação e a RN/ponto em aberto que a originou. */
const CAMPOS_REGRAS: { grupo: string; campos: CampoRegra[] }[] = [
  {
    grupo: 'Planejamento das aulas',
    campos: [
      { chave: 'disciplinas_por_mes', rotulo: 'Disciplinas por mês', ajuda: 'Quantas disciplinas correm em cada mês letivo.', origem: 'RN05', tipo: 'numero', min: 1, max: 12 },
      { chave: 'aulas_por_disciplina_mes', rotulo: 'Aulas por disciplina no mês', ajuda: 'Quantas aulas cada disciplina tem no mês.', origem: 'Ponto 1', tipo: 'numero', min: 1, max: 31 },
      { chave: 'organizacao_disciplinas_mes', rotulo: 'Disciplinas do mês', ajuda: 'Paralelo alterna as datas (A, B, A, B); sequencial termina uma antes da outra (A, A, B, B).', origem: 'Ponto 2', tipo: 'opcoes', opcoes: [{ value: 'paralelo', label: 'Em paralelo' }, { value: 'sequencial', label: 'Em sequência' }] },
      { chave: 'quinta_semana', rotulo: 'Mês com 5 semanas', ajuda: 'Na 5ª ocorrência do dia de aula, gerar uma aula a mais e redividir a carga, ou ignorar a data.', origem: 'Ponto 1', tipo: 'opcoes', opcoes: [{ value: 'aula_extra', label: 'Gera aula a mais' }, { value: 'ignorar', label: 'Ignorar a 5ª semana' }] },
      { chave: 'fonte_qtd_aulas', rotulo: 'Quantidade de aulas vem de', ajuda: 'Do calendário (aulas por mês) ou da quantidade cadastrada em cada disciplina.', origem: 'RN01', tipo: 'opcoes', opcoes: [{ value: 'calendario', label: 'Calendário' }, { value: 'disciplina', label: 'Cadastro da disciplina' }] },
      { chave: 'capacidade_insuficiente', rotulo: 'Curso não cabe no período', ajuda: 'Quando faltam meses letivos para todas as disciplinas.', origem: 'RN05', tipo: 'opcoes', opcoes: [{ value: 'alertar', label: 'Alertar' }, { value: 'bloquear', label: 'Bloquear o cronograma' }] },
    ],
  },
  {
    grupo: 'Carga horária',
    campos: [
      { chave: 'carga_horaria_padrao', rotulo: 'Carga padrão da disciplina (h)', ajuda: 'Sugerida ao cadastrar disciplinas.', origem: 'RN01', tipo: 'numero', min: 1 },
      { chave: 'duracao_aula', rotulo: 'Horas de cada aula', ajuda: 'Dividir a carga pelas aulas (2 aulas = 20 h; 3 aulas = 13,33 h) ou usar duração fixa.', origem: 'Ponto 1', tipo: 'opcoes', opcoes: [{ value: 'dividir_carga', label: 'Dividir a carga' }, { value: 'fixa', label: 'Duração fixa' }] },
      { chave: 'duracao_aula_horas', rotulo: 'Duração fixa (h)', ajuda: 'Usada quando "Horas de cada aula" é fixa.', origem: 'Ponto 1', tipo: 'numero', min: 0.5, passo: 0.5 },
      { chave: 'horas_abatidas', rotulo: 'A ata abate', ajuda: 'As horas da aula prevista ou a duração informada na ata.', origem: 'RN03.4', tipo: 'opcoes', opcoes: [{ value: 'previstas', label: 'Horas previstas' }, { value: 'registradas', label: 'Horas registradas na ata' }] },
    ],
  },
  {
    grupo: 'Frequência e conclusão',
    campos: [
      { chave: 'frequencia_base', rotulo: 'Frequência medida em', ajuda: 'Número de aulas ou horas.', origem: 'Ponto 4', tipo: 'opcoes', opcoes: [{ value: 'aulas', label: 'Aulas' }, { value: 'horas', label: 'Horas' }] },
      { chave: 'frequencia_minima_pct', rotulo: 'Frequência mínima (%)', ajuda: 'Abaixo disso o aluno aparece como em risco.', origem: 'RN07', tipo: 'numero', min: 0, max: 100 },
      { chave: 'saldo_ao_fim_turma', rotulo: 'Turma termina com saldo', ajuda: 'Só alertar (a Diretoria decide) ou bloquear a conclusão até zerar o saldo.', origem: 'Ponto 5', tipo: 'opcoes', opcoes: [{ value: 'alertar', label: 'Alertar' }, { value: 'bloquear_conclusao', label: 'Bloquear conclusão' }] },
    ],
  },
  {
    grupo: 'Registro de atas',
    campos: [
      { chave: 'bloquear_ata_fora_periodo', rotulo: 'Bloquear ata fora do período da turma', ajuda: '', origem: 'RN03.5', tipo: 'bool' },
      { chave: 'excluir_ata_devolve_saldo', rotulo: 'Excluir ata devolve as horas ao saldo', ajuda: 'Desligado: só a Diretoria exclui atas que abatem horas.', origem: 'RN03.5', tipo: 'bool' },
    ],
  },
  {
    grupo: 'Turmas EAD — prazos',
    campos: [
      { chave: 'ead_prazo_dias_padrao', rotulo: 'Dias para concluir cada disciplina', ajuda: 'Contados da liberação. A disciplina pode ter prazo próprio no cadastro dela.', origem: 'EAD', tipo: 'numero', min: 1, max: 730 },
      { chave: 'ead_liberacao', rotulo: 'Liberação das disciplinas', ajuda: 'Uma por vez, na ordem do curso, ou todas no início da turma.', origem: 'EAD', tipo: 'opcoes', opcoes: [{ value: 'sequencial', label: 'Uma por vez' }, { value: 'todas_no_inicio', label: 'Todas no início' }] },
      { chave: 'ead_proxima_libera', rotulo: 'A próxima disciplina libera quando', ajuda: 'Vale para a liberação uma por vez.', origem: 'EAD', tipo: 'opcoes', opcoes: [{ value: 'anterior_concluida_ou_vencida', label: 'A anterior é concluída ou vence' }, { value: 'anterior_vencida', label: 'O prazo da anterior vence' }, { value: 'anterior_concluida', label: 'A anterior é concluída' }] },
      { chave: 'ead_ao_vencer', rotulo: 'Disciplina com prazo vencido', ajuda: 'Bloquear o acesso no AVA ou só avisar o aluno.', origem: 'EAD', tipo: 'opcoes', opcoes: [{ value: 'bloquear', label: 'Bloquear no AVA' }, { value: 'alertar', label: 'Só avisar' }] },
    ],
  },
];

const PERFIS_COORDENACAO: Opcao[] = [{ value: 'admin', label: 'Diretoria (admin)' }, { value: 'polo', label: 'Coordenação do Polo' }];

const novoCalendario = (regras: RegrasCalendario): CalendarioInput => ({
  nome: '',
  descricao: '',
  data_inicio: `${anoAtual}-01-01`,
  data_fim: `${anoAtual}-12-31`,
  dias_semana: [6],
  meses_recesso: [7, 12],
  feriados: [],
  datas_excluidas: [],
  datas_extras: [],
  regras,
  ativo: true,
});

const ListaDatas: React.FC<{ rotulo: string; datas: string[]; onChange: (d: string[]) => void }> = ({ rotulo, datas, onChange }) => {
  const [nova, setNova] = useState('');
  return (
    <div>
      <label className={labelCls}>{rotulo}</label>
      <div className="flex gap-2">
        <input type="date" className={inputCls} value={nova} onChange={(e) => setNova(e.target.value)} />
        <button type="button" disabled={!nova} onClick={() => { onChange([...new Set([...datas, nova])].sort()); setNova(''); }} className="rounded-xl border border-slate-700 px-3 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40">Adicionar</button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {datas.map((d) => (
          <span key={d} className="inline-flex items-center gap-1 rounded-lg bg-slate-800 px-2 py-1 text-xs text-slate-200">
            {fmtData(d)}
            <button type="button" aria-label={`Remover ${fmtData(d)}`} onClick={() => onChange(datas.filter((x) => x !== d))}><X className="h-3 w-3" /></button>
          </span>
        ))}
      </div>
    </div>
  );
};

/** Calendário Acadêmico: a coordenação define datas e regras; todo curso vinculado segue o calendário. */
export const CalendariosPage: React.FC = () => {
  const [calendarios, setCalendarios] = useState<Calendario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const [regrasPadrao, setRegrasPadrao] = useState<RegrasCalendario | null>(null);
  const [form, setForm] = useState<CalendarioInput | null>(null);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState('');
  const [previa, setPrevia] = useState<{ calendario: Calendario; datas: DatasLetivas } | null>(null);
  const [novoFeriado, setNovoFeriado] = useState({ data: '', descricao: '' });

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const [lista, regras] = await Promise.all([cargaHorariaApi.listarCalendarios(), cargaHorariaApi.regrasPadrao()]);
      setCalendarios(lista);
      setRegrasPadrao(regras);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar os calendários.'));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const abrirNovo = () => { if (regrasPadrao) { setForm(novoCalendario(regrasPadrao)); setEditandoId(null); setErroForm(''); } };
  const abrirEdicao = (c: Calendario) => {
    const { id, total_cursos: _total, ...dados } = c;
    setForm({ ...dados, regras: { ...(regrasPadrao || {}), ...dados.regras } as RegrasCalendario });
    setEditandoId(id);
    setErroForm('');
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    if (!form.dias_semana.length) { setErroForm('Escolha pelo menos um dia de aula.'); return; }
    const original = editandoId ? calendarios.find((c) => c.id === editandoId) : null;
    if (original && (original.data_inicio !== form.data_inicio || original.data_fim !== form.data_fim)) {
      // A vigência é o período das turmas dos cursos ligados a este calendário.
      const afetadas = await cargaHorariaApi.turmasAfetadas(original.id).catch(() => null);
      if (afetadas && !window.confirm(
        `Mudar a vigência atualiza o início e o fim de ${afetadas} turma(s) aberta(s) dos cursos deste calendário. Continuar?`,
      )) return;
    }
    setSalvando(true);
    setErroForm('');
    try {
      if (editandoId) await cargaHorariaApi.atualizarCalendario(editandoId, form);
      else await cargaHorariaApi.criarCalendario(form);
      setForm(null);
      setAviso(editandoId ? 'Calendário atualizado. Regere o cronograma das turmas para aplicar as novas regras.' : 'Calendário criado.');
      await carregar();
    } catch (error) {
      setErroForm(erroApi(error, 'Não foi possível salvar o calendário.'));
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (c: Calendario) => {
    if (!window.confirm(`Excluir o calendário "${c.nome}"?`)) return;
    try {
      await cargaHorariaApi.excluirCalendario(c.id);
      setAviso('Calendário excluído.');
      await carregar();
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível excluir o calendário.'));
    }
  };

  const verPrevia = async (c: Calendario) => {
    try {
      setPrevia({ calendario: c, datas: await cargaHorariaApi.datasLetivas(c.id) });
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível calcular as datas letivas.'));
    }
  };

  const setRegra = (chave: keyof RegrasCalendario, valor: unknown) =>
    form && setForm({ ...form, regras: { ...form.regras, [chave]: valor } });
  const alternar = (lista: number[], valor: number) =>
    lista.includes(valor) ? lista.filter((v) => v !== valor) : [...lista, valor].sort((a, b) => a - b);

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Calendários Acadêmicos</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Datas letivas e regras de carga horária, progresso e frequência. Todo curso é vinculado a um calendário e segue
            obrigatoriamente as regras dele; as turmas herdam do curso.
          </p>
        </div>
        <button type="button" onClick={abrirNovo} disabled={!regrasPadrao} className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-xs font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
          <Plus className="h-4 w-4" /> Novo calendário
        </button>
      </header>

      {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
      {aviso && <p role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{aviso}</p>}

      {carregando ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : !calendarios.length ? (
        <p className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-10 text-center text-sm text-slate-400">Nenhum calendário cadastrado.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {calendarios.map((c) => (
            <section key={c.id} className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-bold text-white">{c.nome}</h2>
                  <p className="text-xs text-slate-500">{fmtData(c.data_inicio)} a {fmtData(c.data_fim)} · {c.total_cursos} curso(s)</p>
                </div>
                {!c.ativo && <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-400">Inativo</span>}
              </div>
              <dl className="mt-3 space-y-1 text-xs text-slate-300">
                <div><dt className="inline text-slate-500">Aulas: </dt><dd className="inline">{c.dias_semana.map((d) => DIAS_SEMANA[d]).join(', ')}</dd></div>
                <div><dt className="inline text-slate-500">Recesso: </dt><dd className="inline">{c.meses_recesso.map((m) => MESES[m - 1]).join(', ') || '—'}</dd></div>
                <div><dt className="inline text-slate-500">Plano: </dt><dd className="inline">{c.regras.disciplinas_por_mes} disciplina(s)/mês · {c.regras.aulas_por_disciplina_mes} aula(s) cada · {c.regras.organizacao_disciplinas_mes}</dd></div>
                <div><dt className="inline text-slate-500">Frequência mínima: </dt><dd className="inline">{c.regras.frequencia_minima_pct}% ({c.regras.frequencia_base})</dd></div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={() => verPrevia(c)} className="inline-flex items-center gap-1 rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"><CalendarDays className="h-3.5 w-3.5" /> Datas letivas</button>
                <button type="button" onClick={() => abrirEdicao(c)} className="inline-flex items-center gap-1 rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"><Pencil className="h-3.5 w-3.5" /> Editar</button>
                <button type="button" onClick={() => excluir(c)} disabled={c.total_cursos > 0} title={c.total_cursos ? 'Há cursos vinculados' : 'Excluir'} className="inline-flex items-center gap-1 rounded-xl border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-40"><Trash2 className="h-3.5 w-3.5" /> Excluir</button>
              </div>
            </section>
          ))}
        </div>
      )}

      {/* Prévia das datas letivas */}
      {previa && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-3 sm:p-6" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setPrevia(null); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="previa-titulo" className="glass max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 id="previa-titulo" className="text-xl font-extrabold text-white">Datas letivas · {previa.calendario.nome}</h2>
                <p className="text-xs text-slate-400">{previa.datas.total} dia(s) de aula. Meses com 5 semanas destacados.</p>
              </div>
              <button type="button" aria-label="Fechar" onClick={() => setPrevia(null)} className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {previa.datas.meses.map((m) => {
                const [ano, mes] = m.mes.split('-');
                return (
                  <div key={m.mes} className={`rounded-xl border p-3 ${m.recesso ? 'border-slate-800 bg-slate-950/30 opacity-60' : m.quinta_semana.length ? 'border-amber-500/40 bg-amber-500/5' : 'border-slate-800 bg-slate-950/40'}`}>
                    <p className="text-sm font-bold text-white">{MESES[Number(mes) - 1]} {ano}</p>
                    <p className="text-xs text-slate-500">{m.recesso ? 'Recesso' : `${m.datas.length} dia(s) de aula${m.quinta_semana.length ? ' · 5 semanas' : ''}`}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.datas.map((d) => (
                        <span key={d} className={`rounded-md px-1.5 py-0.5 text-[11px] ${m.quinta_semana.includes(d) ? 'bg-amber-500/20 text-amber-200' : 'bg-slate-800 text-slate-200'}`}>{d.slice(8, 10)}</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      )}

      {/* Formulário */}
      {form && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-3 sm:p-6" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setForm(null); }}>
          <form onSubmit={salvar} role="dialog" aria-modal="true" aria-labelledby="form-calendario" className="glass max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 bg-slate-900/95 p-5 backdrop-blur">
              <h2 id="form-calendario" className="text-xl font-extrabold text-white">{editandoId ? 'Editar calendário' : 'Novo calendário'}</h2>
              <button type="button" aria-label="Fechar" onClick={() => setForm(null)} className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
            </header>
            <div className="space-y-6 p-5">
              <section className="grid gap-3 md:grid-cols-4">
                <div className="md:col-span-2"><label className={labelCls}>Nome</label><input required minLength={2} className={inputCls} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></div>
                <div><label className={labelCls}>Início da vigência</label><input required type="date" className={inputCls} value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} /></div>
                <div><label className={labelCls}>Fim da vigência</label><input required type="date" className={inputCls} value={form.data_fim} onChange={(e) => setForm({ ...form, data_fim: e.target.value })} /></div>
                <div className="md:col-span-3"><label className={labelCls}>Descrição</label><input className={inputCls} value={form.descricao || ''} onChange={(e) => setForm({ ...form, descricao: e.target.value })} /></div>
                <label className="flex items-end gap-2 pb-2 text-sm text-slate-300"><input type="checkbox" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /> Ativo</label>
              </section>

              <section>
                <h3 className="mb-2 text-sm font-bold text-white">Dias de aula</h3>
                <div className="flex flex-wrap gap-2">
                  {DIAS_SEMANA.map((d, i) => (
                    <button key={d} type="button" aria-pressed={form.dias_semana.includes(i)} onClick={() => setForm({ ...form, dias_semana: alternar(form.dias_semana, i) })} className={`rounded-xl border px-3 py-1.5 text-xs font-semibold ${form.dias_semana.includes(i) ? 'border-nexus-yellow bg-nexus-yellow/10 text-nexus-yellow' : 'border-slate-700 text-slate-400 hover:bg-slate-800'}`}>{d}</button>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="mb-1 text-sm font-bold text-white">Meses de recesso <span className="ml-1 text-[10px] font-semibold uppercase text-slate-500">Ponto 3</span></h3>
                <p className="mb-2 text-xs text-slate-500">Sem aulas previstas nesses meses (padrão: julho e dezembro).</p>
                <div className="flex flex-wrap gap-2">
                  {MESES.map((m, i) => (
                    <button key={m} type="button" aria-pressed={form.meses_recesso.includes(i + 1)} onClick={() => setForm({ ...form, meses_recesso: alternar(form.meses_recesso, i + 1) })} className={`rounded-xl border px-3 py-1.5 text-xs ${form.meses_recesso.includes(i + 1) ? 'border-amber-500/60 bg-amber-500/10 text-amber-200' : 'border-slate-700 text-slate-400 hover:bg-slate-800'}`}>{m.slice(0, 3)}</button>
                  ))}
                </div>
              </section>

              <section className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className={labelCls}>Feriados</label>
                  <div className="flex gap-2">
                    <input type="date" className={inputCls} value={novoFeriado.data} onChange={(e) => setNovoFeriado({ ...novoFeriado, data: e.target.value })} />
                    <button type="button" disabled={!novoFeriado.data} onClick={() => { setForm({ ...form, feriados: [...form.feriados.filter((f) => f.data !== novoFeriado.data), { data: novoFeriado.data, descricao: novoFeriado.descricao || null }].sort((a, b) => a.data.localeCompare(b.data)) }); setNovoFeriado({ data: '', descricao: '' }); }} className="rounded-xl border border-slate-700 px-3 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40">Adicionar</button>
                  </div>
                  <input className={`${inputCls} mt-2`} placeholder="Descrição (opcional)" value={novoFeriado.descricao} onChange={(e) => setNovoFeriado({ ...novoFeriado, descricao: e.target.value })} />
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {form.feriados.map((f) => (
                      <span key={f.data} className="inline-flex items-center gap-1 rounded-lg bg-slate-800 px-2 py-1 text-xs text-slate-200">
                        {fmtData(f.data)}{f.descricao ? ` · ${f.descricao}` : ''}
                        <button type="button" aria-label="Remover feriado" onClick={() => setForm({ ...form, feriados: form.feriados.filter((x) => x.data !== f.data) })}><X className="h-3 w-3" /></button>
                      </span>
                    ))}
                  </div>
                </div>
                <ListaDatas rotulo="Datas sem aula (exceções)" datas={form.datas_excluidas} onChange={(d) => setForm({ ...form, datas_excluidas: d })} />
                <ListaDatas rotulo="Datas extras de aula" datas={form.datas_extras} onChange={(d) => setForm({ ...form, datas_extras: d })} />
              </section>

              {CAMPOS_REGRAS.map((g) => (
                <section key={g.grupo}>
                  <h3 className="mb-2 text-sm font-bold text-white">{g.grupo}</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    {g.campos.map((c) => (
                      <div key={c.chave} className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <label htmlFor={`regra-${c.chave}`} className="text-xs font-semibold text-slate-200">{c.rotulo}</label>
                          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-400">{c.origem}</span>
                        </div>
                        {c.tipo === 'numero' ? (
                          <input id={`regra-${c.chave}`} type="number" required min={c.min} max={c.max} step={c.passo || 1} className={inputCls}
                            disabled={c.chave === 'duracao_aula_horas' && form.regras.duracao_aula !== 'fixa'}
                            value={form.regras[c.chave] as number} onChange={(e) => setRegra(c.chave, Number(e.target.value))} />
                        ) : c.tipo === 'opcoes' ? (
                          <select id={`regra-${c.chave}`} className={inputCls} value={form.regras[c.chave] as string} onChange={(e) => setRegra(c.chave, e.target.value)}>
                            {c.opcoes?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        ) : (
                          <label className="flex items-center gap-2 text-sm text-slate-300">
                            <input id={`regra-${c.chave}`} type="checkbox" checked={Boolean(form.regras[c.chave])} onChange={(e) => setRegra(c.chave, e.target.checked)} /> Ativado
                          </label>
                        )}
                        {c.ajuda && <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{c.ajuda}</p>}
                      </div>
                    ))}
                    {g.grupo === 'Registro de atas' && (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-200">Quem pode trocar o tipo da aula</span>
                          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-400">RN03.5</span>
                        </div>
                        {PERFIS_COORDENACAO.map((p) => (
                          <label key={p.value} className="flex items-center gap-2 text-sm text-slate-300">
                            <input type="checkbox" checked={form.regras.perfis_alteram_tipo_aula.includes(p.value)}
                              onChange={(e) => setRegra('perfis_alteram_tipo_aula', e.target.checked
                                ? [...form.regras.perfis_alteram_tipo_aula, p.value]
                                : form.regras.perfis_alteram_tipo_aula.filter((x) => x !== p.value))} /> {p.label}
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              ))}

              {erroForm && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erroForm}</p>}
            </div>
            <footer className="sticky bottom-0 flex justify-end gap-2 border-t border-slate-800 bg-slate-900/95 p-4 backdrop-blur">
              <button type="button" onClick={() => setForm(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800">Cancelar</button>
              <button type="submit" disabled={salvando} className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-5 py-2 text-xs font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
                {salvando && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Salvar calendário
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
};
