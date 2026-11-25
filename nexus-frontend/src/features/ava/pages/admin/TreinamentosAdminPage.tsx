import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Award,
  Copy,
  GraduationCap,
  Layers,
  Loader2,
  Pause,
  Pencil,
  Play,
  Plus,
  Search,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import { mensagemErro, tempoRelativo } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { rotuloPerfil } from '@/features/chat/utils';
import { CATEGORIA, PERFIS_ALVO, Participante, Treinamento, treinamentosAdminApi } from '../../treinamentosApi';
import { TreinamentoFormDrawer } from '../../components/treinamentos/TreinamentoFormDrawer';

const POR_PAGINA = 20;

const publicoDe = (t: Treinamento) => {
  const perfis = t.perfis_alvo.map((p) => PERFIS_ALVO.find((x) => x.valor === p)?.rotulo ?? p).join(', ');
  const unidades = t.polos.length + t.escolas.length;
  return unidades ? `${perfis} · ${unidades} unidade(s)` : `${perfis} · todas as unidades`;
};

const ParticipantesModal: React.FC<{ treinamento: Treinamento; onFechar: () => void }> = ({ treinamento, onFechar }) => {
  const [lista, setLista] = useState<Participante[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    treinamentosAdminApi.participantes(treinamento.id).then(setLista).catch((e) => setErro(mensagemErro(e)));
  }, [treinamento.id]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onMouseDown={onFechar}>
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold text-white">Participantes</h2>
            <p className="truncate text-xs text-slate-400">{treinamento.titulo}</p>
          </div>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800"><X size={18} /></button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {erro ? <p className="text-sm text-red-300">{erro}</p> : !lista ? (
            <div className="flex justify-center py-10 text-blue-400"><Loader2 className="animate-spin" /></div>
          ) : lista.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-400">Ninguém começou este treinamento ainda.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="text-[11px] uppercase tracking-wide text-slate-500">
                <tr><th className="py-2">Participante</th><th className="py-2">Unidade</th><th className="py-2">Progresso</th><th className="py-2 text-right">Situação</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {lista.map((p) => (
                  <tr key={p.usuario_id}>
                    <td className="py-2.5">
                      <span className="block font-medium text-slate-100">{p.nome}</span>
                      <span className="text-[11px] text-slate-500">{rotuloPerfil(p.perfil)}</span>
                    </td>
                    <td className="py-2.5 text-xs text-slate-300">{p.unidade || '—'}</td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-800">
                          <span className="block h-full bg-nexus-yellow" style={{ width: `${p.concluido_em ? 100 : p.progresso_pct}%` }} />
                        </span>
                        <span className="text-xs text-slate-400">{p.aulas_concluidas}/{p.total_aulas}</span>
                      </div>
                    </td>
                    <td className="py-2.5 text-right text-xs">
                      {p.concluido_em ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 font-semibold text-emerald-300" title={`Código ${p.codigo_validacao}`}>
                          <Award size={12} /> Concluiu
                        </span>
                      ) : (
                        <span className="text-slate-400">{p.ultimo_acesso_em ? `visto ${tempoRelativo(p.ultimo_acesso_em)}` : 'Em andamento'}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

/** CRUD de Treinamentos, Workshops e Capacitações para Polos, Escolas e Professores. */
export const TreinamentosAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [itens, setItens] = useState<Treinamento[]>([]);
  const [total, setTotal] = useState(0);
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [situacao, setSituacao] = useState<'todos' | 'publicado' | 'rascunho'>('todos');
  const [offset, setOffset] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState<Treinamento | null | undefined>(undefined);
  const [participantes, setParticipantes] = useState<Treinamento | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const r = await treinamentosAdminApi.listar({ q: buscaAplicada || undefined, situacao, limite: POR_PAGINA, offset });
      setItens(r.items);
      setTotal(r.total);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar os treinamentos.'));
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, situacao, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    const t = window.setTimeout(() => { setBuscaAplicada(busca.trim()); setOffset(0); }, 350);
    return () => window.clearTimeout(t);
  }, [busca]);

  const acao = async (fn: () => Promise<unknown>) => {
    setErro(null);
    try {
      await fn();
      await carregar();
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-nexus-yellow/15 text-nexus-yellow"><GraduationCap size={24} /></span>
          <div>
            <h1 className="text-3xl font-extrabold text-white">Treinamentos</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              Treinamentos, workshops e capacitações para Polos, Escolas e Professores, com certificado de conclusão.
            </p>
          </div>
        </div>
        <button type="button" onClick={() => setEditando(null)}
          className="inline-flex items-center gap-2 self-start rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
          <Plus size={16} /> Novo treinamento
        </button>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar pelo título…"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 py-2 pl-8 pr-3 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
        </div>
        <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900/60 p-1">
          {([['todos', 'Todos'], ['publicado', 'Publicados'], ['rascunho', 'Rascunhos']] as const).map(([v, r]) => (
            <button key={v} type="button" onClick={() => { setSituacao(v); setOffset(0); }}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${situacao === v ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
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
          <GraduationCap className="mx-auto mb-3 text-slate-600" size={32} />
          <p className="text-sm text-slate-300">Nenhum treinamento encontrado.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Treinamento</th>
                <th className="px-4 py-3">Situação</th>
                <th className="px-4 py-3">Público</th>
                <th className="px-4 py-3">Conteúdo</th>
                <th className="px-4 py-3">Participação</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {itens.map((t) => (
                <tr key={t.id} className="hover:bg-slate-900">
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => navigate(`/admin/treinamentos/${t.id}`)} className="flex items-center gap-3 text-left">
                      <span className="h-10 w-16 shrink-0 overflow-hidden rounded-lg bg-gradient-to-br from-blue-900 to-slate-950">
                        {t.capa_url && <img src={urlArquivo(t.capa_url)} alt="" className="h-full w-full object-cover" />}
                      </span>
                      <span className="min-w-0">
                        <span className="block max-w-[260px] truncate font-semibold text-slate-100 hover:text-nexus-yellow">{t.titulo}</span>
                        <span className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${CATEGORIA[t.categoria].classe}`}>
                          {CATEGORIA[t.categoria].rotulo}
                        </span>
                        {t.carga_horaria ? <span className="ml-2 text-[11px] text-slate-500">{t.carga_horaria}h</span> : null}
                      </span>
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                      t.publicado ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-slate-600 bg-slate-800 text-slate-300'}`}>
                      {t.publicado ? 'Publicado' : 'Rascunho'}
                    </span>
                    {t.data_fim && <span className="block pt-1 text-[11px] text-slate-500">até {new Date(`${t.data_fim}T00:00`).toLocaleDateString('pt-BR')}</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">{publicoDe(t)}</td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    <span className="flex items-center gap-1"><Layers size={12} className="text-slate-500" /> {t.total_capitulos} cap. · {t.total_aulas} aulas</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    <button type="button" onClick={() => setParticipantes(t)} className="flex items-center gap-1 hover:text-nexus-yellow">
                      <Users size={12} /> {t.total_participantes} · {t.total_concluintes} concluíram
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      {[
                        { r: 'Montar conteúdo', i: Layers, f: () => navigate(`/admin/treinamentos/${t.id}`) },
                        { r: 'Editar', i: Pencil, f: () => setEditando(t) },
                        { r: 'Duplicar', i: Copy, f: () => void acao(() => treinamentosAdminApi.duplicar(t.id)) },
                        { r: t.publicado ? 'Despublicar' : 'Publicar', i: t.publicado ? Pause : Play, f: () => void acao(() => treinamentosAdminApi.alternar(t.id)) },
                        {
                          r: 'Excluir', i: Trash2, f: () => {
                            if (window.confirm(`Excluir "${t.titulo}" com todo o conteúdo e o progresso dos participantes?`)) {
                              void acao(() => treinamentosAdminApi.excluir(t.id));
                            }
                          },
                        },
                      ].map(({ r, i: Icone, f }) => (
                        <button key={r} type="button" onClick={f} title={r} aria-label={r}
                          className={`rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 ${r === 'Excluir' ? 'hover:text-red-300' : 'hover:text-white'}`}>
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
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{offset + 1}–{Math.min(offset + POR_PAGINA, total)} de {total}</span>
          <div className="flex gap-2">
            <button type="button" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - POR_PAGINA))}
              className="rounded-lg border border-slate-700 px-3 py-1.5 disabled:opacity-40">Anterior</button>
            <button type="button" disabled={offset + POR_PAGINA >= total} onClick={() => setOffset((o) => o + POR_PAGINA)}
              className="rounded-lg border border-slate-700 px-3 py-1.5 disabled:opacity-40">Próxima</button>
          </div>
        </div>
      )}

      {editando !== undefined && (
        <TreinamentoFormDrawer treinamento={editando} onFechar={() => setEditando(undefined)}
          onSalvo={(t, novo) => {
            setEditando(undefined);
            if (novo) navigate(`/admin/treinamentos/${t.id}`);
            else void carregar();
          }} />
      )}
      {participantes && <ParticipantesModal treinamento={participantes} onFechar={() => setParticipantes(null)} />}
    </div>
  );
};
