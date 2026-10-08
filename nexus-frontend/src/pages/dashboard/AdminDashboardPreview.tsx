import React, { FormEvent, useMemo, useState } from 'react';
import {
  ArrowDownToLine,
  Award,
  Building2,
  CalendarDays,
  ChevronRight,
  GraduationCap,
  KeyRound,
  MapPin,
  School,
  Users,
  X,
} from 'lucide-react';
import { Link } from 'react-router-dom';

type WidgetId = 'students' | 'enrollments' | 'ranking' | 'units' | 'teachers' | 'certificates';
type UnitTab = 'polos' | 'escolas';
type DemoFilters = {
  dataInicio: string;
  dataFim: string;
  mes: string;
  semestre: string;
  ano: string;
  polo: string;
  escola: string;
  pais: string;
  estado: string;
  curso: string;
};

interface DemoSection {
  title: string;
  lines: string[];
}

interface DemoItem {
  id: string;
  title: string;
  subtitle: string;
  date: string;
  polo?: string;
  escola?: string;
  pais?: string;
  estado?: string;
  curso?: string;
  semestre?: string;
  licenses?: number;
  fields: Array<[string, string]>;
  sections?: DemoSection[];
}

const initialFilters: DemoFilters = {
  dataInicio: '',
  dataFim: '',
  mes: '',
  semestre: '',
  ano: '',
  polo: '',
  escola: '',
  pais: '',
  estado: '',
  curso: '',
};

const demoStudents: DemoItem[] = [
  {
    id: 'aluno-1',
    title: 'Ana Beatriz Martins',
    subtitle: 'Matrícula DEMO-2025-001 · Ativo',
    date: '2025-02-10',
    polo: 'Polo São Paulo',
    escola: 'Escola Central',
    pais: 'Brasil',
    estado: 'SP',
    curso: 'Teologia',
    semestre: '1º',
    fields: [
      ['E-mail', 'ana.martins@example.test'],
      ['Polo', 'Polo São Paulo'],
      ['Escola', 'Escola Central'],
      ['Curso', 'Teologia'],
      ['Semestre', '1º semestre'],
    ],
  },
  {
    id: 'aluno-2',
    title: 'Lucas Ferreira Costa',
    subtitle: 'Matrícula DEMO-2025-014 · Ativo',
    date: '2025-04-18',
    polo: 'Polo Campinas',
    escola: 'Escola Esperança',
    pais: 'Brasil',
    estado: 'SP',
    curso: 'Teologia',
    semestre: '2º',
    fields: [
      ['E-mail', 'lucas.costa@example.test'],
      ['Polo', 'Polo Campinas'],
      ['Escola', 'Escola Esperança'],
      ['Curso', 'Teologia'],
      ['Semestre', '2º semestre'],
    ],
  },
  {
    id: 'aluno-3',
    title: 'Mariana Oliveira Santos',
    subtitle: 'Matrícula DEMO-2025-027 · Ativo',
    date: '2025-07-03',
    polo: 'Polo Rio de Janeiro',
    escola: 'Escola Semeadores',
    pais: 'Brasil',
    estado: 'RJ',
    curso: 'Teologia',
    semestre: '3º',
    fields: [
      ['E-mail', 'mariana.santos@example.test'],
      ['Polo', 'Polo Rio de Janeiro'],
      ['Escola', 'Escola Semeadores'],
      ['Curso', 'Teologia'],
      ['Semestre', '3º semestre'],
    ],
  },
];

