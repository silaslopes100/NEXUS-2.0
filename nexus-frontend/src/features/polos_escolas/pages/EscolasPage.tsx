import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  Building2,
  CalendarDays,
  CheckCircle2,
  Edit2,
  KeyRound,
  Loader2,
  MapPin,
  Plus,
  Search,
  School,
  UserCheck,
  Users,
  X,
} from 'lucide-react';
import { alunosApi } from '@/features/alunos/api';
import { EscolaEditModal } from '@/features/polos_escolas/components/EscolaEditModal';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  EscolaCreatePayload,
  EscolaItem,
  PoloItem,
  ResumoOperacionalEscola,
} from '@/types/polos';
import { useAuthStore } from '@/stores/authStore';

const PAGE_SIZE = 50;
const initialForm: EscolaCreatePayload = {
  polo_id: '',
  nome: '',
  endereco: { logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', estado: '', cep: '' },
  secretario_nome: '',
  secretario_cpf: '',
  secretario_email: '',
  secretario_senha: '',
};

type Indicador = 'alunos' | 'aulas' | 'professores' | 'turmas';
type Registro = Record<string, unknown>;

const statusClass = (status: string) =>
  status === 'ativo'
    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
    : 'border-slate-700 bg-slate-800 text-slate-400';

const IndicadorCard: React.FC<{
  label: string;
  value: number;
  icon: React.ReactNode;
  onClick?: () => void;
}> = ({ label, value, icon, onClick }) => (
  <button
    type="button"
    disabled={!onClick}
    onClick={onClick}
    className={`rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-left ${
      onClick ? 'transition-colors hover:border-blue-500/50 hover:bg-slate-900' : 'cursor-default'
    }`}
  >
    <span className="flex items-center justify-between text-xs font-semibold uppercase text-slate-500">
      {label}
      <span className="text-blue-300">{icon}</span>
    </span>
    <strong className="mt-2 block text-2xl font-black text-white">{value}</strong>
  </button>
);

function mostrarValor(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string' && value.includes('T')) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) return date.toLocaleDateString('pt-BR');
  }
  return String(value);
}

