import React, { useEffect, useRef, useState } from 'react';
import { Eye, FileUp, ImagePlus, Loader2, Search, Video, X, Youtube } from 'lucide-react';
import { ArquivoEnviado, urlArquivo } from '@/lib/uploadDireto';
import { rotuloPerfil, tamanhoLegivel } from '@/features/chat/utils';
import {
  Aviso,
  AvisoPayload,
  Autor,
  FrequenciaAviso,
  LarguraAviso,
  Midia,
  PERFIS_OPCOES,
  UsuarioBusca,
  avisosApi,
  mensagemErro,
  midiaParaArquivo,
} from '../api';
import { EditorRico } from './editor/EditorRico';
import { AvisoConteudo, LARGURAS } from './AvisoModal';

const MAX_MIDIAS = 10;
const ACEITA = 'image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm,video/quicktime,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt';
const CORES = ['#FFB800', '#2563EB', '#16A34A', '#DC2626', '#7C3AED', '#0891B2', '#EA580C', '#DB2777'];

const FREQUENCIAS: { valor: FrequenciaAviso; rotulo: string; ajuda: string }[] = [
  { valor: 'uma_vez', rotulo: 'Uma vez', ajuda: 'Aparece no primeiro acesso dentro do período e não volta.' },
  { valor: 'ate_confirmar', rotulo: 'Até confirmar leitura', ajuda: 'Reaparece a cada acesso até o usuário clicar em "Li e estou ciente".' },
  { valor: 'toda_sessao', rotulo: 'Todo acesso', ajuda: 'Aparece sempre que o usuário abrir a plataforma durante o período.' },
];

/** Item de mídia em edição: arquivo enviado (com progresso) ou link de vídeo. */
interface ItemMidia {
  chave: string;
  tipo: 'arquivo_enviado' | 'video_link';
  url?: string;
  arquivo?: ArquivoEnviado;
  nome?: string;
  mime?: string;
  tamanho?: number;
  progresso?: number;
  erro?: string;
  embed_tipo?: 'youtube' | 'vimeo' | null;
  embed_id?: string | null;
}

/** <input type="datetime-local"> trabalha em horário local, sem fuso. */
const paraCampoData = (iso?: string | null) => {
  if (!iso) return '';
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
};

