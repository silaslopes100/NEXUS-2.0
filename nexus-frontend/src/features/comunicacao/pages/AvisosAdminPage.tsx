import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  BarChart3,
  CalendarClock,
  Copy,
  Eye,
  Loader2,
  Megaphone,
  Pause,
  Pencil,
  Play,
  Plus,
  Search,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import { Avatar } from '@/features/chat/components/Avatar';
import { rotuloPerfil } from '@/features/chat/utils';
import { Aviso, EstatisticasAviso, StatusAviso, avisosApi, mensagemErro, rotuloPerfis } from '../api';
import { AvisoFormDrawer } from '../components/AvisoFormDrawer';
import { AvisoConteudo, LARGURAS } from '../components/AvisoModal';

const STATUS: Record<StatusAviso, { rotulo: string; classe: string }> = {
  ativo: { rotulo: 'No ar', classe: 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300' },
  agendado: { rotulo: 'Agendado', classe: 'border-blue-500/40 bg-blue-500/15 text-blue-300' },
  expirado: { rotulo: 'Encerrado', classe: 'border-slate-600 bg-slate-800 text-slate-400' },
  inativo: { rotulo: 'Pausado', classe: 'border-amber-500/40 bg-amber-500/15 text-amber-300' },
};
const FREQ: Record<string, string> = { uma_vez: 'Uma vez', ate_confirmar: 'Até confirmar', toda_sessao: 'Todo acesso' };
const POR_PAGINA = 20;

const dataHora = (v: string) =>
  new Date(v).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });

const publicoDe = (a: Aviso) =>
  a.publico_tipo === 'todos' ? 'Todos' : a.publico_tipo === 'perfis' ? rotuloPerfis(a.perfis) : 'Usuários específicos';

