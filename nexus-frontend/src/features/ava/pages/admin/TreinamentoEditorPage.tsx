import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Award, Eye, Layers, ListOrdered, Loader2, Pencil, PlayCircle, Plus, Users } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { Aula, Capitulo, ReordenarPayload, avaAdminApi, formatarDuracao } from '../../api';
import { CATEGORIA, PERFIS_ALVO, Treinamento, treinamentosAdminApi } from '../../treinamentosApi';
import { EstruturaEditor } from '../../components/editor/EstruturaEditor';
import { AulaDrawer } from '../../components/editor/AulaDrawer';
import { TreinamentoFormDrawer } from '../../components/treinamentos/TreinamentoFormDrawer';
import { botaoPrimario, botaoSecundario, campo } from '../../components/editor/estilos';

/** Montagem do conteúdo de um treinamento (mesmo editor das disciplinas, sem aulas de avaliação). */
export const TreinamentoEditorPage: React.FC = () => {
  const { treinamentoId = '' } = useParams();
  const navigate = useNavigate();
  const [treinamento, setTreinamento] = useState<Treinamento | null>(null);
  const [capitulos, setCapitulos] = useState<Capitulo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [novoCapitulo, setNovoCapitulo] = useState('');
  const [criandoCap, setCriandoCap] = useState(false);
  const [drawer, setDrawer] = useState<{ capitulo: Capitulo; aula: Aula | null } | null>(null);
  const [editando, setEditando] = useState(false);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      const e = await treinamentosAdminApi.estrutura(treinamentoId);
      setTreinamento(e.treinamento);
      setCapitulos(e.capitulos);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar o treinamento.'));
    } finally {
      setCarregando(false);
    }
  }, [treinamentoId]);

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

  const reordenar = async (antes: Capitulo[], payload: ReordenarPayload) => {
    try {
      await treinamentosAdminApi.reordenar(treinamentoId, payload);
    } catch (e) {
      setCapitulos(antes);
      setErro(mensagemErro(e, 'Não foi possível salvar a nova ordem.'));
    }
  };

  const criarCapitulo = async () => {
    const titulo = novoCapitulo.trim();
    if (!titulo) return;
    setCriandoCap(true);
    await executar(async () => {
      const c = await treinamentosAdminApi.criarCapitulo(treinamentoId, { titulo, publicado: true });
      setCapitulos((l) => [...l, c]);
      setNovoCapitulo('');
    });
    setCriandoCap(false);
  };

  const substituirCapitulo = (c: Capitulo) => setCapitulos((l) => l.map((x) => (x.id === c.id ? c : x)));
  const aulaAlterada = (aula: Aula) =>
    setCapitulos((l) => l.map((c) => (c.id !== aula.capitulo_id ? c
      : { ...c, aulas: c.aulas.some((a) => a.id === aula.id) ? c.aulas.map((a) => (a.id === aula.id ? aula : a)) : [...c.aulas, aula] })));

  if (carregando) return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;
  if (!treinamento) {
    return (
      <div className="max-w-3xl space-y-4">
        <Link to="/admin/treinamentos" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Treinamentos</Link>
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      </div>
    );
  }

  const t = treinamento;
  const totalAulas = capitulos.reduce((s, c) => s + c.aulas.length, 0);
  const totalMin = capitulos.reduce((s, c) => s + c.aulas.reduce((x, a) => x + (a.duracao_min || 0), 0), 0);
  const publico = t.perfis_alvo.map((p) => PERFIS_ALVO.find((x) => x.valor === p)?.rotulo ?? p).join(', ');

  return (
    <div className="max-w-6xl space-y-6">
      <Link to="/admin/treinamentos" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Treinamentos</Link>

      <header className="flex flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl md:flex-row md:items-center">
        <div className="aspect-video w-full shrink-0 overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-blue-900/60 to-slate-950 md:w-56">
          {t.capa_url && <img src={urlArquivo(t.capa_url)} alt="" className="h-full w-full object-cover" />}
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-bold ${CATEGORIA[t.categoria].classe}`}>{CATEGORIA[t.categoria].rotulo}</span>
          <h1 className="text-2xl font-extrabold text-white md:text-3xl">{t.titulo}</h1>
          <div className="flex flex-wrap gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1"><Layers size={13} /> {capitulos.length} capítulos</span>
            <span className="flex items-center gap-1"><PlayCircle size={13} /> {totalAulas} aulas</span>
            {totalMin > 0 && <span>{formatarDuracao(totalMin)} de conteúdo</span>}
            {t.carga_horaria ? <span>{t.carga_horaria}h de carga horária</span> : null}
            <span className="flex items-center gap-1"><Users size={13} /> {publico}{t.polos.length + t.escolas.length ? ` · ${t.polos.length + t.escolas.length} unidade(s)` : ''}</span>
            {t.certificado_ativo && <span className="flex items-center gap-1"><Award size={13} /> com certificado</span>}
          </div>
        </div>
        <div className="flex flex-col gap-3 md:items-end">
          <span className={`self-start rounded-full px-3 py-1 text-xs font-bold md:self-end ${t.publicado ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-800 text-slate-300'}`}>
            {t.publicado ? 'Publicado' : 'Rascunho'}
          </span>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={totalAulas === 0} onClick={() => navigate(`/admin/treinamentos/${t.id}/previa`)} className={botaoSecundario}>
              <Eye size={15} /> Pré-visualizar
            </button>
            <button type="button" onClick={() => setEditando(true)} className={botaoSecundario}><Pencil size={15} /> Dados</button>
            <button type="button" onClick={() => void executar(async () => setTreinamento(await treinamentosAdminApi.alternar(t.id)),
              t.publicado ? 'Treinamento despublicado.' : 'Treinamento publicado.')}
              className={t.publicado ? botaoSecundario : botaoPrimario}>
              {t.publicado ? 'Despublicar' : 'Publicar'}
            </button>
          </div>
        </div>
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
        <h2 className="flex items-center gap-2 text-lg font-bold text-white"><ListOrdered size={18} className="text-nexus-yellow" /> Estrutura</h2>
        {capitulos.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
            <Layers className="mx-auto mb-3 text-slate-600" size={32} />
            <p className="text-sm text-slate-300">Comece criando o primeiro capítulo.</p>
          </div>
        )}
        <EstruturaEditor
          capitulos={capitulos}
          setCapitulos={setCapitulos}
          onReordenar={reordenar}
          onRenomearCapitulo={(c, titulo) =>
            void executar(async () => substituirCapitulo(await avaAdminApi.atualizarCapitulo(c.id, { titulo, descricao: c.descricao, publicado: c.publicado })))}
          onPublicarCapitulo={(c) =>
            void executar(async () => substituirCapitulo(await avaAdminApi.atualizarCapitulo(c.id, { titulo: c.titulo, descricao: c.descricao, publicado: !c.publicado })))}
          onDuplicarCapitulo={(c) => void executar(async () => { await avaAdminApi.duplicarCapitulo(c.id); await carregar(); }, 'Capítulo duplicado (oculto até você publicar).')}
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
          <input value={novoCapitulo} onChange={(e) => setNovoCapitulo(e.target.value)} maxLength={255} placeholder="Título do novo capítulo" className={campo} />
          <button type="submit" disabled={!novoCapitulo.trim() || criandoCap} className={`${botaoPrimario} shrink-0`}>
            {criandoCap ? <Loader2 size={14} className="animate-spin" /> : <Plus size={16} />} Novo capítulo
          </button>
        </form>
      </section>

      {drawer && (
        <AulaDrawer
          key={drawer.aula?.id ?? `nova-${drawer.capitulo.id}`}
          reordenarItens={(payload) => treinamentosAdminApi.reordenar(treinamentoId, payload)}
          permitirAvaliacao={false}
          capituloId={drawer.capitulo.id}
          capituloTitulo={drawer.capitulo.titulo}
          aula={drawer.aula}
          onFechar={() => setDrawer(null)}
          onAlterada={aulaAlterada}
        />
      )}
      {editando && (
        <TreinamentoFormDrawer treinamento={t} onFechar={() => setEditando(false)}
          onSalvo={(novo) => { setEditando(false); setTreinamento(novo); setAviso('Dados salvos.'); }} />
      )}
    </div>
  );
};
