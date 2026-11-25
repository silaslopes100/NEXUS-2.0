import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Eye,
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
  ProfessorVinculadoDisciplina,
} from '@/features/cursos/api';
import { aulasApi, DisciplinaAulasResumo } from '@/features/aulas/api';
import { formatarData } from '@/features/turmas/api';
import { avaliacoesApi, AvaliacaoResumo } from '@/features/avaliacoes/api';
import { AvaliacaoEditorModal } from '@/features/avaliacoes/components/AvaliacaoEditorModal';
import { MenuAcoes } from '@/components/content/MenuAcoes';

type DisciplinaForm = {
  curso_id: string;
  semestre: string;
  nome: string;
  ordem: string;
  carga_horaria: string;
  qtd_aulas_prevista: string;
  tipo: string;
  eh_extra_grade: boolean;
  ativo: boolean;
  preco: string;
  peso_livro_g: string;
  sku: string;
  ead_prazo_dias: string;
};

const initialForm: DisciplinaForm = {
  curso_id: '',
  semestre: '',
  nome: '',
  ordem: '0',
  carga_horaria: '40',
  qtd_aulas_prevista: '2',
  ead_prazo_dias: '',
  tipo: 'presencial',
  eh_extra_grade: false,
  ativo: true,
  preco: '',
  peso_livro_g: '',
  sku: '',
};

const formatBRL = (valor?: number | null) =>
  valor == null ? '-' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);