const EstatisticasModal: React.FC<{ aviso: Aviso; onFechar: () => void }> = ({ aviso, onFechar }) => {
  const [dados, setDados] = useState<EstatisticasAviso | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    avisosApi.estatisticas(aviso.id).then(setDados).catch((e) => setErro(mensagemErro(e)));
  }, [aviso.id]);
  const pct = (n: number) => (dados?.publico_estimado ? Math.round((n / dados.publico_estimado) * 100) : 0);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onMouseDown={onFechar}>
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <h3 className="font-semibold text-white">Alcance · {aviso.titulo}</h3>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        {erro && <p className="m-5 text-sm text-red-300">{erro}</p>}
        {!dados && !erro && <div className="flex justify-center py-12 text-blue-400"><Loader2 className="animate-spin" /></div>}
        {dados && (
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 [&>*:last-child:nth-child(odd)]:col-span-2 sm:[&>*:last-child:nth-child(odd)]:col-span-1">
              {[
                ['Público estimado', dados.publico_estimado, ''],
                ['Visualizaram', dados.visualizacoes, `${pct(dados.visualizacoes)}%`],
                ['Confirmaram', dados.confirmacoes, aviso.exige_confirmacao ? `${pct(dados.confirmacoes)}%` : '—'],
              ].map(([r, v, p]) => (
                <div key={r as string} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">{r}</p>
                  <p className="text-2xl font-extrabold text-white">{v}</p>
                  {p && <p className="text-xs text-slate-400">{p}</p>}
                </div>
              ))}
            </div>
            {dados.itens.length === 0 ? (
              <p className="text-center text-sm text-slate-400">Ninguém visualizou ainda.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="text-[11px] uppercase tracking-wide text-slate-500">
                  <tr><th className="py-2">Usuário</th><th>Última vez</th><th className="text-center">Vezes</th><th>Confirmou</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {dados.itens.map((i) => (
                    <tr key={i.usuario.id}>
                      <td className="py-2">
                        <span className="flex items-center gap-2">
                          <Avatar nome={i.usuario.nome} usuarioId={i.usuario.id} fotoUrl={i.usuario.foto_url} tamanho="sm" />
                          <span>
                            <span className="block text-slate-100">{i.usuario.nome}</span>
                            <span className="text-[11px] text-slate-500">{rotuloPerfil(i.usuario.perfil)}</span>
                          </span>
                        </span>
                      </td>
                      <td className="text-xs text-slate-400">{dataHora(i.ultima_vez_em)}</td>
                      <td className="text-center text-slate-300">{i.vezes}</td>
                      <td className="text-xs text-slate-400">{i.confirmado_em ? dataHora(i.confirmado_em) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/** CRUD dos avisos (pop-ups) exibidos ao abrir a plataforma. */
export const AvisosAdminPage: React.FC = () => {
  const [itens, setItens] = useState<Aviso[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<StatusAviso | ''>('');
  const [busca, setBusca] = useState('');
  const [termo, setTermo] = useState('');
  const [offset, setOffset] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState<Aviso | null | undefined>(undefined);
  const [estatisticas, setEstatisticas] = useState<Aviso | null>(null);
  const [previa, setPrevia] = useState<Aviso | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const r = await avisosApi.listar({ status, busca: termo, offset, limite: POR_PAGINA });
      setItens(r.itens);
      setTotal(r.total);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar os avisos.'));
    } finally {
      setCarregando(false);
    }
  }, [status, termo, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    const id = window.setTimeout(() => { setTermo(busca); setOffset(0); }, 350);
    return () => window.clearTimeout(id);
  }, [busca]);

  const acao = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await carregar();
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  const abrirEdicao = async (a: Aviso) => {
    try {
      setEditando(await avisosApi.obter(a.id)); // traz a lista de usuários específicos
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-nexus-yellow/15 text-nexus-yellow">
            <Megaphone size={24} />
          </span>
          <div>
            <h1 className="text-3xl font-extrabold text-white">Avisos (Pop-ups)</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              Lembretes que aparecem quando os usuários abrem a plataforma. Programe o período, escolha o público e
              acompanhe quem visualizou.
            </p>
          </div>
        </div>
        <button type="button" onClick={() => setEditando(null)}
          className="inline-flex items-center gap-2 self-start rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
          <Plus size={16} /> Novo aviso
        </button>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar pelo título…"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 py-2 pl-8 pr-3 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
        </div>
        <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900/60 p-1">
          {([['', 'Todos'], ['ativo', 'No ar'], ['agendado', 'Agendados'], ['inativo', 'Pausados'], ['expirado', 'Encerrados']] as const).map(([v, r]) => (
            <button key={v} type="button" onClick={() => { setStatus(v); setOffset(0); }}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${status === v ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
              {r}
            </button>
          ))}
        </div>
      </div>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {carregando ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : itens.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <Megaphone className="mx-auto mb-3 text-slate-600" size={32} />
          <p className="text-sm text-slate-300">Nenhum aviso encontrado.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Aviso</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3">Período</th>
                <th className="px-4 py-3">Público</th>
                <th className="px-4 py-3">Alcance</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {itens.map((a) => (
                <tr key={a.id} className="hover:bg-slate-900">
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2">
                      <span className="h-8 w-1.5 shrink-0 rounded-full" style={{ background: a.cor_destaque || '#FFB800' }} />
                      <span className="min-w-0">
                        <span className="block max-w-[260px] truncate font-semibold text-slate-100">{a.titulo}</span>
                        <span className="text-[11px] text-slate-500">
                          {FREQ[a.frequencia]}{a.exige_confirmacao ? ' · exige confirmação' : ''}{a.midias.length ? ` · ${a.midias.length} mídia(s)` : ''}
                        </span>
                      </span>
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${STATUS[a.status].classe}`}>
                      {STATUS[a.status].rotulo}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    <span className="flex items-center gap-1"><CalendarClock size={12} /> {dataHora(a.inicio_em)}</span>
                    <span className="pl-4">até {dataHora(a.fim_em)}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    <span className="flex items-center gap-1"><Users size={12} className="text-slate-500" /> {publicoDe(a)}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    {a.total_visualizacoes} visualizações
                    {a.exige_confirmacao && <span className="block text-slate-500">{a.total_confirmacoes} confirmações</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      {[
                        { t: 'Pré-visualizar', i: Eye, f: () => setPrevia(a) },
                        { t: 'Alcance', i: BarChart3, f: () => setEstatisticas(a) },
                        { t: 'Editar', i: Pencil, f: () => void abrirEdicao(a) },
                        { t: 'Duplicar', i: Copy, f: () => void acao(() => avisosApi.duplicar(a.id)) },
                        { t: a.ativo ? 'Pausar' : 'Ativar', i: a.ativo ? Pause : Play, f: () => void acao(() => avisosApi.alternar(a.id)) },
                        {
                          t: 'Excluir', i: Trash2, perigo: true,
                          f: () => window.confirm(`Excluir o aviso "${a.titulo}"?`) && void acao(() => avisosApi.excluir(a.id)),
                        },
                      ].map(({ t, i: Icone, f, perigo }) => (
                        <button key={t} type="button" title={t} aria-label={t} onClick={f}
                          className={`rounded-lg p-1.5 hover:bg-slate-800 ${perigo ? 'text-red-400' : 'text-slate-300 hover:text-white'}`}>
                          <Icone size={15} />
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > POR_PAGINA && (
        <div className="flex items-center justify-center gap-3 text-sm text-slate-400">
          <button type="button" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - POR_PAGINA))}
            className="rounded-lg border border-slate-700 px-3 py-1 disabled:opacity-40">Anterior</button>
          <span>{offset + 1}–{Math.min(offset + POR_PAGINA, total)} de {total}</span>
          <button type="button" disabled={offset + POR_PAGINA >= total} onClick={() => setOffset((o) => o + POR_PAGINA)}
            className="rounded-lg border border-slate-700 px-3 py-1 disabled:opacity-40">Próxima</button>
        </div>
      )}

      {editando !== undefined && (
        <AvisoFormDrawer aviso={editando} onFechar={() => setEditando(undefined)}
          onSalvo={() => { setEditando(undefined); void carregar(); }} />
      )}
      {estatisticas && <EstatisticasModal aviso={estatisticas} onFechar={() => setEstatisticas(null)} />}
      {previa && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" onMouseDown={() => setPrevia(null)}>
          <div className={`w-full ${LARGURAS[previa.largura].classe}`} onMouseDown={(e) => e.stopPropagation()}>
            <AvisoConteudo titulo={previa.titulo} conteudoHtml={previa.conteudo_html} midias={previa.midias}
              corDestaque={previa.cor_destaque} exigeConfirmacao={previa.exige_confirmacao}
              onFechar={() => setPrevia(null)} onConfirmar={() => setPrevia(null)} onAdiar={() => setPrevia(null)}
              contador="Pré-visualização" />
          </div>
        </div>
      )}
    </div>
  );
};