const demoEnrollments: DemoItem[] = [
  { id: 'mat-1', title: 'Ana Beatriz Martins', subtitle: 'Nova matrícula · 3 licenças/livros', date: '2025-02-10', polo: 'Polo São Paulo', escola: 'Escola Central', semestre: '1º', licenses: 3, fields: [['Curso', 'Teologia'], ['Quantidade adquirida', '3']] },
  { id: 'mat-2', title: 'Lucas Ferreira Costa', subtitle: 'Nova matrícula · 2 licenças/livros', date: '2025-04-18', polo: 'Polo Campinas', escola: 'Escola Esperança', semestre: '2º', licenses: 2, fields: [['Curso', 'Teologia'], ['Quantidade adquirida', '2']] },
  { id: 'mat-3', title: 'Mariana Oliveira Santos', subtitle: 'Nova matrícula · 4 licenças/livros', date: '2025-07-03', polo: 'Polo Rio de Janeiro', escola: 'Escola Semeadores', semestre: '3º', licenses: 4, fields: [['Curso', 'Teologia'], ['Quantidade adquirida', '4']] },
  { id: 'mat-4', title: 'Rafael Almeida Souza', subtitle: 'Nova matrícula · 1 licença/livro', date: '2025-08-21', polo: 'Polo São Paulo', escola: 'Escola Central', semestre: '3º', licenses: 1, fields: [['Curso', 'Teologia'], ['Quantidade adquirida', '1']] },
  { id: 'mat-5', title: 'Beatriz Lima Carvalho', subtitle: 'Nova matrícula · 5 licenças/livros', date: '2025-10-06', polo: 'Polo Campinas', escola: 'Escola Esperança', semestre: '1º', licenses: 5, fields: [['Curso', 'Teologia'], ['Quantidade adquirida', '5']] },
];

const demoPoles: DemoItem[] = [
  { id: 'polo-1', title: 'Polo São Paulo', subtitle: 'Ativo · São Paulo/SP', date: '2022-01-12', fields: [['Responsável', 'Carlos Mendes'], ['E-mail', 'sp@example.test'], ['Endereço', 'Av. Paulista, 1000 · São Paulo/SP'], ['Escolas vinculadas', '1'], ['Alunos ativos', '320']] },
  { id: 'polo-2', title: 'Polo Campinas', subtitle: 'Ativo · Campinas/SP', date: '2022-06-21', fields: [['Responsável', 'Patrícia Nogueira'], ['E-mail', 'campinas@example.test'], ['Endereço', 'Rua das Flores, 85 · Campinas/SP'], ['Escolas vinculadas', '1'], ['Alunos ativos', '185']] },
  { id: 'polo-3', title: 'Polo Rio de Janeiro', subtitle: 'Ativo · Rio de Janeiro/RJ', date: '2023-03-09', fields: [['Responsável', 'João Ribeiro'], ['E-mail', 'rio@example.test'], ['Endereço', 'Rua do Carmo, 22 · Rio de Janeiro/RJ'], ['Escolas vinculadas', '1'], ['Alunos ativos', '142']] },
];

const demoSchools: DemoItem[] = [
  { id: 'escola-1', title: 'Escola Central', subtitle: 'Ativa · Polo São Paulo', date: '2022-02-01', polo: 'Polo São Paulo', fields: [['Responsável', 'Fernanda Alves'], ['E-mail', 'central@example.test'], ['Endereço', 'Rua Aurora, 12 · São Paulo/SP'], ['Polo vinculado', 'Polo São Paulo'], ['Alunos ativos', '320']] },
  { id: 'escola-2', title: 'Escola Esperança', subtitle: 'Ativa · Polo Campinas', date: '2022-07-01', polo: 'Polo Campinas', fields: [['Responsável', 'Roberto Dias'], ['E-mail', 'esperanca@example.test'], ['Endereço', 'Av. Brasil, 250 · Campinas/SP'], ['Polo vinculado', 'Polo Campinas'], ['Alunos ativos', '185']] },
  { id: 'escola-3', title: 'Escola Semeadores', subtitle: 'Ativa · Polo Rio de Janeiro', date: '2023-04-01', polo: 'Polo Rio de Janeiro', fields: [['Responsável', 'Sônia Castro'], ['E-mail', 'semeadores@example.test'], ['Endereço', 'Rua da Paz, 40 · Rio de Janeiro/RJ'], ['Polo vinculado', 'Polo Rio de Janeiro'], ['Alunos ativos', '142']] },
];

