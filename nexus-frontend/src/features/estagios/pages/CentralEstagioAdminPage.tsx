import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  BarChart3,
  Briefcase,
  ClipboardList,
  FileSpreadsheet,
  FileText,
  FolderCog,
  Images,
  Inbox,
  Loader2,
  RefreshCw,
  Search,
} from 'lucide-react';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { baixarArquivo, erroDeBlob } from '@/lib/download';
import { urlArquivo } from '@/lib/uploadDireto';
import {
  ETAPA_TITULO,
  Etapa,
  FiltrosRelatorio,
  Relatorio,
  STATUS_ESTAGIO,
  StatusEstagio,
  SubmissaoLista,
  erroEstagio,
  estagiosApi,
  formatarDataHora,
} from '@/features/estagios/api';
import { StatusEstagioBadge } from '@/features/estagios/components/EstagioComum';
import { EstagioDetalheDrawer } from '@/features/estagios/components/EstagioDetalheDrawer';
import { GestaoArquivosEstagio } from '@/features/estagios/components/GestaoArquivosEstagio';

type Aba = 'analise' | 'todas' | 'relatorios' | 'arquivos';
interface Opcao { id: string; nome: string }

const listaDe = (data: unknown): Opcao[] => {
  const itens = Array.isArray(data) ? data : ((data as { items?: Opcao[] })?.items || []);
  return itens.map((i: Opcao) => ({ id: String(i.id), nome: i.nome }));
};

const campo = 'rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

/** Polos (admin) e escolas (admin ou polo) para os filtros. */
const useUnidades = (perfil: string, poloUsuario?: string | null) => {
  const [polos, setPolos] = useState<Opcao[]>([]);
  const [escolas, setEscolas] = useState<Opcao[]>([]);
  const [poloSel, setPoloSel] = useState('');
  useEffect(() => {
    if (perfil === 'admin') polosEscolasApi.listarPolos({ limit: 200 }).then((d) => setPolos(listaDe(d))).catch(() => setPolos([]));
  }, [perfil]);
  useEffect(() => {
    const polo = perfil === 'polo' ? poloUsuario : poloSel;
    if (perfil === 'escola' || (perfil === 'admin' && !polo)) { setEscolas([]); return; }
    if (!polo) return;
    polosEscolasApi.listarEscolasDoPolo(polo).then((d) => setEscolas(listaDe(d))).catch(() => setEscolas([]));
  }, [perfil, poloSel, poloUsuario]);
  return { polos, escolas, setPoloSel };
};

const Miniatura: React.FC<{ s: SubmissaoLista }> = ({ s }) => (
  <div className="relative flex h-28 items-center justify-center overflow-hidden rounded-xl bg-slate-950">
    {s.miniatura_url ? (
      <img src={urlArquivo(s.miniatura_url)} alt="" loading="lazy" className="h-full w-full object-cover" />
    ) : (
      <Images size={28} className="text-slate-700" />
    )}
    <div className="absolute bottom-2 left-2 flex gap-1">
      <span className="inline-flex items-center gap-1 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] text-white"><FileText size={11} /> Carta</span>
      <span className="inline-flex items-center gap-1 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] text-white"><FileText size={11} /> Relatório</span>
    </div>
    {s.total_fotos > 0 && (
      <span className="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold text-white">
        <Images size={11} className="mr-1 inline" />{s.total_fotos} fotos
      </span>
    )}
  </div>
);

