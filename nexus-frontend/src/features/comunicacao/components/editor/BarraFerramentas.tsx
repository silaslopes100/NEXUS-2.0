import React, { useState } from 'react';
import type { Editor } from '@tiptap/react';
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  Bold,
  Heading1,
  Heading2,
  Heading3,
  Highlighter,
  Italic,
  Link2,
  List,
  ListOrdered,
  Minus,
  Palette,
  Quote,
  Redo2,
  RemoveFormatting,
  Strikethrough,
  Underline as UnderlineIcon,
  Undo2,
  Unlink,
} from 'lucide-react';
import type { VarianteEditor } from './EditorRico';

const CORES = ['#0f172a', '#475569', '#ffffff', '#dc2626', '#ea580c', '#ca8a04', '#16a34a', '#0891b2', '#2563eb',
  '#7c3aed', '#db2777', '#FFB800'];
const REALCES = ['#fde68a', '#bbf7d0', '#bfdbfe', '#fbcfe8', '#fecaca', '#e9d5ff'];
const TAMANHOS = ['12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px'];

interface BotaoProps {
  titulo: string;
  ativo?: boolean;
  desabilitado?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

const Botao: React.FC<BotaoProps> = ({ titulo, ativo, desabilitado, onClick, children }) => (
  <button
    type="button"
    title={titulo}
    aria-label={titulo}
    aria-pressed={ativo}
    disabled={desabilitado}
    onMouseDown={(e) => e.preventDefault()}
    onClick={onClick}
    className={`inline-flex h-8 w-8 items-center justify-center rounded-lg text-sm transition-colors disabled:opacity-30 ${
      ativo ? 'bg-nexus-yellow/20 text-nexus-yellow' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
    }`}
  >
    {children}
  </button>
);

const Separador = () => <span className="mx-1 h-5 w-px bg-slate-700" aria-hidden />;

const Paleta: React.FC<{
  titulo: string;
  icone: React.ReactNode;
  cores: string[];
  atual?: string | null;
  onEscolher: (cor: string | null) => void;
  permitirLivre?: boolean;
}> = ({ titulo, icone, cores, atual, onEscolher, permitirLivre }) => {
  const [aberta, setAberta] = useState(false);
  return (
    <div className="relative">
      <Botao titulo={titulo} ativo={aberta || !!atual} onClick={() => setAberta((v) => !v)}>
        <span className="relative">
          {icone}
          {atual && <span className="absolute -bottom-1 left-0 right-0 h-0.5 rounded" style={{ background: atual }} />}
        </span>
      </Botao>
      {aberta && (
        <div
          className="absolute left-0 top-9 z-20 w-48 max-w-[calc(100vw-2rem)] -translate-x-1/3 rounded-xl sm:translate-x-0 border border-slate-700 bg-slate-900 p-2 shadow-xl"
          onMouseLeave={() => setAberta(false)}
        >
          <div className="grid grid-cols-6 gap-1.5">
            {cores.map((c) => (
              <button
                key={c}
                type="button"
                title={c}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => { onEscolher(c); setAberta(false); }}
                className="h-6 w-6 rounded-md border border-slate-600"
                style={{ background: c }}
              />
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between gap-2">
            {permitirLivre && (
              <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <input
                  type="color"
                  className="h-6 w-8 cursor-pointer rounded border border-slate-600 bg-transparent"
                  onChange={(e) => onEscolher(e.target.value)}
                />
                Outra
              </label>
            )}
            <button
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => { onEscolher(null); setAberta(false); }}
              className="text-[11px] text-slate-400 hover:text-white"
            >
              Remover
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export const BarraFerramentas: React.FC<{ editor: Editor | null; variante: VarianteEditor }> = ({
  editor,
  variante,
}) => {
  if (!editor) return <div className="h-10 border-b border-slate-800" />;
  const completo = variante === 'aviso';
  const c = () => editor.chain().focus();

  const definirLink = () => {
    const anterior = editor.getAttributes('link').href as string | undefined;
    const url = window.prompt('Endereço do link (https://...)', anterior || 'https://');
    if (url === null) return;
    if (!url.trim() || url.trim() === 'https://') {
      c().extendMarkRange('link').unsetLink().run();
      return;
    }
    const href = /^(https?:|mailto:)/i.test(url.trim()) ? url.trim() : `https://${url.trim()}`;
    c().extendMarkRange('link').setLink({ href }).run();
  };

  const tamanhoAtual = (editor.getAttributes('textStyle').fontSize as string | undefined) || '';

  return (
    <div className="flex flex-wrap items-center gap-0.5 border-b border-slate-800 bg-slate-900/70 px-1.5 py-1">
      <Botao titulo="Negrito (Ctrl+B)" ativo={editor.isActive('bold')} onClick={() => c().toggleBold().run()}>
        <Bold size={15} />
      </Botao>
      <Botao titulo="Itálico (Ctrl+I)" ativo={editor.isActive('italic')} onClick={() => c().toggleItalic().run()}>
        <Italic size={15} />
      </Botao>
      <Botao titulo="Sublinhado (Ctrl+U)" ativo={editor.isActive('underline')} onClick={() => c().toggleUnderline().run()}>
        <UnderlineIcon size={15} />
      </Botao>
      <Botao titulo="Tachado" ativo={editor.isActive('strike')} onClick={() => c().toggleStrike().run()}>
        <Strikethrough size={15} />
      </Botao>

      <Separador />
      <Paleta
        titulo="Cor do texto"
        icone={<Palette size={15} />}
        cores={CORES}
        atual={editor.getAttributes('textStyle').color as string | undefined}
        onEscolher={(cor) => (cor ? c().setColor(cor).run() : c().unsetColor().run())}
        permitirLivre
      />
      {completo && (
        <>
          <Paleta
            titulo="Realce"
            icone={<Highlighter size={15} />}
            cores={REALCES}
            atual={editor.getAttributes('highlight').color as string | undefined}
            onEscolher={(cor) => (cor ? c().setHighlight({ color: cor }).run() : c().unsetHighlight().run())}
          />
          <select
            title="Tamanho do texto"
            aria-label="Tamanho do texto"
            value={tamanhoAtual}
            onChange={(e) => (e.target.value ? c().setFontSize(e.target.value).run() : c().unsetFontSize().run())}
            className="h-8 rounded-lg border border-slate-700 bg-slate-950 px-1.5 text-xs text-slate-200"
          >
            <option value="">Tamanho</option>
            {TAMANHOS.map((t) => (
              <option key={t} value={t}>{t.replace('px', '')}</option>
            ))}
          </select>
        </>
      )}

      <Separador />
      {completo && (
        <Botao titulo="Título 1" ativo={editor.isActive('heading', { level: 1 })} onClick={() => c().toggleHeading({ level: 1 }).run()}>
          <Heading1 size={15} />
        </Botao>
      )}
      <Botao titulo="Título" ativo={editor.isActive('heading', { level: 2 })} onClick={() => c().toggleHeading({ level: 2 }).run()}>
        <Heading2 size={15} />
      </Botao>
      <Botao titulo="Subtítulo" ativo={editor.isActive('heading', { level: 3 })} onClick={() => c().toggleHeading({ level: 3 }).run()}>
        <Heading3 size={15} />
      </Botao>
      <Botao titulo="Lista" ativo={editor.isActive('bulletList')} onClick={() => c().toggleBulletList().run()}>
        <List size={15} />
      </Botao>
      <Botao titulo="Lista numerada" ativo={editor.isActive('orderedList')} onClick={() => c().toggleOrderedList().run()}>
        <ListOrdered size={15} />
      </Botao>
      <Botao titulo="Citação" ativo={editor.isActive('blockquote')} onClick={() => c().toggleBlockquote().run()}>
        <Quote size={15} />
      </Botao>
      {completo && (
        <Botao titulo="Linha divisória" onClick={() => c().setHorizontalRule().run()}>
          <Minus size={15} />
        </Botao>
      )}

      <Separador />
      <Botao titulo="Alinhar à esquerda" ativo={editor.isActive({ textAlign: 'left' })} onClick={() => c().setTextAlign('left').run()}>
        <AlignLeft size={15} />
      </Botao>
      <Botao titulo="Centralizar" ativo={editor.isActive({ textAlign: 'center' })} onClick={() => c().setTextAlign('center').run()}>
        <AlignCenter size={15} />
      </Botao>
      <Botao titulo="Alinhar à direita" ativo={editor.isActive({ textAlign: 'right' })} onClick={() => c().setTextAlign('right').run()}>
        <AlignRight size={15} />
      </Botao>
      <Botao titulo="Justificar" ativo={editor.isActive({ textAlign: 'justify' })} onClick={() => c().setTextAlign('justify').run()}>
        <AlignJustify size={15} />
      </Botao>

      <Separador />
      <Botao titulo="Inserir link" ativo={editor.isActive('link')} onClick={definirLink}>
        <Link2 size={15} />
      </Botao>
      {editor.isActive('link') && (
        <Botao titulo="Remover link" onClick={() => c().unsetLink().run()}>
          <Unlink size={15} />
        </Botao>
      )}
      <Botao titulo="Limpar formatação" onClick={() => c().unsetAllMarks().clearNodes().run()}>
        <RemoveFormatting size={15} />
      </Botao>

      <span className="ml-auto flex">
        <Botao titulo="Desfazer" desabilitado={!editor.can().undo()} onClick={() => c().undo().run()}>
          <Undo2 size={15} />
        </Botao>
        <Botao titulo="Refazer" desabilitado={!editor.can().redo()} onClick={() => c().redo().run()}>
          <Redo2 size={15} />
        </Botao>
      </span>
    </div>
  );
};
