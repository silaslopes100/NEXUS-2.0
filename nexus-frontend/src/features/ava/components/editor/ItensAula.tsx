import React, { useRef, useState } from 'react';
import {
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  FileText,
  GripVertical,
  Image as ImageIcon,
  Link2,
  Loader2,
  Pencil,
  Plus,
  Trash2,
  Type,
  UploadCloud,
  Video,
} from 'lucide-react';
import { ArquivoEnviado, urlArquivo } from '@/lib/uploadDireto';
import { mensagemErro } from '@/features/comunicacao/api';
import { tamanhoLegivel } from '@/features/chat/utils';
import { EditorRico } from '@/features/comunicacao/components/editor/EditorRico';
import {
  ACEITA_DOCUMENTOS,
  ACEITA_IMAGENS,
  EmbedResolvido,
  ItemAula,
  ItemPayload,
  ROTULO_ITEM,
  ROTULO_PROVEDOR,
  TipoItem,
  avaAdminApi,
} from '../../api';
import { botaoPrimario, botaoSecundario, campo, rotulo } from './estilos';

const ICONE: Record<TipoItem, React.ElementType> = {
  video_embed: Video,
  arquivo: FileText,
  imagem: ImageIcon,
  link: Link2,
  texto: Type,
};

const NOVOS: TipoItem[] = ['video_embed', 'arquivo', 'imagem', 'link', 'texto'];

// ---------------------------------------------------------------------------
// Formulário de um item
// ---------------------------------------------------------------------------

interface FormProps {
  aulaId: string;
  tipo: TipoItem;
  item?: ItemAula;
  onSalvo: (item: ItemAula) => void;
  onCancelar: () => void;
}

