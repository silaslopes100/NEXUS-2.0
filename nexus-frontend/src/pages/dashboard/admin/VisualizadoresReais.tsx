import React, { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Award, Building2, ChevronLeft, ChevronRight, ExternalLink, GraduationCap, KeyRound, Loader2, MapPin, Search, Trophy, Users, X,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { alunosGestaoApi } from '@/features/alunos/api';
import { formatBRL } from '@/features/financeiro/types';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { professoresApi } from '@/features/professores/api';
import { AdminDashboardMetrics, DashboardExecutivo, FiltrosDashboard, RankingPolos } from '@/types/admin';
import { EnderecoCompleto, EscolaItem, PoloItem } from '@/types/polos';
import { Professor } from '@/types/professor';
import { fmtData, fmtInt, fmtPct } from './formato';

type WidgetId = 'alunos' | 'matriculas' | 'ranking' | 'unidades' | 'professores' | 'certificados';
type Aba = 'polos' | 'escolas';

/** Registro exibido na lista e no painel de detalhe do modal. */
interface ItemVisualizador {
  id: string;
  titulo: string;
  subtitulo: string;
  campos: Array<[string, string]>;
  links?: Array<{ rotulo: string; to: string }>;
  arquivo?: string | null;
}

interface Pagina { total: number; itens: ItemVisualizador[] }

const POR_PAGINA = 20;
const inputCls = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

const endereco = (e?: EnderecoCompleto | null) => {
  if (!e) return '—';
  const rua = [e.logradouro, e.numero].filter(Boolean).join(', ');
  const cidade = [e.cidade, e.estado].filter(Boolean).join('/');
  return [rua, e.bairro, cidade].filter(Boolean).join(' · ') || '—';
};
const ou = (v?: string | number | null) => (v === undefined || v === null || v === '' ? '—' : String(v));

interface Props {
  metrics: AdminDashboardMetrics | null;
  executivo: DashboardExecutivo | null;
  ranking: RankingPolos | null;
  filtros: FiltrosDashboard;
}

/** Cards clicáveis com contagem que abrem listas reais com busca e detalhe (requisitos 1.1–1.4). */
export const VisualizadoresReais: React.FC<Props> = ({ metrics, executivo, ranking, filtros }) => {
  const [ativo, setAtivo] = useState<WidgetId | null>(null);
  const [aba, setAba] = useState<Aba>('polos');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [pagina, setPagina] = useState(0);
  const [dados, setDados] = useState<Pagina | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [selecionado, setSelecionado] = useState<ItemVisualizador | null>(null);

  const rankingPorPolo = useMemo(
    () => new Map((ranking?.items || []).map((r) => [r.polo_id, r])),
    [ranking],
  );
  const periodoTxt = executivo ? `${fmtData(executivo.periodo.inicio)} a ${fmtData(executivo.periodo.fim)}` : 'período do painel';

  const widgets: Array<{ id: WidgetId | 'licencas'; titulo: string; valor: string; descricao: string; icone: React.ElementType }> = [
    { id: 'alunos', titulo: 'Alunos ativos', valor: fmtInt(metrics?.alunos_ativos), descricao: 'Buscar aluno e abrir a ficha', icone: Users },
    { id: 'matriculas', titulo: 'Matrículas EAD', valor: fmtInt(executivo?.crescimento.novas_matriculas), descricao: `No período · ${fmtInt(metrics?.matriculas_total)} no total`, icone: GraduationCap },
    { id: 'ranking', titulo: 'Ranking de Polos', valor: ranking ? `${fmtInt(ranking.items.length)} polos` : '—', descricao: 'Por índice de desempenho no período', icone: Trophy },
    { id: 'unidades', titulo: 'Polos / Escolas ativas', valor: metrics ? `${fmtInt(metrics.polos_ativos)} / ${fmtInt(metrics.escolas_ativas)}` : '—', descricao: 'Responsável, endereço e números', icone: Building2 },
    { id: 'professores', titulo: 'Professores ativos', valor: fmtInt(metrics?.professores_ativos), descricao: 'Lotação, disciplinas e aulas', icone: GraduationCap },
    { id: 'certificados', titulo: 'Certificados emitidos', valor: fmtInt(executivo?.academico.certificados_periodo), descricao: `No período · ${fmtInt(metrics?.certificados_emitidos)} no total`, icone: Award },
    { id: 'licencas', titulo: 'Estoque de licenças', valor: fmtInt(metrics?.licencas_em_estoque), descricao: 'Ir para Gestão de Licenças', icone: KeyRound },
  ];

  const carregar = useCallback(async (): Promise<Pagina> => {
    const offset = pagina * POR_PAGINA;
    const q = buscaAplicada || undefined;
    switch (ativo) {
      case 'alunos': {
        const r = await alunosGestaoApi.listar({ polo_id: filtros.polo_id, escola_id: filtros.escola_id, q, limit: POR_PAGINA, offset });
        return {
          total: r.total,
          itens: r.items.map((a) => ({
            id: a.id,
            titulo: a.nome,
            subtitulo: `${ou(a.numero_matricula)} · ${a.status}`,
            campos: [
              ['E-mail', ou(a.email)], ['Polo', ou(a.polo_nome)], ['Escola', ou(a.escola_nome)],
              ['Modalidade', ou(a.modalidade)], ['Turmas', a.turmas.length ? a.turmas.join(', ') : '—'],
              ['Presença', fmtPct(a.percentual_presenca)], ['Disciplinas em curso', fmtInt(a.disciplinas_em_curso)],
              ['Último acesso', fmtData(a.ultimo_acesso_em)],
            ],
            links: [
              { rotulo: 'Ficha completa (histórico e presenças)', to: `/admin/usuarios/${a.usuario_id}` },
              { rotulo: 'Abrir na Central de Alunos', to: `/admin/alunos?q=${encodeURIComponent(a.numero_matricula || a.nome)}` },
            ],
          })),
        };
      }
      case 'matriculas': {
        const r = await adminApi.listMatriculasDashboard({ ...filtros, q, limit: POR_PAGINA, offset });
        return {
          total: r.total,
          itens: r.items.map((m) => ({
            id: m.id,
            titulo: m.aluno_nome,
            subtitulo: `${ou(m.curso_nome)} · ${fmtData(m.data_matricula)}`,
            campos: [
              ['Matrícula', ou(m.numero_matricula)], ['Curso', ou(m.curso_nome)], ['Polo', ou(m.polo_nome)],
              ['Escola', ou(m.escola_nome)], ['Data da matrícula', fmtData(m.data_matricula)],
            ],
            links: m.numero_matricula ? [{ rotulo: 'Abrir na Central de Alunos', to: `/admin/alunos?q=${encodeURIComponent(m.numero_matricula)}` }] : [],
          })),
        };
      }
      case 'ranking': {
        const termo = buscaAplicada.toLowerCase();
        const todos = (ranking?.items || []).filter((r) => !termo || r.polo_nome.toLowerCase().includes(termo));
        return {
          total: todos.length,
          itens: todos.slice(offset, offset + POR_PAGINA).map((r) => ({
            id: r.polo_id,
            titulo: `${r.posicao}º · ${r.polo_nome}`,
            subtitulo: `${fmtInt(r.novas_licencas)} nova(s) licença(s) · ${formatBRL(r.receita_paga)}`,
            campos: [
              ['Posição', `${r.posicao}º`], ['Novas licenças', fmtInt(r.novas_licencas)], ['Receita paga', formatBRL(r.receita_paga)],
              ['Alunos ativos', fmtInt(r.alunos_ativos)], ['Escolas ativas', fmtInt(r.escolas_ativas)], ['Presença média', fmtPct(r.presenca_pct)],
            ],
            links: [{ rotulo: 'Gerenciar polo', to: '/admin/polos-escolas' }],
          })),
        };
      }
      case 'unidades': {
        if (aba === 'polos') {
          const r = await polosEscolasApi.listarPolos({ search: q, limit: POR_PAGINA, offset });
          return {
            total: r.total,
            itens: (r.items as PoloItem[]).map((p) => {
              const nums = rankingPorPolo.get(p.id);
              return {
                id: p.id,
                titulo: p.nome,
                subtitulo: `${p.status === 'ativo' ? 'Ativo' : 'Inativo'} · ${ou([p.endereco?.cidade, p.endereco?.estado].filter(Boolean).join('/'))}`,
                campos: [
                  ['Responsável', ou(p.coordenador_nome)], ['E-mail', ou(p.coordenador_email)], ['Endereço', endereco(p.endereco)],
                  ['Alunos ativos', nums ? fmtInt(nums.alunos_ativos) : '—'], ['Escolas ativas', nums ? fmtInt(nums.escolas_ativas) : '—'],
                  ['Novas licenças (período)', nums ? fmtInt(nums.novas_licencas) : '—'],
                ],
                links: [{ rotulo: 'Gerenciar polos', to: '/admin/polos-escolas' }],
              };
            }),
          };
        }
        const r = await polosEscolasApi.listarEscolas({ polo_id: filtros.polo_id, q, status: 'ativo', limit: POR_PAGINA, offset });
        return {
          total: r.total,
          itens: (r.items as EscolaItem[]).map((e) => ({
            id: e.id,
            titulo: e.nome,
            subtitulo: `${ou(e.polo_nome) === '—' ? 'Sem polo' : e.polo_nome} · ${ou([e.endereco?.cidade, e.endereco?.estado].filter(Boolean).join('/'))}`,
            campos: [
              ['Responsável', ou(e.secretario_nome)], ['E-mail', ou(e.secretario_email)], ['Endereço', endereco(e.endereco)],
              ['Polo vinculado', ou(e.polo_nome)], ['Turmas', fmtInt(e.total_turmas ?? null)],
            ],
            links: [{ rotulo: 'Gerenciar escolas', to: '/admin/escolas' }],
          })),
        };
      }
      case 'professores': {
        const r = await professoresApi.listar({ search: q, polo_id: filtros.polo_id, escola_id: filtros.escola_id, limit: POR_PAGINA, offset });
        return {
          total: r.total,
          itens: r.items.map((p: Professor) => ({
            id: p.id,
            titulo: p.nome || 'Professor sem nome',
            subtitulo: `${p.status === 'ativo' || !p.status ? 'Ativo' : p.status} · ${ou(p.polo_nome)}`,
            campos: [
              ['E-mail', ou(p.email)], ['Polo', ou(p.polo_nome)], ['Escola', ou(p.escola_nome)],
              ['Disciplinas', p.materias?.length ? p.materias.join(', ') : '—'], ['Início das atividades', fmtData(p.data_inicio)],
              ['Aulas ministradas', fmtInt(p.quantidade_aulas ?? null)], ['Horas', fmtInt(p.horas_totais ?? null)],
            ],
            links: [
              ...(p.usuario_id ? [{ rotulo: 'Ficha completa', to: `/admin/usuarios/${p.usuario_id}` }] : []),
              { rotulo: 'Atas, anexos e chamada', to: `/admin/aulas?professor=${p.id}` },
            ],
          })),
        };
      }
      case 'certificados': {
        const r = await adminApi.listCertificadosDashboard({ ...filtros, q, limit: POR_PAGINA, offset });
        return {
          total: r.total,
          itens: r.items.map((c) => ({
            id: c.id,
            titulo: c.aluno_nome,
            subtitulo: `${ou(c.curso_nome)} · emitido em ${fmtData(c.emitido_em)}`,
            campos: [
              ['Matrícula', ou(c.numero_matricula)], ['Curso', ou(c.curso_nome)], ['Polo', ou(c.polo_nome)],
              ['Emissão', fmtData(c.emitido_em)], ['Estágio Teologia do Ministério', fmtData(c.data_estagio_teologia_ministerio)],
              ['Estágio Homilética', fmtData(c.data_estagio_homiletica)],
            ],
            arquivo: c.url_arquivo,
          })),
        };
      }
      default:
        return { total: 0, itens: [] };
    }
  }, [ativo, aba, buscaAplicada, pagina, filtros, ranking, rankingPorPolo]);

  useEffect(() => {
    if (!ativo) return undefined;
    let vivo = true;
    setCarregando(true);
    setErro('');
    carregar()
      .then((p) => vivo && setDados(p))
      .catch(() => vivo && setErro('Não foi possível carregar os registros.'))
      .finally(() => vivo && setCarregando(false));
    return () => { vivo = false; };
  }, [ativo, carregar]);

  const abrir = (id: WidgetId) => {
    setAtivo(id);
    setAba('polos');
    setBusca('');
    setBuscaAplicada('');
    setPagina(0);
    setDados(null);
    setSelecionado(null);
  };
  const fechar = () => { setAtivo(null); setSelecionado(null); };
  const buscar = (e: FormEvent) => { e.preventDefault(); setPagina(0); setSelecionado(null); setBuscaAplicada(busca.trim()); };

  useEffect(() => {
    if (!ativo) return undefined;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') fechar(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [ativo]);

  const widgetAtivo = widgets.find((w) => w.id === ativo);
  const usaPeriodo = ativo === 'matriculas' || ativo === 'certificados' || ativo === 'ranking';
  const usaUnidade = ativo === 'alunos' || ativo === 'matriculas' || ativo === 'professores' || ativo === 'certificados'
    || (ativo === 'unidades' && aba === 'escolas');
  const totalPaginas = dados ? Math.max(1, Math.ceil(dados.total / POR_PAGINA)) : 1;
  const vazio = ativo === 'matriculas'
    ? 'Nenhuma matrícula EAD no período. O módulo de matrículas EAD ainda está em implantação: os registros aparecem aqui assim que forem lançados.'
    : 'Nenhum registro encontrado com os filtros atuais.';

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-white">Consultas rápidas</h2>
        <p className="mt-1 text-xs text-slate-400">Listas com dados reais. Período e unidade vêm dos filtros do painel.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {widgets.map((w) => {
          const Icone = w.icone;
          const cls = 'group w-full rounded-2xl border border-slate-800 bg-slate-900/80 p-5 text-left shadow-md transition-all hover:border-slate-600 hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-nexus-yellow/60';
          const conteudo = (
            <>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{w.titulo}</span>
                <span className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-nexus-yellow"><Icone className="h-4 w-4" /></span>
              </div>
              <div className="mt-3 text-2xl font-black text-white">{w.valor}</div>
              <div className="mt-2 flex items-center justify-between gap-2 text-xs text-slate-400">
                <span>{w.descricao}</span>
                <ChevronRight className="h-4 w-4 shrink-0 text-slate-500 transition-transform group-hover:translate-x-1" />
              </div>
            </>
          );
          return w.id === 'licencas' ? (
            <Link key={w.id} to="/admin/licencas" className={`glass block ${cls}`}>{conteudo}</Link>
          ) : (
            <button key={w.id} type="button" onClick={() => abrir(w.id as WidgetId)} className={`glass ${cls}`}>{conteudo}</button>
          );
        })}
      </div>

      {ativo && widgetAtivo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-3 sm:p-6"
          role="presentation"
          onMouseDown={(e) => { if (e.target === e.currentTarget) fechar(); }}
        >
          <section role="dialog" aria-modal="true" aria-labelledby="visualizador-titulo" className="glass flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-slate-800 p-5">
              <div>
                <h2 id="visualizador-titulo" className="text-xl font-extrabold text-white">{widgetAtivo.titulo}</h2>
                <p className="mt-1 text-xs text-slate-400">
                  {[usaPeriodo && `Período: ${periodoTxt}`, usaUnidade && (filtros.polo_id || filtros.escola_id) && 'Filtrado pela unidade do painel']
                    .filter(Boolean).join(' · ') || 'Todos os registros'}
                </p>
              </div>
              <button type="button" aria-label="Fechar" onClick={fechar} className="rounded-xl border border-slate-700 p-2 text-slate-400 hover:bg-slate-800 hover:text-white"><X className="h-5 w-5" /></button>
            </header>

            <div className="flex flex-wrap items-center gap-3 border-b border-slate-800 p-4">
              {ativo === 'unidades' && (
                <div className="flex gap-2">
                  {(['polos', 'escolas'] as Aba[]).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => { setAba(t); setPagina(0); setSelecionado(null); }}
                      className={`rounded-xl border px-4 py-2 text-sm font-semibold ${aba === t ? 'border-nexus-yellow bg-nexus-yellow/10 text-nexus-yellow' : 'border-slate-700 text-slate-400 hover:bg-slate-800'}`}
                    >
                      {t === 'polos' ? 'Polos' : 'Escolas ativas'}
                    </button>
                  ))}
                </div>
              )}
              <form onSubmit={buscar} className="flex min-w-[220px] flex-1 gap-2">
                <input className={inputCls} value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome ou matrícula" aria-label="Buscar" />
                <button type="submit" className="inline-flex items-center gap-1.5 rounded-xl bg-nexus-yellow px-4 py-2 text-xs font-bold text-ink hover:bg-nexus-yellow-hover"><Search className="h-4 w-4" /> Buscar</button>
              </form>
            </div>

            <div className="grid min-h-0 flex-1 gap-0 overflow-hidden lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
              <div className="flex min-h-0 flex-col border-slate-800 lg:border-r">
                <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 px-4 py-2.5 text-xs text-slate-500">
                  <span>{dados ? `${fmtInt(dados.total)} registro(s)` : ' '}</span>
                  {carregando && <Loader2 className="h-4 w-4 animate-spin text-blue-400" />}
                </div>
                <div className="min-h-[240px] flex-1 divide-y divide-slate-800 overflow-y-auto">
                  {erro ? (
                    <p className="p-8 text-center text-sm text-red-300">{erro}</p>
                  ) : !dados ? (
                    <p className="p-8 text-center text-sm text-slate-500">Carregando...</p>
                  ) : !dados.itens.length ? (
                    <p className="p-8 text-center text-sm text-slate-500">{vazio}</p>
                  ) : dados.itens.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setSelecionado(item)}
                      className={`flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-slate-800/60 ${selecionado?.id === item.id ? 'bg-blue-500/10' : ''}`}
                    >
                      <span className="min-w-0 flex-1">
                        <strong className="block truncate text-sm text-white">{item.titulo}</strong>
                        <small className="block truncate text-xs text-slate-500">{item.subtitulo}</small>
                      </span>
                      <ChevronRight className="h-4 w-4 shrink-0 text-slate-500" />
                    </button>
                  ))}
                </div>
                {dados && dados.total > POR_PAGINA && (
                  <div className="flex items-center justify-between border-t border-slate-800 px-4 py-2 text-xs text-slate-400">
                    <button type="button" disabled={pagina === 0 || carregando} onClick={() => setPagina(pagina - 1)} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 hover:text-white disabled:opacity-40">
                      <ChevronLeft className="h-4 w-4" /> Anterior
                    </button>
                    <span>Página {pagina + 1} de {totalPaginas}</span>
                    <button type="button" disabled={pagina + 1 >= totalPaginas || carregando} onClick={() => setPagina(pagina + 1)} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 hover:text-white disabled:opacity-40">
                      Próxima <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              <div className="min-h-[240px] overflow-y-auto border-t border-slate-800 bg-slate-950/40 p-4 lg:border-t-0">
                {selecionado ? (
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <span className="rounded-xl border border-slate-800 bg-slate-950 p-2.5 text-nexus-yellow"><MapPin className="h-5 w-5" /></span>
                      <div>
                        <h3 className="font-bold text-white">{selecionado.titulo}</h3>
                        <p className="mt-1 text-xs text-slate-400">{selecionado.subtitulo}</p>
                      </div>
                    </div>
                    <dl className="grid gap-2 sm:grid-cols-2">
                      {selecionado.campos.map(([rotulo, valor]) => (
                        <div key={rotulo} className="rounded-lg border border-slate-800 bg-slate-900/80 p-3">
                          <dt className="text-[10px] font-bold uppercase text-slate-500">{rotulo}</dt>
                          <dd className="mt-1 break-words text-xs text-slate-200">{valor}</dd>
                        </div>
                      ))}
                    </dl>
                    {(selecionado.links?.length || selecionado.arquivo) && (
                      <div className="flex flex-wrap gap-2">
                        {selecionado.links?.map((l) => (
                          <Link key={l.to} to={l.to} className="inline-flex items-center gap-1 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800">
                            {l.rotulo} <ChevronRight className="h-3.5 w-3.5" />
                          </Link>
                        ))}
                        {selecionado.arquivo && (
                          <a href={selecionado.arquivo} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800">
                            Abrir certificado <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex h-full min-h-56 flex-col items-center justify-center text-center">
                    <p className="text-sm font-semibold text-slate-300">Selecione um registro</p>
                    <p className="mt-1 max-w-xs text-xs leading-relaxed text-slate-500">Os detalhes aparecem aqui, com atalhos para a tela de gestão.</p>
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      )}
    </section>
  );
};