const demoTeachers: DemoItem[] = [
  {
    id: 'prof-1',
    title: 'Pr. Daniel Carvalho',
    subtitle: 'Ativo · Teologia Sistemática',
    date: '2023-02-15',
    fields: [['E-mail', 'daniel.carvalho@example.test'], ['Polo', 'Polo São Paulo'], ['Escola', 'Escola Central'], ['Início das atividades', '15/02/2023']],
    sections: [
      { title: 'Anexos de aula', lines: ['12/09/2025 · Teologia Sistemática · Apostila (demonstração)', '19/09/2025 · Hermenêutica · Material de apoio (demonstração)'] },
      { title: 'Atas', lines: ['Ata da aula de 12/09/2025 · Teologia Sistemática', 'Ata da aula de 19/09/2025 · Hermenêutica'] },
      { title: 'Lista de chamada', lines: ['Teologia Sistemática · 18 de 20 aulas · 90% de presença', 'Hermenêutica · 16 de 18 aulas · 88,9% de presença', 'Alunos: Ana Beatriz Martins (95%), Lucas Ferreira Costa (85%)'] },
    ],
  },
  {
    id: 'prof-2',
    title: 'Profa. Helena Duarte',
    subtitle: 'Ativa · História da Igreja',
    date: '2024-01-08',
    fields: [['E-mail', 'helena.duarte@example.test'], ['Polo', 'Polo Campinas'], ['Escola', 'Escola Esperança'], ['Início das atividades', '08/01/2024']],
    sections: [
      { title: 'Anexos de aula', lines: ['05/09/2025 · História da Igreja · Slides (demonstração)'] },
      { title: 'Atas', lines: ['Ata da aula de 05/09/2025 · História da Igreja'] },
      { title: 'Lista de chamada', lines: ['História da Igreja · 14 de 16 aulas · 87,5% de presença', 'Alunos: Mariana Oliveira Santos (92%), Rafael Almeida Souza (83%)'] },
    ],
  },
];

const demoCertificates: DemoItem[] = [
  {
    id: 'cert-1',
    title: 'Ana Beatriz Martins',
    subtitle: 'Certificado emitido · Teologia',
    date: '2025-08-12',
    fields: [['Curso', 'Teologia'], ['Data de emissão', '12/08/2025'], ['Histórico', 'Concluído (demonstração)']],
    sections: [{ title: 'Estágios obrigatórios', lines: ['Teologia do Ministério · entregue em 10/05/2025', 'Homilética · entregue em 22/06/2025'] }],
  },
  {
    id: 'cert-2',
    title: 'Lucas Ferreira Costa',
    subtitle: 'Certificado emitido · Teologia',
    date: '2025-09-24',
    fields: [['Curso', 'Teologia'], ['Data de emissão', '24/09/2025'], ['Histórico', 'Concluído (demonstração)']],
    sections: [{ title: 'Estágios obrigatórios', lines: ['Teologia do Ministério · entregue em 03/06/2025', 'Homilética · entregue em 18/08/2025'] }],
  },
];

const widgets: Array<{ id: WidgetId | 'licenses'; title: string; value: string; description: string; icon: React.ElementType }> = [
  { id: 'students', title: 'Alunos Ativos', value: '647', description: 'Abrir listagem, filtrar e consultar perfil', icon: Users },
  { id: 'enrollments', title: 'Quantidade de Matrículas', value: '1.284', description: 'Filtrar por período e gerar ranking em PDF', icon: GraduationCap },
  { id: 'ranking', title: 'Ranking de Polos', value: '3 polos', description: 'Novas licenças/livros por período · PDF', icon: Award },
  { id: 'units', title: 'Polos e Escolas Ativas', value: '48 / 126', description: 'Abrir listagens e consultar detalhes', icon: Building2 },
  { id: 'teachers', title: 'Professores Ativos', value: '124', description: 'Consultar perfil, anexos, atas e chamada', icon: GraduationCap },
  { id: 'certificates', title: 'Emissões de Certificados', value: '86', description: 'Consultar alunos e estágios obrigatórios', icon: Award },
  { id: 'licenses', title: 'Estoque de Licenças', value: '2.450', description: 'Ir para Gestão Acadêmica › Licenças', icon: KeyRound },
];

const inputClass = 'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

function matchesDate(date: string, filters: DemoFilters): boolean {
  if (filters.dataInicio && date < filters.dataInicio) return false;
  if (filters.dataFim && date > filters.dataFim) return false;
  if (filters.mes && date.slice(5, 7) !== filters.mes) return false;
  if (filters.ano && date.slice(0, 4) !== filters.ano) return false;
  return true;
}

function optionsFor(key: 'polo' | 'escola' | 'pais' | 'estado' | 'curso'): string[] {
  const source = key === 'polo'
    ? [...demoStudents, ...demoEnrollments, ...demoSchools]
    : key === 'escola'
      ? [...demoStudents, ...demoEnrollments, ...demoSchools]
      : demoStudents;
  const values = source.map((item) => item[key] || '').filter(Boolean);
  return [...new Set(values)].sort();
}

