import React, { useEffect } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextStyle from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import TextAlign from '@tiptap/extension-text-align';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import Highlight from '@tiptap/extension-highlight';
import { TamanhoFonte } from './extensaoTamanhoFonte';
import { BarraFerramentas } from './BarraFerramentas';

export type VarianteEditor = 'post' | 'aviso';

interface Props {
  valor: string;
  onChange: (html: string) => void;
  variante?: VarianteEditor;
  placeholder?: string;
  /** Classe de altura mínima da área de edição. */
  alturaMinima?: string;
  autoFocus?: boolean;
}

/**
 * Editor de texto rico (TipTap). `post`: formatação essencial do feed.
 * `aviso`: completo (cor, realce, tamanho, alinhamento/justificação, títulos, divisória).
 * O HTML gerado é sanitizado de novo no backend antes de gravar.
 */
export const EditorRico: React.FC<Props> = ({
  valor,
  onChange,
  variante = 'post',
  placeholder = 'Escreva aqui...',
  alturaMinima = 'min-h-[120px]',
  autoFocus,
}) => {
  const completo = variante === 'aviso';
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: completo ? [1, 2, 3, 4] : [2, 3] },
        code: false,
        codeBlock: false,
        horizontalRule: completo ? {} : false,
      }),
      Underline,
      TextStyle,
      Color,
      TamanhoFonte,
      Highlight.configure({ multicolor: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Link.configure({
        openOnClick: false,
        autolink: true,
        protocols: ['http', 'https', 'mailto'],
        HTMLAttributes: { target: '_blank', rel: 'noopener noreferrer nofollow' },
      }),
      Placeholder.configure({ placeholder }),
    ],
    content: valor || '',
    autofocus: autoFocus ? 'end' : false,
    editorProps: {
      attributes: {
        class: `conteudo-rico ProseMirror-nexus ${alturaMinima} px-3 py-2.5 text-sm text-slate-100 focus:outline-none`,
      },
    },
    onUpdate: ({ editor: e }) => onChange(e.isEmpty ? '' : e.getHTML()),
  });

  // Sincroniza quando o valor muda de fora (limpar após publicar, abrir para edição).
  useEffect(() => {
    if (!editor) return;
    const atual = editor.isEmpty ? '' : editor.getHTML();
    if ((valor || '') !== atual) editor.commands.setContent(valor || '', false);
  }, [valor, editor]);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950/60 focus-within:border-nexus-yellow/70">
      <BarraFerramentas editor={editor} variante={variante} />
      <EditorContent editor={editor} />
    </div>
  );
};
