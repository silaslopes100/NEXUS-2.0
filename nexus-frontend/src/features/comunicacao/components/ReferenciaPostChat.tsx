import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Newspaper } from 'lucide-react';
import { urlArquivo } from '@/lib/uploadDireto';
import { Post, feedApi } from '../api';

const cache = new Map<string, Promise<Post | null>>();

const carregar = (id: string) => {
  if (!cache.has(id)) cache.set(id, feedApi.obter(id).catch(() => null));
  return cache.get(id)!;
};

const trecho = (html: string) => {
  const div = document.createElement('div');
  div.innerHTML = html;
  return (div.textContent || '').trim();
};

/** Cartão do post do feed ao qual a mensagem do chat responde. */
export const ReferenciaPostChat: React.FC<{ postId: string; minha: boolean }> = ({ postId, minha }) => {
  const [post, setPost] = useState<Post | null | undefined>(undefined);
  useEffect(() => {
    let vivo = true;
    carregar(postId).then((p) => vivo && setPost(p));
    return () => {
      vivo = false;
    };
  }, [postId]);

  const capa = post?.midias.find((m) => m.tipo === 'imagem')?.url ?? post?.links[0]?.imagem_url;
  const borda = minha ? 'border-slate-900/20 bg-black/10 hover:bg-black/15' : 'border-white/10 bg-black/20 hover:bg-black/30';

  return (
    <Link to={`/feed/${postId}`} className={`mb-1.5 flex gap-2 rounded-lg border p-2 ${borda}`}>
      {capa ? (
        <img src={urlArquivo(capa)} alt="" className="h-12 w-12 shrink-0 rounded-md object-cover" />
      ) : (
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-black/20"><Newspaper size={18} /></span>
      )}
      <span className="min-w-0 text-xs">
        <span className="block font-semibold opacity-80">Em resposta à publicação{post ? ` de ${post.autor.nome}` : ''}</span>
        <span className="line-clamp-2 opacity-70">
          {post === undefined ? 'Carregando…' : post === null ? 'Publicação indisponível' : trecho(post.conteudo_html) || 'Publicação com mídia'}
        </span>
      </span>
    </Link>
  );
};
