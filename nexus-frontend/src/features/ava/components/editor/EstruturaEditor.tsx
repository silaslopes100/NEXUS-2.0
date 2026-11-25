import React, { useRef, useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Check,
  ChevronDown,
  ClipboardCheck,
  Copy,
  Eye,
  EyeOff,
  GripVertical,
  Lock,
  Pencil,
  PlayCircle,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { Aula, Capitulo, ReordenarPayload, duracaoCapitulo, formatarDuracao } from '../../api';

const idCap = (id: string) => `c:${id}`;
const idAula = (id: string) => `a:${id}`;
const idVazio = (id: string) => `d:${id}`;
const semPrefixo = (id: string) => id.slice(2);

// ---------------------------------------------------------------------------
// Aula (linha)
// ---------------------------------------------------------------------------

const LinhaAula: React.FC<{ aula: Aula; numero: number; onAbrir: () => void; onExcluir: () => void }> = ({ aula, numero, onAbrir, onExcluir }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: idAula(aula.id) });
  const avaliacao = aula.tipo === 'avaliacao';
  return (
    <li ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`group flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2.5 hover:border-slate-700 ${isDragging ? 'z-20 opacity-60 shadow-2xl' : ''}`}>
      <button type="button" {...attributes} {...listeners} aria-label="Arrastar aula"
        className="cursor-grab touch-none text-slate-600 hover:text-slate-300 active:cursor-grabbing">
        <GripVertical size={16} />
      </button>
      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${avaliacao ? 'bg-blue-500/15 text-blue-300' : 'bg-nexus-yellow/10 text-nexus-yellow'}`}>
        {avaliacao ? <ClipboardCheck size={16} /> : <PlayCircle size={16} />}
      </span>
      <button type="button" onClick={onAbrir} className="min-w-0 flex-1 text-left">
        <span className="block truncate text-sm font-medium text-slate-100">
          <span className="mr-1.5 text-slate-500">{numero}.</span>{aula.titulo}
        </span>
        <span className="flex flex-wrap items-center gap-x-2 text-[11px] text-slate-500">
          {avaliacao ? (
            <span>{aula.avaliacao_disciplina_nome ? `${aula.avaliacao_disciplina_nome} — ` : ''}{aula.avaliacao_titulo || 'Avaliação não definida'}</span>
          ) : (
            <span>{aula.itens.length} conteúdo(s)</span>
          )}
          {aula.duracao_min ? <span>· {formatarDuracao(aula.duracao_min)}</span> : null}
          {aula.liberar_apos_dias ? <span className="flex items-center gap-0.5">· <Lock size={10} /> {aula.liberar_apos_dias}d</span> : null}
          {!aula.obrigatoria && <span>· opcional</span>}
        </span>
      </button>
      {!aula.publicado && <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-400">Rascunho</span>}
      <button type="button" onClick={onAbrir} aria-label="Editar aula" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
        <Pencil size={14} />
      </button>
      <button type="button" onClick={onExcluir} aria-label="Excluir aula" className="rounded-lg p-1.5 text-slate-400 opacity-0 hover:bg-red-500/10 hover:text-red-300 group-hover:opacity-100">
        <Trash2 size={14} />
      </button>
    </li>
  );
};

// ---------------------------------------------------------------------------
// Capítulo
// ---------------------------------------------------------------------------

interface CapituloProps {
  capitulo: Capitulo;
  numero: number;
  aberto: boolean;
  onAlternar: () => void;
  onRenomear: (titulo: string) => void;
  onPublicar: () => void;
  onDuplicar: () => void;
  onExcluir: () => void;
  onNovaAula: () => void;
  onAbrirAula: (aula: Aula) => void;
  onExcluirAula: (aula: Aula) => void;
}

const CapituloCard: React.FC<CapituloProps> = (p) => {
  const { capitulo: c } = p;
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: idCap(c.id) });
  const { setNodeRef: setVazioRef, isOver } = useDroppable({ id: idVazio(c.id) });
  const [editando, setEditando] = useState(false);
  const [titulo, setTitulo] = useState(c.titulo);
  const duracao = duracaoCapitulo(c);

  const confirmar = () => {
    const t = titulo.trim();
    if (t && t !== c.titulo) p.onRenomear(t);
    else setTitulo(c.titulo);
    setEditando(false);
  };

  return (
    <li ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`rounded-2xl border bg-slate-900/70 ${isDragging ? 'z-30 border-nexus-yellow/60 opacity-70 shadow-2xl' : 'border-slate-800'}`}>
      <div className="flex items-center gap-2 px-3 py-3 sm:px-4">
        <button type="button" {...attributes} {...listeners} aria-label="Arrastar capítulo"
          className="cursor-grab touch-none text-slate-600 hover:text-slate-300 active:cursor-grabbing">
          <GripVertical size={18} />
        </button>
        <button type="button" onClick={p.onAlternar} aria-label={p.aberto ? 'Recolher' : 'Expandir'}
          className="rounded-lg p-1 text-slate-400 hover:bg-slate-800">
          <ChevronDown size={18} className={`transition ${p.aberto ? '' : '-rotate-90'}`} />
        </button>
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600/20 text-sm font-black text-blue-200">
          {p.numero}
        </span>
        {editando ? (
          <span className="flex min-w-0 flex-1 items-center gap-1">
            <input value={titulo} autoFocus maxLength={255} onChange={(e) => setTitulo(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') confirmar(); if (e.key === 'Escape') { setTitulo(c.titulo); setEditando(false); } }}
              className="min-w-0 flex-1 rounded-lg border border-nexus-yellow bg-slate-950 px-2 py-1 text-sm font-semibold text-white focus:outline-none" />
            <button type="button" onClick={confirmar} aria-label="Salvar" className="rounded-lg p-1.5 text-emerald-300 hover:bg-slate-800"><Check size={16} /></button>
            <button type="button" onClick={() => { setTitulo(c.titulo); setEditando(false); }} aria-label="Cancelar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800"><X size={16} /></button>
          </span>
        ) : (
          <button type="button" onDoubleClick={() => setEditando(true)} onClick={p.onAlternar} className="min-w-0 flex-1 text-left">
            <span className="block truncate font-semibold text-white">{c.titulo}</span>
            <span className="text-[11px] text-slate-500">
              {c.aulas.length} aula(s){duracao ? ` · ${formatarDuracao(duracao)}` : ''}
            </span>
          </button>
        )}
        {!c.publicado && <span className="hidden rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-400 sm:inline">Oculto</span>}
        <div className="flex items-center">
          <button type="button" onClick={() => setEditando(true)} aria-label="Renomear" title="Renomear"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"><Pencil size={14} /></button>
          <button type="button" onClick={p.onPublicar} aria-label={c.publicado ? 'Ocultar' : 'Publicar'} title={c.publicado ? 'Ocultar do aluno' : 'Publicar'}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">{c.publicado ? <Eye size={14} /> : <EyeOff size={14} />}</button>
          <button type="button" onClick={p.onDuplicar} aria-label="Duplicar" title="Duplicar"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"><Copy size={14} /></button>
          <button type="button" onClick={p.onExcluir} aria-label="Excluir" title="Excluir"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-red-500/10 hover:text-red-300"><Trash2 size={14} /></button>
        </div>
      </div>

      {p.aberto && (
        <div className="space-y-2 border-t border-slate-800 px-3 py-3 sm:px-4">
          <SortableContext items={c.aulas.map((a) => idAula(a.id))} strategy={verticalListSortingStrategy}>
            <ul ref={setVazioRef} className={`min-h-[8px] space-y-2 rounded-xl ${isOver && !c.aulas.length ? 'bg-nexus-yellow/5 outline-dashed outline-1 outline-nexus-yellow/40' : ''}`}>
              {c.aulas.map((a, i) => (
                <LinhaAula key={a.id} aula={a} numero={i + 1} onAbrir={() => p.onAbrirAula(a)} onExcluir={() => p.onExcluirAula(a)} />
              ))}
            </ul>
          </SortableContext>
          {!c.aulas.length && <p className="py-2 text-center text-xs text-slate-500">Nenhuma aula. Arraste uma aula para cá ou crie uma nova.</p>}
          <button type="button" onClick={p.onNovaAula}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-slate-700 py-2 text-xs font-semibold text-slate-300 hover:border-nexus-yellow/60 hover:text-white">
            <Plus size={14} /> Nova aula
          </button>
        </div>
      )}
    </li>
  );
};

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

export interface AcoesEstrutura {
  onReordenar: (capitulos: Capitulo[], payload: ReordenarPayload) => Promise<void>;
  onRenomearCapitulo: (c: Capitulo, titulo: string) => void;
  onPublicarCapitulo: (c: Capitulo) => void;
  onDuplicarCapitulo: (c: Capitulo) => void;
  onExcluirCapitulo: (c: Capitulo) => void;
  onNovaAula: (c: Capitulo) => void;
  onAbrirAula: (c: Capitulo, a: Aula) => void;
  onExcluirAula: (a: Aula) => void;
}

interface Props extends AcoesEstrutura {
  capitulos: Capitulo[];
  setCapitulos: React.Dispatch<React.SetStateAction<Capitulo[]>>;
}

export const EstruturaEditor: React.FC<Props> = ({ capitulos, setCapitulos, ...acoes }) => {
  const [fechados, setFechados] = useState<Set<string>>(new Set());
  const inicio = useRef<Capitulo[] | null>(null);
  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const capDe = (lista: Capitulo[], id: string) => {
    if (id.startsWith('c:') || id.startsWith('d:')) return semPrefixo(id);
    const aula = semPrefixo(id);
    return lista.find((c) => c.aulas.some((a) => a.id === aula))?.id;
  };

  const aoIniciar = (_: DragStartEvent) => {
    inicio.current = capitulos;
  };

  /** Move a aula para outro capítulo enquanto arrasta (pré-visualização ao vivo). */
  const aoPassar = ({ active, over }: DragOverEvent) => {
    if (!over || !String(active.id).startsWith('a:')) return;
    const ativo = String(active.id);
    const alvo = String(over.id);
    setCapitulos((lista) => {
      const origem = capDe(lista, ativo);
      const destino = capDe(lista, alvo);
      if (!origem || !destino || origem === destino) return lista;
      const aulaId = semPrefixo(ativo);
      const aula = lista.find((c) => c.id === origem)!.aulas.find((a) => a.id === aulaId)!;
      return lista.map((c) => {
        if (c.id === origem) return { ...c, aulas: c.aulas.filter((a) => a.id !== aulaId) };
        if (c.id === destino) {
          const idx = alvo.startsWith('a:') ? c.aulas.findIndex((a) => a.id === semPrefixo(alvo)) : c.aulas.length;
          const aulas = [...c.aulas];
          aulas.splice(idx < 0 ? aulas.length : idx, 0, { ...aula, capitulo_id: destino });
          return { ...c, aulas };
        }
        return c;
      });
    });
  };

  const aoSoltar = ({ active, over }: DragEndEvent) => {
    const antes = inicio.current ?? capitulos;
    inicio.current = null;
    if (!over) {
      setCapitulos(antes);
      return;
    }
    const ativo = String(active.id);
    const alvo = String(over.id);
    let nova = capitulos;
    let payload: ReordenarPayload;

    if (ativo.startsWith('c:')) {
      const de = capitulos.findIndex((c) => c.id === semPrefixo(ativo));
      const para = capitulos.findIndex((c) => c.id === capDe(capitulos, alvo));
      if (de < 0 || para < 0 || de === para) return;
      nova = arrayMove(capitulos, de, para).map((c, ordem) => ({ ...c, ordem }));
      payload = { capitulos: nova.map((c) => ({ id: c.id, ordem: c.ordem })) };
    } else {
      const capId = capDe(capitulos, ativo);
      const cap = capitulos.find((c) => c.id === capId);
      if (!cap) return;
      if (alvo.startsWith('a:') && capDe(capitulos, alvo) === capId) {
        const de = cap.aulas.findIndex((a) => a.id === semPrefixo(ativo));
        const para = cap.aulas.findIndex((a) => a.id === semPrefixo(alvo));
        if (de !== para && de >= 0 && para >= 0) {
          nova = capitulos.map((c) => (c.id === capId ? { ...c, aulas: arrayMove(c.aulas, de, para) } : c));
        }
      }
      nova = nova.map((c) => ({ ...c, aulas: c.aulas.map((a, ordem) => ({ ...a, ordem, capitulo_id: c.id })) }));
      const mudou = (a: Aula) => {
        const original = antes.flatMap((c) => c.aulas).find((x) => x.id === a.id);
        return !original || original.ordem !== a.ordem || original.capitulo_id !== a.capitulo_id;
      };
      const aulas = nova.flatMap((c) => c.aulas).filter(mudou);
      if (!aulas.length) {
        setCapitulos(nova);
        return;
      }
      payload = { aulas: aulas.map((a) => ({ id: a.id, ordem: a.ordem, capitulo_id: a.capitulo_id })) };
    }
    setCapitulos(nova);
    acoes.onReordenar(antes, payload).catch(() => undefined);
  };

  const alternar = (id: string) =>
    setFechados((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <DndContext sensors={sensores} collisionDetection={closestCorners} onDragStart={aoIniciar} onDragOver={aoPassar}
      onDragEnd={aoSoltar} onDragCancel={() => { if (inicio.current) setCapitulos(inicio.current); inicio.current = null; }}>
      <SortableContext items={capitulos.map((c) => idCap(c.id))} strategy={verticalListSortingStrategy}>
        <ul className="space-y-4">
          {capitulos.map((c, i) => (
            <CapituloCard key={c.id} capitulo={c} numero={i + 1} aberto={!fechados.has(c.id)} onAlternar={() => alternar(c.id)}
              onRenomear={(t) => acoes.onRenomearCapitulo(c, t)} onPublicar={() => acoes.onPublicarCapitulo(c)}
              onDuplicar={() => acoes.onDuplicarCapitulo(c)} onExcluir={() => acoes.onExcluirCapitulo(c)}
              onNovaAula={() => acoes.onNovaAula(c)} onAbrirAula={(a) => acoes.onAbrirAula(c, a)}
              onExcluirAula={acoes.onExcluirAula} />
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
};
