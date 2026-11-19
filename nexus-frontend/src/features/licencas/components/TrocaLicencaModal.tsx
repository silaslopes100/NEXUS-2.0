import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, Loader2, Plus, Repeat, Trash2, X } from 'lucide-react';
import { cursosApi, Curso, Disciplina } from '@/features/cursos/api';
import { EstoqueDisciplina } from '@/features/licencas/api';
import { financeiroApi } from '@/features/financeiro/api';
import { EnderecoEntrega, erroApi, MOTIVO_TROCA, MotivoTroca, Pedido } from '@/features/financeiro/types';

const inputClass = 'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-blue-500';
const labelCls = 'block space-y-1 text-sm text-slate-300';

interface Linha {
  chave: number;
  devolver: string;
  receber: string;
  quantidade: string;
}

const novaLinha = (chave: number): Linha => ({ chave, devolver: '', receber: '', quantidade: '1' });

const ENDERECO_VAZIO: EnderecoEntrega = {
  nome: '', cep: '', logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', uf: '', telefone: '',
};

interface Props {
  /** Saldo da unidade (Polo ou Escola) por disciplina. */
  estoque: EstoqueDisciplina | null;
  onFechar: () => void;
  onConcluido: (pedido: Pedido) => void;
}

/**
 * Troca de licença em 2 etapas:
 * 1) escolher as disciplinas (devolver × quantidade → receber);
 * 2) formulário de troca de livro (motivo, entrega e confirmação).
 * As licenças a devolver ficam reservadas até o Admin concluir ou recusar a troca.
 */
