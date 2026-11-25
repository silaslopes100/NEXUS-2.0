import React, { useState } from 'react';
import { Clock, FileText, Link2, Loader2, NotebookPen, Pencil, Star, Trash2 } from 'lucide-react';
import { ConteudoHtml } from '@/features/comunicacao/components/ConteudoHtml';
import { mensagemErro } from '@/features/comunicacao/api';
import { tamanhoLegivel } from '@/features/chat/utils';
import { Anotacao, AulaAluno, PlayerApi, tempoVideo } from '../../alunoApi';
import { BotaoDownload } from './ConteudoItem';

type Aba = 'visao' | 'materiais' | 'anotacoes';

interface Props {
  api: PlayerApi;
  aula: AulaAluno;
  previa: boolean;
  /** Posição atual do vídeo (para carimbar a anotação). */
  posicaoVideo: () => number | null;
  /** Volta o vídeo para a posição da anotação. */
  onIrPara?: (seg: number) => void;
}

const Estrelas: React.FC<{ api: PlayerApi; aulaId: string; inicial?: number | null; desabilitado: boolean }> = ({ api, aulaId, inicial, desabilitado }) => {
  const [nota, setNota] = useState(inicial ?? 0);
  const [sobre, setSobre] = useState(0);
  const [obrigado, setObrigado] = useState(false);
  const votar = async (n: number) => {
    const anterior = nota;
    setNota(n);
    try {
      await api.avaliarAula(aulaId, n);
      setObrigado(true);
    } catch {
      setNota(anterior);
    }
  };
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3">
      <span className="text-sm text-slate-300">O que achou desta aula?</span>
      <span className="flex" onMouseLeave={() => setSobre(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" disabled={desabilitado} onMouseEnter={() => setSobre(n)} onClick={() => void votar(n)}
            aria-label={`${n} estrela${n > 1 ? 's' : ''}`} className="p-0.5 disabled:cursor-not-allowed">
            <Star size={22} className={(sobre || nota) >= n ? 'fill-nexus-yellow text-nexus-yellow' : 'text-slate-600'} />
          </button>
        ))}
      </span>
      {obrigado && <span className="text-xs text-emerald-300">Obrigado pelo retorno!</span>}
    </div>
  );
};

