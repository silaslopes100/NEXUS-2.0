import React, { useState } from 'react';
import { ClipboardCheck, Loader2, PlayCircle, X } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { EditorRico } from '@/features/comunicacao/components/editor/EditorRico';
import { Aula, AulaPayload, ItemAula, TipoAula, avaAdminApi } from '../../api';
import { ItensAula } from './ItensAula';
import { SeletorAvaliacao } from './SeletorAvaliacao';
import { botaoPrimario, botaoSecundario, campo, rotulo } from './estilos';

interface Props {
  disciplinaId: string;
  cursoId?: string | null;
  capituloId: string;
  capituloTitulo: string;
  /** Aula existente (edição) ou nada (nova aula). */
  aula?: Aula | null;
  onFechar: () => void;
  /** Chamado a cada gravação (aula criada/atualizada ou itens alterados). */
  onAlterada: (aula: Aula) => void;
}

const OPCOES: { tipo: TipoAula; titulo: string; texto: string; icone: React.ElementType }[] = [
  { tipo: 'conteudo', titulo: 'Conteúdo', texto: 'Vídeos, PDFs, slides, imagens, links e textos.', icone: PlayCircle },
  { tipo: 'avaliacao', titulo: 'Avaliação', texto: 'Uma avaliação cadastrada nas disciplinas do curso.', icone: ClipboardCheck },
];

