import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowUp, Loader2, Newspaper, ShieldCheck } from 'lucide-react';
import { useIntervalo } from '@/features/chat/hooks/useIntervalo';
import { Post, feedApi, mensagemErro } from '../api';
import { usePerfilAtual } from '../usePerfilAtual';
import { FeedCompositor } from '../components/FeedCompositor';
import { FeedPostCard } from '../components/FeedPostCard';

const INTERVALO_NOVIDADES_MS = 60_000;

export const FeedPage: React.FC = () => {
  const { podePublicar, rotaModeracao } = usePerfilAtual();
  const [posts, setPosts] = useState<Post[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [novidades, setNovidades] = useState(false);
  const [pendentes, setPendentes] = useState(0);
  const sentinela = useRef<HTMLDivElement>(null);
  const topo = useRef<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const pag = await feedApi.listar();
      setPosts(pag.itens);
      setCursor(pag.proximo_cursor ?? null);
      topo.current = pag.itens.find((p) => !p.fixado)?.id ?? pag.itens[0]?.id ?? null;
      setNovidades(false);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar o feed.'));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (!podePublicar) return;
    feedApi.resumoModeracao().then((r) => setPendentes(r.pendentes)).catch(() => undefined);
  }, [podePublicar, posts.length]);

  // Verifica se há publicações novas sem recarregar a lista (banner "Novas publicações").
  useIntervalo(() => {
    if (carregando) return;
    feedApi.listar(null, 5).then((pag) => {
      const primeiro = pag.itens.find((p) => !p.fixado)?.id ?? null;
      if (primeiro && topo.current && primeiro !== topo.current && !posts.some((p) => p.id === primeiro)) {
        setNovidades(true);
      }
    }).catch(() => undefined);
  }, INTERVALO_NOVIDADES_MS, !carregando);

  const carregarMais = useCallback(async () => {
    if (!cursor || carregandoMais) return;
    setCarregandoMais(true);
    try {
      const pag = await feedApi.listar(cursor);
      setPosts((atuais) => [...atuais, ...pag.itens.filter((p) => !atuais.some((a) => a.id === p.id))]);
      setCursor(pag.proximo_cursor ?? null);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar mais publicações.'));
    } finally {
      setCarregandoMais(false);
    }
  }, [cursor, carregandoMais]);

  // Rolagem infinita.
  useEffect(() => {
    const alvo = sentinela.current;
    if (!alvo || !cursor) return undefined;
    const obs = new IntersectionObserver((entradas) => entradas[0].isIntersecting && void carregarMais(), {
      rootMargin: '600px',
    });
    obs.observe(alvo);
    return () => obs.disconnect();
  }, [cursor, carregarMais]);

  const atualizar = (p: Post) => setPosts((atuais) => atuais.map((x) => (x.id === p.id ? p : x)));
  const remover = (id: string) => setPosts((atuais) => atuais.filter((x) => x.id !== id));
  const adicionar = (p: Post) => {
    setPosts((atuais) => {
      const fixados = atuais.filter((x) => x.fixado);
      const demais = atuais.filter((x) => !x.fixado);
      return [...fixados, p, ...demais];
    });
    topo.current = p.id;
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-nexus-yellow/15 text-nexus-yellow">
            <Newspaper size={22} />
          </span>
          <div>
            <h1 className="text-2xl font-extrabold text-white">Feed</h1>
            <p className="text-sm text-slate-400">Artigos, reflexões teológicas e novidades da Etademp.</p>
          </div>
        </div>
        {podePublicar && pendentes > 0 && (
          <Link to={rotaModeracao}
            className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20">
            <ShieldCheck size={14} /> {pendentes} comentário{pendentes > 1 ? 's' : ''} para moderar
          </Link>
        )}
      </header>

      {podePublicar && <FeedCompositor onSalvo={adicionar} />}

      {novidades && (
        <div className="sticky top-20 z-20 flex justify-center">
          <button type="button" onClick={() => { window.scrollTo({ top: 0, behavior: 'smooth' }); void carregar(); }}
            className="inline-flex items-center gap-1.5 rounded-full bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-lg hover:bg-blue-500">
            <ArrowUp size={14} /> Novas publicações
          </button>
        </div>
      )}

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
          <button type="button" onClick={() => void carregar()} className="ml-auto text-xs font-semibold underline">Tentar de novo</button>
        </div>
      )}

      {carregando ? (
        <div className="flex justify-center py-16 text-nexus-yellow"><Loader2 className="animate-spin" /></div>
      ) : posts.length === 0 && !erro ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <Newspaper className="mx-auto mb-3 text-slate-600" size={32} />
          <p className="text-sm text-slate-300">Ainda não há publicações.</p>
          {podePublicar && <p className="mt-1 text-xs text-slate-500">Seja o primeiro a compartilhar algo com a comunidade.</p>}
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((p) => (
            <FeedPostCard key={p.id} post={p} onAtualizado={atualizar} onExcluido={remover} />
          ))}
        </div>
      )}

      <div ref={sentinela} />
      {carregandoMais && <div className="flex justify-center py-6 text-slate-400"><Loader2 className="animate-spin" /></div>}
      {!carregando && !cursor && posts.length > 0 && (
        <p className="py-6 text-center text-xs text-slate-500">Você chegou ao fim do feed.</p>
      )}
    </div>
  );
};
