import React, { useMemo, useState } from 'react';
import { Check, Clock3, CornerDownRight, Loader2, Send, Trash2, X } from 'lucide-react';
import { Avatar } from '@/features/chat/components/Avatar';
import { rotuloPerfil } from '@/features/chat/utils';
import { Comentario, Post, atualizarContadoresMenu, feedApi, mensagemErro, tempoRelativo } from '../api';
import { usePerfilAtual } from '../usePerfilAtual';

const URL = /(https?:\/\/[^\s<>"']+)/g;

/** Texto puro com links clicáveis (comentários não aceitam HTML). */
const TextoComLinks: React.FC<{ texto: string }> = ({ texto }) => (
  <>
    {texto.split(URL).map((parte, i) =>
      i % 2 === 1 ? (
        <a key={i} href={parte} target="_blank" rel="noopener noreferrer nofollow" className="text-blue-400 underline">
          {parte}
        </a>
      ) : (
        <React.Fragment key={i}>{parte}</React.Fragment>
      ),
    )}
  </>
);

const CampoComentario: React.FC<{
  placeholder: string;
  autoFocus?: boolean;
  onEnviar: (texto: string) => Promise<void>;
  onCancelar?: () => void;
}> = ({ placeholder, autoFocus, onEnviar, onCancelar }) => {
  const { user, nome } = usePerfilAtual();
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const enviar = async () => {
    if (!texto.trim() || enviando) return;
    setEnviando(true);
    try {
      await onEnviar(texto.trim());
      setTexto('');
    } finally {
      setEnviando(false);
    }
  };
  return (
    <div className="flex items-start gap-2">
      <Avatar nome={nome} usuarioId={user?.id} fotoUrl={user?.foto_url} tamanho="sm" />
      <div className="flex flex-1 items-end gap-1 rounded-2xl border border-slate-700 bg-slate-950/60 px-3 py-1.5 focus-within:border-nexus-yellow/70">
        <textarea
          autoFocus={autoFocus}
          value={texto}
          maxLength={2000}
          rows={1}
          onChange={(e) => {
            setTexto(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void enviar();
            }
            if (e.key === 'Escape') onCancelar?.();
          }}
          placeholder={placeholder}
          className="max-h-40 flex-1 resize-none bg-transparent py-1 text-sm text-white placeholder-slate-500 focus:outline-none"
        />
        <button type="button" onClick={() => void enviar()} disabled={!texto.trim() || enviando} aria-label="Enviar comentário"
          className="mb-0.5 rounded-full p-1.5 text-nexus-yellow hover:bg-slate-800 disabled:opacity-40">
          {enviando ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
};

interface ItemProps {
  c: Comentario;
  onResponder?: () => void;
  onAtualizar: (c: Comentario | null) => void;
}

const ItemComentario: React.FC<ItemProps> = ({ c, onResponder, onAtualizar }) => {
  const [ocupado, setOcupado] = useState(false);
  const pendente = c.status === 'pendente';

  const acao = async (fn: () => Promise<unknown>, depois: Comentario | null) => {
    setOcupado(true);
    try {
      await fn();
      onAtualizar(depois);
      atualizarContadoresMenu();
    } catch (e) {
      window.alert(mensagemErro(e));
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="flex items-start gap-2">
      <Avatar nome={c.autor.nome} usuarioId={c.autor.id} fotoUrl={c.autor.foto_url} tamanho="sm" />
      <div className="min-w-0 flex-1">
        <div className={`rounded-2xl px-3 py-2 ${pendente ? 'border border-dashed border-amber-500/50 bg-amber-500/5' : 'bg-slate-800/70'}`}>
          <p className="flex flex-wrap items-center gap-x-2 text-xs">
            <span className="font-semibold text-slate-100">{c.autor.nome}</span>
            {c.autor.perfil && <span className="text-slate-500">{rotuloPerfil(c.autor.perfil)}</span>}
            {pendente && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                <Clock3 size={10} /> Aguardando aprovação
              </span>
            )}
          </p>
          <p className="mt-0.5 whitespace-pre-wrap break-words text-sm text-slate-200"><TextoComLinks texto={c.texto} /></p>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-3 px-2 text-[11px] text-slate-500">
          <span>{tempoRelativo(c.criado_em)}</span>
          {onResponder && <button type="button" onClick={onResponder} className="font-semibold hover:text-slate-200">Responder</button>}
          {pendente && c.pode_moderar && (
            <>
              <button type="button" disabled={ocupado} onClick={() => void acao(() => feedApi.aprovar(c.id), { ...c, status: 'aprovado' })}
                className="inline-flex items-center gap-1 font-semibold text-emerald-400 hover:text-emerald-300">
                <Check size={12} /> Aprovar
              </button>
              <button type="button" disabled={ocupado} onClick={() => void acao(() => feedApi.rejeitar(c.id), null)}
                className="inline-flex items-center gap-1 font-semibold text-red-400 hover:text-red-300">
                <X size={12} /> Rejeitar
              </button>
            </>
          )}
          {c.pode_excluir && (
            <button type="button" disabled={ocupado} aria-label="Excluir comentário"
              onClick={() => window.confirm('Excluir este comentário?') && void acao(() => feedApi.excluirComentario(c.id), null)}
              className="hover:text-red-400">
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

interface Props {
  post: Post;
  /** Já começa com a lista completa (página do post). */
  completo?: boolean;
  focarCampo?: boolean;
  onTotal: (delta: number) => void;
}

export const ComentariosSecao: React.FC<Props> = ({ post, completo, focarCampo, onTotal }) => {
  const [itens, setItens] = useState<Comentario[]>(post.comentarios_recentes);
  const [carregouTudo, setCarregouTudo] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [respondendo, setRespondendo] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = async (continuar = false) => {
    setCarregando(true);
    try {
      const pag = await feedApi.comentarios(post.id, continuar ? cursor : null);
      setItens((atuais) => (continuar ? [...atuais, ...pag.itens] : pag.itens));
      setCursor(pag.proximo_cursor ?? null);
      setCarregouTudo(true);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar os comentários.'));
    } finally {
      setCarregando(false);
    }
  };

  React.useEffect(() => {
    if (completo) void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completo, post.id]);

  const raiz = useMemo(() => itens.filter((c) => !c.parent_id), [itens]);
  const respostas = useMemo(() => {
    const mapa: Record<string, Comentario[]> = {};
    itens.filter((c) => c.parent_id).forEach((c) => (mapa[c.parent_id!] ||= []).push(c));
    return mapa;
  }, [itens]);

  const comentar = async (texto: string, parentId?: string) => {
    setErro(null);
    try {
      const novo = await feedApi.comentar(post.id, texto, parentId);
      setItens((atuais) => [...atuais, novo]);
      setRespondendo(null);
      onTotal(1);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível comentar.'));
      throw e;
    }
  };

  const atualizar = (id: string) => (c: Comentario | null) => {
    if (c) {
      setItens((atuais) => atuais.map((x) => (x.id === id ? c : x)));
    } else {
      const removidos = itens.filter((x) => x.id === id || x.parent_id === id).length;
      setItens((atuais) => atuais.filter((x) => x.id !== id && x.parent_id !== id));
      onTotal(-removidos);
    }
  };

  const ocultos = post.total_comentarios - itens.length;

  return (
    <div className="space-y-3 border-t border-slate-800 px-4 pb-4 pt-3">
      {!carregouTudo && ocultos > 0 && (
        <button type="button" onClick={() => void carregar()} disabled={carregando}
          className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          {carregando ? 'Carregando…' : `Ver todos os ${post.total_comentarios} comentários`}
        </button>
      )}
      {raiz.map((c) => (
        <div key={c.id} className="space-y-2">
          <ItemComentario c={c} onAtualizar={atualizar(c.id)}
            onResponder={post.permite_comentarios ? () => setRespondendo(c.id) : undefined} />
          {(respostas[c.id]?.length || respondendo === c.id) && (
            <div className="ml-10 space-y-2 border-l border-slate-800 pl-3">
              {respostas[c.id]?.map((r) => (
                <ItemComentario key={r.id} c={r} onAtualizar={atualizar(r.id)}
                  onResponder={post.permite_comentarios ? () => setRespondendo(c.id) : undefined} />
              ))}
              {respondendo === c.id && (
                <div className="flex items-start gap-1">
                  <CornerDownRight size={14} className="mt-2.5 shrink-0 text-slate-600" />
                  <div className="flex-1">
                    <CampoComentario autoFocus placeholder={`Responder a ${c.autor.nome.split(' ')[0]}…`}
                      onEnviar={(t) => comentar(t, c.id)} onCancelar={() => setRespondendo(null)} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      {carregouTudo && cursor && (
        <button type="button" onClick={() => void carregar(true)} disabled={carregando}
          className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          {carregando ? 'Carregando…' : 'Carregar mais comentários'}
        </button>
      )}
      {erro && <p className="text-xs text-red-300">{erro}</p>}
      {post.permite_comentarios ? (
        <CampoComentario autoFocus={focarCampo} placeholder="Adicione um comentário…" onEnviar={(t) => comentar(t)} />
      ) : (
        <p className="text-xs text-slate-500">Os comentários estão desativados nesta publicação.</p>
      )}
    </div>
  );
};
