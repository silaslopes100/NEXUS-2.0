import React, { useMemo } from 'react';
import DOMPurify from 'dompurify';

// Links do conteúdo sempre em nova aba e sem acesso à janela de origem.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer nofollow');
  }
});

const OPCOES = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'a', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2',
    'h3', 'h4', 'hr', 'span', 'mark'],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'style', 'data-color'],
  ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|\/)/i,
};

/** Renderiza o HTML do editor rico (já sanitizado no backend; DOMPurify como defesa extra). */
export const ConteudoHtml: React.FC<{ html: string; className?: string }> = ({ html, className = '' }) => {
  const limpo = useMemo(() => DOMPurify.sanitize(html || '', OPCOES), [html]);
  if (!limpo) return null;
  return <div className={`conteudo-rico break-words text-sm text-slate-200 ${className}`} dangerouslySetInnerHTML={{ __html: limpo }} />;
};
