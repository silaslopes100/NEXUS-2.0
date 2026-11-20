import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react';
import { Post, feedApi, mensagemErro } from '../api';
import { FeedPostCard } from '../components/FeedPostCard';

/** Uma publicação com todos os comentários (destino dos links das notificações e do "Copiar link"). */
export const FeedPostPage: React.FC = () => {
  const { postId = '' } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState<Post | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    setPost(null);
    setErro(null);
    feedApi.obter(postId).then(setPost).catch((e) => setErro(mensagemErro(e, 'Publicação não encontrada.')));
  }, [postId]);

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Link to="/feed" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white">
        <ArrowLeft size={16} /> Voltar ao feed
      </Link>
      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}
      {!post && !erro && <div className="flex justify-center py-16 text-nexus-yellow"><Loader2 className="animate-spin" /></div>}
      {post && (
        <FeedPostCard key={post.id} post={post} detalhe onAtualizado={setPost} onExcluido={() => navigate('/feed')} />
      )}
    </div>
  );
};
