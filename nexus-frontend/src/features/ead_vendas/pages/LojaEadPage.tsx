import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertCircle, ArrowRight, BookMarked, CalendarClock, CheckCircle2, Clock, GraduationCap, Loader2, Lock, Package,
  PartyPopper, PlayCircle, Receipt, ShoppingBag, Sparkles, Truck,
} from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { RegularizacaoEadModal } from '@/features/alunos/components/RegularizacaoEadModal';
import { urlArquivo } from '@/lib/uploadDireto';
import { useAuthStore } from '@/stores/authStore';
import { CheckoutDrawer } from '../components/CheckoutDrawer';
import {
  DisciplinaLoja, ESTADO, Loja, PedidoAluno, STATUS_PEDIDO, TurmaLoja, brl, dataBr, lojaApi,
} from '../api';

type Aba = 'disciplinas' | 'pedidos';

const CardDisciplina: React.FC<{ d: DisciplinaLoja; onComprar: () => void; onPagamento: () => void }> = ({ d, onComprar, onPagamento }) => {
  const navigate = useNavigate();
  const estado = ESTADO[d.estado];
  const destaque = d.estado === 'disponivel' || d.estado === 'recompra';
  return (
    <article className={`flex flex-col overflow-hidden rounded-2xl border bg-slate-900/70 transition ${
      destaque ? 'border-nexus-yellow/50 shadow-nexus-glow' : 'border-slate-800'}`}>
      <div className="relative aspect-[16/7] overflow-hidden">
        {d.capa_url ? <img src={urlArquivo(d.capa_url)} alt="" className="h-full w-full object-cover" /> : (
          <span className="flex h-full w-full items-center justify-center bg-gradient-to-br from-blue-800 via-indigo-900 to-slate-950 text-white/15"><GraduationCap size={42} /></span>
        )}
        <span className={`absolute left-3 top-3 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${estado.classe}`}>{estado.rotulo}</span>
        {(d.estado === 'aguardando' || d.estado === 'em_breve') && (
          <span className="absolute inset-0 flex items-center justify-center bg-slate-950/60"><Lock className="text-slate-300" size={26} /></span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="line-clamp-2 font-bold leading-snug text-white">{d.nome}</h3>
          <p className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-slate-400">
            {d.total_aulas ? <span>{d.total_aulas} aulas</span> : null}
            {d.prazo_dias ? <span className="flex items-center gap-1"><Clock size={11} /> {d.prazo_dias} dias</span> : null}
            {d.livro_disponivel && <span className="flex items-center gap-1 text-nexus-yellow"><BookMarked size={11} /> livro disponível</span>}
          </p>
        </div>
        <div className="mt-auto space-y-2">
          {d.estado === 'aguardando' && (
            <p className="flex items-center gap-2 rounded-xl border border-slate-800 py-2.5 text-center text-xs text-slate-300">
              <CalendarClock size={14} className="ml-3 text-blue-300" />
              {d.libera_em ? `Libera em ${dataBr(d.libera_em)}` : 'Libera após a disciplina anterior'}
            </p>
          )}
          {d.estado === 'em_breve' && (
            <p className="rounded-xl border border-slate-800 py-2.5 text-center text-xs text-slate-300">Conteúdo em preparação</p>
          )}
          {destaque && (
            <button type="button" onClick={onComprar}
              className="flex w-full items-center justify-between rounded-xl bg-nexus-yellow px-4 py-3 text-sm font-extrabold text-ink hover:bg-nexus-yellow-hover">
              <span className="flex items-center gap-2"><ShoppingBag size={16} /> {d.estado === 'recompra' ? 'Comprar novamente' : 'Comprar'}</span>
              <span>{brl(d.valor_ead)}</span>
            </button>
          )}
          {d.estado === 'pendente' && (
            <button type="button" onClick={onPagamento}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-amber-500/50 py-3 text-sm font-bold text-amber-200 hover:bg-amber-500/10">
              <Receipt size={16} /> Ver pagamento
            </button>
          )}
          {d.estado === 'encerrada' && (
            <p className="rounded-xl border border-red-500/30 py-2.5 text-center text-xs text-red-200">Prazo encerrado — fale com a secretaria</p>
          )}
          {(d.estado === 'comprada' || d.estado === 'concluida' || d.estado === 'bolsa') && (
            <button type="button" onClick={() => navigate(`/aluno/ava/disciplinas/${d.id}`)}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 py-3 text-sm font-bold text-white hover:bg-emerald-400">
              <PlayCircle size={16} /> {d.estado === 'concluida' ? 'Revisar' : 'Estudar'}
            </button>
          )}
          {d.estado === 'comprada' && d.data_limite && (
            <p className="text-center text-[11px] text-slate-500">Conclua até {dataBr(d.data_limite)}</p>
          )}
        </div>
      </div>
    </article>
  );
};

const ListaPedidos: React.FC<{ pedidos: PedidoAluno[] | null; onAbrir: (p: PedidoAluno) => void }> = ({ pedidos, onAbrir }) => {
  if (!pedidos) return <div className="flex justify-center py-12 text-blue-400"><Loader2 className="animate-spin" /></div>;
  if (!pedidos.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
        <Receipt className="mx-auto mb-3 text-slate-600" size={32} />
        <p className="text-slate-300">Você ainda não fez nenhum pedido.</p>
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {pedidos.map((p) => (
        <li key={p.id} className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 sm:flex-row sm:items-center">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${p.com_livro ? 'bg-amber-500/15 text-amber-300' : 'bg-blue-500/15 text-blue-300'}`}>
            {p.com_livro ? <Package size={18} /> : <GraduationCap size={18} />}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-white">{p.disciplina_nome || 'Disciplina EAD'}{p.com_livro ? ' + livro físico' : ''}</p>
            <p className="text-xs text-slate-400">
              {p.numero} · {p.criado_em ? new Date(p.criado_em).toLocaleDateString('pt-BR') : ''} · {p.billing_type === 'BOLETO' ? 'Boleto' : 'Pix'}
            </p>
            {p.codigo_rastreio && (
              <p className="mt-1 flex items-center gap-1 text-xs text-emerald-300"><Truck size={12} /> {p.transportadora || 'Rastreio'}: {p.codigo_rastreio}</p>
            )}
          </div>
          <div className="flex items-center gap-3 sm:flex-col sm:items-end">
            <span className="font-bold text-white">{brl(p.valor_total)}</span>
            <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
              p.status === 'cancelado' ? 'bg-slate-800 text-slate-400'
                : p.status === 'aguardando_pagamento' ? 'bg-amber-500/15 text-amber-300' : 'bg-emerald-500/15 text-emerald-300'}`}>
              {STATUS_PEDIDO[p.status] ?? p.status}
            </span>
          </div>
          {p.status === 'aguardando_pagamento' && (
            <button type="button" onClick={() => onAbrir(p)} className="rounded-xl border border-amber-500/50 px-3 py-2 text-xs font-bold text-amber-200 hover:bg-amber-500/10">
              Pagar
            </button>
          )}
        </li>
      ))}
    </ul>
  );
};

/** Loja do aluno EAD: compra progressiva das disciplinas da Turma EAD e os pedidos. */
export const LojaEadPage: React.FC = () => {
  const { user } = useAuthStore();
  const [params, setParams] = useSearchParams();
  const [loja, setLoja] = useState<Loja | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aba, setAba] = useState<Aba>('disciplinas');
  const [turmaId, setTurmaId] = useState<string | null>(null);
  const [pedidos, setPedidos] = useState<PedidoAluno[] | null>(null);
  const [checkout, setCheckout] = useState<{ turma: TurmaLoja; disciplina: DisciplinaLoja; pedido?: PedidoAluno | null } | null>(null);
  const [entrando, setEntrando] = useState<string | null>(null);
  const [regularizar, setRegularizar] = useState(!!user?.aluno_desistente);
  const bemvindo = params.get('bemvindo') === '1';

  const carregar = useCallback(async () => {
    try {
      const l = await lojaApi.loja();
      setLoja(l);
      setTurmaId((atual) => atual && l.turmas.some((t) => t.id === atual) ? atual : l.turmas[0]?.id ?? null);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar a loja.'));
    }
  }, []);

  const carregarPedidos = useCallback(() => {
    lojaApi.pedidos().then(setPedidos).catch(() => setPedidos([]));
  }, []);

  useEffect(() => {
    if (user?.aluno_desistente) return;
    void carregar();
  }, [carregar, user?.aluno_desistente]);

  useEffect(() => {
    if (aba === 'pedidos') carregarPedidos();
  }, [aba, carregarPedidos]);

  // "Liberar disciplina" no AVA: /aluno/compras?disciplina=:id abre o checkout direto.
  useEffect(() => {
    const alvo = params.get('disciplina');
    if (!alvo || !loja) return;
    for (const t of loja.turmas) {
      const d = t.disciplinas.find((x) => x.id === alvo);
      if (d && (d.estado === 'disponivel' || d.estado === 'recompra')) {
        setTurmaId(t.id);
        setCheckout({ turma: t, disciplina: d });
        break;
      }
      if (d && d.estado === 'pendente' && d.pedido_id) {
        setTurmaId(t.id);
        lojaApi.pedido(d.pedido_id).then((p) => setCheckout({ turma: t, disciplina: d, pedido: p })).catch(() => undefined);
        break;
      }
      if (d) {
        setTurmaId(t.id);
        break;
      }
    }
    params.delete('disciplina');
    setParams(params, { replace: true });
  }, [loja, params, setParams]);

  const turma = loja?.turmas.find((t) => t.id === turmaId) ?? null;

  const semestres = useMemo(() => {
    const grupos = new Map<number, DisciplinaLoja[]>();
    (turma?.disciplinas ?? []).forEach((d) => grupos.set(d.semestre || 0, [...(grupos.get(d.semestre || 0) ?? []), d]));
    return [...grupos.entries()].sort(([a], [b]) => a - b);
  }, [turma]);

  const resumo = useMemo(() => {
    const l = turma?.disciplinas ?? [];
    return {
      liberadas: l.filter((d) => d.estado === 'comprada' || d.estado === 'concluida' || d.estado === 'bolsa').length,
      disponiveis: l.filter((d) => d.estado === 'disponivel' || d.estado === 'recompra').length,
      total: l.length,
    };
  }, [turma]);

  const abrirPagamento = async (t: TurmaLoja, d: DisciplinaLoja) => {
    if (!d.pedido_id) return;
    try {
      setCheckout({ turma: t, disciplina: d, pedido: await lojaApi.pedido(d.pedido_id) });
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  const abrirPedido = (p: PedidoAluno) => {
    for (const t of loja?.turmas ?? []) {
      const d = t.disciplinas.find((x) => x.id === p.disciplina_id);
      if (d) {
        setCheckout({ turma: t, disciplina: d, pedido: p });
        return;
      }
    }
  };

  const entrarNaTurma = async (id: string) => {
    setEntrando(id);
    setErro(null);
    try {
      const l = await lojaApi.entrarNaTurma(id);
      setLoja(l);
      setTurmaId(id);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível entrar na turma.'));
    } finally {
      setEntrando(null);
    }
  };

  const mudou = useCallback(() => {
    void carregar();
    if (aba === 'pedidos') carregarPedidos();
  }, [carregar, carregarPedidos, aba]);

  if (regularizar || user?.aluno_desistente) {
    return (
      <>
        <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 text-center text-sm text-amber-100">
          Sua matrícula precisa ser regularizada antes de comprar novas disciplinas.
        </div>
        {regularizar && <RegularizacaoEadModal onFechar={() => setRegularizar(false)} />}
      </>
    );
  }
  if (erro && !loja) {
    return (
      <div role="alert" className="mx-auto mt-10 flex max-w-xl items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" /> {erro}
      </div>
    );
  }
  if (!loja) return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {bemvindo && (
        <div className="flex items-start gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
          <PartyPopper className="mt-0.5 shrink-0 text-emerald-300" />
          <div className="flex-1 text-sm text-emerald-100">
            <p className="font-bold">Matrícula confirmada! Bem-vindo(a) ao EAD.</p>
            <p>Compre a primeira disciplina liberada para começar a estudar. Você recebe acesso assim que o pagamento for confirmado.</p>
          </div>
          <button type="button" onClick={() => { params.delete('bemvindo'); setParams(params, { replace: true }); }}
            className="text-xs font-semibold text-emerald-200 hover:text-white">Fechar</button>
        </div>
      )}

      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950 p-6 shadow-2xl sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-nexus-yellow/10 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div className="space-y-2">
            <p className="flex items-center gap-2 text-sm font-semibold text-nexus-yellow"><Sparkles size={16} /> Cursos & Matrículas EAD</p>
            <h1 className="text-3xl font-extrabold text-white">{turma ? turma.nome : 'Minhas matrículas'}</h1>
            {turma && <p className="text-slate-300">{turma.curso_nome}</p>}
            {turma?.bolsista && (
              <span className="inline-block rounded-full bg-violet-500/20 px-3 py-1 text-xs font-bold text-violet-200">
                Bolsista — as disciplinas são liberadas sem custo, conforme o calendário
              </span>
            )}
            {loja.turmas.length > 1 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {loja.turmas.map((t) => (
                  <button key={t.id} type="button" onClick={() => setTurmaId(t.id)}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${t.id === turmaId ? 'bg-nexus-yellow text-ink' : 'border border-slate-700 text-slate-300 hover:bg-slate-800'}`}>
                    {t.nome}
                  </button>
                ))}
              </div>
            )}
          </div>
          {turma && (
            <div className="grid grid-cols-3 gap-2 text-center sm:gap-3 [&>div]:px-2 sm:[&>div]:px-4">
              {[['Liberadas', resumo.liberadas], ['Para comprar', resumo.disponiveis], ['Disciplinas', resumo.total]].map(([r, v]) => (
                <div key={r} className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
                  <p className="text-2xl font-extrabold text-white">{v}</p>
                  <p className="text-[11px] text-slate-400">{r}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      <div className="flex gap-1 self-start rounded-xl border border-slate-800 bg-slate-900/60 p-1">
        {([['disciplinas', 'Disciplinas'], ['pedidos', 'Meus pedidos']] as const).map(([v, r]) => (
          <button key={v} type="button" onClick={() => setAba(v)}
            className={`rounded-lg px-4 py-1.5 text-xs font-semibold ${aba === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
            {r}
          </button>
        ))}
      </div>

      {aba === 'pedidos' ? (
        <ListaPedidos pedidos={pedidos} onAbrir={abrirPedido} />
      ) : !turma ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <GraduationCap className="mx-auto mb-3 text-slate-600" size={36} />
          <p className="text-slate-300">Você ainda não está em nenhuma Turma EAD aberta. Escolha uma turma abaixo para começar.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {semestres.map(([s, lista]) => (
            <section key={s} className="space-y-3">
              {s > 0 && <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">{s}º semestre</h2>}
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {lista.map((d) => (
                  <CardDisciplina key={d.id} d={d}
                    onComprar={() => setCheckout({ turma, disciplina: d })}
                    onPagamento={() => void abrirPagamento(turma, d)} />
                ))}
              </div>
            </section>
          ))}
          <p className="flex items-start gap-2 text-xs text-slate-500">
            <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
            As disciplinas abrem para compra conforme o calendário da turma. Depois de liberada, cada uma tem um prazo para ser concluída.
          </p>
        </div>
      )}

      {aba === 'disciplinas' && loja.outras_turmas.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-white">{loja.turmas.length ? 'Outras turmas EAD abertas' : 'Turmas EAD abertas'}</h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {loja.outras_turmas.map((t) => (
              <article key={t.id} className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-nexus-yellow">{t.codigo || 'Turma EAD'}</p>
                  <p className="font-bold text-white">{t.nome}</p>
                  <p className="text-sm text-slate-400">{t.curso_nome}</p>
                </div>
                <p className="text-xs text-slate-400">
                  {t.data_inicio ? `Início ${dataBr(t.data_inicio)} · ` : ''}{t.total_disciplinas} disciplinas · matrícula gratuita
                </p>
                <div className="mt-auto flex gap-2">
                  <Link to={`/matricula-ead/${t.id}`} className="rounded-xl border border-slate-700 px-3 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800">Detalhes</Link>
                  <button type="button" disabled={entrando === t.id || t.vagas_restantes === 0} onClick={() => void entrarNaTurma(t.id)}
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-nexus-yellow py-2.5 text-xs font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
                    {entrando === t.id ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                    {t.vagas_restantes === 0 ? 'Turma lotada' : 'Entrar na turma'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {checkout && (
        <CheckoutDrawer
          key={`${checkout.disciplina.id}-${checkout.pedido?.id ?? 'novo'}`}
          turma={checkout.turma}
          disciplina={checkout.disciplina}
          endereco={loja.endereco}
          pedidoInicial={checkout.pedido}
          onFechar={() => setCheckout(null)}
          onMudou={mudou}
        />
      )}
    </div>
  );
};
