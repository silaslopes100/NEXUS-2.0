import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Eye,
  ImagePlus,
  Layers,
  ListOrdered,
  Loader2,
  PlayCircle,
  Plus,
  Settings2,
  ShoppingBag,
} from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { ACEITA_IMAGENS, Aula, Capitulo, ConfigAva, Estrutura, ReordenarPayload, avaAdminApi, formatarBRL, formatarDuracao } from '../../api';
import { EstruturaEditor } from '../../components/editor/EstruturaEditor';
import { AulaDrawer } from '../../components/editor/AulaDrawer';
import { botaoPrimario, botaoSecundario, campo, rotulo } from '../../components/editor/estilos';

const Interruptor: React.FC<{ ligado: boolean; onChange: (v: boolean) => void; rotulo: string; ajuda: string; disabled?: boolean }> = ({
  ligado, onChange, rotulo: r, ajuda, disabled,
}) => (
  <label className={`flex cursor-pointer items-start gap-3 ${disabled ? 'opacity-60' : ''}`}>
    <button type="button" role="switch" aria-checked={ligado} disabled={disabled} onClick={() => onChange(!ligado)}
      className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition ${ligado ? 'bg-emerald-500' : 'bg-slate-700'}`}>
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${ligado ? 'left-[22px]' : 'left-0.5'}`} />
    </button>
    <span>
      <span className="block text-sm font-semibold text-white">{r}</span>
      <span className="block text-xs text-slate-400">{ajuda}</span>
    </span>
  </label>
);

