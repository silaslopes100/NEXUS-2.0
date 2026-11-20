import { Extension } from '@tiptap/react';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    tamanhoFonte: {
      setFontSize: (tamanho: string) => ReturnType;
      unsetFontSize: () => ReturnType;
    };
  }
}

/** Tamanho do texto como atributo do mark `textStyle` (gera `<span style="font-size: 18px">`). */
export const TamanhoFonte = Extension.create({
  name: 'tamanhoFonte',

  addGlobalAttributes() {
    return [
      {
        types: ['textStyle'],
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (el) => (el as HTMLElement).style.fontSize || null,
            renderHTML: (attrs) => (attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {}),
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      setFontSize:
        (tamanho) =>
        ({ chain }) =>
          chain().setMark('textStyle', { fontSize: tamanho }).run(),
      unsetFontSize:
        () =>
        ({ chain }) =>
          chain().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run(),
    };
  },
});
