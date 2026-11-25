import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Award,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Eye,
  ListVideo,
  Loader2,
  PartyPopper,
  RotateCcw,
  Trophy,
  X,
} from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { formatarNota, Resultado } from '@/features/avaliacoes/api';
import { RealizarAvaliacao } from '@/features/avaliacoes/components/RealizarAvaliacao';
import { formatarDuracao } from '../../api';
import { AulaAluno, Conclusao, DisciplinaPlayer, PlayerApi, Recompensa, avaAlunoApi } from '../../alunoApi';
import { CelebracaoRecompensa } from '../../components/gamificacao/CelebracaoRecompensa';
import { VideoEmbed, VideoEmbedHandle } from '../../components/player/VideoEmbed';
import { ConteudoItem } from '../../components/player/ConteudoItem';
import { SidebarCapitulos } from '../../components/player/SidebarCapitulos';
import { AbasAula } from '../../components/player/AbasAula';
import { soltarConfete } from '../../utils/confete';

interface Props {
  /** Pré-visualização do admin: sem travas e sem gravar progresso. */
  previa?: boolean;
  /** Treinamento (Polo/Escola/Professor) usa o mesmo player com outra API e outros caminhos. */
  modo?: 'disciplina' | 'treinamento';
  api?: PlayerApi;
  /** Baixa o certificado (treinamentos). */
  onBaixarCertificado?: (id: string) => Promise<void>;
}

const CAMINHOS = {
  disciplina: { base: '/aluno/ava/disciplinas', voltar: '/aluno/ava', admin: '/admin/ava/disciplinas', item: 'Disciplina' },
  treinamento: { base: '/treinamentos', voltar: '/treinamentos', admin: '/admin/treinamentos', item: 'Treinamento' },
} as const;

interface Aviso {
  id: number;
  texto: string;
  tipo: 'sucesso' | 'info';
}