/** Montagem do conteúdo EAD de uma disciplina: Capítulos >> Aulas >> Conteúdos. */
export const AvaDisciplinaEditorPage: React.FC = () => {
  const { disciplinaId = '' } = useParams();
  const navigate = useNavigate();
  const [estrutura, setEstrutura] = useState<Estrutura | null>(null);
  const [capitulos, setCapitulos] = useState<Capitulo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [novoCapitulo, setNovoCapitulo] = useState('');
  const [criandoCap, setCriandoCap] = useState(false);
  const [drawer, setDrawer] = useState<{ capitulo: Capitulo; aula: Aula | null } | null>(null);
  const [mostrarConfig, setMostrarConfig] = useState(false);
  const [descricao, setDescricao] = useState('');
  const [valorEad, setValorEad] = useState('');
  const [valorLivro, setValorLivro] = useState('');
  const [enviandoCapa, setEnviandoCapa] = useState(false);
  const inputCapa = useRef<HTMLInputElement>(null);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      const e = await avaAdminApi.estrutura(disciplinaId);
      setEstrutura(e);
      setCapitulos(e.capitulos);
      setDescricao(e.config.descricao_ava ?? '');
      setValorEad(String(e.config.valor_ead ?? 45));
      setValorLivro(String(e.config.valor_livro_ead ?? 25));
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar a disciplina.'));
    } finally {
      setCarregando(false);
    }
  }, [disciplinaId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (!aviso) return;
    const t = window.setTimeout(() => setAviso(null), 2500);
    return () => window.clearTimeout(t);
  }, [aviso]);

  const executar = async (fn: () => Promise<unknown>, ok?: string) => {
    setErro(null);
    try {
      await fn();
      if (ok) setAviso(ok);
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  // ----------------------------------------------------------------- configuração

  const salvarConfig = (parcial: Partial<ConfigAva>) =>
    executar(async () => {
      if (!estrutura) return;
      const atual = estrutura.config;
      const cfg = await avaAdminApi.salvarConfig(disciplinaId, {
        capa_url: atual.capa_url, descricao_ava: atual.descricao_ava, sequencial: atual.sequencial,
        publicado: atual.publicado, valor_ead: atual.valor_ead ?? 45, livro_disponivel: atual.livro_disponivel ?? false,
        valor_livro_ead: atual.valor_livro_ead ?? 25, ...parcial,
      });
      setEstrutura({ ...estrutura, config: cfg });
    }, 'Configuração salva.');

  const enviarCapa = async (f: File) => {
    setEnviandoCapa(true);
    try {
      const enviado = await avaAdminApi.enviarArquivo(f);
      await salvarConfig({ capa_url: enviado.url });
    } catch (e) {
      setErro(mensagemErro(e, 'Falha no envio da capa.'));
    } finally {
      setEnviandoCapa(false);
    }
  };

  // ----------------------------------------------------------------- capítulos

  const criarCapitulo = async () => {
    const titulo = novoCapitulo.trim();
    if (!titulo) return;
    setCriandoCap(true);
    await executar(async () => {
      const c = await avaAdminApi.criarCapitulo(disciplinaId, { titulo, publicado: true });
      setCapitulos((l) => [...l, c]);
      setNovoCapitulo('');
    });
    setCriandoCap(false);
  };

  const substituirCapitulo = (c: Capitulo) => setCapitulos((l) => l.map((x) => (x.id === c.id ? c : x)));

  const reordenar = async (antes: Capitulo[], payload: ReordenarPayload) => {
    try {
      await avaAdminApi.reordenar(disciplinaId, payload);
    } catch (e) {
      setCapitulos(antes);
      setErro(mensagemErro(e, 'Não foi possível salvar a nova ordem.'));
    }
  };

  const aulaAlterada = (aula: Aula) =>
    setCapitulos((l) =>
      l.map((c) =>
        c.id !== aula.capitulo_id ? c
          : { ...c, aulas: c.aulas.some((a) => a.id === aula.id) ? c.aulas.map((a) => (a.id === aula.id ? aula : a)) : [...c.aulas, aula] },
      ),
    );

  // ----------------------------------------------------------------- render

  if (carregando) {
    return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;
  }
  if (!estrutura) {
    return (
      <div className="max-w-3xl space-y-4">
        <Link to="/admin/ava" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Conteúdo EAD</Link>
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      </div>
    );
  }

  const { disciplina, config } = estrutura;
  const totalAulas = capitulos.reduce((s, c) => s + c.aulas.length, 0);
  const totalMin = capitulos.reduce((s, c) => s + c.aulas.reduce((x, a) => x + (a.duracao_min || 0), 0), 0);

  return (
    <div className="max-w-6xl space-y-6">
      <Link to="/admin/ava" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white">
        <ArrowLeft size={14} /> Conteúdo EAD
      </Link>

      <header className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 shadow-xl">
        <div className="relative flex flex-col gap-5 p-6 md:flex-row md:items-center">
          <button type="button" onClick={() => inputCapa.current?.click()} disabled={enviandoCapa}
            className="group relative aspect-video w-full shrink-0 overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-blue-900/60 to-slate-950 md:w-56">
            {config.capa_url ? (
              <img src={urlArquivo(config.capa_url)} alt="Capa da disciplina" className="h-full w-full object-cover" />
            ) : (
              <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-xs text-slate-400">
                <ImagePlus size={22} /> Adicionar capa
              </span>
            )}
            <span className="absolute inset-0 hidden items-center justify-center bg-black/50 text-xs font-semibold text-white group-hover:flex">
              {enviandoCapa ? <Loader2 className="animate-spin" /> : 'Trocar capa'}
            </span>
          </button>
          <input ref={inputCapa} type="file" hidden accept={ACEITA_IMAGENS}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void enviarCapa(f); e.target.value = ''; }} />

          <div className="min-w-0 flex-1 space-y-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">{disciplina.curso_nome}{disciplina.semestre ? ` · ${disciplina.semestre}º semestre` : ''}</p>
              <h1 className="text-2xl font-extrabold text-white md:text-3xl">{disciplina.nome}</h1>
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1"><Layers size={13} /> {capitulos.length} capítulos</span>
              <span className="flex items-center gap-1"><PlayCircle size={13} /> {totalAulas} aulas</span>
              {totalMin > 0 && <span>{formatarDuracao(totalMin)} de conteúdo</span>}
            </div>
          </div>

          <div className="flex flex-col gap-3 md:items-end">
            <span className={`self-start rounded-full px-3 py-1 text-xs font-bold md:self-end ${config.publicado ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-800 text-slate-300'}`}>
              {config.publicado ? 'Publicado para os alunos' : 'Rascunho'}
            </span>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => navigate(`/admin/ava/disciplinas/${disciplinaId}/previa`)}
                disabled={totalAulas === 0} className={botaoSecundario} title="Ver como o aluno verá (inclui rascunhos)">
                <Eye size={15} /> Pré-visualizar
              </button>
              <button type="button" onClick={() => setMostrarConfig((v) => !v)} className={botaoSecundario}>
                <Settings2 size={15} /> Configurações
              </button>
              <button type="button" onClick={() => void salvarConfig({ publicado: !config.publicado })}
                className={config.publicado ? botaoSecundario : botaoPrimario}>
                {config.publicado ? 'Despublicar' : 'Publicar'}
              </button>
            </div>
          </div>
        </div>

        {mostrarConfig && (
          <div className="grid gap-5 border-t border-slate-800 bg-slate-950/40 p-6 md:grid-cols-2">
            <div className="space-y-4">
              <Interruptor ligado={config.sequencial} onChange={(v) => void salvarConfig({ sequencial: v })}
                rotulo="Ordem obrigatória"
                ajuda="O aluno só libera a próxima aula depois de concluir a anterior." />
              <Interruptor ligado={config.publicado} onChange={(v) => void salvarConfig({ publicado: v })}
                rotulo="Publicado"
                ajuda="Visível na Sala de Aula Virtual dos alunos EAD que têm a disciplina liberada." />
            </div>
            <div className="space-y-2">
              <label className="block">
                <span className={rotulo}>Apresentação da disciplina</span>
                <textarea value={descricao} onChange={(e) => setDescricao(e.target.value)} rows={4} maxLength={5000}
                  className={campo} placeholder="Texto curto exibido no topo da disciplina para o aluno." />
              </label>
              <div className="flex justify-end">
                <button type="button" disabled={descricao === (config.descricao_ava ?? '')}
                  onClick={() => void salvarConfig({ descricao_ava: descricao })} className={botaoPrimario}>
                  Salvar apresentação
                </button>
              </div>
            </div>
            <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="flex items-center gap-2 text-sm font-bold text-white">
                  <ShoppingBag size={16} className="text-nexus-yellow" /> Venda EAD
                </p>
                <span className="text-[11px] text-slate-400">
                  Fica à venda na loja do aluno quando estiver <b>publicada</b> e liberada no calendário da Turma EAD.
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <label className="block">
                  <span className={rotulo}>Valor da disciplina (R$)</span>
                  <input type="number" min={0} step="0.01" value={valorEad} onChange={(e) => setValorEad(e.target.value)} className={campo} />
                </label>
                <div className="flex items-end pb-1">
                  <Interruptor ligado={config.livro_disponivel ?? false}
                    onChange={(v) => void salvarConfig({ livro_disponivel: v })}
                    rotulo="Oferecer livro físico"
                    ajuda="Upsell no checkout, sem licença (a avaliação é feita no AVA)." />
                </div>
                <label className="block">
                  <span className={rotulo}>Valor do livro (R$)</span>
                  <input type="number" min={0} step="0.01" value={valorLivro} disabled={!config.livro_disponivel}
                    onChange={(e) => setValorLivro(e.target.value)} className={`${campo} disabled:opacity-50`} />
                </label>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs text-slate-400">
                  Aluno paga {formatarBRL(Number(valorEad) || 0)}
                  {config.livro_disponivel ? ` · com o livro, ${formatarBRL((Number(valorEad) || 0) + (Number(valorLivro) || 0))}` : ''}
                </span>
                <button type="button"
                  disabled={valorEad === '' || Number(valorEad) < 0 || valorLivro === '' || Number(valorLivro) < 0
                    || (Number(valorEad) === config.valor_ead && Number(valorLivro) === config.valor_livro_ead)}
                  onClick={() => void salvarConfig({ valor_ead: Number(valorEad), valor_livro_ead: Number(valorLivro) })}
                  className={botaoPrimario}>
                  Salvar valores
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}
      {aviso && (
        <div role="status" className="fixed bottom-6 right-6 z-[70] rounded-xl border border-emerald-500/30 bg-emerald-950/90 px-4 py-3 text-sm font-semibold text-emerald-200 shadow-2xl">
          {aviso}
        </div>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><ListOrdered size={18} className="text-nexus-yellow" /> Estrutura</h2>
          <p className="hidden text-xs text-slate-500 sm:block">Arraste para reordenar capítulos e aulas (inclusive entre capítulos).</p>
        </div>

        {capitulos.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
            <Layers className="mx-auto mb-3 text-slate-600" size={32} />
            <p className="text-sm text-slate-300">Comece criando o primeiro capítulo.</p>
            <p className="mt-1 text-xs text-slate-500">Ex.: “Módulo 1 — Fundamentos”.</p>
          </div>
        )}

        <EstruturaEditor
          capitulos={capitulos}
          setCapitulos={setCapitulos}
          onReordenar={reordenar}
          onRenomearCapitulo={(c, titulo) =>
            void executar(async () => substituirCapitulo(await avaAdminApi.atualizarCapitulo(c.id, { titulo, descricao: c.descricao, publicado: c.publicado })))}
          onPublicarCapitulo={(c) =>
            void executar(async () => substituirCapitulo(await avaAdminApi.atualizarCapitulo(c.id, { titulo: c.titulo, descricao: c.descricao, publicado: !c.publicado })),
              c.publicado ? 'Capítulo ocultado.' : 'Capítulo publicado.')}
          onDuplicarCapitulo={(c) =>
            void executar(async () => { await avaAdminApi.duplicarCapitulo(c.id); await carregar(); }, 'Capítulo duplicado (oculto até você publicar).')}
          onExcluirCapitulo={(c) => {
            if (!window.confirm(`Excluir o capítulo "${c.titulo}" e todas as suas ${c.aulas.length} aula(s)?`)) return;
            void executar(async () => { await avaAdminApi.excluirCapitulo(c.id); setCapitulos((l) => l.filter((x) => x.id !== c.id)); }, 'Capítulo excluído.');
          }}
          onNovaAula={(c) => setDrawer({ capitulo: c, aula: null })}
          onAbrirAula={(c, a) => setDrawer({ capitulo: c, aula: a })}
          onExcluirAula={(a) => {
            if (!window.confirm(`Excluir a aula "${a.titulo}"?`)) return;
            void executar(async () => {
              await avaAdminApi.excluirAula(a.id);
              setCapitulos((l) => l.map((c) => ({ ...c, aulas: c.aulas.filter((x) => x.id !== a.id) })));
            }, 'Aula excluída.');
          }}
        />

        <form onSubmit={(e) => { e.preventDefault(); void criarCapitulo(); }}
          className="flex flex-col gap-2 rounded-2xl border border-dashed border-slate-700 p-3 sm:flex-row">
          <input value={novoCapitulo} onChange={(e) => setNovoCapitulo(e.target.value)} maxLength={255}
            placeholder="Título do novo capítulo" className={campo} />
          <button type="submit" disabled={!novoCapitulo.trim() || criandoCap} className={`${botaoPrimario} shrink-0`}>
            {criandoCap ? <Loader2 size={14} className="animate-spin" /> : <Plus size={16} />} Novo capítulo
          </button>
        </form>
      </section>

      {drawer && (
        <AulaDrawer
          key={drawer.aula?.id ?? `nova-${drawer.capitulo.id}`}
          reordenarItens={(payload) => avaAdminApi.reordenar(disciplinaId, payload)}
          cursoId={disciplina.curso_id}
          capituloId={drawer.capitulo.id}
          capituloTitulo={drawer.capitulo.titulo}
          aula={drawer.aula}
          onFechar={() => setDrawer(null)}
          onAlterada={aulaAlterada}
        />
      )}
    </div>
  );
};