export const TrocaLicencaModal: React.FC<Props> = ({ estoque, onFechar, onConcluido }) => {
  const [etapa, setEtapa] = useState<1 | 2>(1);
  const [linhas, setLinhas] = useState<Linha[]>([novaLinha(1)]);
  const [proximaChave, setProximaChave] = useState(2);
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [disciplinas, setDisciplinas] = useState<Disciplina[]>([]);
  const [motivo, setMotivo] = useState<MotivoTroca | ''>('');
  const [descricao, setDescricao] = useState('');
  const [outroEndereco, setOutroEndereco] = useState(false);
  const [endereco, setEndereco] = useState<EnderecoEntrega>(ENDERECO_VAZIO);
  const [confirmado, setConfirmado] = useState(false);
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [concluido, setConcluido] = useState<Pedido | null>(null);

  useEffect(() => {
    cursosApi.listar().then(setCursos).catch(() => setCursos([]));
    cursosApi.listarDisciplinas().then(setDisciplinas).catch(() => setDisciplinas([]));
  }, []);

  const nomePorId = useMemo(() => new Map(disciplinas.map((d) => [d.id, d.nome])), [disciplinas]);

  // Disciplinas com saldo na unidade (só essas podem ser devolvidas).
  const comSaldo = useMemo(
    () => (estoque?.items || [])
      .filter((i) => i.materia_id && i.quantidade_disponivel > 0)
      .map((i) => ({ id: i.materia_id as string, nome: i.disciplina_nome || nomePorId.get(i.materia_id as string) || 'Disciplina', saldo: i.quantidade_disponivel }))
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [estoque, nomePorId],
  );
  const saldoDe = (id: string) => comSaldo.find((d) => d.id === id)?.saldo ?? 0;

  // Disciplinas ativas agrupadas por curso, para "Licença a receber".
  const grupos = useMemo(() => {
    const ativas = disciplinas.filter((d) => d.ativo !== false);
    const porCurso = new Map<string, Disciplina[]>();
    for (const d of ativas) {
      const chave = d.curso_id || '';
      porCurso.set(chave, [...(porCurso.get(chave) || []), d]);
    }
    const nomeCurso = (id: string) => cursos.find((c) => c.id === id)?.nome || 'Sem curso';
    return Array.from(porCurso.entries())
      .map(([cursoId, lista]) => ({ curso: nomeCurso(cursoId), lista: lista.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')) }))
      .sort((a, b) => a.curso.localeCompare(b.curso, 'pt-BR'));
  }, [cursos, disciplinas]);

  const usadoEmOutras = (linha: Linha) =>
    linhas.filter((l) => l.chave !== linha.chave && l.devolver === linha.devolver)
      .reduce((soma, l) => soma + (Number(l.quantidade) || 0), 0);

  const atualizar = (chave: number, campo: keyof Omit<Linha, 'chave'>, valor: string) =>
    setLinhas((atuais) => atuais.map((l) => {
      if (l.chave !== chave) return l;
      const nova = { ...l, [campo]: valor };
      if (campo === 'devolver' && valor === l.receber) nova.receber = '';
      return nova;
    }));

  const errosLinha = (linha: Linha): string | null => {
    if (!linha.devolver || !linha.receber) return 'Escolha as duas disciplinas.';
    const qtd = Number(linha.quantidade);
    if (!Number.isInteger(qtd) || qtd < 1) return 'Quantidade inválida.';
    const disponivel = saldoDe(linha.devolver) - usadoEmOutras(linha);
    if (qtd > disponivel) return `Saldo insuficiente: ${Math.max(0, disponivel)} disponível(is).`;
    return null;
  };

  const etapa1Valida = linhas.length > 0 && linhas.every((l) => !errosLinha(l));

  const enviar = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!motivo) { setErro('Escolha o motivo da troca.'); return; }
    if (motivo === 'outro' && !descricao.trim()) { setErro('Descreva o motivo da troca.'); return; }
    if (!confirmado) { setErro('Confirme a devolução dos livros para continuar.'); return; }
    setEnviando(true);
    setErro('');
    try {
      const pedido = await financeiroApi.solicitarTroca({
        itens: linhas.map((l) => ({
          disciplina_devolver_id: l.devolver,
          disciplina_receber_id: l.receber,
          quantidade: Number(l.quantidade),
        })),
        motivo,
        descricao: descricao.trim() || undefined,
        endereco: outroEndereco ? endereco : undefined,
      });
      setConcluido(pedido);
    } catch (error) {
      setErro(erroApi(error, 'Não foi possível enviar a solicitação de troca.'));
    } finally {
      setEnviando(false);
    }
  };

  const campoEndereco = (campo: keyof EnderecoEntrega, rotulo: string, extra = '') => (
    <label className={`${labelCls} ${extra}`}>
      <span>{rotulo}</span>
      <input
        className={inputClass}
        value={endereco[campo] || ''}
        maxLength={campo === 'uf' ? 2 : 255}
        onChange={(e) => setEndereco({ ...endereco, [campo]: campo === 'uf' ? e.target.value.toUpperCase() : e.target.value })}
      />
    </label>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="troca-titulo"
        className="glass my-auto max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 id="troca-titulo" className="flex items-center gap-2 text-xl font-bold text-white">
              <Repeat size={20} className="text-blue-400" />
              {concluido ? 'Solicitação enviada' : etapa === 1 ? 'Trocar licença' : 'Formulário de troca de livro'}
            </h2>
            {!concluido && (
              <ol className="mt-2 flex items-center gap-2 text-xs">
                <li className={etapa === 1 ? 'font-semibold text-white' : 'text-slate-500'}>1 · Disciplinas</li>
                <ArrowRight size={12} className="text-slate-600" />
                <li className={etapa === 2 ? 'font-semibold text-white' : 'text-slate-500'}>2 · Formulário</li>
              </ol>
            )}
          </div>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        </header>

        {erro && <div role="alert" className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</div>}

        {concluido ? (
          <div className="mt-5 space-y-4">
            <p className="flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
              <span>
                Solicitação <strong>{concluido.numero}</strong> enviada ao administrador. As licenças a devolver ficaram
                reservadas. Acompanhe o andamento em <strong>Meus Pedidos</strong>.
              </span>
            </p>
            <div className="flex justify-end">
              <button type="button" onClick={() => onConcluido(concluido)} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-on-accent">
                Concluir
              </button>
            </div>
          </div>
        ) : etapa === 1 ? (
          <div className="mt-5 space-y-4">
            <p className="text-sm text-slate-400">
              Escolha a licença que vai devolver e a que vai receber no lugar. O livro físico também é trocado.
            </p>
            {!comSaldo.length && (
              <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
                Não há licenças disponíveis no seu saldo para trocar.
              </p>
            )}
            <ul className="space-y-3">
              {linhas.map((linha, indice) => {
                const problema = linha.devolver && linha.receber ? errosLinha(linha) : null;
                return (
                  <li key={linha.chave} className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="grid gap-3 md:grid-cols-[1fr_96px_auto_1fr_auto] md:items-end">
                      <label className={labelCls}>
                        <span>Licença a devolver</span>
                        <select className={inputClass} value={linha.devolver} onChange={(e) => atualizar(linha.chave, 'devolver', e.target.value)}>
                          <option value="">Selecione</option>
                          {comSaldo.map((d) => <option key={d.id} value={d.id}>{d.nome} — {d.saldo} disponível(is)</option>)}
                        </select>
                      </label>
                      <label className={labelCls}>
                        <span>Qtd.</span>
                        <input type="number" min={1} step={1} className={inputClass} value={linha.quantidade}
                          onChange={(e) => atualizar(linha.chave, 'quantidade', e.target.value)} />
                      </label>
                      <ArrowRight size={18} className="mx-auto hidden text-slate-500 md:mb-2.5 md:block" aria-hidden="true" />
                      <label className={labelCls}>
                        <span>Licença a receber</span>
                        <select className={inputClass} value={linha.receber} onChange={(e) => atualizar(linha.chave, 'receber', e.target.value)}>
                          <option value="">Selecione</option>
                          {grupos.map((g) => (
                            <optgroup key={g.curso} label={g.curso}>
                              {g.lista.filter((d) => d.id !== linha.devolver).map((d) => <option key={d.id} value={d.id}>{d.nome}</option>)}
                            </optgroup>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        onClick={() => setLinhas((atuais) => atuais.filter((l) => l.chave !== linha.chave))}
                        disabled={linhas.length === 1}
                        aria-label={`Remover troca ${indice + 1}`}
                        className="rounded-lg border border-slate-700 p-2 text-slate-400 hover:text-red-300 disabled:opacity-30 md:mb-0.5"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                    {problema && <p className="mt-2 text-xs text-red-300">{problema}</p>}
                  </li>
                );
              })}
            </ul>
            <button
              type="button"
              onClick={() => { setLinhas((atuais) => [...atuais, novaLinha(proximaChave)]); setProximaChave((c) => c + 1); }}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-300 hover:text-blue-200"
            >
              <Plus size={15} /> Adicionar outra troca
            </button>
            <div className="flex flex-col-reverse gap-2 border-t border-slate-800 pt-4 sm:flex-row sm:justify-end">
              <button type="button" onClick={onFechar} className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300">
                Cancelar
              </button>
              <button
                type="button"
                disabled={!etapa1Valida}
                onClick={() => { setErro(''); setEtapa(2); }}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent disabled:opacity-50"
              >
                Seguir para FORMULÁRIO DE TROCA DE LIVRO <ArrowRight size={15} />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={enviar} className="mt-5 space-y-5">
            <section className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
              <h3 className="text-xs font-semibold uppercase text-slate-500">Resumo da troca</h3>
              <ul className="mt-2 space-y-1.5 text-sm">
                {linhas.map((l) => (
                  <li key={l.chave} className="flex flex-wrap items-center gap-2 text-slate-200">
                    <span>{nomePorId.get(l.devolver) || comSaldo.find((d) => d.id === l.devolver)?.nome}</span>
                    <span className="text-slate-500">× {l.quantidade}</span>
                    <ArrowRight size={14} className="text-slate-500" />
                    <span className="font-semibold text-white">{nomePorId.get(l.receber)}</span>
                  </li>
                ))}
              </ul>
            </section>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className={labelCls}>
                <span>Motivo da troca</span>
                <select required className={inputClass} value={motivo} onChange={(e) => setMotivo(e.target.value as MotivoTroca)}>
                  <option value="">Selecione</option>
                  {(Object.keys(MOTIVO_TROCA) as MotivoTroca[]).map((m) => <option key={m} value={m}>{MOTIVO_TROCA[m]}</option>)}
                </select>
              </label>
              <label className={`${labelCls} sm:col-span-2`}>
                <span>Descrição {motivo === 'outro' ? '' : '(opcional)'}</span>
                <textarea rows={3} maxLength={2000} className={inputClass} value={descricao} onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Conte o que aconteceu (ex.: turma mudou de grade, livro veio com páginas faltando)." />
              </label>
            </div>

            <fieldset className="space-y-3">
              <legend className="text-sm font-semibold text-white">Entrega do livro novo</legend>
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="radio" name="endereco" checked={!outroEndereco} onChange={() => setOutroEndereco(false)} />
                Usar o endereço cadastrado do Polo
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="radio" name="endereco" checked={outroEndereco} onChange={() => setOutroEndereco(true)} />
                Informar outro endereço
              </label>
              {outroEndereco && (
                <div className="grid gap-3 sm:grid-cols-6">
                  {campoEndereco('nome', 'Destinatário', 'sm:col-span-4')}
                  {campoEndereco('cep', 'CEP', 'sm:col-span-2')}
                  {campoEndereco('logradouro', 'Logradouro', 'sm:col-span-4')}
                  {campoEndereco('numero', 'Número', 'sm:col-span-2')}
                  {campoEndereco('complemento', 'Complemento', 'sm:col-span-3')}
                  {campoEndereco('bairro', 'Bairro', 'sm:col-span-3')}
                  {campoEndereco('cidade', 'Cidade', 'sm:col-span-4')}
                  {campoEndereco('uf', 'UF', 'sm:col-span-2')}
                  {campoEndereco('telefone', 'Telefone de contato', 'sm:col-span-3')}
                </div>
              )}
            </fieldset>

            <label className="flex items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-sm text-slate-300">
              <input type="checkbox" className="mt-1" checked={confirmado} onChange={(e) => setConfirmado(e.target.checked)} />
              <span>
                Confirmo que os livros devolvidos serão enviados ao Estoque Central em bom estado e que as licenças a
                devolver ficam reservadas até a conclusão da troca.
              </span>
            </label>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-800 pt-4 sm:flex-row sm:justify-end">
              <button type="button" onClick={() => { setErro(''); setEtapa(1); }} className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300">
                Voltar
              </button>
              <button type="submit" disabled={enviando} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-on-accent disabled:opacity-50">
                {enviando && <Loader2 size={15} className="animate-spin" />} Enviar solicitação
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
};