const detectarVideo = (url: string): { embed_tipo: 'youtube' | 'vimeo'; embed_id: string } | null => {
  const yt = url.match(/(?:youtube(?:-nocookie)?\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  if (yt) return { embed_tipo: 'youtube', embed_id: yt[1] };
  const vm = url.match(/vimeo\.com\/(?:video\/)?(\d{6,12})/);
  if (vm) return { embed_tipo: 'vimeo', embed_id: vm[1] };
  return null;
};

const tipoDoMime = (mime = '') => (mime.startsWith('image/') ? 'imagem' : mime.startsWith('video/') ? 'video' : 'arquivo');

const daMidia = (m: Midia): ItemMidia =>
  m.tipo === 'video_link'
    ? { chave: m.url, tipo: 'video_link', url: m.url, embed_tipo: m.embed_tipo, embed_id: m.embed_id }
    : { chave: m.url, tipo: 'arquivo_enviado', arquivo: midiaParaArquivo(m), nome: m.nome ?? '', mime: m.mime ?? '',
      tamanho: m.tamanho ?? 0, progresso: 100 };

const paraPreview = (itens: ItemMidia[]): Midia[] =>
  itens
    .filter((i) => i.tipo === 'video_link' || i.arquivo)
    .map((i) =>
      i.tipo === 'video_link'
        ? { tipo: 'video_link', url: i.url!, embed_tipo: i.embed_tipo, embed_id: i.embed_id }
        : { tipo: tipoDoMime(i.mime), url: i.arquivo!.url, nome: i.nome, mime: i.mime, tamanho: i.tamanho },
    );

const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none';
const rotulo = 'mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400';

interface Props {
  aviso?: Aviso | null;
  onFechar: () => void;
  onSalvo: (a: Aviso) => void;
}

export const AvisoFormDrawer: React.FC<Props> = ({ aviso, onFechar, onSalvo }) => {
  const agora = new Date();
  const umaSemana = new Date(agora.getTime() + 7 * 86400_000);
  const [titulo, setTitulo] = useState(aviso?.titulo ?? '');
  const [html, setHtml] = useState(aviso?.conteudo_html ?? '');
  const [publico, setPublico] = useState<AvisoPayload['publico_tipo']>(aviso?.publico_tipo ?? 'todos');
  const [perfis, setPerfis] = useState<string[]>(aviso?.perfis ?? []);
  const [usuarios, setUsuarios] = useState<Autor[]>(aviso?.usuarios ?? []);
  const [inicio, setInicio] = useState(paraCampoData(aviso?.inicio_em ?? agora.toISOString()));
  const [fim, setFim] = useState(paraCampoData(aviso?.fim_em ?? umaSemana.toISOString()));
  const [frequencia, setFrequencia] = useState<FrequenciaAviso>(aviso?.frequencia ?? 'uma_vez');
  const [exigeConfirmacao, setExigeConfirmacao] = useState(aviso?.exige_confirmacao ?? false);
  const [prioridade, setPrioridade] = useState(aviso?.prioridade ?? 0);
  const [ativo, setAtivo] = useState(aviso?.ativo ?? true);
  const [cor, setCor] = useState(aviso?.cor_destaque ?? '#FFB800');
  const [largura, setLargura] = useState<LarguraAviso>(aviso?.largura ?? 'media');
  const [midias, setMidias] = useState<ItemMidia[]>(() => (aviso?.midias ?? []).map(daMidia));
  const [linkVideo, setLinkVideo] = useState('');
  const [busca, setBusca] = useState('');
  const [resultados, setResultados] = useState<UsuarioBusca[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [preview, setPreview] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const inputArquivo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (publico !== 'usuarios' || busca.trim().length < 2) {
      setResultados([]);
      return undefined;
    }
    const id = window.setTimeout(() => {
      setBuscando(true);
      avisosApi.buscarUsuarios(busca.trim()).then(setResultados).catch(() => setResultados([]))
        .finally(() => setBuscando(false));
    }, 300);
    return () => window.clearTimeout(id);
  }, [busca, publico]);

  useEffect(() => {
    if (frequencia === 'ate_confirmar') setExigeConfirmacao(true);
  }, [frequencia]);

  const enviar = async (lista: FileList | null) => {
    if (!lista?.length) return;
    for (const arq of Array.from(lista).slice(0, MAX_MIDIAS - midias.length)) {
      const chave = `${arq.name}-${arq.size}-${Math.random()}`;
      setMidias((ms) => [...ms, { chave, tipo: 'arquivo_enviado', nome: arq.name, mime: arq.type, tamanho: arq.size, progresso: 0 }]);
      try {
        const res = await avisosApi.enviarMidia(arq, (pct) =>
          setMidias((ms) => ms.map((m) => (m.chave === chave ? { ...m, progresso: pct } : m))));
        setMidias((ms) => ms.map((m) => (m.chave === chave ? { ...m, arquivo: res, progresso: 100 } : m)));
      } catch (e) {
        setMidias((ms) => ms.map((m) => (m.chave === chave ? { ...m, erro: mensagemErro(e, 'Falha no envio.') } : m)));
      }
    }
  };

  const adicionarVideo = () => {
    const url = linkVideo.trim();
    const embed = detectarVideo(url);
    if (!embed) {
      setErro('Informe um link válido do YouTube ou do Vimeo.');
      return;
    }
    setErro(null);
    setMidias((ms) => [...ms, { chave: url, tipo: 'video_link', url, ...embed }]);
    setLinkVideo('');
  };

  const enviando = midias.some((m) => m.tipo === 'arquivo_enviado' && !m.arquivo && !m.erro);

  const salvar = async () => {
    setErro(null);
    if (!titulo.trim()) return setErro('Informe o título do aviso.');
    if (!inicio || !fim) return setErro('Informe o período de divulgação.');
    if (new Date(fim) <= new Date(inicio)) return setErro('A data de fim deve ser posterior à de início.');
    if (publico === 'perfis' && !perfis.length) return setErro('Escolha ao menos um perfil.');
    if (publico === 'usuarios' && !usuarios.length) return setErro('Escolha ao menos um usuário.');
    const dados: AvisoPayload = {
      titulo: titulo.trim(),
      conteudo_html: html,
      publico_tipo: publico,
      perfis: publico === 'perfis' ? perfis : [],
      usuarios: publico === 'usuarios' ? usuarios.map((u) => u.id) : [],
      polo_id: aviso?.polo_id ?? null,
      escola_id: aviso?.escola_id ?? null,
      inicio_em: new Date(inicio).toISOString(),
      fim_em: new Date(fim).toISOString(),
      frequencia,
      exige_confirmacao: exigeConfirmacao,
      prioridade,
      ativo,
      cor_destaque: cor,
      largura,
      midias: midias
        .filter((m) => m.tipo === 'video_link' || m.arquivo)
        .map((m) => (m.tipo === 'video_link' ? { tipo: 'video_link', url: m.url! } : { tipo: 'arquivo_enviado', arquivo: m.arquivo! })),
    };
    setSalvando(true);
    try {
      onSalvo(aviso ? await avisosApi.editar(aviso.id, dados) : await avisosApi.criar(dados));
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível salvar o aviso.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onMouseDown={onFechar}>
      <aside className="flex h-full w-full max-w-3xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-lg font-bold text-white">{aviso ? 'Editar aviso' : 'Novo aviso (pop-up)'}</h2>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setPreview(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800">
              <Eye size={14} /> Pré-visualizar
            </button>
            <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white">
              <X size={18} />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-6 py-5">
          <section className="space-y-4">
            <div>
              <label className={rotulo} htmlFor="aviso-titulo">Título</label>
              <input id="aviso-titulo" value={titulo} maxLength={200} onChange={(e) => setTitulo(e.target.value)} className={campo}
                placeholder="Ex.: Matrículas abertas para o 2º semestre" />
            </div>
            <div>
              <span className={rotulo}>Conteúdo</span>
              <EditorRico valor={html} onChange={setHtml} variante="aviso" alturaMinima="min-h-[200px]"
                placeholder="Escreva o aviso. Use negrito, cores, tamanhos e alinhamento para destacar o que importa." />
            </div>
          </section>

          <section className="space-y-3">
            <span className={rotulo}>Mídias ({midias.length}/{MAX_MIDIAS})</span>
            {midias.length > 0 && (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {midias.map((m) => (
                  <div key={m.chave} className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
                    <button type="button" aria-label="Remover mídia" onClick={() => setMidias((ms) => ms.filter((x) => x.chave !== m.chave))}
                      className="absolute right-1 top-1 z-10 rounded-full bg-black/70 p-1 text-white hover:bg-black">
                      <X size={12} />
                    </button>
                    {m.tipo === 'video_link' ? (
                      <div className="flex h-24 flex-col items-center justify-center gap-1 px-2 text-center">
                        {m.embed_tipo === 'youtube' && m.embed_id ? (
                          <img src={`https://img.youtube.com/vi/${m.embed_id}/mqdefault.jpg`} alt="" className="absolute inset-0 h-full w-full object-cover opacity-70" />
                        ) : null}
                        <Youtube size={20} className="relative text-red-400" />
                        <span className="relative text-[11px] text-slate-200">{m.embed_tipo === 'vimeo' ? 'Vimeo' : 'YouTube'}</span>
                      </div>
                    ) : m.arquivo && m.mime?.startsWith('image/') ? (
                      <img src={urlArquivo(m.arquivo.url)} alt="" className="h-24 w-full object-cover" />
                    ) : (
                      <div className="flex h-24 flex-col items-center justify-center gap-1 px-2 text-center">
                        {m.mime?.startsWith('video/') ? <Video size={20} className="text-slate-400" /> : <FileUp size={20} className="text-slate-400" />}
                        <span className="line-clamp-2 text-[11px] text-slate-300">{m.nome}</span>
                        <span className="text-[10px] text-slate-500">{tamanhoLegivel(m.tamanho)}</span>
                      </div>
                    )}
                    {m.tipo === 'arquivo_enviado' && !m.arquivo && !m.erro && (
                      <div className="absolute inset-x-0 bottom-0 h-1 bg-slate-800">
                        <div className="h-full bg-nexus-yellow" style={{ width: `${m.progresso ?? 0}%` }} />
                      </div>
                    )}
                    {m.erro && <p className="absolute inset-x-0 bottom-0 bg-red-600/90 px-1 py-0.5 text-[10px] text-white">{m.erro}</p>}
                  </div>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button type="button" disabled={midias.length >= MAX_MIDIAS} onClick={() => inputArquivo.current?.click()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40">
                <ImagePlus size={15} /> Imagem, vídeo ou arquivo
              </button>
              <input ref={inputArquivo} type="file" hidden multiple accept={ACEITA}
                onChange={(e) => { void enviar(e.target.files); e.target.value = ''; }} />
              <div className="flex min-w-[260px] flex-1 gap-2">
                <input value={linkVideo} onChange={(e) => setLinkVideo(e.target.value)} placeholder="Link do YouTube ou Vimeo"
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), adicionarVideo())} className={campo} />
                <button type="button" onClick={adicionarVideo} disabled={!linkVideo.trim() || midias.length >= MAX_MIDIAS}
                  className="shrink-0 rounded-xl bg-slate-800 px-3 text-xs text-white hover:bg-slate-700 disabled:opacity-40">Adicionar</button>
              </div>
            </div>
            <p className="text-[11px] text-slate-500">Imagens até 10 MB, vídeos até 100 MB e documentos até 20 MB.</p>
          </section>

          <section className="space-y-3">
            <span className={rotulo}>Quem vê</span>
            <div className="flex flex-wrap gap-2">
              {([['todos', 'Todos os usuários'], ['perfis', 'Tipos de usuário'], ['usuarios', 'Usuários específicos']] as const).map(([v, r]) => (
                <button key={v} type="button" onClick={() => setPublico(v)}
                  className={`rounded-xl border px-3 py-1.5 text-sm ${publico === v ? 'border-nexus-yellow bg-nexus-yellow/15 text-nexus-yellow' : 'border-slate-700 text-slate-300 hover:bg-slate-800'}`}>
                  {r}
                </button>
              ))}
            </div>
            {publico === 'perfis' && (
              <div className="flex flex-wrap gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                {PERFIS_OPCOES.map((o) => (
                  <label key={o.valor} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm text-slate-200 hover:bg-slate-800">
                    <input type="checkbox" checked={perfis.includes(o.valor)}
                      onChange={(e) => setPerfis((ps) => (e.target.checked ? [...ps, o.valor] : ps.filter((p) => p !== o.valor)))} />
                    {o.rotulo}
                  </label>
                ))}
              </div>
            )}
            {publico === 'usuarios' && (
              <div className="space-y-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                {usuarios.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {usuarios.map((u) => (
                      <span key={u.id} className="inline-flex items-center gap-1 rounded-full bg-blue-500/15 px-2.5 py-1 text-xs text-blue-200">
                        {u.nome}
                        <button type="button" aria-label={`Remover ${u.nome}`} onClick={() => setUsuarios((us) => us.filter((x) => x.id !== u.id))}>
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome, e-mail ou CPF…"
                    className={`${campo} pl-8`} />
                  {buscando && <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-slate-500" />}
                </div>
                {resultados.length > 0 && (
                  <ul className="max-h-48 overflow-y-auto rounded-xl border border-slate-800">
                    {resultados.filter((r) => !usuarios.some((u) => u.id === r.id)).map((r) => (
                      <li key={r.id}>
                        <button type="button" onClick={() => { setUsuarios((us) => [...us, r]); setBusca(''); }}
                          className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-800">
                          <span className="min-w-0">
                            <span className="block truncate text-slate-100">{r.nome}</span>
                            <span className="block truncate text-[11px] text-slate-500">
                              {[rotuloPerfil(r.perfil), r.email, r.escola_nome || r.polo_nome].filter(Boolean).join(' · ')}
                            </span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>

          <section className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={rotulo} htmlFor="aviso-inicio">Início da divulgação</label>
              <input id="aviso-inicio" type="datetime-local" value={inicio} onChange={(e) => setInicio(e.target.value)} className={campo} />
            </div>
            <div>
              <label className={rotulo} htmlFor="aviso-fim">Fim da divulgação</label>
              <input id="aviso-fim" type="datetime-local" value={fim} onChange={(e) => setFim(e.target.value)} className={campo} />
            </div>
          </section>

          <section className="space-y-3">
            <span className={rotulo}>Exibição</span>
            <div className="grid gap-2 sm:grid-cols-3">
              {FREQUENCIAS.map((f) => (
                <button key={f.valor} type="button" onClick={() => setFrequencia(f.valor)}
                  className={`rounded-xl border p-3 text-left ${frequencia === f.valor ? 'border-nexus-yellow bg-nexus-yellow/10' : 'border-slate-700 hover:bg-slate-800'}`}>
                  <span className={`block text-sm font-semibold ${frequencia === f.valor ? 'text-nexus-yellow' : 'text-slate-100'}`}>{f.rotulo}</span>
                  <span className="mt-0.5 block text-[11px] text-slate-400">{f.ajuda}</span>
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={exigeConfirmacao} disabled={frequencia === 'ate_confirmar'}
                onChange={(e) => setExigeConfirmacao(e.target.checked)} />
              Exigir confirmação de leitura ("Li e estou ciente")
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
              Ativo (desmarque para pausar sem excluir)
            </label>
          </section>

          <section className="grid gap-4 sm:grid-cols-3">
            <div>
              <span className={rotulo}>Cor de destaque</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {CORES.map((c) => (
                  <button key={c} type="button" aria-label={c} onClick={() => setCor(c)}
                    className={`h-7 w-7 rounded-lg border-2 ${cor.toLowerCase() === c.toLowerCase() ? 'border-white' : 'border-transparent'}`}
                    style={{ background: c }} />
                ))}
                <input type="color" value={cor} onChange={(e) => setCor(e.target.value)} aria-label="Outra cor"
                  className="h-7 w-9 cursor-pointer rounded border border-slate-600 bg-transparent" />
              </div>
            </div>
            <div>
              <label className={rotulo} htmlFor="aviso-largura">Tamanho do pop-up</label>
              <select id="aviso-largura" value={largura} onChange={(e) => setLargura(e.target.value as LarguraAviso)} className={campo}>
                {Object.entries(LARGURAS).map(([v, l]) => <option key={v} value={v}>{l.rotulo}</option>)}
              </select>
            </div>
            <div>
              <label className={rotulo} htmlFor="aviso-prioridade">Prioridade (0–100)</label>
              <input id="aviso-prioridade" type="number" min={0} max={100} value={prioridade}
                onChange={(e) => setPrioridade(Math.max(0, Math.min(100, Number(e.target.value) || 0)))} className={campo} />
              <p className="mt-1 text-[11px] text-slate-500">Maior aparece primeiro quando há vários avisos.</p>
            </div>
          </section>
        </div>

        <footer className="flex items-center gap-3 border-t border-slate-800 px-6 py-4">
          {erro && <p className="flex-1 text-xs text-red-300">{erro}</p>}
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={onFechar} className="rounded-xl px-4 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancelar</button>
            <button type="button" onClick={() => void salvar()} disabled={salvando || enviando}
              className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-5 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
              {salvando && <Loader2 size={15} className="animate-spin" />} {aviso ? 'Salvar alterações' : 'Criar aviso'}
            </button>
          </div>
        </footer>
      </aside>

      {preview && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" onMouseDown={(e) => { e.stopPropagation(); setPreview(false); }}>
          <div className={`w-full ${LARGURAS[largura].classe}`} onMouseDown={(e) => e.stopPropagation()}>
            <AvisoConteudo titulo={titulo} conteudoHtml={html} midias={paraPreview(midias)} corDestaque={cor}
              exigeConfirmacao={exigeConfirmacao} onFechar={() => setPreview(false)} onConfirmar={() => setPreview(false)}
              onAdiar={() => setPreview(false)} contador="Pré-visualização" />
          </div>
        </div>
      )}
    </div>
  );
};