/** "49,90" ou "49.90" -> 49.9; vazio -> null; inválido/negativo -> NaN. */
const parsePreco = (valor: string): number | null => {
  const texto = valor.trim().replace(/\s|R\$/g, '');
  if (!texto) return null;
  const normalizado = texto.includes(',') ? texto.replace(/\./g, '').replace(',', '.') : texto;
  const numero = Number(normalizado);
  return Number.isFinite(numero) && numero >= 0 ? Math.round(numero * 100) / 100 : Number.NaN;
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
  const [situacaoFilter, setSituacaoFilter] = useState<'todas' | 'ativas' | 'inativas'>('todas');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editing, setEditing] = useState<Disciplina | null>(null);
  const [form, setForm] = useState<DisciplinaForm>(initialForm);
  const [formError, setFormError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [visualizando, setVisualizando] = useState<Disciplina | null>(null);
  const [professoresVinculados, setProfessoresVinculados] = useState<ProfessorVinculadoDisciplina[]>([]);
  const [carregandoProfessores, setCarregandoProfessores] = useState(false);
  const [erroProfessores, setErroProfessores] = useState('');
  const [tentativaProfessores, setTentativaProfessores] = useState(0);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null
  );
  const [avaliacoesPorDisciplina, setAvaliacoesPorDisciplina] = useState<Map<string, AvaliacaoResumo>>(
    new Map()
  );
  const [editandoAvaliacao, setEditandoAvaliacao] = useState<Disciplina | null>(null);
  const carregarAvaliacoes = () =>
    avaliacoesApi
      .listar()
      .then((itens) => setAvaliacoesPorDisciplina(new Map(itens.map((item) => [item.disciplina_id, item]))))
      .catch(() => setAvaliacoesPorDisciplina(new Map()));
  const [aulasPorDisciplina, setAulasPorDisciplina] = useState<Map<string, DisciplinaAulasResumo>>(
    new Map()
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
    // Auditoria de aulas: complementar, não bloqueia a lista se falhar.
    aulasApi
      .resumoDisciplinas()
      .then((itens) => setAulasPorDisciplina(new Map(itens.map((item) => [item.disciplina_id, item]))))
      .catch(() => setAulasPorDisciplina(new Map()));
    void carregarAvaliacoes();
  }, []);

  useEffect(() => {
    if (!visualizando) {
      setProfessoresVinculados([]);
      setErroProfessores('');
      setCarregandoProfessores(false);
      return;
    }

    let active = true;
    setCarregandoProfessores(true);
    setErroProfessores('');
    cursosApi.listarProfessoresDisciplina(visualizando.id)
      .then((items) => {
        if (active) setProfessoresVinculados(items);
      })
      .catch((err: unknown) => {
        if (active) {
          setErroProfessores(
            cursosApiErrorMessage(err, 'Não foi possível carregar os professores vinculados.')
          );
        }
      })
      .finally(() => {
        if (active) setCarregandoProfessores(false);
      });

    return () => {
      active = false;
    };
  }, [visualizando, tentativaProfessores]);

  const cursoPorId = useMemo(
    () => new Map(cursos.map((curso) => [curso.id, curso.nome])),
    [cursos]
  );

  const disciplinasFiltradas = useMemo(() => {
    const termo = search.trim().toLocaleLowerCase('pt-BR');
    return disciplinas.filter((disciplina) => {
      if (cursoFilter && disciplina.curso_id !== cursoFilter) return false;
      const ativa = disciplina.ativo !== false;
      if (situacaoFilter === 'ativas' && !ativa) return false;
      if (situacaoFilter === 'inativas' && ativa) return false;
      if (!termo) return true;
      const cursoNome = cursoPorId.get(disciplina.curso_id || '') || '';
      return `${disciplina.nome} ${cursoNome} ${disciplina.sku || ''}`.toLocaleLowerCase('pt-BR').includes(termo);
    });
  }, [cursoFilter, situacaoFilter, cursoPorId, disciplinas, search]);

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
      ativo: disciplina.ativo !== false,
      preco: disciplina.preco == null ? '' : Number(disciplina.preco).toFixed(2).replace('.', ','),
      peso_livro_g: disciplina.peso_livro_g == null ? '' : String(disciplina.peso_livro_g),
      sku: disciplina.sku || '',
      ead_prazo_dias: disciplina.ead_prazo_dias == null ? '' : String(disciplina.ead_prazo_dias),
    });
    setFormError('');
    setIsFormOpen(true);
  };

  const salvarDisciplina = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const preco = parsePreco(form.preco);
    if (preco !== null && Number.isNaN(preco)) {
      setFormError('Preço inválido. Use um valor como 49,90.');
      return;
    }
    setIsSaving(true);
    setFormError('');
    setFeedback(null);

    const payload: DisciplinaInput = {
      preco,
      peso_livro_g: optionalNumber(form.peso_livro_g),
      curso_id: form.curso_id || null,
      semestre: optionalNumber(form.semestre),
      nome: form.nome.trim(),
      ordem: Number(form.ordem),
      carga_horaria: optionalNumber(form.carga_horaria),
      qtd_aulas_prevista: optionalNumber(form.qtd_aulas_prevista),
      ead_prazo_dias: optionalNumber(form.ead_prazo_dias),
      tipo: form.tipo.trim(),
      eh_extra_grade: form.eh_extra_grade,
      ativo: form.ativo,
      sku: form.sku.trim().toUpperCase() || null,
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
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center sm:p-8">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Disciplinas
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Cadastre as disciplinas e acompanhe as aulas que cada polo está dando em cada uma.
          </p>
        </div>
        <button
          type="button"
          disabled={isLoading}
          onClick={abrirCadastro}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
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

      <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex flex-col gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-bold text-white">Lista de disciplinas</h2>
            <p className="text-xs text-slate-500">{disciplinasFiltradas.length} disciplinas</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
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
            <select
              aria-label="Filtrar por situação"
              className={inputClass}
              value={situacaoFilter}
              onChange={(event) => setSituacaoFilter(event.target.value as 'todas' | 'ativas' | 'inativas')}
            >
              <option value="todas">Ativas e inativas</option>
              <option value="ativas">Só ativas</option>
              <option value="inativas">Só inativas</option>
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
            <table className="w-full min-w-[960px] text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="p-4">Disciplina</th>
                  <th className="p-4">SKU</th>
                  <th className="p-4">Curso / semestre</th>
                  <th className="p-4">Carga horária</th>
                  <th className="p-4">Aulas previstas</th>
                  <th className="p-4">Tipo</th>
                  <th className="p-4">Preço</th>
                  <th className="p-4">Aulas registradas</th>
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
                      {disciplina.ativo === false && (
                        <span className="ml-1 rounded-full border border-slate-600 px-2 py-0.5 text-xs text-slate-400">
                          Inativa
                        </span>
                      )}
                    </td>
                    <td className="p-4">
                      <span className="whitespace-nowrap font-mono text-xs text-slate-400">{disciplina.sku || '—'}</span>
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
                    <td className="p-4 whitespace-nowrap">
                      {disciplina.preco == null ? '—' : formatBRL(Number(disciplina.preco))}
                    </td>
                    <td className="p-4">
                      {(() => {
                        const resumo = aulasPorDisciplina.get(disciplina.id);
                        if (!resumo) return <span className="text-xs text-slate-500">Nenhuma</span>;
                        return (
                          <Link
                            to={`/admin/aulas?disciplina=${disciplina.id}`}
                            className="group inline-flex flex-col text-left"
                          >
                            <span className="font-semibold text-white group-hover:text-nexus-yellow">
                              {resumo.total_aulas} aula(s)
                            </span>
                            <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                              <CalendarDays className="h-3 w-3" />
                              última em {formatarData(resumo.ultima_aula)}
                            </span>
                          </Link>
                        );
                      })()}
                    </td>
                    <td className="p-4">
                      <div className="flex justify-end gap-2">
                        <Link
                          to={`/admin/aulas?disciplina=${disciplina.id}`}
                          aria-label={`Ver aulas de ${disciplina.nome}`}
                          title="Ver aulas dadas nos polos"
                          className="rounded-lg border border-nexus-yellow/30 p-2 text-nexus-yellow hover:bg-nexus-yellow/10"
                        >
                          <ClipboardList size={16} />
                        </Link>
                        <button
                          type="button"
                          aria-label={`Visualizar professores de ${disciplina.nome}`}
                          onClick={() => {
                            setTentativaProfessores(0);
                            setVisualizando(disciplina);
                          }}
                          className="rounded-lg border border-blue-500/30 p-2 text-blue-300 hover:bg-blue-500/10"
                        >
                          <Eye size={16} />
                        </button>
                        {(() => {
                          const av = avaliacoesPorDisciplina.get(disciplina.id);
                          return (
                            <button
                              type="button"
                              aria-label={`Avaliação de ${disciplina.nome}`}
                              title={
                                av
                                  ? `${av.ativo ? 'Avaliação ativa' : 'Avaliação em rascunho'} · ${av.total_questoes} questão(ões)`
                                  : 'Cadastrar avaliação'
                              }
                              onClick={() => setEditandoAvaliacao(disciplina)}
                              className={`relative rounded-lg border p-2 ${
                                av?.ativo
                                  ? 'border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10'
                                  : 'border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-white'
                              }`}
                            >
                              <ClipboardCheck size={16} />
                              <span
                                className={`absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-slate-900 ${
                                  av?.ativo ? 'bg-emerald-400' : av ? 'bg-amber-400' : 'bg-slate-600'
                                }`}
                              />
                            </button>
                          );
                        })()}
                        <MenuAcoes
                          rotulo={`Mais ações de ${disciplina.nome}`}
                          acoes={[
                            { label: 'Editar', icon: <Pencil size={14} />, onClick: () => abrirEdicao(disciplina) },
                            {
                              label: deletingId === disciplina.id ? 'Excluindo…' : 'Excluir',
                              icon:
                                deletingId === disciplina.id ? (
                                  <Loader2 size={14} className="animate-spin" />
                                ) : (
                                  <Trash2 size={14} />
                                ),
                              perigo: true,
                              disabled: deletingId === disciplina.id,
                              onClick: () => void excluirDisciplina(disciplina),
                            },
                          ]}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
                {disciplinasFiltradas.length === 0 && (
                  <tr>
                    <td colSpan={9} className="p-12 text-center text-slate-500">
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

      {editandoAvaliacao && (
        <AvaliacaoEditorModal
          disciplinaId={editandoAvaliacao.id}
          disciplinaNome={editandoAvaliacao.nome}
          onClose={() => setEditandoAvaliacao(null)}
          onSalvo={(ativo) => {
            setFeedback({
              type: 'success',
              message: ativo ? 'Avaliação salva e ativada.' : 'Avaliação salva como rascunho.',
            });
            setEditandoAvaliacao(null);
            void carregarAvaliacoes();
          }}
        />
      )}

      {visualizando && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setVisualizando(null);
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="disciplina-professores-titulo"
            className="glass my-auto w-full max-w-3xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
          >
            <header className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-blue-300">
                  Professores vinculados
                </p>
                <h2 id="disciplina-professores-titulo" className="mt-1 text-xl font-bold text-white">
                  {visualizando.nome}
                </h2>
              </div>
              <button
                type="button"
                aria-label="Fechar professores vinculados"
                onClick={() => setVisualizando(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X size={20} />
              </button>
            </header>

            {carregandoProfessores ? (
              <div role="status" className="flex items-center justify-center gap-2 py-12 text-blue-300">
                <Loader2 className="animate-spin" size={18} />
                Carregando professores...
              </div>
            ) : erroProfessores ? (
              <div className="flex flex-col items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 sm:flex-row sm:items-center sm:justify-between">
                <p role="alert" className="text-sm text-red-200">{erroProfessores}</p>
                <button
                  type="button"
                  onClick={() => setTentativaProfessores((tentativa) => tentativa + 1)}
                  className="shrink-0 text-sm font-semibold text-blue-300 hover:underline"
                >
                  Tentar novamente
                </button>
              </div>
            ) : professoresVinculados.length === 0 ? (
              <p className="rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-sm text-slate-400">
                Nenhum professor vinculado a esta disciplina.
              </p>
            ) : (
              <div className="max-h-[60vh] space-y-3 overflow-y-auto">
                {professoresVinculados.map((professor) => (
                  <article
                    key={professor.professor_id}
                    className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4 sm:grid-cols-2"
                  >
                    <div className="sm:col-span-2">
                      <h3 className="font-semibold text-white">{professor.nome}</h3>
                      <p className="text-sm text-slate-400">{professor.email || 'E-mail não informado'}</p>
                    </div>
                    <p className="text-sm text-slate-300">
                      <span className="text-slate-500">Polo: </span>
                      {professor.polo_nome || 'Não vinculado'}
                    </p>
                    <p className="text-sm text-slate-300">
                      <span className="text-slate-500">Escola: </span>
                      {professor.escola_nome || 'Não vinculada'}
                    </p>
                    <p className="text-sm text-slate-300">
                      <span className="text-slate-500">Valor hora/aula: </span>
                      {professor.valor_hora_aula == null
                        ? 'Não informado'
                        : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
                            .format(professor.valor_hora_aula)}
                    </p>
                    <p className="text-sm text-slate-300">
                      <span className="text-slate-500">Quantidade de aulas: </span>
                      {professor.quantidade_aulas}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

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
            className="glass my-auto w-full max-w-2xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
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
                <span>Carga horária (h) *</span>
                <input
                  required
                  type="number"
                  min={1}
                  step={1}
                  className={inputClass}
                  value={form.carga_horaria}
                  onChange={(event) => setForm({ ...form, carga_horaria: event.target.value })}
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Aulas previstas *</span>
                <input
                  required
                  type="number"
                  min={1}
                  step={1}
                  className={inputClass}
                  value={form.qtd_aulas_prevista}
                  onChange={(event) =>
                    setForm({ ...form, qtd_aulas_prevista: event.target.value })
                  }
                />
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Prazo EAD (dias)</span>
                <input
                  type="number"
                  min={1}
                  max={730}
                  step={1}
                  placeholder="Padrão do calendário"
                  className={inputClass}
                  value={form.ead_prazo_dias}
                  onChange={(event) => setForm({ ...form, ead_prazo_dias: event.target.value })}
                />
                <span className="block text-xs text-slate-500">Na turma EAD, dias para concluir depois de liberada.</span>
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
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>SKU</span>
                <input
                  maxLength={64}
                  placeholder="Gerado automaticamente se vazio"
                  className={`${inputClass} font-mono uppercase`}
                  value={form.sku}
                  onChange={(event) => setForm({ ...form, sku: event.target.value })}
                />
                <span className="block text-xs text-slate-500">Código do kit (livro + licença) usado em pedidos e no estoque.</span>
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Preço da disciplina (R$)</span>
                <input
                  inputMode="decimal"
                  placeholder="Ex.: 49,90"
                  className={inputClass}
                  value={form.preco}
                  onChange={(event) => setForm({ ...form, preco: event.target.value })}
                />
                <span className="block text-xs text-slate-500">
                  Valor de 1 livro + 1 licença. Com preço, a disciplina fica à venda em "Comprar Disciplinas"; em branco, não é vendida.
                </span>
              </label>
              <label className="space-y-1.5 text-sm text-slate-300">
                <span>Peso do livro (g)</span>
                <input
                  type="number"
                  min={0}
                  step={10}
                  placeholder="Ex.: 450"
                  className={inputClass}
                  value={form.peso_livro_g}
                  onChange={(event) => setForm({ ...form, peso_livro_g: event.target.value })}
                />
                <span className="block text-xs text-slate-500">Usado na etiqueta de envio.</span>
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
              <label className="flex items-start gap-2 text-sm text-slate-300 sm:col-span-2">
                <input
                  type="checkbox"
                  checked={form.ativo}
                  onChange={(event) => setForm({ ...form, ativo: event.target.checked })}
                  className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-950 text-blue-600"
                />
                <span>
                  Disciplina ativa
                  <span className="block text-xs text-slate-500">
                    Inativa sai da compra por Curso e não entra no preço do curso. Pedidos e notas já feitos não mudam.
                  </span>
                </span>
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
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
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
