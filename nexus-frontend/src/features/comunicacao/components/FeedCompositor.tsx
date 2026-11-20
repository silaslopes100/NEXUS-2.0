import React, { useEffect, useRef, useState } from 'react';
import { FileUp, Globe2, ImagePlus, Link2, Loader2, Lock, MessageSquareOff, Video, X } from 'lucide-react';
import { ArquivoEnviado, urlArquivo } from '@/lib/uploadDireto';
import { Avatar } from '@/features/chat/components/Avatar';
import { tamanhoLegivel } from '@/features/chat/utils';
import {
  LinkPreview,
  PERFIS_OPCOES,
  Post,
  PostPayload,
  feedApi,
  mensagemErro,
  midiaParaArquivo,
} from '../api';
import { usePerfilAtual } from '../usePerfilAtual';
import { EditorRico } from './editor/EditorRico';
import { CartaoLink } from './CartaoLink';

const MAX_MIDIAS = 10;
const MAX_LINKS = 3;
const ACEITA = {
  imagem: 'image/jpeg,image/png,image/webp,image/gif',
  video: 'video/mp4,video/webm,video/quicktime',
  arquivo: '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt',
};
const URL_NO_TEXTO = /\bhttps?:\/\/[^\s<>"']+/i;

interface Envio {
  chave: string;
  nome: string;
  tamanho: number;
  mime: string;
  progresso: number;
  arquivo?: ArquivoEnviado;
  erro?: string;
}

const textoPuro = (html: string) => {
  const div = document.createElement('div');
  div.innerHTML = html;
  return div.textContent || '';
};

interface Props {
  /** Post em edição (sem ele, cria uma publicação nova). */
  post?: Post;
  onSalvo: (post: Post) => void;
  onCancelar?: () => void;
}

export const FeedCompositor: React.FC<Props> = ({ post, onSalvo, onCancelar }) => {
  const { user, nome, papel } = usePerfilAtual();
  const editando = !!post;
  const [aberto, setAberto] = useState(editando);
  const [html, setHtml] = useState(post?.conteudo_html ?? '');
  const [envios, setEnvios] = useState<Envio[]>(
    () => post?.midias.map((m) => ({ chave: m.url, nome: m.nome ?? '', tamanho: m.tamanho ?? 0, mime: m.mime ?? '',
      progresso: 100, arquivo: midiaParaArquivo(m) })) ?? [],
  );
  const [links, setLinks] = useState<LinkPreview[]>(post?.links ?? []);
  const [linksDescartados, setLinksDescartados] = useState<string[]>([]);
  const [carregandoLink, setCarregandoLink] = useState<string | null>(null);
  const [campoLink, setCampoLink] = useState<string | null>(null);
  const [perfis, setPerfis] = useState<string[]>(post?.publico_perfis ?? []);
  const [soUnidade, setSoUnidade] = useState(!!(post?.polo_id || post?.escola_id));
  const [comentarios, setComentarios] = useState(post?.permite_comentarios ?? true);
  const [mostrarPublico, setMostrarPublico] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const inputs = { imagem: useRef<HTMLInputElement>(null), video: useRef<HTMLInputElement>(null),
    arquivo: useRef<HTMLInputElement>(null) };

  const unidade = papel === 'polo' ? { polo_id: user?.polo_id } : papel === 'escola' ? { escola_id: user?.escola_id } : null;

  const adicionarLink = async (url: string) => {
    const alvo = url.trim();
    if (!alvo || links.length >= MAX_LINKS || links.some((l) => l.url === alvo) || carregandoLink) return;
    setCarregandoLink(alvo);
    try {
      const prev = await feedApi.linkPreview(alvo);
      setLinks((ls) => (ls.some((l) => l.url === prev.url) ? ls : [...ls, prev]));
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível ler este link.'));
    } finally {
      setCarregandoLink(null);
    }
  };

  // Detecta o primeiro link digitado/colado no texto e monta a prévia (como no LinkedIn).
  useEffect(() => {
    if (links.length) return undefined;
    const achado = textoPuro(html).match(URL_NO_TEXTO)?.[0]?.replace(/[).,;!?]+$/, '');
    if (!achado || linksDescartados.includes(achado)) return undefined;
    const id = window.setTimeout(() => void adicionarLink(achado), 700);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [html, links.length]);

  const enviar = async (lista: FileList | null) => {
    if (!lista?.length) return;
    const arquivos = Array.from(lista).slice(0, MAX_MIDIAS - envios.length);
    if (arquivos.length < lista.length) setErro(`Limite de ${MAX_MIDIAS} mídias por publicação.`);
    for (const arq of arquivos) {
      const chave = `${arq.name}-${arq.size}-${Math.random()}`;
      setEnvios((es) => [...es, { chave, nome: arq.name, tamanho: arq.size, mime: arq.type, progresso: 0 }]);
      try {
        const res = await feedApi.enviarMidia(arq, (pct) =>
          setEnvios((es) => es.map((e) => (e.chave === chave ? { ...e, progresso: pct } : e))));
        setEnvios((es) => es.map((e) => (e.chave === chave ? { ...e, progresso: 100, arquivo: res } : e)));
      } catch (e) {
        setEnvios((es) => es.map((x) => (x.chave === chave ? { ...x, erro: mensagemErro(e, 'Falha no envio.') } : x)));
      }
    }
  };

  const limpar = () => {
    setHtml('');
    setEnvios([]);
    setLinks([]);
    setLinksDescartados([]);
    setPerfis([]);
    setSoUnidade(false);
    setComentarios(true);
    setErro(null);
    setAberto(false);
  };

  const enviando = envios.some((e) => !e.arquivo && !e.erro);
  const vazio = !textoPuro(html).trim() && !envios.some((e) => e.arquivo) && !links.length;

  const salvar = async () => {
    setErro(null);
    setSalvando(true);
    const dados: PostPayload = {
      conteudo_html: html,
      midias: envios.filter((e) => e.arquivo).map((e) => e.arquivo!),
      links: links.map((l) => ({ url: l.url })),
      publico_perfis: perfis.length ? perfis : null,
      polo_id: soUnidade ? unidade?.polo_id ?? null : null,
      escola_id: soUnidade ? unidade?.escola_id ?? null : null,
      permite_comentarios: comentarios,
    };
    try {
      const salvo = editando ? await feedApi.editar(post!.id, dados) : await feedApi.criar(dados);
      onSalvo(salvo);
      if (!editando) limpar();
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível publicar.'));
    } finally {
      setSalvando(false);
    }
  };

  if (!aberto) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
        <Avatar nome={nome} usuarioId={user?.id} fotoUrl={user?.foto_url} />
        <button
          type="button"
          onClick={() => setAberto(true)}
          className="flex-1 rounded-full border border-slate-700 bg-slate-950/60 px-4 py-2.5 text-left text-sm text-slate-400 hover:border-slate-600 hover:bg-slate-900"
        >
          Compartilhe um artigo, uma reflexão ou uma novidade…
        </button>
        <button type="button" title="Adicionar imagem" onClick={() => { setAberto(true); setTimeout(() => inputs.imagem.current?.click(), 50); }}
          className="hidden rounded-xl p-2 text-sky-400 hover:bg-slate-800 sm:block">
          <ImagePlus size={20} />
        </button>
        {['imagem', 'video', 'arquivo'].map((t) => (
          <input key={t} ref={inputs[t as keyof typeof inputs]} type="file" multiple hidden accept={ACEITA[t as keyof typeof ACEITA]}
            onChange={(e) => { void enviar(e.target.files); e.target.value = ''; }} />
        ))}
      </div>
    );
  }

  const publicoRotulo = perfis.length
    ? PERFIS_OPCOES.filter((o) => perfis.includes(o.valor)).map((o) => o.rotulo).join(', ')
    : 'Todos';

  return (
    <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex items-center gap-3">
        <Avatar nome={nome} usuarioId={user?.id} fotoUrl={user?.foto_url} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white">{nome}</p>
          <button type="button" onClick={() => setMostrarPublico((v) => !v)}
            className="mt-0.5 inline-flex items-center gap-1 rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300 hover:bg-slate-800">
            {perfis.length || soUnidade ? <Lock size={11} /> : <Globe2 size={11} />}
            {publicoRotulo}{soUnidade ? ' · minha unidade' : ''}
          </button>
        </div>
        {(onCancelar || !editando) && (
          <button type="button" aria-label="Fechar" onClick={() => (editando ? onCancelar?.() : limpar())}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X size={18} />
          </button>
        )}
      </div>

      {mostrarPublico && (
        <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-sm">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Quem pode ver</p>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setPerfis([])}
                className={`rounded-full border px-3 py-1 text-xs ${!perfis.length ? 'border-nexus-yellow bg-nexus-yellow/15 text-nexus-yellow' : 'border-slate-700 text-slate-300'}`}>
                Todos
              </button>
              {PERFIS_OPCOES.map((o) => {
                const ativo = perfis.includes(o.valor);
                return (
                  <button key={o.valor} type="button"
                    onClick={() => setPerfis((ps) => (ativo ? ps.filter((p) => p !== o.valor) : [...ps, o.valor]))}
                    className={`rounded-full border px-3 py-1 text-xs ${ativo ? 'border-nexus-yellow bg-nexus-yellow/15 text-nexus-yellow' : 'border-slate-700 text-slate-300 hover:bg-slate-800'}`}>
                    {o.rotulo}
                  </button>
                );
              })}
            </div>
          </div>
          {unidade && (
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input type="checkbox" checked={soUnidade} onChange={(e) => setSoUnidade(e.target.checked)} />
              Somente para {papel === 'polo' ? 'o meu polo (e escolas vinculadas)' : 'a minha escola'}
            </label>
          )}
          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input type="checkbox" checked={!comentarios} onChange={(e) => setComentarios(!e.target.checked)} />
            <MessageSquareOff size={13} /> Desativar comentários
          </label>
        </div>
      )}

      <EditorRico valor={html} onChange={setHtml} variante="post" autoFocus={!editando}
        placeholder="Sobre o que você quer falar? Cole um link para mostrar a prévia." alturaMinima="min-h-[110px]" />

      {links.map((l) => (
        <CartaoLink key={l.url} link={l} onRemover={() => {
          setLinks((ls) => ls.filter((x) => x.url !== l.url));
          setLinksDescartados((d) => [...d, l.url]);
        }} />
      ))}
      {carregandoLink && (
        <p className="flex items-center gap-2 text-xs text-slate-400"><Loader2 size={14} className="animate-spin" /> Gerando prévia de {carregandoLink}</p>
      )}

      {envios.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {envios.map((e) => (
            <div key={e.chave} className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
              <button type="button" aria-label="Remover" onClick={() => setEnvios((es) => es.filter((x) => x.chave !== e.chave))}
                className="absolute right-1 top-1 z-10 rounded-full bg-black/70 p-1 text-white hover:bg-black">
                <X size={12} />
              </button>
              {e.arquivo && e.mime.startsWith('image/') ? (
                <img src={urlArquivo(e.arquivo.url)} alt="" className="h-24 w-full object-cover" />
              ) : (
                <div className="flex h-24 flex-col items-center justify-center gap-1 px-2 text-center">
                  {e.mime.startsWith('video/') ? <Video size={20} className="text-slate-400" /> : <FileUp size={20} className="text-slate-400" />}
                  <span className="line-clamp-2 text-[11px] text-slate-300">{e.nome}</span>
                  <span className="text-[10px] text-slate-500">{tamanhoLegivel(e.tamanho)}</span>
                </div>
              )}
              {!e.arquivo && !e.erro && (
                <div className="absolute inset-x-0 bottom-0 h-1 bg-slate-800">
                  <div className="h-full bg-nexus-yellow transition-all" style={{ width: `${e.progresso}%` }} />
                </div>
              )}
              {e.erro && <p className="absolute inset-x-0 bottom-0 bg-red-600/90 px-1 py-0.5 text-[10px] text-white">{e.erro}</p>}
            </div>
          ))}
        </div>
      )}

      {campoLink !== null && (
        <form className="flex gap-2" onSubmit={(ev) => { ev.preventDefault(); void adicionarLink(campoLink); setCampoLink(null); }}>
          <input autoFocus value={campoLink} onChange={(ev) => setCampoLink(ev.target.value)} placeholder="https://..."
            className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-nexus-yellow focus:outline-none" />
          <button type="submit" className="rounded-xl bg-slate-800 px-3 text-sm text-white hover:bg-slate-700">Adicionar</button>
          <button type="button" onClick={() => setCampoLink(null)} className="px-2 text-sm text-slate-400">Cancelar</button>
        </form>
      )}

      {erro && <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">{erro}</p>}

      <div className="flex flex-wrap items-center gap-1 border-t border-slate-800 pt-3">
        <button type="button" onClick={() => inputs.imagem.current?.click()} disabled={envios.length >= MAX_MIDIAS}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-sky-400 hover:bg-slate-800 disabled:opacity-40">
          <ImagePlus size={16} /> Foto
        </button>
        <button type="button" onClick={() => inputs.video.current?.click()} disabled={envios.length >= MAX_MIDIAS}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-emerald-400 hover:bg-slate-800 disabled:opacity-40">
          <Video size={16} /> Vídeo
        </button>
        <button type="button" onClick={() => inputs.arquivo.current?.click()} disabled={envios.length >= MAX_MIDIAS}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-amber-400 hover:bg-slate-800 disabled:opacity-40">
          <FileUp size={16} /> Documento
        </button>
        <button type="button" onClick={() => setCampoLink('')} disabled={links.length >= MAX_LINKS}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-violet-400 hover:bg-slate-800 disabled:opacity-40">
          <Link2 size={16} /> Link
        </button>
        {['imagem', 'video', 'arquivo'].map((t) => (
          <input key={t} ref={inputs[t as keyof typeof inputs]} type="file" multiple hidden accept={ACEITA[t as keyof typeof ACEITA]}
            onChange={(ev) => { void enviar(ev.target.files); ev.target.value = ''; }} />
        ))}
        <div className="ml-auto flex items-center gap-2">
          {editando && onCancelar && (
            <button type="button" onClick={onCancelar} className="rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-slate-800">
              Cancelar
            </button>
          )}
          <button type="button" onClick={() => void salvar()} disabled={salvando || enviando || vazio}
            className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-5 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
            {salvando && <Loader2 size={15} className="animate-spin" />}
            {editando ? 'Salvar' : 'Publicar'}
          </button>
        </div>
      </div>
    </div>
  );
};