/** Player da disciplina (estilo Hotmart/Kiwify): conteúdo à esquerda, trilha de aulas à direita. */
export const AvaDisciplinaPage: React.FC<Props> = ({ previa = false, modo = 'disciplina', api = avaAlunoApi, onBaixarCertificado }) => {
  const { disciplinaId = '', aulaId } = useParams();
  const navigate = useNavigate();
  const cam = CAMINHOS[modo];
  const base = previa ? `${cam.admin}/${disciplinaId}/previa` : `${cam.base}/${disciplinaId}`;
  const voltar = previa ? `${cam.admin}/${disciplinaId}` : cam.voltar;
  const [baixando, setBaixando] = useState(false);
  const baixarCertificado = async () => {
    if (!onBaixarCertificado) return;
    setBaixando(true);
    try {
      await onBaixarCertificado(disciplinaId);
    } catch (e) {
      avisar(e instanceof Error && e.message ? e.message : 'Não foi possível gerar o certificado.', 'info');
    } finally {
      setBaixando(false);
    }
  };

  const [disciplina, setDisciplina] = useState<DisciplinaPlayer | null>(null);
  const [aula, setAula] = useState<AulaAluno | null>(null);
  const [carregandoAula, setCarregandoAula] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [erroAula, setErroAula] = useState<string | null>(null);
  const [concluindo, setConcluindo] = useState(false);
  const [modoProva, setModoProva] = useState(false);
  const [trilhaMobile, setTrilhaMobile] = useState(false);
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const [celebracao, setCelebracao] = useState<'disciplina' | null>(null);
  const [recompensa, setRecompensa] = useState<Recompensa | null>(null);
  const video = useRef<VideoEmbedHandle>(null);
  const enviado = useRef({ pct: 0, em: 0 });

  const avisar = useCallback((texto: string, tipo: Aviso['tipo'] = 'sucesso') => {
    const id = Date.now() + Math.random();
    setAvisos((l) => [...l, { id, texto, tipo }]);
    window.setTimeout(() => setAvisos((l) => l.filter((a) => a.id !== id)), 3500);
  }, []);

  const carregarDisciplina = useCallback(async () => {
    try {
      const d = await api.disciplina(disciplinaId);
      setDisciplina(d);
      return d;
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível abrir a disciplina.'));
      return null;
    }
  }, [disciplinaId, api]);

  useEffect(() => {
    setDisciplina(null);
    setErro(null);
    void carregarDisciplina();
  }, [carregarDisciplina]);

  // Sem aula na URL: abre a próxima (ou a primeira disponível).
  useEffect(() => {
    if (!disciplina || aulaId) return;
    const primeira = disciplina.capitulos.flatMap((c) => c.aulas).find((a) => a.status !== 'bloqueada');
    const alvo = disciplina.proxima_aula_id || primeira?.id;
    if (alvo) navigate(`${base}/aulas/${alvo}`, { replace: true });
  }, [disciplina, aulaId, base, navigate]);

  useEffect(() => {
    if (!aulaId) return;
    let ativo = true;
    setCarregandoAula(true);
    setErroAula(null);
    setModoProva(false);
    setTrilhaMobile(false);
    enviado.current = { pct: 0, em: Date.now() };
    api
      .aula(aulaId)
      .then((a) => {
        if (!ativo) return;
        setAula(a);
        enviado.current.pct = a.percentual;
      })
      .catch((e) => ativo && setErroAula(mensagemErro(e, 'Não foi possível abrir a aula.')))
      .finally(() => ativo && setCarregandoAula(false));
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return () => {
      ativo = false;
    };
  }, [aulaId, api]);

  // ------------------------------------------------------------------ conclusão

  const aplicarConclusao = useCallback(
    async (c: Conclusao) => {
      setAula((a) => (a && a.id === c.aula_id ? { ...a, status: 'concluida', percentual: 100 } : a));
      await carregarDisciplina();
      const r = c.recompensa;
      const xp = r && r.xp_ganho > 0 ? ` · +${r.xp_ganho} XP` : '';
      const fogo = r && r.streak_atual > 1 ? ` · 🔥 ${r.streak_atual} dias` : '';
      const especial = !!r && (r.subiu_nivel || r.conquistas.length > 0);
      if (especial) setRecompensa(r);
      if (c.ja_estava_concluida) {
        if (especial) soltarConfete();
        return;
      }
      if (c.disciplina_concluida) {
        soltarConfete(3200);
        setCelebracao('disciplina');
        if (xp) avisar(`${cam.item} concluída${xp}`);
      } else if (c.capitulo_concluido) {
        soltarConfete();
        avisar(`Capítulo concluído! Continue assim 🚀${xp}`);
      } else {
        if (especial) soltarConfete();
        avisar(`Aula concluída ✓${xp}${fogo}`);
      }
    },
    [carregarDisciplina, avisar],
  );

  const concluirEAvancar = async () => {
    if (!aula) return;
    if (previa || aula.status === 'concluida') {
      if (aula.proxima_id) navigate(`${base}/aulas/${aula.proxima_id}`);
      return;
    }
    setConcluindo(true);
    try {
      const c = await api.concluir(aula.id);
      await aplicarConclusao(c);
      if (c.proxima_aula_id && !c.disciplina_concluida) navigate(`${base}/aulas/${c.proxima_aula_id}`);
    } catch (e) {
      avisar(mensagemErro(e), 'info');
    } finally {
      setConcluindo(false);
    }
  };

  const aoAndamento = useCallback(
    (pct: number, pos: number) => {
      if (previa || !aula || aula.status === 'concluida') return;
      const agora = Date.now();
      const ultimo = enviado.current;
      if (pct < 90 && pct < ultimo.pct + 10 && agora - ultimo.em < 30_000) return;
      enviado.current = { pct: Math.max(pct, ultimo.pct), em: agora };
      api
        .progresso(aula.id, pct, Math.floor(pos))
        .then((c) => c && aplicarConclusao(c))
        .catch(() => undefined);
    },
    [previa, aula, aplicarConclusao, api],
  );

  const aoResultadoProva = useCallback(
    async (r: Resultado) => {
      if (!aula || !r.aprovado) return;
      try {
        await aplicarConclusao(await api.concluir(aula.id));
      } catch {
        /* a conclusão também acontece ao reabrir a aula */
      }
    },
    [aula, aplicarConclusao, api],
  );

  // ------------------------------------------------------------------ render

  if (erro) {
    return (
      <div className="mx-auto max-w-xl space-y-4 py-10">
        <Link to={voltar} className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Voltar</Link>
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          <AlertCircle size={18} className="mt-0.5 shrink-0 text-amber-300" /> {erro}
        </div>
      </div>
    );
  }
  if (!disciplina) return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;

  const d = disciplina.disciplina;
  const semAulas = disciplina.capitulos.every((c) => c.aulas.length === 0);
  const videos = aula?.itens.filter((i) => i.tipo === 'video_embed') ?? [];
  const outros = aula?.itens.filter((i) => i.tipo !== 'video_embed') ?? [];
  const av = aula?.avaliacao;

  const trilha = (
    <SidebarCapitulos capitulos={disciplina.capitulos} aulaAtualId={aulaId}
      onAbrir={(id) => navigate(`${base}/aulas/${id}`)} />
  );

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 pb-24">
      {previa && (
        <div className="flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-sm text-blue-100">
          <Eye size={16} /> Pré-visualização como aluno: todas as aulas abertas e nada é gravado.
          <Link to={voltar} className="ml-auto font-semibold text-blue-200 underline">Voltar ao editor</Link>
        </div>
      )}

      {/* Cabeçalho da disciplina */}
      <header className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 sm:flex-row sm:items-center">
        <Link to={voltar} aria-label="Voltar" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white">
          <ArrowLeft size={18} />
        </Link>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs uppercase tracking-wide text-slate-500">{d.curso_nome}</p>
          <h1 className="truncate text-lg font-bold text-white sm:text-xl">{d.nome}</h1>
        </div>
        <div className="flex items-center gap-3 sm:w-72">
          <div className="flex-1">
            <div className="mb-1 flex justify-between text-[11px] text-slate-400">
              <span>{d.aulas_concluidas} de {d.total_aulas} aulas</span>
              <span className="font-bold text-white">{d.progresso_pct}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-gradient-to-r from-nexus-yellow to-emerald-400 transition-all duration-700" style={{ width: `${d.progresso_pct}%` }} />
            </div>
          </div>
          {d.progresso_pct === 100 && <Trophy className="text-nexus-yellow" size={22} />}
          {disciplina.certificado_disponivel && onBaixarCertificado && (
            <button type="button" onClick={() => void baixarCertificado()} disabled={baixando}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-emerald-500 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-400 disabled:opacity-50">
              {baixando ? <Loader2 size={14} className="animate-spin" /> : <Award size={14} />} Certificado
            </button>
          )}
        </div>
      </header>

      {semAulas ? (
        <div className="rounded-2xl border border-dashed border-slate-700 p-12 text-center text-slate-400">
          O conteúdo desta disciplina está sendo preparado.
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          {/* Conteúdo */}
          <main className="min-w-0 space-y-5">
            {carregandoAula && !aula ? (
              <div className="flex aspect-video items-center justify-center rounded-2xl bg-slate-900 text-blue-400"><Loader2 className="animate-spin" /></div>
            ) : erroAula ? (
              <div role="alert" className="flex items-start gap-2 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 text-sm text-amber-100">
                <AlertCircle size={18} className="mt-0.5 shrink-0 text-amber-300" /> {erroAula}
              </div>
            ) : aula ? (
              <div className={`space-y-5 transition-opacity ${carregandoAula ? 'opacity-50' : ''}`}>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-nexus-yellow">
                    {aula.capitulo_titulo} · Aula {aula.numero} de {aula.total_aulas}
                  </p>
                  <h2 className="mt-1 text-2xl font-extrabold text-white sm:text-3xl">{aula.titulo}</h2>
                  <p className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    {aula.duracao_min ? <span className="flex items-center gap-1"><Clock size={12} /> {formatarDuracao(aula.duracao_min)}</span> : null}
                    {aula.status === 'concluida' && <span className="flex items-center gap-1 text-emerald-300"><CheckCircle2 size={12} /> Concluída</span>}
                  </p>
                </div>

                {aula.tipo === 'avaliacao' ? (
                  modoProva && !previa ? (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6">
                      <RealizarAvaliacao
                        chave={aula.id}
                        iniciar={() => api.iniciarAvaliacao!(aula.id)}
                        rotuloVoltar="Voltar à aula"
                        rotuloSair="Sair e continuar depois (o tempo continua contando)"
                        semTentativas="Você usou todas as tentativas desta avaliação. Fale com a secretaria EAD."
                        onResultado={(r) => void aoResultadoProva(r)}
                        onVoltar={() => {
                          setModoProva(false);
                          void api.aula(aula.id).then(setAula).catch(() => undefined);
                        }}
                      />
                    </div>
                  ) : av ? (
                    <div className="overflow-hidden rounded-2xl border border-blue-500/30 bg-gradient-to-br from-blue-950/60 to-slate-900">
                      <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center">
                        <span className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl ${av.aprovado ? 'bg-emerald-500/20 text-emerald-300' : 'bg-blue-500/20 text-blue-200'}`}>
                          {av.aprovado ? <Trophy size={30} /> : <ClipboardCheck size={30} />}
                        </span>
                        <div className="min-w-0 flex-1 space-y-1">
                          <h3 className="text-xl font-bold text-white">{av.titulo}</h3>
                          <p className="text-sm text-slate-300">
                            {av.total_questoes} questões
                            {av.tempo_limite_min ? ` · ${av.tempo_limite_min} min` : ' · sem limite de tempo'}
                            {` · nota mínima ${formatarNota(av.nota_minima)}`}
                          </p>
                          <p className="text-xs text-slate-400">
                            {av.tentativas_usadas}/{av.tentativas_max} tentativas usadas
                            {av.melhor_nota != null && ` · sua melhor nota: ${formatarNota(av.melhor_nota)}`}
                          </p>
                        </div>
                        {av.aprovado ? (
                          <span className="rounded-xl bg-emerald-500/15 px-4 py-2 text-sm font-bold text-emerald-300">Aprovado ✓</span>
                        ) : (
                          <button type="button" disabled={previa || !av.pode_realizar} onClick={() => setModoProva(true)}
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-nexus-yellow px-6 py-3 text-base font-bold text-ink shadow-nexus-glow hover:bg-nexus-yellow-hover disabled:cursor-not-allowed disabled:opacity-50">
                            {av.tentativa_aberta_id ? <><RotateCcw size={18} /> Continuar avaliação</> : <>Iniciar avaliação <ArrowRight size={18} /></>}
                          </button>
                        )}
                      </div>
                      {av.instrucoes && <p className="whitespace-pre-line border-t border-slate-800 px-6 py-4 text-sm text-slate-300">{av.instrucoes}</p>}
                      {!av.ativa && <p className="border-t border-slate-800 px-6 py-3 text-xs text-amber-300">Esta avaliação ainda não está disponível.</p>}
                      {av.ativa && !av.aprovado && !av.pode_realizar && !previa && (
                        <p className="border-t border-slate-800 px-6 py-3 text-xs text-amber-300">Você usou todas as tentativas. Fale com a secretaria EAD.</p>
                      )}
                    </div>
                  ) : (
                    <p className="rounded-2xl border border-slate-800 p-6 text-sm text-slate-400">Avaliação não configurada.</p>
                  )
                ) : (
                  <>
                    {videos.map((v, i) => (
                      <div key={v.id} className="space-y-2">
                        <VideoEmbed ref={i === 0 ? video : undefined} item={v}
                          inicioSeg={i === 0 && aula.status !== 'concluida' ? aula.posicao_seg : null}
                          onAndamento={i === 0 ? aoAndamento : undefined} />
                        {videos.length > 1 && v.titulo && <p className="text-sm font-semibold text-slate-200">{v.titulo}</p>}
                      </div>
                    ))}
                    {outros.map((item) => <ConteudoItem key={item.id} item={item} />)}
                    {aula.itens.length === 0 && (
                      <p className="rounded-2xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">Esta aula ainda não tem conteúdos.</p>
                    )}
                  </>
                )}

                {!modoProva && (
                  <AbasAula api={api} aula={aula} previa={previa} posicaoVideo={() => video.current?.posicao() ?? null}
                    onIrPara={(seg) => {
                      video.current?.irPara(seg);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }} />
                )}
              </div>
            ) : null}
          </main>

          {/* Trilha (desktop) */}
          <aside className="hidden lg:block">
            <div className="sticky top-20 max-h-[calc(100vh-10rem)] space-y-3 overflow-y-auto pr-1">
              <p className="flex items-center gap-2 px-1 text-xs font-bold uppercase tracking-wide text-slate-400"><ListVideo size={14} /> Conteúdo</p>
              {trilha}
            </div>
          </aside>
        </div>
      )}

      {/* Barra de navegação fixa */}
      {aula && !modoProva && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-800 bg-slate-950/95 backdrop-blur lg:left-72">
          <div className="mx-auto flex max-w-[1400px] items-center gap-2 px-3 py-3 sm:px-6">
            <button type="button" disabled={!aula.anterior_id} onClick={() => aula.anterior_id && navigate(`${base}/aulas/${aula.anterior_id}`)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2.5 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-40">
              <ArrowLeft size={16} /> <span className="hidden sm:inline">Anterior</span>
            </button>
            <button type="button" onClick={() => setTrilhaMobile(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-3 py-2.5 text-sm text-slate-200 hover:bg-slate-800 lg:hidden">
              <ListVideo size={16} /> Aulas
            </button>
            <div className="flex-1" />
            {aula.tipo === 'avaliacao' && aula.status !== 'concluida' ? (
              aula.proxima_id && (
                <button type="button" onClick={() => navigate(`${base}/aulas/${aula.proxima_id}`)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800">
                  Pular por enquanto <ArrowRight size={16} />
                </button>
              )
            ) : (
              <button type="button" onClick={() => void concluirEAvancar()} disabled={concluindo || (aula.status === 'concluida' && !aula.proxima_id)}
                className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-5 py-2.5 text-sm font-bold text-ink shadow-nexus-glow hover:bg-nexus-yellow-hover disabled:opacity-50 sm:px-6">
                {concluindo ? <Loader2 size={16} className="animate-spin" /> : aula.status === 'concluida' ? null : <CheckCircle2 size={16} />}
                {aula.status === 'concluida' || previa
                  ? aula.proxima_id ? 'Próxima aula' : 'Última aula'
                  : aula.proxima_id ? 'Concluir e avançar' : 'Concluir aula'}
                {(aula.status === 'concluida' || previa || aula.proxima_id) && <ArrowRight size={16} />}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Trilha (mobile, bottom sheet) */}
      {trilhaMobile && (
        <div className="fixed inset-0 z-50 flex items-end bg-black/60 lg:hidden" onClick={() => setTrilhaMobile(false)}>
          <div className="max-h-[80vh] w-full overflow-y-auto rounded-t-3xl border-t border-slate-700 bg-slate-950 p-4" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <p className="font-bold text-white">Conteúdo da disciplina</p>
              <button type="button" onClick={() => setTrilhaMobile(false)} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800"><X size={18} /></button>
            </div>
            {trilha}
          </div>
        </div>
      )}

      {/* Avisos */}
      <div className="pointer-events-none fixed bottom-20 right-4 z-[60] flex flex-col items-end gap-2" aria-live="polite">
        {avisos.map((a) => (
          <div key={a.id} className={`rounded-xl border px-4 py-3 text-sm font-semibold shadow-2xl ${
            a.tipo === 'sucesso' ? 'border-emerald-500/30 bg-emerald-950/95 text-emerald-100' : 'border-amber-500/30 bg-amber-950/95 text-amber-100'}`}>
            {a.texto}
          </div>
        ))}
      </div>

      {/* Conquista nova / subida de nível (depois da celebração da disciplina, se houver) */}
      {recompensa && !celebracao && <CelebracaoRecompensa recompensa={recompensa} onFechar={() => setRecompensa(null)} />}

      {/* Celebração de disciplina concluída */}
      {celebracao && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4" onClick={() => setCelebracao(null)}>
          <div role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-3xl border border-nexus-yellow/40 bg-gradient-to-b from-slate-900 to-slate-950 p-8 text-center shadow-nexus-glow">
            <span className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-nexus-yellow/15 text-nexus-yellow">
              <PartyPopper size={40} />
            </span>
            <h2 className="text-2xl font-extrabold text-white">{cam.item} concluíd{modo === 'treinamento' ? 'o' : 'a'}!</h2>
            <p className="mt-2 text-sm text-slate-300">
              Parabéns! Você finalizou <strong className="text-white">{d.nome}</strong>.
              {modo === 'treinamento'
                ? disciplina.certificado_disponivel ? ' Seu certificado já está disponível.' : ''
                : ' Que tal começar a próxima?'}
            </p>
            <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
              <button type="button" onClick={() => setCelebracao(null)} className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800">
                Revisar conteúdo
              </button>
              {modo === 'treinamento' && disciplina.certificado_disponivel && onBaixarCertificado ? (
                <button type="button" onClick={() => void baixarCertificado()} disabled={baixando}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-nexus-yellow px-5 py-2.5 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
                  {baixando ? <Loader2 size={16} className="animate-spin" /> : <Award size={16} />} Baixar certificado
                </button>
              ) : (
                <button type="button" onClick={() => navigate(cam.voltar)}
                  className="rounded-xl bg-nexus-yellow px-5 py-2.5 text-sm font-bold text-ink hover:bg-nexus-yellow-hover">
                  {modo === 'treinamento' ? 'Ver treinamentos' : 'Ver minhas disciplinas'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
