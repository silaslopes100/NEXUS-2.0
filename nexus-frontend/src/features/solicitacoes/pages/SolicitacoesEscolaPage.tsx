import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowLeft, FileText, Loader2, Minus, Plus, Send, ShoppingBag } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { financeiroApi } from '@/features/financeiro/api';
import { CursoCatalogo, CursoCatalogoDetalhe } from '@/features/financeiro/types';
import { cursosApiErrorMessage } from '@/features/cursos/api';
import { abrirPdf, erroDeBlob } from '@/lib/download';
import { brl, dataBR, Solicitacao, solicitacoesApi, STATUS_SOLICITACAO } from '@/features/solicitacoes/api';

type Carrinho = Record<string, { nome: string; preco: number; quantidade: number }>;

const NovaSolicitacao: React.FC<{ escolaId: string; onCriada: (s: Solicitacao) => void; onVoltar: () => void }> = ({
  escolaId,
  onCriada,
  onVoltar,
}) => {
  const [cursos, setCursos] = useState<CursoCatalogo[] | null>(null);
  const [curso, setCurso] = useState<CursoCatalogoDetalhe | null>(null);
  const [carregandoCurso, setCarregandoCurso] = useState(false);
  const [carrinho, setCarrinho] = useState<Carrinho>({});
  const [observacao, setObservacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    financeiroApi
      .catalogoCursos()
      .then(setCursos)
      .catch((err) => {
        setCursos([]);
        setErro(cursosApiErrorMessage(err, 'Não foi possível carregar os cursos.'));
      });
  }, []);

  const abrirCurso = async (id: string) => {
    setCarregandoCurso(true);
    setErro('');
    try {
      setCurso(await financeiroApi.catalogoCurso(id));
    } catch (err) {
      setErro(cursosApiErrorMessage(err, 'Não foi possível carregar as disciplinas.'));
    } finally {
      setCarregandoCurso(false);
    }
  };

  const alterar = (id: string, nome: string, preco: number, delta: number) =>
    setCarrinho((c) => {
      const quantidade = Math.max(0, (c[id]?.quantidade || 0) + delta);
      const novo = { ...c };
      if (quantidade === 0) delete novo[id];
      else novo[id] = { nome, preco, quantidade };
      return novo;
    });

  const itens = Object.entries(carrinho);
  const total = itens.reduce((s, [, i]) => s + i.preco * i.quantidade, 0);

  const enviar = async () => {
    setEnviando(true);
    setErro('');
    try {
      onCriada(
        await solicitacoesApi.criar(
          escolaId,
          itens.map(([disciplina_id, i]) => ({ disciplina_id, quantidade: i.quantidade })),
          observacao.trim()
        )
      );
    } catch (err) {
      setErro(cursosApiErrorMessage(err, 'Não foi possível enviar a solicitação.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <section className="space-y-4">
        <button type="button" onClick={curso ? () => setCurso(null) : onVoltar}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white">
          <ArrowLeft size={16} /> {curso ? 'Escolher outro curso' : 'Voltar às solicitações'}
        </button>
        {erro && (
          <div className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            <AlertCircle size={16} className="mt-0.5 shrink-0" /> {erro}
          </div>
        )}
        {!curso ? (
          cursos === null || carregandoCurso ? (
            <div className="flex justify-center py-12 text-blue-400"><Loader2 className="animate-spin" /></div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {cursos.map((c) => (
                <button key={c.id} type="button" onClick={() => void abrirCurso(c.id)}
                  className="glass rounded-2xl border border-slate-800 bg-slate-900 p-4 text-left hover:border-nexus-yellow/50">
                  <p className="font-semibold text-white">{c.nome}</p>
                  <p className="mt-1 text-sm text-slate-400">
                    {c.disciplinas_a_venda} de {c.disciplinas} disciplina(s) disponíveis
                    {c.disciplinas_a_venda > 0 && <> · curso completo {brl(c.preco_curso)}</>}
                  </p>
                </button>
              ))}
              {cursos.length === 0 && <p className="text-sm text-slate-500">Nenhum curso com disciplinas ativas.</p>}
            </div>
          )
        ) : (
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-white">{curso.nome}</h2>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-slate-400">Cada unidade é uma licença + o livro da disciplina.</p>
              <button type="button" disabled={!curso.disciplinas.some((d) => d.a_venda)}
                onClick={() => curso.disciplinas.filter((d) => d.a_venda && !carrinho[d.disciplina_id])
                  .forEach((d) => alterar(d.disciplina_id, d.nome, Number(d.preco), 1))}
                className="rounded-xl border border-nexus-yellow/40 px-3 py-1.5 text-sm text-nexus-yellow hover:bg-nexus-yellow/10 disabled:opacity-40">
                Adicionar curso completo ({brl(curso.disciplinas.filter((d) => d.a_venda).reduce((t, d) => t + Number(d.preco || 0), 0))})
              </button>
            </div>
            {curso.disciplinas.map((d) => {
              const qtd = carrinho[d.disciplina_id]?.quantidade || 0;
              const preco = Number(d.preco || 0);
              return (
                <div key={d.disciplina_id} className={`glass flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900 p-3 ${d.a_venda ? '' : 'opacity-60'}`}>
                  <div className="min-w-0">
                    <p className="font-medium text-white">{d.nome}</p>
                    <p className="text-xs text-slate-500">
                      {d.semestre ? `Semestre ${d.semestre} · ` : ''}{d.a_venda ? `${brl(preco)} · ` : ''}o Polo tem {d.saldo_polo} em estoque
                    </p>
                  </div>
                  {!d.a_venda ? (
                    <span className="shrink-0 rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-400">Preço não definido</span>
                  ) : (
                  <div className="flex shrink-0 items-center gap-2">
                    <button type="button" aria-label={`Diminuir ${d.nome}`} disabled={!qtd}
                      onClick={() => alterar(d.disciplina_id, d.nome, preco, -1)}
                      className="rounded-lg border border-slate-700 p-1.5 text-slate-300 disabled:opacity-30"><Minus size={14} /></button>
                    <input aria-label={`Quantidade de ${d.nome}`} inputMode="numeric" value={qtd}
                      onChange={(e) => alterar(d.disciplina_id, d.nome, preco, (Number(e.target.value.replace(/\D/g, '')) || 0) - qtd)}
                      className="w-14 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-center text-white" />
                    <button type="button" aria-label={`Aumentar ${d.nome}`}
                      onClick={() => alterar(d.disciplina_id, d.nome, preco, 1)}
                      className="rounded-lg border border-slate-700 p-1.5 text-slate-300"><Plus size={14} /></button>
                  </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <aside className="glass h-fit space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-4 lg:sticky lg:top-20">
        <h2 className="flex items-center gap-2 font-semibold text-white"><ShoppingBag size={17} /> Sua solicitação</h2>
        {itens.length === 0 ? (
          <p className="text-sm text-slate-500">Escolha um curso e as quantidades por disciplina.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {itens.map(([id, i]) => (
              <li key={id} className="flex justify-between gap-2 text-slate-300">
                <span className="truncate">{i.quantidade}× {i.nome}</span>
                <span className="shrink-0">{brl(i.preco * i.quantidade)}</span>
              </li>
            ))}
          </ul>
        )}
        <div className="flex justify-between border-t border-slate-800 pt-2 font-semibold text-white">
          <span>Total estimado</span><span>{brl(total)}</span>
        </div>
        <textarea rows={2} value={observacao} onChange={(e) => setObservacao(e.target.value)} placeholder="Observação para o Polo (opcional)"
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-500" />
        <p className="text-xs text-slate-500">
          Sem pagamento agora. Quando o Polo atender, você recebe a Nota de Prestação de Contas para repassar o valor.
        </p>
        <button type="button" disabled={!itens.length || enviando} onClick={() => void enviar()}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-nexus-yellow py-3 font-bold text-ink disabled:opacity-40">
          {enviando ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Enviar ao Polo
        </button>
      </aside>
    </div>
  );
};

export const SolicitacoesEscolaPage: React.FC = () => {
  const escolaId = useAuthStore((s) => s.user?.escola_id) || '';
  const [lista, setLista] = useState<Solicitacao[] | null>(null);
  const [nova, setNova] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');

  const carregar = () =>
    solicitacoesApi
      .daEscola(escolaId)
      .then(setLista)
      .catch((err) => {
        setLista([]);
        setErro(cursosApiErrorMessage(err, 'Não foi possível carregar as solicitações.'));
      });

  useEffect(() => {
    if (escolaId) void carregar();
    else setLista([]);
  }, [escolaId]);

  const baixarNota = async (s: Solicitacao) => {
    try {
      abrirPdf(await solicitacoesApi.notaPdf(s.id), `${s.nota_numero || 'nota'}.pdf`);
    } catch (err) {
      setErro(await erroDeBlob(err, 'Não foi possível gerar a Nota.'));
    }
  };

  const pendentesRepasse = useMemo(
    () => (lista || []).filter((s) => s.nota_status === 'emitida').reduce((t, s) => t + Number(s.nota_valor_total || 0), 0),
    [lista]
  );

  if (!escolaId) {
    return <p className="p-8 text-center text-slate-400">Seu usuário não está vinculado a uma Escola.</p>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Solicitar licenças e livros</h1>
          <p className="text-sm text-slate-400">Peça ao seu Polo; ele atende e emite a Nota de Prestação de Contas.</p>
        </div>
        {!nova && (
          <button type="button" onClick={() => setNova(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 font-bold text-ink">
            <Plus size={16} /> Nova solicitação
          </button>
        )}
      </header>

      {aviso && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">{aviso}</div>}
      {erro && <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</div>}

      {nova ? (
        <NovaSolicitacao
          escolaId={escolaId}
          onVoltar={() => setNova(false)}
          onCriada={(s) => {
            setNova(false);
            setAviso(`Solicitação ${s.numero} enviada ao Polo. Você será avisado quando ele responder.`);
            void carregar();
          }}
        />
      ) : lista === null ? (
        <div className="flex justify-center py-12 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : (
        <>
          {pendentesRepasse > 0 && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
              Valor a repassar ao Polo: <strong>{brl(pendentesRepasse)}</strong>
            </div>
          )}
          <div className="space-y-3">
            {lista.map((s) => (
              <article key={s.id} className="glass rounded-2xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-white">{s.numero}</p>
                    <p className="text-xs text-slate-500">Enviada em {dataBR(s.criado_em)} · {s.polo_nome}</p>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${STATUS_SOLICITACAO[s.status].classe}`}>
                    {STATUS_SOLICITACAO[s.status].texto}
                  </span>
                </div>
                <ul className="mt-3 space-y-0.5 text-sm text-slate-300">
                  {s.itens.map((i) => (
                    <li key={i.id}>
                      {i.disciplina_nome}: {i.quantidade} pedida(s)
                      {s.status !== 'pendente' && s.status !== 'recusada' && ` · ${i.quantidade_atendida} recebida(s)`}
                    </li>
                  ))}
                </ul>
                {s.status === 'recusada' && s.motivo_recusa && (
                  <p className="mt-2 text-sm text-red-300">Motivo: {s.motivo_recusa}</p>
                )}
                {s.nota_id && (
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <p className="text-sm text-slate-300">
                      Nota {s.nota_numero} · <strong className="text-white">{brl(s.nota_valor_total)}</strong> ·{' '}
                      {s.nota_status === 'repasse_recebido'
                        ? <span className="text-emerald-300">repasse confirmado em {dataBR(s.nota_repasse_em)}</span>
                        : <span className="text-amber-300">repassar até {dataBR(s.nota_vencimento)}</span>}
                    </p>
                    <button type="button" onClick={() => void baixarNota(s)}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800">
                      <FileText size={15} /> Baixar Nota de Prestação de Contas
                    </button>
                  </div>
                )}
              </article>
            ))}
            {lista.length === 0 && (
              <p className="glass rounded-2xl border border-slate-800 bg-slate-900 p-10 text-center text-sm text-slate-500">
                Nenhuma solicitação ainda.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
};