function filterArea(item: DemoItem, filters: DemoFilters): boolean {
  return (!filters.polo || item.polo === filters.polo)
    && (!filters.escola || item.escola === filters.escola)
    && (!filters.pais || item.pais === filters.pais)
    && (!filters.estado || item.estado === filters.estado)
    && (!filters.curso || item.curso === filters.curso);
}

function DashboardFilters({
  filters,
  onChange,
  mode,
}: {
  filters: DemoFilters;
  onChange: (next: DemoFilters) => void;
  mode: 'students' | 'period' | 'teacher';
}) {
  const select = (label: string, key: keyof DemoFilters, values: string[]) => (
    <label className="flex min-w-36 flex-col gap-1 text-xs text-slate-400" key={key}>
      {label}
      <select className={inputClass} value={filters[key]} onChange={(event) => onChange({ ...filters, [key]: event.target.value })}>
        <option value="">Todos</option>
        {values.map((value) => <option key={value} value={value}>{value}</option>)}
      </select>
    </label>
  );
  const dateInputs = (
    <>
      <label className="flex min-w-36 flex-col gap-1 text-xs text-slate-400">Data inicial<input className={inputClass} type="date" value={filters.dataInicio} onChange={(event) => onChange({ ...filters, dataInicio: event.target.value })} /></label>
      <label className="flex min-w-36 flex-col gap-1 text-xs text-slate-400">Data final<input className={inputClass} type="date" value={filters.dataFim} onChange={(event) => onChange({ ...filters, dataFim: event.target.value })} /></label>
    </>
  );
  return (
    <div className="flex flex-wrap gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      {dateInputs}
      {mode === 'students' ? (
        <>
          {select('Polo', 'polo', optionsFor('polo'))}
          {select('Escola', 'escola', optionsFor('escola'))}
          {select('País', 'pais', optionsFor('pais'))}
          {select('Estado', 'estado', optionsFor('estado'))}
          {select('Curso', 'curso', optionsFor('curso'))}
          {select('Semestre', 'semestre', ['1º', '2º', '3º'])}
        </>
      ) : mode === 'period' ? (
        <>
          <label className="flex min-w-36 flex-col gap-1 text-xs text-slate-400">Mês
            <select className={inputClass} value={filters.mes} onChange={(event) => onChange({ ...filters, mes: event.target.value })}>
              <option value="">Todos</option>
              {Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={String(index + 1).padStart(2, '0')}>{new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date(2025, index, 1))}</option>)}
            </select>
          </label>
          {select('Semestre', 'semestre', ['1º', '2º', '3º'])}
          {select('Ano', 'ano', ['2024', '2025', '2026'])}
          {select('Polo', 'polo', optionsFor('polo'))}
          {select('Escola', 'escola', optionsFor('escola'))}
        </>
      ) : null}
      <button type="button" onClick={() => onChange(initialFilters)} className="self-end rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800">Limpar filtros</button>
    </div>
  );
}

