import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, History, Loader2, PackagePlus, RefreshCw, Search, SlidersHorizontal, X } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { erroApi, EstoqueItem, EstoqueMovimentacao, formatData, TipoMovimentacaoEstoque } from '@/features/financeiro/types';
import { cursosApi, Curso } from '@/features/cursos/api';

/** Saldo considerado baixo (aviso em âmbar). */
const ESTOQUE_BAIXO = 5;

const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-nexus-yellow';

const TIPO_MOV: Record<TipoMovimentacaoEstoque, { label: string; className: string }> = {
  entrada: { label: 'Entrada', className: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  ajuste: { label: 'Ajuste', className: 'bg-blue-500/15 text-blue-300 border-blue-500/30' },
  baixa_envio: { label: 'Baixa (envio)', className: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
};

const Saldo: React.FC<{ quantidade: number }> = ({ quantidade }) => {
  if (quantidade < 0) {
    return (
      <span className="font-bold text-red-400">
        {quantidade} <span className="text-xs font-semibold">· faltando {Math.abs(quantidade)}</span>
      </span>
    );
  }
  if (quantidade === 0) return <span className="font-bold text-red-400">0</span>;
  if (quantidade <= ESTOQUE_BAIXO) return <span className="font-bold text-amber-300">{quantidade}</span>;
  return <span className="font-bold text-white">{quantidade}</span>;
};

type Acao = { tipo: 'entrada' | 'ajuste'; item: EstoqueItem };

/**
 * Estoque Central de livros (controle interno do Admin).
 * Uma linha por Disciplina cadastrada; a baixa é automática ao marcar um pedido como enviado.
 */
export const EstoquePage: React.FC = () => {
  const [itens, setItens] = useState<EstoqueItem[]>([]);
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [busca, setBusca] = useState('');
  const [cursoId, setCursoId] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [acao, setAcao] = useState<Acao | null>(null);
  const [historico, setHistorico] = useState<EstoqueItem | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const resposta = await financeiroApi.listEstoque({ curso_id: cursoId || undefined });
      setItens(resposta.items);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar o estoque.'));
    } finally {
      setCarregando(false);
    }
  }, [cursoId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    cursosApi.listar().then(setCursos).catch(() => setCursos([]));
  }, []);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR');
    if (!termo) return itens;
    return itens.filter((item) =>
      `${item.disciplina_nome} ${item.sku || ''} ${item.curso_nome || ''}`.toLocaleLowerCase('pt-BR').includes(termo),
    );
  }, [busca, itens]);

  const resumo = useMemo(
    () => ({
      livros: itens.reduce((soma, item) => soma + Math.max(0, item.quantidade), 0),
      zerados: itens.filter((item) => item.quantidade <= 0).length,
      baixos: itens.filter((item) => item.quantidade > 0 && item.quantidade <= ESTOQUE_BAIXO).length,
    }),
    [itens],
  );

  const aoSalvar = (atualizado: EstoqueItem, mensagem: string) => {
    setItens((atuais) => atuais.map((item) => (item.disciplina_id === atualizado.disciplina_id ? { ...item, ...atualizado } : item)));
    setSucesso(mensagem);
    setAcao(null);
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/30 p-6 shadow-xl sm:flex-row sm:items-start">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Estoque</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Livros guardados no Estoque Central, por Disciplina. Registre as entradas e ajuste após o inventário; a baixa é
            feita automaticamente quando um pedido é marcado como enviado.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void carregar()}
          disabled={carregando}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} /> Atualizar
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
          <p className="text-xs font-semibold text-slate-400">Livros em estoque</p>
          <p className="mt-1 text-2xl font-extrabold text-white">{resumo.livros.toLocaleString('pt-BR')}</p>
        </div>
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
          <p className="text-xs font-semibold text-slate-400">Disciplinas sem estoque</p>
          <p className="mt-1 text-2xl font-extrabold text-red-400">{resumo.zerados}</p>
        </div>
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
          <p className="text-xs font-semibold text-slate-400">Estoque baixo (até {ESTOQUE_BAIXO})</p>
          <p className="mt-1 text-2xl font-extrabold text-amber-300">{resumo.baixos}</p>
        </div>
      </section>

      <section className="glass grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4 sm:grid-cols-[1fr_280px]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            placeholder="Buscar por disciplina, SKU ou curso"
            className={`${campo} pl-9`}
          />
        </div>
        <select aria-label="Curso" value={cursoId} onChange={(event) => setCursoId(event.target.value)} className={campo}>
          <option value="">Todos os cursos</option>
          {cursos.map((curso) => (
            <option key={curso.id} value={curso.id}>{curso.nome}</option>
          ))}
        </select>
      </section>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}
      {sucesso && (
        <div role="status" className="flex items-center justify-between gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
          {sucesso}
          <button type="button" aria-label="Fechar aviso" onClick={() => setSucesso('')} className="rounded p-1 hover:bg-emerald-500/10">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Disciplina</th>
                <th className="px-4 py-3">Curso</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Em estoque</th>
                <th className="px-4 py-3">Atualizado em</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {carregando ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" /> Carregando estoque...
                  </td>
                </tr>
              ) : filtrados.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    {itens.length === 0 ? 'Nenhuma disciplina cadastrada.' : 'Nenhuma disciplina encontrada com os filtros.'}
                  </td>
                </tr>
              ) : (
                filtrados.map((item) => (
                  <tr key={item.disciplina_id} className="hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-white">{item.disciplina_nome}</p>
                      {!item.disciplina_ativa && <span className="text-xs text-slate-500">Disciplina inativa</span>}
                    </td>
                    <td className="px-4 py-3">
                      <p>{item.curso_nome || 'Sem curso'}</p>
                      {item.semestre != null && <p className="text-xs text-slate-500">Semestre {item.semestre}</p>}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{item.sku || '—'}</td>
                    <td className="px-4 py-3"><Saldo quantidade={item.quantidade} /></td>
                    <td className="px-4 py-3 text-xs text-slate-400">{formatData(item.atualizado_em, true)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setAcao({ tipo: 'entrada', item })}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-nexus-yellow px-3 py-1.5 text-xs font-bold text-ink hover:bg-nexus-yellow-hover"
                        >
                          <PackagePlus className="h-3.5 w-3.5" /> Entrada
                        </button>
                        <button
                          type="button"
                          onClick={() => setAcao({ tipo: 'ajuste', item })}
                          aria-label={`Ajustar estoque de ${item.disciplina_nome}`}
                          title="Ajustar saldo (inventário)"
                          className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
                        >
                          <SlidersHorizontal className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setHistorico(item)}
                          aria-label={`Histórico de ${item.disciplina_nome}`}
                          title="Histórico de movimentações"
                          className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 hover:text-white"
                        >
                          <History className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {acao && <MovimentoModal acao={acao} onClose={() => setAcao(null)} onSalvo={aoSalvar} />}
      {historico && <HistoricoDrawer item={historico} onClose={() => setHistorico(null)} />}
    </div>
  );
};

const MovimentoModal: React.FC<{
  acao: Acao;
  onClose: () => void;
  onSalvo: (item: EstoqueItem, mensagem: string) => void;
}> = ({ acao, onClose, onSalvo }) => {
  const entrada = acao.tipo === 'entrada';
  const [quantidade, setQuantidade] = useState(entrada ? '' : String(Math.max(0, acao.item.quantidade)));
  const [observacao, setObservacao] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  const salvar = async (event: React.FormEvent) => {
    event.preventDefault();
    const valor = Number(quantidade);
    if (!Number.isInteger(valor) || (entrada ? valor <= 0 : valor < 0)) {
      setErro(entrada ? 'Informe uma quantidade maior que zero.' : 'Informe o saldo contado (0 ou mais).');
      return;
    }
    if (!entrada && observacao.trim().length < 3) {
      setErro('Informe o motivo do ajuste.');
      return;
    }
    setSalvando(true);
    setErro('');
    try {
      const nome = acao.item.disciplina_nome;
      if (entrada) {
        const item = await financeiroApi.entradaEstoque(acao.item.disciplina_id, {
          quantidade: valor,
          observacao: observacao.trim() || undefined,
        });
        onSalvo(item, `Entrada de ${valor} livro(s) em ${nome}. Saldo: ${item.quantidade}.`);
      } else {
        const item = await financeiroApi.ajustarEstoque(acao.item.disciplina_id, {
          quantidade: valor,
          observacao: observacao.trim(),
        });
        onSalvo(item, `Saldo de ${nome} ajustado para ${item.quantidade}.`);
      }
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível salvar a movimentação.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="movimento-titulo"
        onSubmit={salvar}
        className="glass w-full max-w-md space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 id="movimento-titulo" className="text-lg font-bold text-white">
              {entrada ? 'Entrada de livros' : 'Ajustar saldo'}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {acao.item.disciplina_nome} · saldo atual <Saldo quantidade={acao.item.quantidade} />
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </header>

        {erro && (
          <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</div>
        )}

        <label className="block space-y-1.5 text-sm text-slate-300">
          <span>{entrada ? 'Quantidade recebida' : 'Saldo contado no inventário'}</span>
          <input
            type="number"
            min={entrada ? 1 : 0}
            step={1}
            autoFocus
            value={quantidade}
            onChange={(event) => setQuantidade(event.target.value)}
            className={campo}
          />
        </label>
        <label className="block space-y-1.5 text-sm text-slate-300">
          <span>{entrada ? 'Observação (opcional)' : 'Motivo do ajuste'}</span>
          <textarea
            rows={3}
            maxLength={500}
            value={observacao}
            onChange={(event) => setObservacao(event.target.value)}
            placeholder={entrada ? 'Ex.: NF 1234, fornecedor' : 'Ex.: inventário mensal, livros danificados'}
            className={campo}
          />
        </label>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800">
            Cancelar
          </button>
          <button
            type="submit"
            disabled={salvando}
            className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50"
          >
            {salvando && <Loader2 className="h-4 w-4 animate-spin" />}
            {entrada ? 'Registrar entrada' : 'Salvar ajuste'}
          </button>
        </div>
      </form>
    </div>
  );
};

const HistoricoDrawer: React.FC<{ item: EstoqueItem; onClose: () => void }> = ({ item, onClose }) => {
  const [movimentos, setMovimentos] = useState<EstoqueMovimentacao[] | null>(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    let ativo = true;
    financeiroApi
      .movimentacoesEstoque(item.disciplina_id)
      .then((lista) => ativo && setMovimentos(lista))
      .catch((error) => {
        if (!ativo) return;
        setMovimentos([]);
        setErro(erroApi(error, 'Não foi possível carregar o histórico.'));
      });
    return () => {
      ativo = false;
    };
  }, [item.disciplina_id]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={onClose}>
      <aside
        onClick={(event) => event.stopPropagation()}
        className="glass h-full w-full max-w-xl space-y-5 overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 text-sm shadow-2xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Histórico do estoque</h2>
            <p className="mt-1 text-slate-400">
              {item.disciplina_nome}
              {item.sku ? <span className="ml-1 font-mono text-xs text-slate-500">· {item.sku}</span> : null}
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        {erro && <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">{erro}</div>}

        {movimentos === null ? (
          <p className="flex items-center gap-2 text-slate-400"><Loader2 className="h-4 w-4 animate-spin" /> Carregando...</p>
        ) : movimentos.length === 0 && !erro ? (
          <p className="rounded-xl border border-slate-800 p-6 text-center text-slate-500">Nenhuma movimentação registrada.</p>
        ) : (
          <ul className="space-y-2">
            {movimentos.map((mov) => (
              <li key={mov.id} className="rounded-xl border border-slate-800 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${TIPO_MOV[mov.tipo].className}`}>
                    {TIPO_MOV[mov.tipo].label}
                  </span>
                  <span className="text-xs text-slate-500">{formatData(mov.criado_em, true)}</span>
                </div>
                <p className="mt-2 text-slate-200">
                  <span className={`font-bold ${mov.quantidade < 0 ? 'text-red-400' : 'text-emerald-300'}`}>
                    {mov.quantidade > 0 ? `+${mov.quantidade}` : mov.quantidade}
                  </span>
                  <span className="text-slate-400"> · saldo após: </span>
                  <Saldo quantidade={mov.saldo_apos} />
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {[
                    mov.pedido_numero && `Pedido ${mov.pedido_numero}`,
                    mov.usuario_nome,
                    // A baixa já mostra o pedido; a observação automática só repetiria o número.
                    !(mov.tipo === 'baixa_envio' && mov.pedido_numero) && mov.observacao,
                  ].filter(Boolean).join(' · ')}
                </p>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
};