export const EscolasPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const role = user?.perfil?.nome?.toLowerCase() || '';
  const isAdmin = role === 'admin';
  const [schools, setSchools] = useState<EscolaItem[]>([]);
  const [poles, setPoles] = useState<PoloItem[]>([]);
  const [query, setQuery] = useState('');
  const [appliedQuery, setAppliedQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<EscolaCreatePayload>(initialForm);
  const [selectedSchool, setSelectedSchool] = useState<EscolaItem | null>(null);
  const [summary, setSummary] = useState<ResumoOperacionalEscola | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [editingSchool, setEditingSchool] = useState<EscolaItem | null>(null);
  const [indicator, setIndicator] = useState<Indicador | null>(null);
  const [indicatorItems, setIndicatorItems] = useState<Registro[]>([]);
  const [indicatorLoading, setIndicatorLoading] = useState(false);

  const loadSchools = useCallback(async () => {
    setLoading(true);
    try {
      const result = await polosEscolasApi.listarEscolas({
        q: appliedQuery || undefined,
        status: statusFilter || undefined,
        polo_id: isAdmin ? undefined : user?.polo_id || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setSchools(result.items || []);
      setTotal(result.total || 0);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'Não foi possível carregar as escolas.');
    } finally {
      setLoading(false);
    }
  }, [appliedQuery, isAdmin, offset, statusFilter, user?.polo_id]);

  useEffect(() => {
    void loadSchools();
  }, [loadSchools]);

  useEffect(() => {
    const loadPoles = isAdmin
      ? polosEscolasApi.listarPolos({ limit: 200 }).then((result) => result.items || [])
      : user?.polo_id
        ? polosEscolasApi.obterPolo(user.polo_id).then((polo) => [polo])
        : Promise.resolve([]);
    loadPoles.then((result) => {
      setPoles(result);
    }).catch((error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'Não foi possível carregar os polos.');
    });
  }, [isAdmin, user?.polo_id]);

  const openSchool = async (school: EscolaItem) => {
    setSelectedSchool(school);
    setSummary(null);
    setIndicator(null);
    setDetailLoading(true);
    try {
      const [details, operationalSummary] = await Promise.all([
        polosEscolasApi.obterEscola(school.id),
        polosEscolasApi.getResumoOperacionalEscola(school.id),
      ]);
      setSelectedSchool(details);
      setSummary(operationalSummary);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'Não foi possível carregar os dados da escola.');
    } finally {
      setDetailLoading(false);
    }
  };

  const loadIndicator = async (kind: Indicador) => {
    if (!selectedSchool) return;
    setIndicator(kind);
    setIndicatorLoading(true);
    try {
      let items: Registro[] = [];
      if (kind === 'alunos') {
        const result = await alunosApi.listar(selectedSchool.polo_id, {
          escola_id: selectedSchool.id,
          limit: 100,
          offset: 0,
        });
        items = result.items as unknown as Registro[];
      } else if (kind === 'turmas') {
        const result = await alunosApi.listarTurmasEscola(selectedSchool.id);
        items = result.items as unknown as Registro[];
      } else if (kind === 'aulas') {
        const result = await polosEscolasApi.listarAulasEscola(selectedSchool.id, {
          limit: 100,
          offset: 0,
        });
        items = result.items as Registro[];
      } else {
        const result = await polosEscolasApi.listarProfessoresEscola(selectedSchool.id, {
          limit: 100,
          offset: 0,
        });
        items = result.items as Registro[];
      }
      setIndicatorItems(items);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || `Não foi possível carregar a lista de ${kind}.`);
      setIndicatorItems([]);
    } finally {
      setIndicatorLoading(false);
    }
  };

  const createSchool = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const poloId = isAdmin ? form.polo_id : user?.polo_id || '';
    if (!poloId) {
      setFeedback('Selecione um polo para cadastrar a escola.');
      return;
    }
    setSaving(true);
    try {
      await polosEscolasApi.criarEscola(poloId, { ...form, polo_id: poloId });
      setCreateOpen(false);
      setForm({ ...initialForm, polo_id: user?.polo_id || '' });
      setFeedback('Escola cadastrada com sucesso.');
      setQuery('');
      setAppliedQuery('');
      setStatusFilter('');
      setOffset(0);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'Não foi possível cadastrar a escola.');
    } finally {
      setSaving(false);
    }
  };

  const deactivateSchool = async (school: EscolaItem) => {
    if (!window.confirm(`Tornar a escola "${school.nome}" inativa? Os dados e vínculos serão preservados.`)) {
      return;
    }
    try {
      await polosEscolasApi.atualizarEscola(school.id, { status: 'inativo' });
      setFeedback('Escola desativada. Os dados e vínculos foram preservados.');
      await loadSchools();
      if (selectedSchool?.id === school.id) {
        setSelectedSchool({ ...selectedSchool, status: 'inativo' });
      }
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      setFeedback(err.response?.data?.detail || 'Não foi possível desativar a escola.');
    }
  };

  const address = selectedSchool?.endereco;
  const indicatorColumns = useMemo(() => {
    if (!indicator) return [];
    const fields: Record<Indicador, Array<[string, keyof Registro]>> = {
      alunos: [['Nome', 'nome'], ['E-mail', 'email'], ['Matrícula', 'numero_matricula'], ['Status', 'status']],
      aulas: [['Data', 'data_aula'], ['Professor', 'professor_nome'], ['Conteúdo', 'conteudo'], ['Aulas previstas', 'total_aulas_previstas']],
      professores: [['Nome', 'nome'], ['E-mail', 'email'], ['Status', 'status'], ['Aulas', 'quantidade_aulas']],
      turmas: [['Turma', 'nome'], ['Alunos', 'total_alunos'], ['Início', 'data_inicio'], ['Fim', 'data_fim']],
    };
    return fields[indicator];
  }, [indicator]);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/30 p-6 shadow-xl sm:flex-row sm:items-center">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-300">
            <School size={16} /> Gestão de unidades
          </p>
          <h1 className="text-3xl font-extrabold text-white">Escolas</h1>
          <p className="mt-1 text-sm text-slate-400">Cadastre, consulte e gerencie as escolas da rede.</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setForm({ ...initialForm, polo_id: user?.polo_id || '' });
            setCreateOpen(true);
          }}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          <Plus size={16} /> Cadastrar escola
        </button>
      </header>

      {feedback && (
        <div role="status" className="flex items-center justify-between rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200">
          <span className="flex items-center gap-2"><CheckCircle2 size={16} />{feedback}</span>
          <button type="button" onClick={() => setFeedback('')} aria-label="Fechar mensagem"><X size={16} /></button>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex flex-col gap-3 border-b border-slate-800 p-4 sm:flex-row">
          <form
            className="flex flex-1 gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              setOffset(0);
              setAppliedQuery(query.trim());
            }}
          >
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar por escola ou cidade"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
            <button type="submit" className="rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white">Buscar</button>
          </form>
          <select
            value={statusFilter}
            onChange={(event) => { setStatusFilter(event.target.value); setOffset(0); }}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
            aria-label="Filtrar por status"
          >
            <option value="">Todos os status</option>
            <option value="ativo">Ativas</option>
            <option value="inativo">Inativas</option>
          </select>
        </div>
        {loading ? (
          <div className="flex justify-center py-16 text-indigo-300"><Loader2 className="animate-spin" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr><th className="p-4">Escola</th><th className="p-4">Cidade</th><th className="p-4">Responsável</th><th className="p-4">Status</th><th className="p-4 text-right">Ações</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {schools.map((school) => (
                  <tr key={school.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4 font-semibold text-white">{school.nome}</td>
                    <td className="p-4">{school.endereco?.cidade || '—'}</td>
                    <td className="p-4">{school.secretario_nome || '—'}</td>
                    <td className="p-4"><span className={`rounded-full border px-2.5 py-1 text-xs ${statusClass(school.status)}`}>{school.status}</span></td>
                    <td className="p-4">
                      <div className="flex justify-end gap-2">
                        <button type="button" onClick={() => void openSchool(school)} className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">Detalhes</button>
                        <button type="button" title="Editar escola" onClick={() => setEditingSchool(school)} className="rounded-lg border border-slate-700 p-1.5 text-slate-300 hover:bg-slate-800"><Edit2 size={15} /></button>
                        {school.status === 'ativo' && (
                          <button type="button" onClick={() => void deactivateSchool(school)} className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10">Inativar</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!schools.length && <tr><td colSpan={5} className="p-12 text-center text-slate-500">Nenhuma escola encontrada.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
        {total > PAGE_SIZE && (
          <footer className="flex items-center justify-between border-t border-slate-800 px-4 py-3 text-sm text-slate-400">
            <span>{offset + 1}–{Math.min(offset + schools.length, total)} de {total}</span>
            <div className="flex items-center gap-2">
              <button type="button" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 disabled:opacity-40"><ArrowLeft size={14} /> Anterior</button>
              <button type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)} className="rounded-lg border border-slate-700 px-3 py-1.5 disabled:opacity-40">Próxima</button>
            </div>
          </footer>
        )}
      </section>

      {selectedSchool && (
        <div className="fixed inset-0 z-40 flex justify-end bg-black/70" onMouseDown={(event) => {
          if (event.target === event.currentTarget) { setSelectedSchool(null); setIndicator(null); }
        }}>
          <aside className="h-full w-full max-w-4xl overflow-y-auto border-l border-slate-800 bg-slate-900 p-5 shadow-2xl sm:p-7">
            <div className="mb-6 flex items-start justify-between gap-3">
              <div>
                <button type="button" onClick={() => { setSelectedSchool(null); setIndicator(null); }} className="mb-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"><ArrowLeft size={14} /> Voltar à consulta</button>
                <h2 className="text-2xl font-bold text-white">{selectedSchool.nome}</h2>
                <span className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-xs ${statusClass(selectedSchool.status)}`}>{selectedSchool.status}</span>
              </div>
              <button type="button" onClick={() => { setSelectedSchool(null); setIndicator(null); }} aria-label="Fechar detalhes" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800"><X /></button>
            </div>

            {detailLoading ? <div className="flex justify-center py-16 text-indigo-300"><Loader2 className="animate-spin" /></div> : (
              <div className="space-y-6">
                <section className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                  <h3 className="mb-4 flex items-center gap-2 font-semibold text-white"><Building2 size={17} className="text-indigo-300" /> Dados cadastrais</h3>
                  <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                    <div><span className="block text-xs uppercase text-slate-500">Polo</span><span className="text-slate-200">{poles.find((polo) => polo.id === selectedSchool.polo_id)?.nome || selectedSchool.polo_id}</span></div>
                    <div><span className="block text-xs uppercase text-slate-500">Responsável</span><span className="text-slate-200">{selectedSchool.secretario_nome || '—'}</span></div>
                    <div><span className="block text-xs uppercase text-slate-500">CPF</span><span className="text-slate-200">{selectedSchool.secretario_cpf || '—'}</span></div>
                    <div><span className="block text-xs uppercase text-slate-500">E-mail</span><span className="text-slate-200">{selectedSchool.secretario_email || '—'}</span></div>
                    <div className="flex items-center gap-1 text-slate-200 sm:col-span-2"><MapPin size={14} className="text-slate-500" />{[address?.logradouro, address?.numero, address?.complemento, address?.bairro, address?.cidade, address?.estado, address?.cep].filter(Boolean).join(', ') || 'Endereço não informado'}</div>
                  </div>
                </section>

                <section>
                  <h3 className="mb-3 font-semibold text-white">Indicadores operacionais</h3>
                  {summary ? (
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                      <IndicadorCard label="Alunos" value={summary.alunos} icon={<Users size={17} />} onClick={() => void loadIndicator('alunos')} />
                      <IndicadorCard label="Aulas" value={summary.aulas} icon={<BookOpen size={17} />} onClick={() => void loadIndicator('aulas')} />
                      <IndicadorCard label="Professores" value={summary.professores} icon={<UserCheck size={17} />} onClick={() => void loadIndicator('professores')} />
                      <IndicadorCard label="Turmas" value={summary.turmas} icon={<CalendarDays size={17} />} onClick={() => void loadIndicator('turmas')} />
                      <IndicadorCard label="Licenças em estoque" value={summary.licencas_estoque} icon={<KeyRound size={17} />} />
                      <IndicadorCard label="Licenças de alunos" value={summary.licencas_alunos} icon={<Users size={17} />} />
                      <IndicadorCard label="Licenças atribuídas" value={summary.licencas_atribuidas} icon={<KeyRound size={17} />} />
                      <IndicadorCard label="Movimentações de licenças" value={summary.licencas_movimentacoes} icon={<KeyRound size={17} />} />
                      <IndicadorCard label="Pedidos de licenças" value={summary.pedidos_licencas} icon={<KeyRound size={17} />} />
                      <IndicadorCard label="Pedidos de livros" value={summary.pedidos_livros} icon={<BookOpen size={17} />} />
                    </div>
                  ) : <p className="rounded-xl border border-slate-800 p-4 text-sm text-slate-400">Os indicadores não estão disponíveis.</p>}
                </section>

                <button
                  type="button"
                  onClick={() => navigate(`${isAdmin ? '/admin' : '/polo'}/escolas/${selectedSchool.id}/licencas`)}
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-500"
                >
                  <KeyRound size={16} /> Gestão de licenças da escola
                </button>

                {indicator && (
                  <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/60">
                    <div className="flex items-center justify-between border-b border-slate-800 p-4">
                      <h3 className="font-semibold capitalize text-white">Lista de {indicator}</h3>
                      <button type="button" onClick={() => setIndicator(null)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800" aria-label="Fechar lista"><X size={18} /></button>
                    </div>
                    {indicatorLoading ? <div className="flex justify-center py-10 text-indigo-300"><Loader2 className="animate-spin" /></div> : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500"><tr>{indicatorColumns.map(([label]) => <th key={label} className="p-3">{label}</th>)}</tr></thead>
                          <tbody className="divide-y divide-slate-800">
                            {indicatorItems.map((item, index) => <tr key={String(item.id || item.aluno_id || index)} className="text-slate-300">{indicatorColumns.map(([label, key]) => <td key={label} className="max-w-xs truncate p-3">{mostrarValor(item[key])}</td>)}</tr>)}
                            {!indicatorItems.length && <tr><td colSpan={indicatorColumns.length} className="p-8 text-center text-slate-500">Nenhum registro encontrado.</td></tr>}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>
                )}
              </div>
            )}
          </aside>
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form onSubmit={createSchool} className="max-h-[90vh] w-full max-w-2xl space-y-4 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="flex items-center justify-between"><h2 className="text-xl font-bold text-white">Cadastrar escola</h2><button type="button" onClick={() => setCreateOpen(false)} aria-label="Fechar"><X /></button></div>
            <input required minLength={2} className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" placeholder="Nome da escola" value={form.nome} onChange={(event) => setForm({ ...form, nome: event.target.value })} />
            {isAdmin && <select required className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" value={form.polo_id} onChange={(event) => setForm({ ...form, polo_id: event.target.value })}><option value="">Selecione o polo</option>{poles.map((polo) => <option key={polo.id} value={polo.id}>{polo.nome}</option>)}</select>}
            <div className="grid gap-3 sm:grid-cols-2">
              {(['logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep'] as const).map((field) => <input key={field} className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" placeholder={field[0].toUpperCase() + field.slice(1)} value={form.endereco?.[field] || ''} onChange={(event) => setForm({ ...form, endereco: { ...form.endereco, [field]: event.target.value } })} />)}
            </div>
            <div className="border-t border-slate-800 pt-4"><h3 className="mb-3 text-sm font-semibold text-slate-200">Responsável da escola</h3><div className="grid gap-3 sm:grid-cols-2">
              <input required className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" placeholder="Nome" value={form.secretario_nome} onChange={(event) => setForm({ ...form, secretario_nome: event.target.value })} />
              <input required minLength={11} className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" placeholder="CPF" value={form.secretario_cpf} onChange={(event) => setForm({ ...form, secretario_cpf: event.target.value })} />
              <input required type="email" className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" placeholder="E-mail" value={form.secretario_email} onChange={(event) => setForm({ ...form, secretario_email: event.target.value })} />
              <input required minLength={8} type="password" className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white" placeholder="Senha inicial" value={form.secretario_senha} onChange={(event) => setForm({ ...form, secretario_senha: event.target.value })} />
            </div></div>
            <div className="flex justify-end gap-2"><button type="button" onClick={() => setCreateOpen(false)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving && <Loader2 className="animate-spin" size={15} />}Cadastrar</button></div>
          </form>
        </div>
      )}

      {editingSchool && <EscolaEditModal escola={editingSchool} polos={poles} onClose={() => setEditingSchool(null)} onSuccess={() => void loadSchools()} />}
    </div>
  );
};
