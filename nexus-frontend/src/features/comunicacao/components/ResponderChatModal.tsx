import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, MessageCircle, Send, X } from 'lucide-react';
import { Avatar } from '@/features/chat/components/Avatar';
import { Post, feedApi, mensagemErro } from '../api';

const trecho = (html: string) => {
  const div = document.createElement('div');
  div.innerHTML = html;
  const t = (div.textContent || '').trim();
  return t.length > 180 ? `${t.slice(0, 179)}…` : t;
};

/** Responde ao autor do post em uma conversa individual do chat (a mensagem leva o cartão do post). */
export const ResponderChatModal: React.FC<{ post: Post; onFechar: () => void }> = ({ post, onFechar }) => {
  const navigate = useNavigate();
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const enviar = async () => {
    if (!texto.trim()) return;
    setEnviando(true);
    setErro(null);
    try {
      const { conversa_id } = await feedApi.responderChat(post.id, texto.trim());
      navigate(`/chat?c=${conversa_id}`);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível enviar a mensagem.'));
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4" onMouseDown={onFechar}>
      <div className="w-full max-w-lg overflow-hidden rounded-t-2xl border border-slate-700 bg-slate-900 shadow-2xl sm:rounded-2xl"
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <h3 className="flex items-center gap-2 font-semibold text-white">
            <MessageCircle size={18} className="text-nexus-yellow" /> Responder via chat
          </h3>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="space-y-4 p-5">
          <div className="flex gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <Avatar nome={post.autor.nome} usuarioId={post.autor.id} fotoUrl={post.autor.foto_url} tamanho="sm" />
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-200">{post.autor.nome}</p>
              <p className="line-clamp-3 text-xs text-slate-400">{trecho(post.conteudo_html) || 'Publicação com mídia'}</p>
            </div>
          </div>
          <textarea
            autoFocus
            value={texto}
            maxLength={4000}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void enviar(); }}
            rows={4}
            placeholder={`Escreva sua mensagem para ${post.autor.nome.split(' ')[0]}…`}
            className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none"
          />
          {erro && <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">{erro}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onFechar} className="rounded-xl px-4 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancelar</button>
            <button type="button" onClick={() => void enviar()} disabled={enviando || !texto.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
              {enviando ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />} Enviar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