/** Central de Estágio: Admin (Coordenação) analisa e gerencia; Polo e Escola consultam os próprios alunos. */
export const CentralEstagioAdminPage: React.FC = () => {
  const { user, perfil: perfilStore } = useAuthStore();
  const perfil = normalizeUserRole(perfilStore?.nome || user?.perfil?.nome) || 'aluno';
  const ehAdmin = perfil === 'admin';
  const [params, setParams] = useSearchParams();
  const aba = (params.get('aba') as Aba) || (ehAdmin ? 'analise' : 'todas');
  const submissaoAberta = params.get('submissao');
  const { polos, escolas, setPoloSel } = useUnidades(perfil, user?.polo_id);

  const definirParam = (chave: string, valor: string | null) => {
    setParams((atual) => {
      const p = new URLSearchParams(atual);
      if (valor) p.set(chave, valor); else p.delete(chave);
      return p;
    }, { replace: chave === 'submissao' && !valor });
  };

  // ---------------- solicitações (cards em análise e tabela completa)
  const [status, setStatus] = useState<StatusEstagio | ''>('');
  const [etapa, setEtapa] = useState<Etapa | ''>('');
  const [poloId, setPoloId] = useState('');
  const [escolaId, setEscolaId] = useState('');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [pagina, setPagina] = useState(0);
  const [lista, setLista] = useState<{ total: number; itens: SubmissaoLista[] } | null>(null);
  const [analise, setAnalise] = useState<{ total: number; itens: SubmissaoLista[] } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const POR_PAGINA = 20;

  const carregarAnalise = useCallback(async () => {
    try {
      setAnalise(await estagiosApi.listar({ status: 'em_analise', limite: 60 }));
    } catch (e) {
      setErro(erroEstagio(e, 'Não foi possível carregar as solicitações em análise.'));
    }
  }, []);

  const carregarLista = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      setLista(await estagiosApi.listar({
        status, etapa, polo_id: poloId, escola_id: escolaId, busca: buscaAplicada,
        limite: POR_PAGINA, offset: pagina * POR_PAGINA,
      }));
    } catch (e) {
      setErro(erroEstagio(e, 'Não foi possível carregar as solicitações.'));
    } finally {
      setCarregando(false);
    }
  }, [status, etapa, poloId, escolaId, buscaAplicada, pagina]);

  useEffect(() => { if (aba === 'analise') void carregarAnalise(); }, [aba, carregarAnalise]);
  useEffect(() => { if (aba === 'todas') void carregarLista(); }, [aba, carregarLista]);

  const aposAvaliar = () => {
    void carregarAnalise();
    if (aba === 'todas') void carregarLista();
    window.dispatchEvent(new Event('nexus:contadores-menu'));
  };

  // ---------------- relatórios
  const [filtrosRel, setFiltrosRel] = useState<FiltrosRelatorio>({ situacao: '', polo_id: '', escola_id: '', de: '', ate: '' });
  const [relatorio, setRelatorio] = useState<Relatorio | null>(null);
  const [exportando, setExportando] = useState<string | null>(null);

  const carregarRelatorio = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      setRelatorio(await estagiosApi.relatorio(filtrosRel));
    } catch (e) {
      setErro(erroEstagio(e, 'Não foi possível gerar o relatório.'));
    } finally {
      setCarregando(false);
    }
  }, [filtrosRel]);

  useEffect(() => { if (aba === 'relatorios') void carregarRelatorio(); }, [aba, carregarRelatorio]);

  const exportar = async (formato: 'pdf' | 'xlsx' | 'csv') => {
    setExportando(formato);
    setErro('');
    try {
      const { blob, nome } = await estagiosApi.exportar(filtrosRel, formato);
      baixarArquivo(blob, nome);
    } catch (e) {
      setErro(await erroDeBlob(e, 'Não foi possível exportar o relatório.'));
    } finally {
      setExportando(null);
    }
  };

  const abas = useMemo(() => [
    ...(ehAdmin ? [{ id: 'analise' as Aba, rotulo: 'Solicitações em Análise', icone: Inbox, contador: analise?.total }] : []),
    { id: 'todas' as Aba, rotulo: ehAdmin ? 'Todas as solicitações' : 'Solicitações', icone: ClipboardList, contador: undefined },
    { id: 'relatorios' as Aba, rotulo: 'Relatórios', icone: BarChart3, contador: undefined },
    ...(ehAdmin ? [{ id: 'arquivos' as Aba, rotulo: 'Gestão de Arquivos', icone: FolderCog, contador: undefined }] : []),
  ], [ehAdmin, analise?.total]);

  const filtroUnidade = (valorPolo: string, valorEscola: string, aoMudarPolo: (v: string) => void, aoMudarEscola: (v: string) => void) => (
    <>
      {ehAdmin && (
        <select aria-label="Polo" value={valorPolo} onChange={(e) => { aoMudarPolo(e.target.value); setPoloSel(e.target.value); }} className={campo}>
          <option value="">Todos os polos</option>
          {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      )}
      {perfil !== 'escola' && (
        <select aria-label="Escola" value={valorEscola} onChange={(e) => aoMudarEscola(e.target.value)} disabled={ehAdmin && !valorPolo} className={`${campo} disabled:opacity-50`}>
          <option value="">{ehAdmin && !valorPolo ? 'Escolha um polo' : 'Todas as escolas'}</option>
          {escolas.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      )}
    </>
  );

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
        <div className="flex items-start gap-4">
          <span className="hidden h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/15 text-blue-300 sm:flex"><Briefcase size={24} /></span>
          <div>
            <h1 className="text-3xl font-extrabold text-white">Central de Estágio</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              {ehAdmin
                ? 'Analise a documentação dos alunos (Teologia do Ministério e Homilética), aprove ou negue com feedback, gere relatórios e mantenha o manual e os modelos atualizados.'
                : 'Acompanhe os estágios dos alunos da sua unidade (somente consulta).'}
            </p>
          </div>
        </div>
      </header>

      <nav className="flex gap-1 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 p-1" aria-label="Seções">
        {abas.map((a) => {
          const Icone = a.icone;
          const ativa = aba === a.id;
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => definirParam('aba', a.id)}
              aria-current={ativa ? 'page' : undefined}
              className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-colors ${
                ativa ? 'bg-blue-600 text-on-accent' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Icone size={16} /> {a.rotulo}
              {!!a.contador && (
                <span className={`rounded-full px-1.5 text-[11px] ${ativa ? 'bg-white/25' : 'bg-amber-500/20 text-amber-300'}`}>{a.contador}</span>
              )}
            </button>
          );
        })}
      </nav>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {aba === 'analise' && ehAdmin && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              {analise ? `${analise.total} solicitação(ões) aguardando análise` : 'Carregando…'}
            </p>
            <button type="button" onClick={() => void carregarAnalise()} className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">
              <RefreshCw size={13} /> Atualizar
            </button>
          </div>
          {!analise ? (
            <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
          ) : analise.itens.length === 0 ? (
            <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-16 text-center">
              <Inbox className="mx-auto mb-3 h-8 w-8 text-slate-500" />
              <h2 className="font-semibold text-white">Nenhuma solicitação em análise</h2>
              <p className="mt-1 text-sm text-slate-400">Quando um aluno enviar a documentação de estágio, ela aparece aqui.</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {analise.itens.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => definirParam('submissao', s.id)}
                  className="glass group flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-left transition hover:-translate-y-0.5 hover:border-amber-500/50"
                >
                  <Miniatura s={s} />
                  <div className="min-w-0 px-1">
                    <p className="truncate font-bold text-white">{s.aluno.nome}</p>
                    <p className="truncate text-xs text-slate-500">{[s.aluno.polo_nome, s.aluno.escola_nome].filter(Boolean).join(' · ') || '—'}</p>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-semibold text-blue-300">{s.etapa_titulo}</span>
                      <span className="shrink-0 text-[11px] text-slate-500">{formatarDataHora(s.enviado_em)}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {aba === 'todas' && (
        <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 p-4">
            <form
              className="relative min-w-[200px] flex-1"
              onSubmit={(e) => { e.preventDefault(); setPagina(0); setBuscaAplicada(busca.trim()); }}
            >
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar aluno ou matrícula (Enter)" className={`${campo} w-full pl-9`} />
            </form>
            <select aria-label="Status" value={status} onChange={(e) => { setPagina(0); setStatus(e.target.value as StatusEstagio | ''); }} className={campo}>
              <option value="">Todos os status</option>
              {(Object.keys(STATUS_ESTAGIO) as StatusEstagio[]).map((k) => <option key={k} value={k}>{STATUS_ESTAGIO[k].label}</option>)}
            </select>
            <select aria-label="Etapa" value={etapa} onChange={(e) => { setPagina(0); setEtapa(e.target.value as Etapa | ''); }} className={campo}>
              <option value="">Todas as etapas</option>
              {(Object.keys(ETAPA_TITULO) as Etapa[]).map((k) => <option key={k} value={k}>{ETAPA_TITULO[k]}</option>)}
            </select>
            {filtroUnidade(poloId, escolaId, (v) => { setPagina(0); setPoloId(v); setEscolaId(''); }, (v) => { setPagina(0); setEscolaId(v); })}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm text-slate-300">
              <thead className="bg-slate-950/50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Aluno</th>
                  <th className="px-4 py-3">Polo / Escola</th>
                  <th className="px-4 py-3">Etapa</th>
                  <th className="px-4 py-3">Enviado em</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Avaliado em</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {carregando && !lista ? (
                  <tr><td colSpan={6} className="py-12 text-center text-blue-400"><Loader2 className="mx-auto animate-spin" /></td></tr>
                ) : !lista || lista.itens.length === 0 ? (
                  <tr><td colSpan={6} className="py-12 text-center text-slate-500">Nenhuma solicitação encontrada.</td></tr>
                ) : lista.itens.map((s) => (
                  <tr key={s.id} onClick={() => definirParam('submissao', s.id)} className="cursor-pointer hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <p className="font-medium text-white">{s.aluno.nome}</p>
                      {s.aluno.numero_matricula && <p className="text-xs text-slate-500">{s.aluno.numero_matricula}</p>}
                    </td>
                    <td className="px-4 py-3 text-xs">{[s.aluno.polo_nome, s.aluno.escola_nome].filter(Boolean).join(' · ') || '—'}</td>
                    <td className="px-4 py-3">{s.etapa_titulo}</td>
                    <td className="whitespace-nowrap px-4 py-3">{formatarDataHora(s.enviado_em)}</td>
                    <td className="px-4 py-3"><StatusEstagioBadge status={s.status} /></td>
                    <td className="whitespace-nowrap px-4 py-3">{formatarDataHora(s.avaliado_em)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {lista && lista.total > POR_PAGINA && (
            <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
              <span>{pagina * POR_PAGINA + 1}–{Math.min((pagina + 1) * POR_PAGINA, lista.total)} de {lista.total}</span>
              <div className="flex gap-2">
                <button type="button" disabled={pagina === 0} onClick={() => setPagina(pagina - 1)} className="rounded-lg border border-slate-700 px-3 py-1.5 disabled:opacity-40">Anterior</button>
                <button type="button" disabled={(pagina + 1) * POR_PAGINA >= lista.total} onClick={() => setPagina(pagina + 1)} className="rounded-lg border border-slate-700 px-3 py-1.5 disabled:opacity-40">Próxima</button>
              </div>
            </div>
          )}
        </section>
      )}

      {aba === 'relatorios' && (
        <section className="space-y-4">
          <div className="glass flex flex-wrap items-end gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              Status
              <select value={filtrosRel.situacao} onChange={(e) => setFiltrosRel({ ...filtrosRel, situacao: e.target.value as FiltrosRelatorio['situacao'] })} className={campo}>
                <option value="">Todos</option>
                <option value="concluido">Concluído (2 etapas aprovadas)</option>
                <option value="pendente">Pendente</option>
              </select>
            </label>
            {perfil !== 'escola' && (
              <div className="flex flex-col gap-1 text-xs text-slate-400">
                <span>Unidade</span>
                <div className="flex flex-wrap gap-2">
                  {filtroUnidade(
                    filtrosRel.polo_id || '',
                    filtrosRel.escola_id || '',
                    (v) => setFiltrosRel({ ...filtrosRel, polo_id: v, escola_id: '' }),
                    (v) => setFiltrosRel({ ...filtrosRel, escola_id: v }),
                  )}
                </div>
              </div>
            )}
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              Enviado de
              <input type="date" value={filtrosRel.de} onChange={(e) => setFiltrosRel({ ...filtrosRel, de: e.target.value })} className={campo} />
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-400">
              até
              <input type="date" value={filtrosRel.ate} onChange={(e) => setFiltrosRel({ ...filtrosRel, ate: e.target.value })} className={campo} />
            </label>
            <div className="ml-auto flex flex-wrap gap-2">
              <button type="button" onClick={() => void exportar('pdf')} disabled={!!exportando} className="inline-flex items-center gap-2 rounded-xl bg-red-600/90 px-3 py-2 text-sm font-semibold text-on-accent hover:bg-red-600 disabled:opacity-50">
                {exportando === 'pdf' ? <Loader2 size={15} className="animate-spin" /> : <FileText size={15} />} Exportar PDF
              </button>
              <button type="button" onClick={() => void exportar('xlsx')} disabled={!!exportando} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-on-accent hover:bg-emerald-500 disabled:opacity-50">
                {exportando === 'xlsx' ? <Loader2 size={15} className="animate-spin" /> : <FileSpreadsheet size={15} />} Exportar XLS
              </button>
              <button type="button" onClick={() => void exportar('csv')} disabled={!!exportando} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50">
                {exportando === 'csv' ? <Loader2 size={15} className="animate-spin" /> : <FileSpreadsheet size={15} />} CSV
              </button>
            </div>
          </div>

          {relatorio && (
            <div className="grid grid-cols-3 gap-3">
              {[
                { rotulo: 'Alunos', valor: relatorio.total, cor: 'text-white' },
                { rotulo: 'Concluídos', valor: relatorio.concluidos, cor: 'text-emerald-300' },
                { rotulo: 'Pendentes', valor: relatorio.pendentes, cor: 'text-amber-300' },
              ].map((k) => (
                <div key={k.rotulo} className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <p className="text-xs font-semibold uppercase text-slate-500">{k.rotulo}</p>
                  <strong className={`mt-1 block text-2xl font-black ${k.cor}`}>{k.valor}</strong>
                </div>
              ))}
            </div>
          )}

          <div className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm text-slate-300">
                <thead className="bg-slate-950/50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Aluno</th>
                    <th className="px-4 py-3">Polo / Escola</th>
                    <th className="px-4 py-3">Teologia do Ministério</th>
                    <th className="px-4 py-3">Homilética</th>
                    <th className="px-4 py-3">Horas</th>
                    <th className="px-4 py-3">Situação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {carregando && !relatorio ? (
                    <tr><td colSpan={6} className="py-12 text-center text-blue-400"><Loader2 className="mx-auto animate-spin" /></td></tr>
                  ) : !relatorio || relatorio.linhas.length === 0 ? (
                    <tr><td colSpan={6} className="py-12 text-center text-slate-500">Nenhum aluno com estágio para os filtros escolhidos.</td></tr>
                  ) : relatorio.linhas.map((l) => (
                    <tr key={l.aluno_id}>
                      <td className="px-4 py-3">
                        <p className="font-medium text-white">{l.aluno_nome}</p>
                        {l.numero_matricula && <p className="text-xs text-slate-500">{l.numero_matricula}</p>}
                      </td>
                      <td className="px-4 py-3 text-xs">{[l.polo_nome, l.escola_nome].filter(Boolean).join(' · ') || '—'}</td>
                      <td className="px-4 py-3">
                        {l.teologia_status ? <StatusEstagioBadge status={l.teologia_status} /> : <span className="text-xs text-slate-500">Não enviado</span>}
                      </td>
                      <td className="px-4 py-3">
                        {l.homiletica_status ? <StatusEstagioBadge status={l.homiletica_status} /> : <span className="text-xs text-slate-500">Não enviado</span>}
                      </td>
                      <td className="px-4 py-3 font-semibold text-white">{l.horas_cumpridas}h</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${
                          l.situacao === 'concluido' ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300' : 'border-slate-600 bg-slate-800 text-slate-300'
                        }`}>
                          {l.situacao === 'concluido' ? 'Concluído' : 'Pendente'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {aba === 'arquivos' && ehAdmin && <GestaoArquivosEstagio />}

      {submissaoAberta && (
        <EstagioDetalheDrawer
          submissaoId={submissaoAberta}
          podeAvaliar={ehAdmin}
          onFechar={() => definirParam('submissao', null)}
          onAtualizado={aposAvaliar}
        />
      )}
    </div>
  );
};