export const AulaDrawer: React.FC<Props> = ({ disciplinaId, cursoId, capituloId, capituloTitulo, aula, onFechar, onAlterada }) => {
  const [atual, setAtual] = useState<Aula | null>(aula ?? null);
  const [tipo, setTipo] = useState<TipoAula | null>(aula?.tipo ?? null);
  const [titulo, setTitulo] = useState(aula?.titulo ?? '');
  const [descricao, setDescricao] = useState(aula?.descricao ?? '');
  const [duracao, setDuracao] = useState(aula?.duracao_min != null ? String(aula.duracao_min) : '');
  const [liberarApos, setLiberarApos] = useState(aula?.liberar_apos_dias != null ? String(aula.liberar_apos_dias) : '');
  const [publicado, setPublicado] = useState(aula?.publicado ?? true);
  const [obrigatoria, setObrigatoria] = useState(aula?.obrigatoria ?? true);
  const [avaliacaoId, setAvaliacaoId] = useState<string | null>(aula?.avaliacao_id ?? null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const salvar = async () => {
    if (!tipo) return;
    setSalvando(true);
    setErro(null);
    const payload: AulaPayload = {
      titulo: titulo.trim(),
      descricao: descricao || null,
      tipo,
      avaliacao_id: tipo === 'avaliacao' ? avaliacaoId : null,
      duracao_min: duracao ? Number(duracao) : null,
      liberar_apos_dias: liberarApos ? Number(liberarApos) : null,
      publicado,
      obrigatoria,
    };
    try {
      const salva = atual ? await avaAdminApi.atualizarAula(atual.id, payload) : await avaAdminApi.criarAula(capituloId, payload);
      onAlterada(salva);
      if (tipo === 'avaliacao' || atual) {
        onFechar();
      } else {
        setAtual(salva); // nova aula de conteúdo: segue no drawer para adicionar os itens
      }
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const itensAlterados = (itens: ItemAula[]) => {
    if (!atual) return;
    const nova = { ...atual, itens };
    setAtual(nova);
    onAlterada(nova);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onMouseDown={onFechar}>
      <aside className="flex h-full w-full max-w-3xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="min-w-0">
            <p className="truncate text-[11px] uppercase tracking-wide text-slate-500">{capituloTitulo}</p>
            <h2 className="text-lg font-bold text-white">{atual ? 'Editar aula' : 'Nova aula'}</h2>
          </div>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-6 py-5">
          {!tipo ? (
            <section className="space-y-3">
              <p className="text-sm text-slate-300">Que tipo de aula você quer criar?</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {OPCOES.map(({ tipo: t, titulo: tt, texto, icone: Icone }) => (
                  <button key={t} type="button" onClick={() => setTipo(t)}
                    className="flex flex-col items-start gap-3 rounded-2xl border border-slate-700 bg-slate-950 p-5 text-left transition hover:border-nexus-yellow hover:shadow-nexus-glow">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-nexus-yellow/15 text-nexus-yellow">
                      <Icone size={22} />
                    </span>
                    <span className="text-base font-bold text-white">{tt}</span>
                    <span className="text-xs text-slate-400">{texto}</span>
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <>
              <section className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${tipo === 'avaliacao' ? 'bg-blue-500/20 text-blue-200' : 'bg-nexus-yellow/15 text-nexus-yellow'}`}>
                    {tipo === 'avaliacao' ? 'Avaliação' : 'Conteúdo'}
                  </span>
                  {!atual && (
                    <button type="button" onClick={() => setTipo(null)} className="text-xs text-slate-400 underline hover:text-white">
                      trocar tipo
                    </button>
                  )}
                </div>

                <label className="block">
                  <span className={rotulo}>Título da aula</span>
                  <input value={titulo} maxLength={255} onChange={(e) => setTitulo(e.target.value)} className={campo} autoFocus
                    placeholder={tipo === 'avaliacao' ? 'Ex.: Avaliação final' : 'Ex.: Aula 1 — Introdução'} />
                </label>

                {tipo === 'avaliacao' && (
                  <SeletorAvaliacao cursoInicial={cursoId} valor={avaliacaoId}
                    onChange={(id, opcao) => {
                      setAvaliacaoId(id);
                      if (opcao && !titulo.trim()) setTitulo(opcao.titulo);
                    }} />
                )}

                <div>
                  <span className={rotulo}>Descrição (opcional)</span>
                  <EditorRico valor={descricao} onChange={setDescricao} variante="aviso" alturaMinima="min-h-[100px]"
                    placeholder="O que o aluno vai aprender nesta aula…" />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <label>
                    <span className={rotulo}>Duração estimada (min)</span>
                    <input type="number" min={0} value={duracao} onChange={(e) => setDuracao(e.target.value)} className={campo} placeholder="Ex.: 15" />
                  </label>
                  <label>
                    <span className={rotulo}>Liberar após (dias)</span>
                    <input type="number" min={0} value={liberarApos} onChange={(e) => setLiberarApos(e.target.value)} className={campo}
                      placeholder="Imediato" />
                    <span className="mt-1 block text-[11px] text-slate-500">Contados a partir da liberação da disciplina para o aluno.</span>
                  </label>
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-slate-200">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={publicado} onChange={(e) => setPublicado(e.target.checked)} /> Publicada
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={obrigatoria} onChange={(e) => setObrigatoria(e.target.checked)} />
                    Obrigatória para concluir a disciplina
                  </label>
                </div>
              </section>

              {tipo === 'conteudo' && atual && (
                <section className="space-y-3 border-t border-slate-800 pt-5">
                  <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">Conteúdos da aula</h3>
                  <ItensAula disciplinaId={disciplinaId} aulaId={atual.id} itens={atual.itens} onChange={itensAlterados} />
                </section>
              )}
              {tipo === 'conteudo' && !atual && (
                <p className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-400">
                  Salve a aula para adicionar vídeos, arquivos e textos.
                </p>
              )}
            </>
          )}
          {erro && <p role="alert" className="text-sm text-red-300">{erro}</p>}
        </div>

        {tipo && (
          <footer className="flex justify-end gap-2 border-t border-slate-800 px-6 py-4">
            <button type="button" onClick={onFechar} className={botaoSecundario}>{atual ? 'Fechar' : 'Cancelar'}</button>
            <button type="button" onClick={() => void salvar()} disabled={salvando || !titulo.trim() || (tipo === 'avaliacao' && !avaliacaoId)}
              className={botaoPrimario}>
              {salvando && <Loader2 size={14} className="animate-spin" />}
              {atual ? 'Salvar aula' : tipo === 'conteudo' ? 'Criar e adicionar conteúdos' : 'Criar aula'}
            </button>
          </footer>
        )}
      </aside>
    </div>
  );
};
