import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Clock3,
  Copy,
  Globe2,
  Lock,
  MessageCircle,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Pin,
  PinOff,
  Send,
  Share2,
  ThumbsUp,
  Trash2,
  X,
} from 'lucide-react';
import { Avatar } from '@/features/chat/components/Avatar';
import { rotuloPerfil } from '@/features/chat/utils';
import { Autor, Post, feedApi, mensagemErro, rotuloPerfis, tempoRelativo } from '../api';
import { usePerfilAtual } from '../usePerfilAtual';
import { ConteudoHtml } from './ConteudoHtml';
import { GaleriaMidias } from './GaleriaMidias';
import { CartaoLink } from './CartaoLink';
import { ComentariosSecao } from './ComentariosSecao';
import { FeedCompositor } from './FeedCompositor';
import { ResponderChatModal } from './ResponderChatModal';

const useFecharAoClicarFora = (aberto: boolean, fechar: () => void) => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!aberto) return undefined;
    const fn = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && fechar();
    document.addEventListener('mousedown', fn);
    return () => document.removeEventListener('mousedown', fn);
  }, [aberto, fechar]);
  return ref;
};

const CurtidasModal: React.FC<{ postId: string; onFechar: () => void }> = ({ postId, onFechar }) => {
  const [lista, setLista] = useState<Autor[] | null>(null);
  useEffect(() => {
    feedApi.curtidas(postId).then(setLista).catch(() => setLista([]));
  }, [postId]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onMouseDown={onFechar}>
      <div className="max-h-[70vh] w-full max-w-sm overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold text-white">Curtidas</h3>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="text-slate-400 hover:text-white"><X size={16} /></button>
        </div>
        <ul className="max-h-[55vh] space-y-2 overflow-y-auto p-4">
          {lista === null && <li className="text-xs text-slate-400">Carregando…</li>}
          {lista?.length === 0 && <li className="text-xs text-slate-400">Ninguém curtiu ainda.</li>}
          {lista?.map((u) => (
            <li key={u.id} className="flex items-center gap-2">
              <Avatar nome={u.nome} usuarioId={u.id} fotoUrl={u.foto_url} tamanho="sm" />
              <div>
                <p className="text-sm text-slate-100">{u.nome}</p>
                <p className="text-[11px] text-slate-500">{rotuloPerfil(u.perfil)}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

interface Props {
  post: Post;
  onAtualizado: (post: Post) => void;
  onExcluido: (id: string) => void;
  /** Página do post: comentários completos abertos. */
  detalhe?: boolean;
}

export const FeedPostCard: React.FC<Props> = ({ post, onAtualizado, onExcluido, detalhe }) => {
  const { userId, admin } = usePerfilAtual();
  const [editando, setEditando] = useState(false);
  const [menu, setMenu] = useState(false);
  const [compartilhar, setCompartilhar] = useState(false);
  const [responderChat, setResponderChat] = useState(false);
  const [verCurtidas, setVerCurtidas] = useState(false);
  const [comentariosAbertos, setComentariosAbertos] = useState(!!detalhe || post.comentarios_recentes.length > 0);
  const [focarComentario, setFocarComentario] = useState(false);
  const [expandido, setExpandido] = useState(!!detalhe);
  const [longo, setLongo] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const corpo = useRef<HTMLDivElement>(null);
  const refMenu = useFecharAoClicarFora(menu, () => setMenu(false));
  const refCompartilhar = useFecharAoClicarFora(compartilhar, () => setCompartilhar(false));
  const meu = post.autor.id === userId;

  useEffect(() => {
    if (corpo.current && !expandido) setLongo(corpo.current.scrollHeight > corpo.current.clientHeight + 4);
  }, [post.conteudo_html, expandido]);

  const curtir = async () => {
    const novo = !post.curtido_por_mim;
    onAtualizado({ ...post, curtido_por_mim: novo, total_curtidas: post.total_curtidas + (novo ? 1 : -1) });
    try {
      const r = await feedApi.curtir(post.id, novo);
      onAtualizado({ ...post, curtido_por_mim: r.curtido, total_curtidas: r.total_curtidas });
    } catch {
      onAtualizado(post);
    }
  };

  const excluir = async () => {
    setMenu(false);
    if (!window.confirm('Excluir esta publicação? Ela deixará de aparecer no feed.')) return;
    try {
      await feedApi.excluir(post.id);
      onExcluido(post.id);
    } catch (e) {
      window.alert(mensagemErro(e));
    }
  };

  const fixar = async () => {
    setMenu(false);
    try {
      onAtualizado(await feedApi.fixar(post.id));
    } catch (e) {
      window.alert(mensagemErro(e));
    }
  };

  const copiarLink = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/feed/${post.id}`);
      setCopiado(true);
      window.setTimeout(() => setCopiado(false), 1800);
    } catch {
      window.prompt('Copie o link:', `${window.location.origin}/feed/${post.id}`);
    }
    setCompartilhar(false);
  };

  if (editando) {
    return <FeedCompositor post={post} onSalvo={(p) => { onAtualizado(p); setEditando(false); }} onCancelar={() => setEditando(false)} />;
  }

  const restrito = !!(post.publico_perfis?.length || post.polo_id || post.escola_id);

  return (
    <article className={`overflow-hidden rounded-2xl border bg-slate-900/70 ${post.fixado ? 'border-nexus-yellow/40' : 'border-slate-800'}`}>
      {post.fixado && (
        <p className="flex items-center gap-1.5 border-b border-slate-800 bg-nexus-yellow/5 px-4 py-1.5 text-[11px] font-semibold text-nexus-yellow">
          <Pin size={12} /> Publicação fixada
        </p>
      )}
      <header className="flex items-start gap-3 px-4 pt-4">
        <Avatar nome={post.autor.nome} usuarioId={post.autor.id} fotoUrl={post.autor.foto_url} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white">{post.autor.nome}</p>
          <p className="text-xs text-slate-400">{rotuloPerfil(post.autor.perfil)}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-1 text-[11px] text-slate-500">
            <Link to={`/feed/${post.id}`} className="hover:underline">{tempoRelativo(post.criado_em)}</Link>
            {post.editado && <span>· editado</span>}
            <span>·</span>
            <span className="inline-flex items-center gap-1" title={restrito ? 'Público restrito' : 'Visível para todos'}>
              {restrito ? <Lock size={11} /> : <Globe2 size={11} />}
              {restrito
                ? [post.publico_perfis?.length ? rotuloPerfis(post.publico_perfis) : null, post.escola_nome || post.polo_nome]
                    .filter(Boolean).join(' · ')
                : 'Todos'}
            </span>
          </p>
        </div>
        {(post.pode_editar || admin) && (
          <div className="relative" ref={refMenu}>
            <button type="button" aria-label="Opções" onClick={() => setMenu((v) => !v)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
              <MoreHorizontal size={18} />
            </button>
            {menu && (
              <div className="absolute right-0 top-9 z-20 w-48 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 py-1 shadow-xl">
                {post.pode_editar && (
                  <button type="button" onClick={() => { setMenu(false); setEditando(true); }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800">
                    <Pencil size={14} /> Editar
                  </button>
                )}
                {admin && (
                  <button type="button" onClick={() => void fixar()}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800">
                    {post.fixado ? <PinOff size={14} /> : <Pin size={14} />} {post.fixado ? 'Desafixar' : 'Fixar no topo'}
                  </button>
                )}
                {post.pode_editar && (
                  <button type="button" onClick={() => void excluir()}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-300 hover:bg-slate-800">
                    <Trash2 size={14} /> Excluir
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </header>

      {post.conteudo_html && (
        <div className="px-4 pt-3">
          <div ref={corpo} className={expandido ? '' : 'max-h-[9.5rem] overflow-hidden'}>
            <ConteudoHtml html={post.conteudo_html} />
          </div>
          {!expandido && longo && (
            <button type="button" onClick={() => setExpandido(true)} className="mt-1 text-xs font-semibold text-slate-400 hover:text-slate-200">
              …ver mais
            </button>
          )}
        </div>
      )}

      {(post.midias.length > 0 || post.links.length > 0) && (
        <div className="space-y-2 px-4 pt-3">
          <GaleriaMidias midias={post.midias} />
          {post.links.map((l) => <CartaoLink key={l.url} link={l} />)}
        </div>
      )}

      <div className="flex items-center justify-between px-4 pb-1 pt-3 text-xs text-slate-400">
        <button type="button" onClick={() => post.total_curtidas > 0 && setVerCurtidas(true)}
          className={`inline-flex items-center gap-1 ${post.total_curtidas ? 'hover:text-blue-300 hover:underline' : 'cursor-default'}`}>
          {post.total_curtidas > 0 && (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-white"><ThumbsUp size={9} /></span>
          )}
          {post.total_curtidas > 0 ? post.total_curtidas : ''}
        </button>
        <div className="flex items-center gap-3">
          {post.pendentes > 0 && (
            <span className="inline-flex items-center gap-1 text-amber-300"><Clock3 size={12} /> {post.pendentes} para aprovar</span>
          )}
          {post.total_comentarios > 0 && (
            <button type="button" onClick={() => setComentariosAbertos((v) => !v)} className="hover:text-slate-200 hover:underline">
              {post.total_comentarios} {post.total_comentarios === 1 ? 'comentário' : 'comentários'}
            </button>
          )}
        </div>
      </div>

      <div className="mx-4 grid grid-cols-3 border-t border-slate-800 py-1">
        <button type="button" onClick={() => void curtir()} aria-pressed={post.curtido_por_mim}
          className={`inline-flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-colors hover:bg-slate-800 ${
            post.curtido_por_mim ? 'text-blue-400' : 'text-slate-300'}`}>
          <ThumbsUp size={17} fill={post.curtido_por_mim ? 'currentColor' : 'none'} /> Curtir
        </button>
        <button type="button" onClick={() => { setComentariosAbertos(true); setFocarComentario(true); }}
          className="inline-flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">
          <MessageSquare size={17} /> Comentar
        </button>
        <div className="relative" ref={refCompartilhar}>
          <button type="button" onClick={() => setCompartilhar((v) => !v)}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">
            {copiado ? <Copy size={17} className="text-emerald-400" /> : <Share2 size={17} />} {copiado ? 'Copiado!' : 'Compartilhar'}
          </button>
          {compartilhar && (
            <div className="absolute bottom-11 right-0 z-20 w-60 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 py-1 shadow-xl">
              {!meu && (
                <button type="button" onClick={() => { setCompartilhar(false); setResponderChat(true); }}
                  className="flex w-full items-start gap-2 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800">
                  <MessageCircle size={15} className="mt-0.5 text-nexus-yellow" />
                  <span>
                    Responder ao autor via chat
                    <span className="block text-[11px] text-slate-500">Mensagem direta para {post.autor.nome.split(' ')[0]}</span>
                  </span>
                </button>
              )}
              <button type="button" onClick={() => void copiarLink()}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800">
                <Send size={15} className="text-sky-400" /> Copiar link da publicação
              </button>
            </div>
          )}
        </div>
      </div>

      {comentariosAbertos && (
        <ComentariosSecao
          post={post}
          completo={detalhe}
          focarCampo={focarComentario}
          onTotal={(d) => onAtualizado({ ...post, total_comentarios: Math.max(0, post.total_comentarios + d) })}
        />
      )}

      {responderChat && <ResponderChatModal post={post} onFechar={() => setResponderChat(false)} />}
      {verCurtidas && <CurtidasModal postId={post.id} onFechar={() => setVerCurtidas(false)} />}
    </article>
  );
};