const Anotacoes: React.FC<Props> = ({ api, aula, previa, posicaoVideo, onIrPara }) => {
  const [lista, setLista] = useState<Anotacao[]>(aula.anotacoes);
  const [texto, setTexto] = useState('');
  const [editando, setEditando] = useState<{ id: string; texto: string } | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const adicionar = async () => {
    if (!texto.trim()) return;
    setSalvando(true);
    setErro(null);
    try {
      const pos = posicaoVideo();
      const nova = await api.criarAnotacao(aula.id, texto.trim(), pos != null ? Math.floor(pos) : null);
      setLista((l) => [nova, ...l]);
      setTexto('');
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const salvarEdicao = async () => {
    if (!editando?.texto.trim()) return;
    try {
      const a = await api.atualizarAnotacao(editando.id, editando.texto.trim());
      setLista((l) => l.map((x) => (x.id === a.id ? a : x)));
      setEditando(null);
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  const excluir = async (id: string) => {
    if (!window.confirm('Excluir esta anotação?')) return;
    try {
      await api.excluirAnotacao(id);
      setLista((l) => l.filter((x) => x.id !== id));
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  if (previa) return <p className="text-sm text-slate-400">As anotações ficam disponíveis para o aluno.</p>;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={3} maxLength={5000}
          placeholder="Anote algo importante desta aula…"
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] text-slate-500">Só você vê suas anotações. No vídeo, guardamos o minuto.</span>
          <button type="button" onClick={() => void adicionar()} disabled={!texto.trim() || salvando}
            className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
            {salvando && <Loader2 size={14} className="animate-spin" />} Salvar anotação
          </button>
        </div>
      </div>
      {erro && <p className="text-xs text-red-300">{erro}</p>}
      {lista.length === 0 ? (
        <p className="text-center text-sm text-slate-500">Nenhuma anotação ainda.</p>
      ) : (
        <ul className="space-y-2">
          {lista.map((a) => (
            <li key={a.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
              <div className="mb-1 flex items-center gap-2 text-[11px] text-slate-500">
                {a.posicao_seg != null && (
                  <button type="button" onClick={() => onIrPara?.(a.posicao_seg!)}
                    className="inline-flex items-center gap-1 rounded-md bg-nexus-yellow/15 px-1.5 py-0.5 font-mono font-semibold text-nexus-yellow hover:bg-nexus-yellow/25">
                    <Clock size={11} /> {tempoVideo(a.posicao_seg)}
                  </button>
                )}
                <span>{new Date(a.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</span>
                <span className="ml-auto flex gap-1">
                  <button type="button" onClick={() => setEditando({ id: a.id, texto: a.texto })} aria-label="Editar"
                    className="rounded p-1 hover:bg-slate-800 hover:text-white"><Pencil size={12} /></button>
                  <button type="button" onClick={() => void excluir(a.id)} aria-label="Excluir"
                    className="rounded p-1 hover:bg-red-500/10 hover:text-red-300"><Trash2 size={12} /></button>
                </span>
              </div>
              {editando?.id === a.id ? (
                <div className="space-y-2">
                  <textarea value={editando.texto} onChange={(e) => setEditando({ ...editando, texto: e.target.value })} rows={3}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-white focus:border-nexus-yellow focus:outline-none" />
                  <div className="flex justify-end gap-2 text-xs">
                    <button type="button" onClick={() => setEditando(null)} className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300">Cancelar</button>
                    <button type="button" onClick={() => void salvarEdicao()} className="rounded-lg bg-nexus-yellow px-3 py-1.5 font-bold text-ink">Salvar</button>
                  </div>
                </div>
              ) : (
                <p className="whitespace-pre-line text-sm text-slate-200">{a.texto}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

/** Abas abaixo do conteúdo: Visão geral, Materiais e Anotações. */
export const AbasAula: React.FC<Props> = (props) => {
  const { aula, previa } = props;
  const [aba, setAba] = useState<Aba>('visao');
  const materiais = aula.itens.filter((i) => i.tipo === 'arquivo' || i.tipo === 'link');
  const abas: { id: Aba; rotulo: string; icone: React.ElementType; total?: number }[] = [
    { id: 'visao', rotulo: 'Visão geral', icone: FileText },
    { id: 'materiais', rotulo: 'Materiais', icone: Link2, total: materiais.length },
    { id: 'anotacoes', rotulo: 'Anotações', icone: NotebookPen, total: previa ? undefined : aula.anotacoes.length },
  ];

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60">
      <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-slate-800 px-2">
        {abas.map(({ id, rotulo, icone: Icone, total }) => (
          <button key={id} type="button" role="tab" aria-selected={aba === id} onClick={() => setAba(id)}
            className={`-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition ${
              aba === id ? 'border-nexus-yellow text-white' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
            <Icone size={15} /> {rotulo}
            {total ? <span className="rounded-full bg-slate-800 px-1.5 text-[11px] text-slate-300">{total}</span> : null}
          </button>
        ))}
      </div>
      <div className="p-4 sm:p-5">
        {aba === 'visao' && (
          <div className="space-y-4">
            {aula.descricao ? (
              <ConteudoHtml html={aula.descricao} className="text-slate-200" />
            ) : (
              <p className="text-sm text-slate-500">Sem descrição para esta aula.</p>
            )}
            {aula.tipo === 'conteudo' && <Estrelas key={aula.id} api={props.api} aulaId={aula.id} inicial={aula.minha_nota} desabilitado={previa} />}
          </div>
        )}
        {aba === 'materiais' &&
          (materiais.length === 0 ? (
            <p className="text-sm text-slate-500">Esta aula não tem materiais para download.</p>
          ) : (
            <ul className="divide-y divide-slate-800">
              {materiais.map((m) => (
                <li key={m.id} className="flex items-center gap-3 py-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-nexus-yellow">
                    {m.tipo === 'link' ? <Link2 size={16} /> : <FileText size={16} />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-white">{m.titulo || m.arquivo_nome || m.url}</span>
                    <span className="block truncate text-[11px] text-slate-500">
                      {m.tipo === 'link' ? m.url : `${m.arquivo_nome}${m.arquivo_tamanho ? ` · ${tamanhoLegivel(m.arquivo_tamanho)}` : ''}`}
                    </span>
                  </span>
                  {m.tipo === 'link' ? (
                    <a href={m.url || '#'} target="_blank" rel="noopener noreferrer"
                      className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-nexus-yellow/60">Abrir</a>
                  ) : (
                    <BotaoDownload item={m} />
                  )}
                </li>
              ))}
            </ul>
          ))}
        {aba === 'anotacoes' && <Anotacoes key={aula.id} {...props} />}
      </div>
    </section>
  );
};
