import React, { useCallback, useEffect, useState } from 'react';
import { ArrowRightLeft, BookOpen, History, Loader2, Receipt, RotateCcw, Unlock, UserX, X } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { PedidoDetalheDrawer } from '@/features/financeiro/components/PedidoDetalheDrawer';
import {
  FichaEad, MOTIVOS, MatriculaEad, MotivoLiberacao, ORIGEM_COMPRA, ROTULO_MOTIVO, TurmaEadOpcao, gestaoEadApi,
} from '../../adminApi';
import { DisciplinaLoja, ESTADO, STATUS_PEDIDO, brl, dataBr } from '../../api';
import { ListaMovimentacoes, MotivoModal } from './Movimentacoes';

type Aba = 'disciplinas' | 'compras' | 'historico';

const data = (d?: string | null) => (d ? new Date(d).toLocaleDateString('pt-BR') : '—');

const LiberarModal: React.FC<{ disciplina: DisciplinaLoja; onConfirmar: (m: MotivoLiberacao, t: string) => Promise<void>; onFechar: () => void }> = ({
  disciplina, onConfirmar, onFechar,
}) => {
  const [motivo, setMotivo] = useState<MotivoLiberacao>('pagamento_externo');
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4" onMouseDown={onFechar}>
      <div className="w-full max-w-md space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div>
          <h3 className="text-lg font-bold text-white">Liberar disciplina</h3>
          <p className="text-sm text-slate-400">{disciplina.nome} — abre no AVA sem cobrança. Uma cobrança pendente dela é cancelada.</p>
        </div>
        <div className="grid gap-2">
          {MOTIVOS.map((m) => (
            <label key={m.valor} className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm ${motivo === m.valor ? 'border-nexus-yellow bg-nexus-yellow/10 text-white' : 'border-slate-700 text-slate-300'}`}>
              <input type="radio" checked={motivo === m.valor} onChange={() => setMotivo(m.valor)} /> {m.rotulo}
            </label>
          ))}
        </div>
        <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={2} maxLength={500}
          placeholder={motivo === 'outro' ? 'Descreva o motivo (obrigatório)' : 'Detalhes (opcional): comprovante, data, atendente…'}
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onFechar} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Voltar</button>
          <button type="button" disabled={enviando || (motivo === 'outro' && !texto.trim())}
            onClick={async () => { setEnviando(true); try { await onConfirmar(motivo, texto.trim()); } finally { setEnviando(false); } }}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 disabled:opacity-50">
            {enviando ? 'Liberando…' : 'Liberar'}
          </button>
        </div>
      </div>
    </div>
  );
};

const CartaoMatricula: React.FC<{
  m: MatriculaEad; turmas: TurmaEadOpcao[]; onAcao: (fn: () => Promise<unknown>, ok: string) => void; onCancelar: () => void;
}> = ({ m, turmas, onAcao, onCancelar }) => {
  const [transferir, setTransferir] = useState(false);
  const destinos = turmas.filter((t) => t.aberta && t.curso_id === m.curso_id && t.id !== m.turma_id);
  const [destino, setDestino] = useState(destinos[0]?.id ?? '');
  const ativa = m.status === 'ativa';
  return (
    <div className={`space-y-3 rounded-2xl border p-4 ${ativa ? 'border-slate-700 bg-slate-950/60' : 'border-red-500/30 bg-red-500/5'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-bold text-white">{m.turma_nome || 'Sem turma'}</p>
          <p className="text-xs text-slate-400">{m.curso_nome} · desde {data(m.data_matricula)} · {m.origem === 'site' ? 'pelo site' : m.origem === 'manual' ? 'manual' : 'legado'}</p>
        </div>
        <div className="flex gap-1.5">
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${m.tipo === 'bolsista' ? 'bg-violet-500/20 text-violet-200' : 'bg-slate-800 text-slate-300'}`}>
            {m.tipo === 'bolsista' ? 'Bolsista' : 'Regular'}
          </span>
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${ativa ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-500/15 text-red-300'}`}>
            {ativa ? 'Ativa' : 'Cancelada'}
          </span>
        </div>
      </div>
      {m.observacao && <p className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-300">{m.observacao}</p>}
      <div className="flex flex-wrap gap-2 text-xs">
        {ativa ? (
          <>
            <button type="button" onClick={() => onAcao(() => gestaoEadApi.atualizar(m.id, { tipo: m.tipo === 'bolsista' ? 'regular' : 'bolsista' }),
              m.tipo === 'bolsista' ? 'Agora é Regular.' : 'Agora é Bolsista.')}
              className="rounded-lg border border-violet-500/40 px-3 py-1.5 font-semibold text-violet-200 hover:bg-violet-500/10">
              {m.tipo === 'bolsista' ? 'Tornar Regular' : 'Tornar Bolsista'}
            </button>
            {destinos.length > 0 && (
              <button type="button" onClick={() => setTransferir((v) => !v)} className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 font-semibold text-slate-200 hover:bg-slate-800">
                <ArrowRightLeft size={12} /> Transferir turma
              </button>
            )}
            <button type="button" onClick={onCancelar} className="inline-flex items-center gap-1 rounded-lg border border-red-500/40 px-3 py-1.5 font-semibold text-red-300 hover:bg-red-500/10">
              <UserX size={12} /> Cancelar matrícula
            </button>
          </>
        ) : (
          <button type="button" onClick={() => onAcao(() => gestaoEadApi.reativar(m.id), 'Matrícula reativada.')}
            className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/40 px-3 py-1.5 font-semibold text-emerald-300 hover:bg-emerald-500/10">
            <RotateCcw size={12} /> Reativar
          </button>
        )}
      </div>
      {transferir && (
        <div className="flex gap-2">
          <select value={destino} onChange={(e) => setDestino(e.target.value)} className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-white">
            {destinos.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
          </select>
          <button type="button" disabled={!destino} onClick={() => { setTransferir(false); onAcao(() => gestaoEadApi.atualizar(m.id, { turma_id: destino }), 'Aluno transferido.'); }}
            className="rounded-lg bg-nexus-yellow px-3 text-xs font-bold text-ink">Confirmar</button>
        </div>
      )}
    </div>
  );
};

/** Ficha EAD do aluno: matrículas, disciplinas (liberar/revogar), compras, pedidos e histórico. */
export const FichaEadDrawer: React.FC<{ alunoId: string; turmas: TurmaEadOpcao[]; onFechar: () => void; onMudou: () => void }> = ({
  alunoId, turmas, onFechar, onMudou,
}) => {
  const [ficha, setFicha] = useState<FichaEad | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>('disciplinas');
  const [liberando, setLiberando] = useState<{ d: DisciplinaLoja; turmaId: string } | null>(null);
  const [revogando, setRevogando] = useState<string | null>(null);
  const [cancelando, setCancelando] = useState<string | null>(null);
  const [pedido, setPedido] = useState<string | null>(null);

  const carregar = useCallback(() => {
    gestaoEadApi.ficha(alunoId).then(setFicha).catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar a ficha.')));
  }, [alunoId]);
  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    if (!aviso) return;
    const t = window.setTimeout(() => setAviso(null), 2500);
    return () => window.clearTimeout(t);
  }, [aviso]);

  const acao = async (fn: () => Promise<unknown>, ok: string) => {
    setErro(null);
    try {
      const r = await fn();
      if (r && typeof r === 'object' && 'aluno_id' in r && 'compras' in r) setFicha(r as FichaEad); else carregar();
      setAviso(ok);
      onMudou();
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  const podeLiberar = (d: DisciplinaLoja) => !['comprada', 'concluida', 'bolsa'].includes(d.estado);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onMouseDown={onFechar}>
      <aside className="flex h-full w-full max-w-3xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-start justify-between gap-3 border-b border-slate-800 px-6 py-4">
          {ficha ? (
            <div>
              <h2 className="text-lg font-bold text-white">{ficha.nome}</h2>
              <p className="text-xs text-slate-400">{[ficha.numero_matricula, ficha.email, ficha.celular].filter(Boolean).join(' · ')}</p>
              {ficha.status_aluno === 'desistente' && <span className="mt-1 inline-block rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-bold text-amber-300">Desistente</span>}
            </div>
          ) : <h2 className="text-lg font-bold text-white">Ficha EAD</h2>}
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"><X size={18} /></button>
        </header>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-6 py-5">
          {erro && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}
          {!ficha ? <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div> : (
            <>
              <section className="space-y-3">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Matrículas</h3>
                {ficha.matriculas.map((m) => (
                  <CartaoMatricula key={m.id} m={m} turmas={turmas} onAcao={(fn, ok) => void acao(fn, ok)} onCancelar={() => setCancelando(m.id)} />
                ))}
              </section>

              <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1">
                {([['disciplinas', 'Disciplinas', BookOpen], ['compras', 'Compras e pedidos', Receipt], ['historico', 'Histórico', History]] as const).map(([v, r, Icone]) => (
                  <button key={v} type="button" onClick={() => setAba(v)}
                    className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${aba === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
                    <Icone size={13} /> {r}
                  </button>
                ))}
              </div>

              {aba === 'disciplinas' && (ficha.turmas.length ? ficha.turmas.map((t) => (
                <section key={t.id} className="space-y-2">
                  <p className="text-xs font-semibold text-slate-400">{t.nome}{t.bolsista ? ' · Bolsista' : ''}</p>
                  <ul className="divide-y divide-slate-800 overflow-hidden rounded-2xl border border-slate-800">
                    {t.disciplinas.map((d) => (
                      <li key={d.id} className="flex items-center gap-3 px-4 py-3">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-white">{d.nome}</p>
                          <p className="text-[11px] text-slate-500">
                            {d.libera_em ? `Libera ${dataBr(d.libera_em)}` : ''}{d.data_limite ? ` · limite ${dataBr(d.data_limite)}` : ''}
                          </p>
                        </div>
                        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${ESTADO[d.estado].classe}`}>{ESTADO[d.estado].rotulo}</span>
                        {podeLiberar(d) && (
                          <button type="button" onClick={() => setLiberando({ d, turmaId: t.id })}
                            className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-emerald-500/40 px-2.5 py-1 text-[11px] font-bold text-emerald-300 hover:bg-emerald-500/10">
                            <Unlock size={11} /> Liberar
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )) : <p className="py-6 text-center text-sm text-slate-500">O aluno não está em nenhuma Turma EAD aberta.</p>)}

              {aba === 'compras' && (
                <div className="space-y-5">
                  <section className="space-y-2">
                    <h3 className="text-sm font-bold text-white">Compras e liberações</h3>
                    {!ficha.compras.length && <p className="text-sm text-slate-500">Nenhuma compra.</p>}
                    <ul className="space-y-2">
                      {ficha.compras.map((c) => {
                        const cancelada = ['cancelado', 'cancelada'].includes((c.status_pagamento || '').toLowerCase());
                        return (
                          <li key={c.id} className={`flex flex-wrap items-center gap-3 rounded-xl border px-4 py-3 ${cancelada ? 'border-slate-800 opacity-60' : 'border-slate-700'}`}>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-white">{c.disciplina_nome}{c.com_livro ? ' + livro' : ''}</p>
                              <p className="text-[11px] text-slate-400">
                                {ORIGEM_COMPRA[c.origem] ?? c.origem} · {c.status_pagamento}
                                {c.motivo ? ` · ${ROTULO_MOTIVO[c.motivo] ?? c.motivo}` : ''}{c.motivo_texto ? ` — ${c.motivo_texto}` : ''}
                                {c.liberada_por_nome ? ` · por ${c.liberada_por_nome}` : ''} · {data(c.liberada_em || c.criado_em)}
                              </p>
                            </div>
                            {c.valor_pago ? <span className="text-sm font-bold text-white">{brl(c.valor_pago)}</span> : null}
                            {c.pedido_id && (
                              <button type="button" onClick={() => setPedido(c.pedido_id!)} className="text-xs font-semibold text-blue-300 hover:underline">{c.pedido_numero || 'Pedido'}</button>
                            )}
                            {c.pode_revogar && (
                              <button type="button" onClick={() => setRevogando(c.id)} className="rounded-lg border border-red-500/40 px-2.5 py-1 text-[11px] font-bold text-red-300 hover:bg-red-500/10">
                                {c.origem === 'manual' || c.origem === 'bolsa' ? 'Revogar' : 'Cancelar'}
                              </button>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </section>
                  <section className="space-y-2">
                    <h3 className="text-sm font-bold text-white">Pedidos</h3>
                    {!ficha.pedidos.length && <p className="text-sm text-slate-500">Nenhum pedido.</p>}
                    <ul className="space-y-2">
                      {ficha.pedidos.map((p) => (
                        <li key={p.id}>
                          <button type="button" onClick={() => setPedido(p.id)} className="flex w-full items-center gap-3 rounded-xl border border-slate-700 px-4 py-3 text-left hover:bg-slate-800/50">
                            <span className="min-w-0 flex-1">
                              <span className="block text-sm font-semibold text-white">{p.numero} · {p.disciplina_nome}{p.com_livro ? ' + livro' : ''}</span>
                              <span className="text-[11px] text-slate-400">{data(p.criado_em)} · {STATUS_PEDIDO[p.status] ?? p.status}</span>
                            </span>
                            <span className="text-sm font-bold text-white">{brl(p.valor_total)}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </section>
                </div>
              )}

              {aba === 'historico' && <ListaMovimentacoes itens={ficha.movimentacoes} mostrarAluno={false} />}
            </>
          )}
        </div>
      </aside>

      <div onMouseDown={(e) => e.stopPropagation()}>
      {aviso && (
        <div role="status" className="fixed bottom-6 right-6 z-[80] rounded-xl border border-emerald-500/30 bg-emerald-950/90 px-4 py-3 text-sm font-semibold text-emerald-200 shadow-2xl">{aviso}</div>
      )}
      {liberando && (
        <LiberarModal disciplina={liberando.d} onFechar={() => setLiberando(null)}
          onConfirmar={async (motivo, texto) => {
            await acao(() => gestaoEadApi.liberar(alunoId, liberando.d.id, { motivo, texto: texto || undefined, turma_id: liberando.turmaId }), 'Disciplina liberada.');
            setLiberando(null);
          }} />
      )}
      {revogando && (
        <MotivoModal titulo="Revogar / cancelar" descricao="A disciplina volta a ficar bloqueada para o aluno." rotuloConfirmar="Revogar" perigo
          onFechar={() => setRevogando(null)}
          onConfirmar={async (motivo) => { await acao(() => gestaoEadApi.revogar(revogando, motivo), 'Revogado.'); setRevogando(null); }} />
      )}
      {cancelando && (
        <MotivoModal titulo="Cancelar matrícula" rotuloConfirmar="Cancelar matrícula" perigo
          descricao="O aluno sai da Turma EAD e perde o acesso às disciplinas do curso. Cobranças em aberto são canceladas."
          onFechar={() => setCancelando(null)}
          onConfirmar={async (motivo) => { await acao(() => gestaoEadApi.cancelar(cancelando, motivo), 'Matrícula cancelada.'); setCancelando(null); }} />
      )}
      </div>
      {pedido && (
        <div onMouseDown={(e) => e.stopPropagation()}>
          <PedidoDetalheDrawer pedidoId={pedido} podeAlterarStatus onClose={() => setPedido(null)} onAlterado={() => { carregar(); onMudou(); }} />
        </div>
      )}
    </div>
  );
};