const ItemForm: React.FC<FormProps> = ({ aulaId, tipo, item, onSalvo, onCancelar }) => {
  const [titulo, setTitulo] = useState(item?.titulo ?? '');
  const [url, setUrl] = useState(item?.tipo === 'link' ? item.url ?? '' : '');
  const [html, setHtml] = useState(item?.conteudo_html ?? '');
  const [permiteDownload, setPermiteDownload] = useState(item?.permite_download ?? true);
  const [embed, setEmbed] = useState<EmbedResolvido | null>(
    item?.tipo === 'video_embed' && item.url
      ? { url: item.url, embed_url: item.url, provedor: item.provedor ?? 'iframe', embed_id: item.embed_id }
      : null,
  );
  const [linkVideo, setLinkVideo] = useState(item?.tipo === 'video_embed' ? item.url ?? '' : '');
  const [arquivo, setArquivo] = useState<ArquivoEnviado | null>(null);
  const [progresso, setProgresso] = useState<number | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const inputArquivo = useRef<HTMLInputElement>(null);

  const verificarVideo = async () => {
    setErro(null);
    try {
      setEmbed(await avaAdminApi.resolverEmbed(linkVideo));
    } catch (e) {
      setEmbed(null);
      setErro(mensagemErro(e, 'Link de vídeo inválido.'));
    }
  };

  const enviar = async (f: File) => {
    setErro(null);
    setProgresso(0);
    try {
      const enviado = await avaAdminApi.enviarArquivo(f, setProgresso);
      setArquivo(enviado);
      if (!titulo) setTitulo(f.name.replace(/\.[^.]+$/, ''));
    } catch (e) {
      setErro(mensagemErro(e, 'Falha no envio do arquivo.'));
    } finally {
      setProgresso(null);
    }
  };

  const salvar = async () => {
    setSalvando(true);
    setErro(null);
    const payload: ItemPayload = {
      tipo,
      titulo: titulo.trim() || null,
      permite_download: permiteDownload,
      url: tipo === 'video_embed' ? embed?.url ?? linkVideo : tipo === 'link' ? url : null,
      conteudo_html: tipo === 'texto' ? html : null,
      arquivo,
    };
    try {
      onSalvo(item ? await avaAdminApi.atualizarItem(item.id, payload) : await avaAdminApi.criarItem(aulaId, payload));
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const ehArquivo = tipo === 'arquivo' || tipo === 'imagem';
  const Icone = ICONE[tipo];

  return (
    <div className="space-y-3 rounded-2xl border border-nexus-yellow/40 bg-slate-950/70 p-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-white">
        <Icone size={16} className="text-nexus-yellow" /> {item ? 'Editar' : 'Adicionar'} {ROTULO_ITEM[tipo].toLowerCase()}
      </p>

      {tipo === 'video_embed' && (
        <div className="space-y-3">
          <div>
            <span className={rotulo}>Link do vídeo</span>
            <div className="flex gap-2">
              <input value={linkVideo} onChange={(e) => { setLinkVideo(e.target.value); setEmbed(null); }}
                onBlur={() => linkVideo && !embed && void verificarVideo()}
                placeholder="https://youtu.be/… · vimeo.com/… · Panda Video" className={campo} />
              <button type="button" onClick={() => void verificarVideo()} disabled={!linkVideo} className={botaoSecundario}>
                Verificar
              </button>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              YouTube (de preferência “não listado”), Vimeo, Panda Video ou qualquer player https incorporável.
            </p>
          </div>
          {embed && (
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="aspect-video bg-black">
                <iframe src={embed.embed_url} title="Prévia do vídeo" className="h-full w-full" allowFullScreen
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" />
              </div>
              <p className="px-3 py-2 text-[11px] text-slate-400">{ROTULO_PROVEDOR[embed.provedor]}</p>
            </div>
          )}
        </div>
      )}

      {tipo === 'link' && (
        <label className="block">
          <span className={rotulo}>Endereço</span>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" className={campo} />
        </label>
      )}

      {ehArquivo && (
        <div>
          <input ref={inputArquivo} type="file" hidden accept={tipo === 'imagem' ? ACEITA_IMAGENS : `${ACEITA_DOCUMENTOS},${ACEITA_IMAGENS}`}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void enviar(f); e.target.value = ''; }} />
          <button type="button" onClick={() => inputArquivo.current?.click()} disabled={progresso !== null}
            className="flex w-full flex-col items-center gap-2 rounded-xl border-2 border-dashed border-slate-700 p-5 text-sm text-slate-300 hover:border-nexus-yellow/60 hover:bg-slate-900">
            {progresso !== null ? (
              <>
                <Loader2 className="animate-spin text-nexus-yellow" />
                Enviando… {Math.round(progresso)}%
                <span className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                  <span className="block h-full bg-nexus-yellow transition-all" style={{ width: `${progresso}%` }} />
                </span>
              </>
            ) : arquivo ? (
              <>
                {tipo === 'imagem' ? <img src={urlArquivo(arquivo.url)} alt="" className="max-h-40 rounded-lg" /> : <FileText className="text-nexus-yellow" />}
                <span className="font-semibold text-white">{arquivo.nome}</span>
                <span className="text-xs text-slate-500">{tamanhoLegivel(arquivo.tamanho)} · clique para trocar</span>
              </>
            ) : item?.arquivo_nome ? (
              <>
                <FileText className="text-nexus-yellow" />
                <span className="font-semibold text-white">{item.arquivo_nome}</span>
                <span className="text-xs text-slate-500">clique para trocar o arquivo</span>
              </>
            ) : (
              <>
                <UploadCloud className="text-nexus-yellow" />
                <span>{tipo === 'imagem' ? 'Enviar imagem (JPG, PNG, WEBP · até 10 MB)' : 'Enviar arquivo (PDF, PPT, DOC, XLS, imagem · até 50 MB)'}</span>
              </>
            )}
          </button>
          {tipo === 'arquivo' && (
            <label className="mt-2 flex items-center gap-2 text-xs text-slate-300">
              <input type="checkbox" checked={permiteDownload} onChange={(e) => setPermiteDownload(e.target.checked)} />
              Permitir que o aluno baixe o arquivo
            </label>
          )}
        </div>
      )}

      {tipo === 'texto' && (
        <EditorRico valor={html} onChange={setHtml} variante="aviso" alturaMinima="min-h-[160px]" placeholder="Escreva o conteúdo…" />
      )}

      <label className="block">
        <span className={rotulo}>Título {tipo === 'texto' || tipo === 'video_embed' ? '(opcional)' : ''}</span>
        <input value={titulo} maxLength={255} onChange={(e) => setTitulo(e.target.value)} className={campo}
          placeholder={tipo === 'arquivo' ? 'Ex.: Slides da aula' : 'Ex.: Introdução'} />
      </label>

      {erro && <p className="text-xs text-red-300">{erro}</p>}

      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancelar} className={botaoSecundario}>Cancelar</button>
        <button type="button" onClick={() => void salvar()} disabled={salvando || progresso !== null} className={botaoPrimario}>
          {salvando && <Loader2 size={14} className="animate-spin" />} Salvar
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Linha ordenável
// ---------------------------------------------------------------------------

const LinhaItem: React.FC<{ item: ItemAula; onEditar: () => void; onExcluir: () => void }> = ({ item, onEditar, onExcluir }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const Icone = ICONE[item.tipo];
  const detalhe =
    item.tipo === 'video_embed' ? ROTULO_PROVEDOR[item.provedor ?? 'iframe']
      : item.tipo === 'link' ? item.url
        : item.arquivo_tamanho ? `${item.arquivo_nome} · ${tamanhoLegivel(item.arquivo_tamanho)}`
          : ROTULO_ITEM[item.tipo];
  return (
    <li ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2.5 ${isDragging ? 'z-10 opacity-70 shadow-xl' : ''}`}>
      <button type="button" {...attributes} {...listeners} aria-label="Arrastar"
        className="cursor-grab touch-none text-slate-600 hover:text-slate-300 active:cursor-grabbing">
        <GripVertical size={16} />
      </button>
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-nexus-yellow">
        <Icone size={16} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-slate-100">{item.titulo || ROTULO_ITEM[item.tipo]}</span>
        <span className="block truncate text-[11px] text-slate-500">{detalhe}</span>
      </span>
      <button type="button" onClick={onEditar} aria-label="Editar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
        <Pencil size={14} />
      </button>
      <button type="button" onClick={onExcluir} aria-label="Excluir" className="rounded-lg p-1.5 text-slate-400 hover:bg-red-500/10 hover:text-red-300">
        <Trash2 size={14} />
      </button>
    </li>
  );
};

// ---------------------------------------------------------------------------
// Lista de itens da aula
// ---------------------------------------------------------------------------

interface Props {
  disciplinaId: string;
  aulaId: string;
  itens: ItemAula[];
  onChange: (itens: ItemAula[]) => void;
}

export const ItensAula: React.FC<Props> = ({ disciplinaId, aulaId, itens, onChange }) => {
  const [form, setForm] = useState<{ tipo: TipoItem; item?: ItemAula } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const aoSoltar = async ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const antes = itens;
    const nova = arrayMove(itens, itens.findIndex((i) => i.id === active.id), itens.findIndex((i) => i.id === over.id))
      .map((i, ordem) => ({ ...i, ordem }));
    onChange(nova);
    try {
      await avaAdminApi.reordenar(disciplinaId, { itens: nova.map((i) => ({ id: i.id, ordem: i.ordem })) });
    } catch (e) {
      onChange(antes);
      setErro(mensagemErro(e, 'Não foi possível salvar a nova ordem.'));
    }
  };

  const excluir = async (item: ItemAula) => {
    if (!window.confirm(`Excluir "${item.titulo || ROTULO_ITEM[item.tipo]}"?`)) return;
    try {
      await avaAdminApi.excluirItem(item.id);
      onChange(itens.filter((i) => i.id !== item.id));
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  const salvo = (novo: ItemAula) => {
    onChange(itens.some((i) => i.id === novo.id) ? itens.map((i) => (i.id === novo.id ? novo : i)) : [...itens, novo]);
    setForm(null);
  };

  return (
    <div className="space-y-3">
      {itens.length === 0 && !form && (
        <p className="rounded-xl border border-dashed border-slate-700 p-4 text-center text-xs text-slate-500">
          Nenhum conteúdo ainda. Adicione vídeos, materiais e textos abaixo.
        </p>
      )}

      <DndContext sensors={sensores} collisionDetection={closestCenter} onDragEnd={(e) => void aoSoltar(e)}>
        <SortableContext items={itens.map((i) => i.id)} strategy={verticalListSortingStrategy}>
          <ul className="space-y-2">
            {itens.map((item) =>
              form?.item?.id === item.id ? (
                <li key={item.id}>
                  <ItemForm aulaId={aulaId} tipo={item.tipo} item={item} onSalvo={salvo} onCancelar={() => setForm(null)} />
                </li>
              ) : (
                <LinhaItem key={item.id} item={item} onEditar={() => setForm({ tipo: item.tipo, item })} onExcluir={() => void excluir(item)} />
              ),
            )}
          </ul>
        </SortableContext>
      </DndContext>

      {form && !form.item && (
        <ItemForm aulaId={aulaId} tipo={form.tipo} onSalvo={salvo} onCancelar={() => setForm(null)} />
      )}

      {erro && <p className="text-xs text-red-300">{erro}</p>}

      {!form && (
        <div className="flex flex-wrap gap-2">
          {NOVOS.map((tipo) => {
            const Icone = ICONE[tipo];
            return (
              <button key={tipo} type="button" onClick={() => setForm({ tipo })}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-nexus-yellow/60 hover:text-white">
                <Plus size={12} /> <Icone size={14} className="text-nexus-yellow" /> {ROTULO_ITEM[tipo]}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