export const AdminDashboardPreview: React.FC = () => {
  const [activeWidget, setActiveWidget] = useState<WidgetId | null>(null);
  const [selectedItem, setSelectedItem] = useState<DemoItem | null>(null);
  const [filters, setFilters] = useState<DemoFilters>(initialFilters);
  const [unitTab, setUnitTab] = useState<UnitTab>('polos');
  const [editPreview, setEditPreview] = useState(false);
  const [notice, setNotice] = useState('');

  const filteredStudents = useMemo(
    () => demoStudents.filter((item) => matchesDate(item.date, filters) && filterArea(item, filters) && (!filters.semestre || filters.semestre === item.semestre)),
    [filters],
  );
  const filteredEnrollments = useMemo(
    () => demoEnrollments.filter((item) => matchesDate(item.date, filters) && (!filters.semestre || filters.semestre === item.semestre) && (!filters.polo || item.polo === filters.polo) && (!filters.escola || item.escola === filters.escola)),
    [filters],
  );
  const ranking = useMemo(() => {
    const totals = new Map<string, number>();
    filteredEnrollments.forEach((item) => totals.set(item.polo || 'Polo não identificado', (totals.get(item.polo || 'Polo não identificado') || 0) + (item.licenses || 0)));
    return [...totals.entries()]
      .map(([polo, quantidade]) => ({ polo, quantidade }))
      .sort((a, b) => b.quantidade - a.quantidade);
  }, [filteredEnrollments]);

  const openWidget = (widget: WidgetId) => {
    setActiveWidget(widget);
    setSelectedItem(null);
    setFilters(initialFilters);
    setUnitTab('polos');
    setEditPreview(false);
    setNotice('');
  };
  const closeWidget = () => {
    setActiveWidget(null);
    setSelectedItem(null);
    setEditPreview(false);
  };

  const visibleItems = useMemo(() => {
    if (activeWidget === 'students') return filteredStudents;
    if (activeWidget === 'enrollments') return filteredEnrollments;
    if (activeWidget === 'teachers') return demoTeachers.filter((teacher) => matchesDate(teacher.date, filters));
    if (activeWidget === 'certificates') return demoCertificates;
    if (activeWidget === 'units') return unitTab === 'polos' ? demoPoles : demoSchools.filter((school) => !filters.polo || school.polo === filters.polo);
    return [];
  }, [activeWidget, filteredStudents, filteredEnrollments, filters, unitTab]);

  const printRanking = () => window.print();
  const filterMode = activeWidget === 'students'
    ? 'students'
    : activeWidget === 'teachers'
      ? 'teacher'
      : 'period';
  const periodLabel = filters.dataInicio || filters.dataFim
    ? `${filters.dataInicio || 'início'} a ${filters.dataFim || 'hoje'}`
    : filters.mes
      ? `Mês ${filters.mes}/${filters.ano || 'qualquer ano'}`
      : `Todos os períodos${filters.ano ? ` de ${filters.ano}` : ''}`;

  const handleEditPreview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setEditPreview(false);
    setNotice('Prévia salva apenas para demonstração. Nenhuma alteração foi gravada.');
  };

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Visualizadores da Dashboard</h2>
          <p className="mt-1 text-xs text-slate-400">Prévia para apresentação aos stakeholders. Consulte listas, filtros e detalhes demonstrativos.</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-bold text-amber-300">
          <span className="h-2 w-2 rounded-full bg-amber-300" /> Dados demonstrativos
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {widgets.map((widget) => {
          const Icon = widget.icon;
          const className = 'group w-full rounded-2xl border border-slate-800 bg-slate-900/80 p-5 text-left shadow-md transition-all hover:border-slate-600 hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-nexus-yellow/60';
          const content = (
            <>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{widget.title}</span>
                <span className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-nexus-yellow"><Icon className="h-4 w-4" /></span>
              </div>
              <div className="mt-3 text-2xl font-black text-white">{widget.value}</div>
              <div className="mt-2 flex items-center justify-between gap-2 text-xs text-slate-400">
                <span>{widget.description}</span><ChevronRight className="h-4 w-4 shrink-0 text-slate-500 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="mt-3 inline-flex rounded-md bg-amber-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-300">Exemplo fictício</span>
            </>
          );
          return widget.id === 'licenses' ? (
            <Link key={widget.id} to="/admin/licencas" className={className}>{content}</Link>
          ) : (
            <button key={widget.id} type="button" onClick={() => { if (widget.id !== 'licenses') openWidget(widget.id); }} className={className}>{content}</button>
          );
        })}
      </div>

      {activeWidget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-3 sm:p-6" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeWidget(); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="dashboard-preview-title" className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-800 bg-slate-900/95 p-5 backdrop-blur">
              <div>
                <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-300">Dados de demonstração</span>
                <h2 id="dashboard-preview-title" className="text-xl font-extrabold text-white">{widgets.find((widget) => widget.id === activeWidget)?.title}</h2>
                <p className="mt-1 text-sm text-slate-400">Conteúdo ilustrativo para validação de fluxo. Não representa registros reais do NeonDB.</p>
              </div>
              <button type="button" aria-label="Fechar" onClick={closeWidget} className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:bg-slate-800 hover:text-white"><X className="h-5 w-5" /></button>
            </header>

            <div className="space-y-5 p-5">
              {activeWidget === 'units' && (
                <div className="flex gap-2">
                  {(['polos', 'escolas'] as UnitTab[]).map((tab) => (
                    <button key={tab} type="button" onClick={() => { setUnitTab(tab); setSelectedItem(null); }} className={`rounded-xl border px-4 py-2 text-sm font-semibold capitalize ${unitTab === tab ? 'border-nexus-yellow bg-nexus-yellow/10 text-nexus-yellow' : 'border-slate-700 text-slate-400 hover:bg-slate-800'}`}>
                      {tab === 'polos' ? 'Polos ativos' : 'Escolas ativas'}
                    </button>
                  ))}
                </div>
              )}

              {(activeWidget === 'students' || activeWidget === 'enrollments' || activeWidget === 'ranking' || activeWidget === 'teachers') && (
                <DashboardFilters filters={filters} onChange={(next) => { setFilters(next); setSelectedItem(null); }} mode={filterMode} />
              )}

              {activeWidget === 'units' && unitTab === 'escolas' && (
                <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <label className="flex min-w-48 flex-col gap-1 text-xs text-slate-400">Filtrar por Polo
                    <select className={inputClass} value={filters.polo} onChange={(event) => { setFilters({ ...filters, polo: event.target.value }); setSelectedItem(null); }}>
                      <option value="">Todos os polos</option>{optionsFor('polo').map((polo) => <option key={polo} value={polo}>{polo}</option>)}
                    </select>
                  </label>
                </div>
              )}

              {activeWidget === 'enrollments' && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <div><p className="text-sm font-bold text-white">{filteredEnrollments.length} matrículas no filtro demonstrativo</p><p className="mt-1 text-xs text-slate-400">Ranking de licenças/livros adquiridos · {periodLabel}</p></div>
                  <button type="button" onClick={printRanking} className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-xs font-bold text-slate-950 hover:bg-nexus-yellow-hover"><ArrowDownToLine className="h-4 w-4" />Gerar PDF do ranking</button>
                </div>
              )}

              {activeWidget === 'ranking' && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <div><p className="text-sm font-bold text-white">Ranking decrescente por novas licenças/livros</p><p className="mt-1 text-xs text-slate-400">Período demonstrativo: {periodLabel}</p></div>
                  <button type="button" onClick={printRanking} className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-xs font-bold text-slate-950 hover:bg-nexus-yellow-hover"><ArrowDownToLine className="h-4 w-4" />Baixar PDF</button>
                </div>
              )}

              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)]">
                <div className="overflow-hidden rounded-xl border border-slate-800">
                  <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 px-4 py-3">
                    <h3 className="text-sm font-bold text-white">{activeWidget === 'ranking' ? 'Polos no ranking' : activeWidget === 'units' ? `${unitTab === 'polos' ? 'Polos' : 'Escolas'} · lista` : 'Resultados'}</h3>
                    <span className="text-xs text-slate-500">{activeWidget === 'ranking' ? ranking.length : visibleItems.length} itens</span>
                  </div>
                  {activeWidget === 'ranking' ? (
                    <ol className="divide-y divide-slate-800">
                      {ranking.map((entry, index) => (
                        <li key={entry.polo} className="flex items-center gap-3 px-4 py-4">
                          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-nexus-yellow/10 text-sm font-black text-nexus-yellow">{index + 1}º</span>
                          <span className="min-w-0 flex-1"><strong className="block truncate text-sm text-white">{entry.polo}</strong><small className="text-xs text-slate-500">Posição no período selecionado</small></span>
                          <strong className="text-sm text-emerald-300">{entry.quantidade} un.</strong>
                        </li>
                      ))}
                      {!ranking.length && <li className="p-8 text-center text-sm text-slate-500">Nenhum exemplo corresponde aos filtros.</li>}
                    </ol>
                  ) : (
                    <div className="divide-y divide-slate-800">
                      {visibleItems.map((item) => (
                        <button key={item.id} type="button" onClick={() => { setSelectedItem(item); setEditPreview(false); setNotice(''); }} className={`flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-slate-800/60 ${selectedItem?.id === item.id ? 'bg-blue-500/10' : ''}`}>
                          <span className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-blue-300"><Users className="h-4 w-4" /></span>
                          <span className="min-w-0 flex-1"><strong className="block truncate text-sm text-white">{item.title}</strong><small className="block truncate text-xs text-slate-500">{item.subtitle}</small></span>
                          <ChevronRight className="h-4 w-4 shrink-0 text-slate-500" />
                        </button>
                      ))}
                      {!visibleItems.length && <div className="p-8 text-center text-sm text-slate-500">Nenhum exemplo corresponde aos filtros.</div>}
                    </div>
                  )}
                </div>

                <div className="min-h-64 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                  {selectedItem ? (
                    <div className="space-y-4">
                      <div className="flex items-start gap-3">
                        <span className="rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-nexus-yellow"><MapPin className="h-5 w-5" /></span>
                        <div><h3 className="font-bold text-white">{selectedItem.title}</h3><p className="mt-1 text-xs text-slate-400">{selectedItem.subtitle}</p></div>
                      </div>
                      <dl className="grid gap-2 sm:grid-cols-2">
                        {selectedItem.fields.map(([label, value]) => <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/80 p-3"><dt className="text-[10px] font-bold uppercase text-slate-500">{label}</dt><dd className="mt-1 text-xs text-slate-200">{value}</dd></div>)}
                      </dl>
                      {selectedItem.sections?.map((section) => <section key={section.title} className="rounded-lg border border-slate-800 bg-slate-900/80 p-3"><h4 className="mb-2 text-xs font-bold text-nexus-yellow">{section.title}</h4><ul className="space-y-1.5">{section.lines.map((line) => <li key={line} className="text-xs leading-relaxed text-slate-300">{line}</li>)}</ul></section>)}
                      {activeWidget === 'students' && (
                        editPreview ? (
                          <form onSubmit={handleEditPreview} className="space-y-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                            <p className="text-xs text-amber-200">Formulário de edição demonstrativo; não grava alterações.</p>
                            <label className="block text-xs text-slate-400">Nome<input className={`${inputClass} mt-1 w-full`} defaultValue={selectedItem.title} /></label>
                            <label className="block text-xs text-slate-400">E-mail<input className={`${inputClass} mt-1 w-full`} defaultValue={selectedItem.fields[0]?.[1]} /></label>
                            <div className="flex gap-2"><button className="rounded-lg bg-nexus-yellow px-3 py-2 text-xs font-bold text-slate-950" type="submit">Salvar prévia</button><button className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300" type="button" onClick={() => setEditPreview(false)}>Cancelar</button></div>
                          </form>
                        ) : <button type="button" onClick={() => setEditPreview(true)} className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800">Editar dados (prévia)</button>
                      )}
                      {notice && <p role="status" className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-300">{notice}</p>}
                    </div>
                  ) : (
                    <div className="flex h-full min-h-56 flex-col items-center justify-center text-center">
                      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-3 text-slate-500">{activeWidget === 'units' ? <School className="h-6 w-6" /> : activeWidget === 'certificates' ? <Award className="h-6 w-6" /> : <CalendarDays className="h-6 w-6" />}</div>
                      <p className="mt-3 text-sm font-semibold text-slate-300">Selecione um registro</p>
                      <p className="mt-1 max-w-xs text-xs leading-relaxed text-slate-500">Os detalhes demonstrativos aparecerão aqui.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>
      )}

      <div className="dashboard-print-report">
        <h1>NEXUS 2.0 · Ranking demonstrativo de Polos</h1>
        <p>Relatório fictício para apresentação · Período: {periodLabel}</p>
        <table><thead><tr><th>Posição</th><th>Polo</th><th>Novas licenças/livros</th></tr></thead><tbody>
          {ranking.map((entry, index) => <tr key={entry.polo}><td>{index + 1}º</td><td>{entry.polo}</td><td>{entry.quantidade}</td></tr>)}
        </tbody></table>
      </div>
      <style>{`
        .dashboard-print-report { display: none; }
        @media print {
          body * { visibility: hidden !important; }
          .dashboard-print-report, .dashboard-print-report * { visibility: visible !important; }
          .dashboard-print-report { display: block !important; position: absolute; inset: 0 auto auto 0; width: 100%; padding: 28px; color: #111; background: #fff; font: 14px Arial, sans-serif; }
          .dashboard-print-report h1 { margin: 0 0 8px; font-size: 22px; }
          .dashboard-print-report p { margin: 0 0 20px; }
          .dashboard-print-report table { width: 100%; border-collapse: collapse; }
          .dashboard-print-report th, .dashboard-print-report td { padding: 10px; border: 1px solid #999; text-align: left; }
        }
      `}</style>
    </section>
  );
};
