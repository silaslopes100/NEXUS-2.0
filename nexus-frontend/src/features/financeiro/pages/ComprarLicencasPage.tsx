import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, BookOpen, GraduationCap, Loader2, Minus, Plus, ShoppingCart, Trash2 } from 'lucide-react';
import { financeiroApi } from '@/features/financeiro/api';
import { MeioPagamentoCheckout, ResultadoCheckout, useOpcoesCheckout } from '@/features/financeiro/components/Checkout';
import {
  CheckoutResposta, CursoCatalogo, CursoCatalogoDetalhe, DisciplinaCatalogo, MeioCobranca, erroApi, formatBRL,
} from '@/features/financeiro/types';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';

interface ItemCarrinho { disciplina: DisciplinaCatalogo; curso: string; quantidade: number }

/**
 * Compra por Curso → Disciplinas → carrinho → pagamento.
 * Cada unidade é um kit: 1 livro físico (enviado pela logística) + 1 licença (estoque do Polo).
 */
export const ComprarLicencasPage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const isAdmin = normalizeUserRole(perfil?.nome) === 'admin';
  const [cursos, setCursos] = useState<CursoCatalogo[]>([]);
  const [curso, setCurso] = useState<CursoCatalogoDetalhe | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [carrinho, setCarrinho] = useState<Record<string, ItemCarrinho>>({});
  const [poloId, setPoloId] = useState(user?.polo_id || '');
  const [polos, setPolos] = useState<{ id: string; nome: string }[]>([]);
  const [meio, setMeio] = useState<MeioCobranca | ''>('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const [resultado, setResultado] = useState<CheckoutResposta | null>(null);

  useEffect(() => {
    financeiroApi.catalogoCursos()
      .then(setCursos)
      .catch((error) => setErro(erroApi(error, 'Não foi possível carregar os cursos.')))
      .finally(() => setCarregando(false));
    if (isAdmin) {
      polosEscolasApi.listarPolos({ limit: 200 })
        .then((data: any) => setPolos(data?.items || []))
        .catch(() => setPolos([]));
    }
  }, [isAdmin]);

  const abrirCurso = async (id: string) => {
    setCarregando(true);
    setErro('');
    try {
      setCurso(await financeiroApi.catalogoCurso(id, poloId || undefined));
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível carregar as disciplinas do curso.'));
    } finally {
      setCarregando(false);
    }
  };

  const itens = useMemo(() => Object.values(carrinho).filter((i) => i.quantidade > 0), [carrinho]);
  const total = itens.reduce((s, i) => s + Number(i.disciplina.preco || 0) * i.quantidade, 0);
  const totalUnidades = itens.reduce((s, i) => s + i.quantidade, 0);
  const opcoes = useOpcoesCheckout('kit', total, poloId);

  const setQtd = (d: DisciplinaCatalogo, valor: number) => {
    const quantidade = Math.max(0, Math.min(100000, Math.floor(valor) || 0));
    setCarrinho((c) => ({ ...c, [d.disciplina_id]: { disciplina: d, curso: curso?.nome || '', quantidade } }));
  };
  const qtd = (id: string) => carrinho[id]?.quantidade || 0;
  const aVenda = (curso?.disciplinas || []).filter((d) => d.a_venda);
  const totalCurso = aVenda.reduce((s, d) => s + Number(d.preco || 0), 0);
  /** Curso completo: 1 unidade de cada disciplina à venda (as quantidades podem ser ajustadas depois). */
  const adicionarCursoCompleto = () =>
    setCarrinho((c) => {
      const novo = { ...c };
      aVenda.forEach((d) => {
        if (!novo[d.disciplina_id]?.quantidade) novo[d.disciplina_id] = { disciplina: d, curso: curso?.nome || '', quantidade: 1 };
      });
      return novo;
    });

  // Semestres do curso (as disciplinas já vêm ordenadas por semestre/ordem).
  const porSemestre = useMemo(() => {
    const grupos = new Map<string, DisciplinaCatalogo[]>();
    (curso?.disciplinas || []).forEach((d) => {
      const chave = d.semestre ? `${d.semestre}º semestre` : 'Outras disciplinas';
      grupos.set(chave, [...(grupos.get(chave) || []), d]);
    });
    return Array.from(grupos.entries());
  }, [curso]);

  const finalizar = async () => {
    setErro('');
    if (!itens.length) { setErro('Adicione ao menos uma disciplina ao carrinho.'); return; }
    if (isAdmin && !poloId) { setErro('Selecione o Polo que está comprando.'); return; }
    if (!meio) { setErro('Escolha a forma de pagamento.'); return; }
    setEnviando(true);
    try {
      const res = await financeiroApi.checkout({
        tipo: 'kit',
        polo_id: isAdmin ? poloId : undefined,
        itens: itens.map((i) => ({ produto_id: i.disciplina.produto_id as string, quantidade: i.quantidade })),
        meio,
      });
      setResultado(res);
      setCarrinho({});
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível concluir a compra.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="max-w-7xl space-y-6">
      <header className="glass rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-amber-950/30 p-6 shadow-xl">
        <h1 className="text-3xl font-extrabold text-white">{curso ? curso.nome : 'Escolha o curso'}</h1>
        <p className="mt-1 text-sm text-slate-400">
          Cada unidade comprada inclui <strong className="text-slate-200">1 livro</strong> (enviado ao endereço do Polo) e
          <strong className="text-slate-200"> 1 licença</strong> para o aluno fazer a avaliação da disciplina.
        </p>
        {curso && (
          <button onClick={() => setCurso(null)} className="mt-3 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white">
            <ArrowLeft size={14} /> Voltar para os cursos
          </button>
        )}
      </header>

      {resultado ? (
        <ResultadoCheckout resultado={resultado} onFechar={() => setResultado(null)} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="space-y-4 lg:col-span-2">
            {erro && <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{erro}</p>}
            {carregando ? (
              <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
            ) : !curso ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {cursos.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => abrirCurso(c.id)}
                    className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-5 text-left transition hover:border-amber-500/50"
                  >
                    <GraduationCap className="mb-3 text-amber-300" />
                    <p className="text-lg font-bold text-white">{c.nome}</p>
                    <p className="mt-1 text-sm text-slate-400">
                      {c.disciplinas_a_venda === c.disciplinas
                        ? `${c.disciplinas} disciplina(s)`
                        : `${c.disciplinas_a_venda} de ${c.disciplinas} disciplina(s) à venda`}
                    </p>
                    {c.disciplinas_a_venda > 0 ? (
                      <p className="mt-2 text-sm text-slate-300">
                        Curso completo: <strong className="text-amber-200">{formatBRL(c.preco_curso)}</strong>
                      </p>
                    ) : (
                      <p className="mt-2 text-xs text-amber-300">Preços ainda não definidos pelo administrador.</p>
                    )}
                  </button>
                ))}
                {!cursos.length && (
                  <p className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-10 text-center text-sm text-slate-500 sm:col-span-2">
                    Nenhum curso com disciplinas ativas. O administrador cadastra as disciplinas e o preço de cada uma em Disciplinas.
                  </p>
                )}
              </div>
            ) : (
              <>
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4">
                <p className="text-sm text-slate-300">
                  Curso completo ({aVenda.length} disciplina{aVenda.length === 1 ? '' : 's'}):{' '}
                  <strong className="text-amber-200">{formatBRL(totalCurso)}</strong> por aluno
                </p>
                <button type="button" disabled={!aVenda.length} onClick={adicionarCursoCompleto}
                  className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-bold text-ink hover:bg-amber-400 disabled:opacity-40">
                  Adicionar curso completo
                </button>
              </div>
              {porSemestre.map(([titulo, disciplinas]) => (
                <div key={titulo} className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
                  <h2 className="border-b border-slate-800 px-4 py-3 text-sm font-bold text-white">{titulo}</h2>
                  <ul className="divide-y divide-slate-800">
                    {disciplinas.map((d) => (
                      <li key={d.disciplina_id} className={`flex flex-wrap items-center justify-between gap-3 p-4 ${d.a_venda ? '' : 'opacity-60'}`}>
                        <div>
                          <p className="flex items-center gap-2 font-semibold text-white"><BookOpen size={15} className="text-slate-400" /> {d.nome}</p>
                          <p className="text-xs text-slate-500">
                            {d.a_venda ? `${formatBRL(d.preco)} por aluno (livro + licença) · ` : ''}seu saldo atual: {d.saldo_polo} licença(s)
                          </p>
                        </div>
                        {!d.a_venda ? (
                          <span className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-400">Preço não definido</span>
                        ) : (
                        <div className="flex items-center rounded-xl border border-slate-700">
                          <button onClick={() => setQtd(d, qtd(d.disciplina_id) - 1)} aria-label={`Diminuir ${d.nome}`} className="p-2 text-slate-400 hover:text-white"><Minus size={14} /></button>
                          <input type="number" min={0} aria-label={`Quantidade de ${d.nome}`} value={qtd(d.disciplina_id)} onChange={(e) => setQtd(d, Number(e.target.value))} className="w-16 bg-transparent text-center text-sm text-white outline-none" />
                          <button onClick={() => setQtd(d, qtd(d.disciplina_id) + 1)} aria-label={`Aumentar ${d.nome}`} className="p-2 text-slate-400 hover:text-white"><Plus size={14} /></button>
                        </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              </>
            )}
          </section>

          <aside className="glass h-fit space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <h2 className="flex items-center gap-2 font-bold text-white"><ShoppingCart size={16} /> Carrinho</h2>
            {isAdmin && (
              <label className="block space-y-1 text-xs text-slate-400">
                <span>Polo que está comprando</span>
                <select className={inputClass} value={poloId} onChange={(e) => setPoloId(e.target.value)}>
                  <option value="">Selecione o Polo…</option>
                  {polos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </label>
            )}
            <ul className="space-y-2 text-sm">
              {itens.map((i) => (
                <li key={i.disciplina.disciplina_id} className="flex items-start justify-between gap-2 text-slate-300">
                  <span>
                    {i.quantidade} × {i.disciplina.nome}
                    <span className="block text-[11px] text-slate-500">{i.curso}</span>
                  </span>
                  <span className="flex items-center gap-2 whitespace-nowrap">
                    {formatBRL(Number(i.disciplina.preco || 0) * i.quantidade)}
                    <button onClick={() => setQtd(i.disciplina, 0)} aria-label={`Remover ${i.disciplina.nome}`} className="text-slate-500 hover:text-red-300"><Trash2 size={13} /></button>
                  </span>
                </li>
              ))}
              {!itens.length && <li className="text-xs text-slate-500">Escolha um curso e as quantidades de cada disciplina.</li>}
            </ul>
            <p className="flex justify-between border-t border-slate-800 pt-3 text-lg font-bold text-white">
              <span>Total <span className="text-xs font-normal text-slate-500">({totalUnidades} livro(s) + {totalUnidades} licença(s))</span></span>
              <span>{formatBRL(total)}</span>
            </p>
            {itens.length > 0 && <MeioPagamentoCheckout opcoes={opcoes} meio={meio} onChange={setMeio} />}
            <button onClick={finalizar} disabled={enviando || !itens.length || !meio} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-2.5 font-semibold text-on-accent disabled:opacity-50">
              {enviando && <Loader2 className="animate-spin" size={16} />} Finalizar e gerar pagamento
            </button>
            <p className="text-[11px] text-slate-500">Após o pagamento, as licenças entram no seu estoque e os livros seguem para envio.</p>
          </aside>
        </div>
      )}
    </div>
  );
};
