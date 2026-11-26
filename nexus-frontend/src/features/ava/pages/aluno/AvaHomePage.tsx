import React, { useEffect, useMemo, useState } from 'react';
import { SomToggle } from '../../components/gamificacao/SomToggle';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Award, BookOpenCheck, CheckCircle2, Clock, GraduationCap, Loader2, Lock, Play, PlayCircle, Sparkles, Trophy } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { urlArquivo } from '@/lib/uploadDireto';
import { formatarDuracao } from '../../api';
import { DisciplinaAluno, HomeAva, PerfilGamificacao, Ranking, SITUACAO, avaAlunoApi, gamificacaoApi, saudacao } from '../../alunoApi';
import { AnelNivel, BarraXp, ConquistaBadge, RankingLista, StreakChip } from '../../components/gamificacao/Gamificacao';

type Filtro = 'todas' | 'andamento' | 'concluidas' | 'bloqueadas';

const ABERTAS = new Set(['liberada', 'concluida']);

const Capa: React.FC<{ url?: string | null; nome: string; className?: string }> = ({ url, nome, className = '' }) =>
  url ? (
    <img src={urlArquivo(url)} alt="" className={`h-full w-full object-cover ${className}`} />
  ) : (
    <span className={`flex h-full w-full items-center justify-center bg-gradient-to-br from-blue-800 via-indigo-900 to-slate-950 text-4xl font-black text-white/15 ${className}`}>
      {nome.slice(0, 2).toUpperCase()}
    </span>
  );

const CardDisciplina: React.FC<{ d: DisciplinaAluno }> = ({ d }) => {
  const navigate = useNavigate();
  const aberta = ABERTAS.has(d.situacao);
  const s = SITUACAO[d.situacao];
  const cta =
    d.situacao === 'concluida' ? 'Revisar' : d.aulas_concluidas ? 'Continuar' : 'Começar';
  return (
    <article className={`group flex flex-col overflow-hidden rounded-2xl border bg-slate-900/70 transition ${
      aberta ? 'border-slate-800 hover:-translate-y-1 hover:border-nexus-yellow/50 hover:shadow-nexus-glow' : 'border-slate-800/70'}`}>
      <div className="relative aspect-video overflow-hidden">
        <Capa url={d.capa_url} nome={d.nome} className={aberta ? 'transition duration-500 group-hover:scale-105' : 'grayscale'} />
        <span className={`absolute left-3 top-3 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${s.classe}`}>{s.rotulo}</span>
        {!aberta && (
          <span className="absolute inset-0 flex items-center justify-center bg-slate-950/50">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-900/90 text-slate-300"><Lock size={20} /></span>
          </span>
        )}
        {aberta && (
          <span className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/30 group-hover:opacity-100">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-nexus-yellow text-ink shadow-xl"><Play size={24} className="ml-1" /></span>
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="line-clamp-2 font-bold leading-snug text-white">{d.nome}</h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {d.total_aulas ? `${d.total_aulas} aulas` : 'Em preparação'}
            {d.duracao_min ? ` · ${formatarDuracao(d.duracao_min)}` : ''}
          </p>
        </div>
        {aberta ? (
          <div className="mt-auto space-y-3">
            <div>
              <div className="mb-1 flex justify-between text-[11px] text-slate-400">
                <span>{d.aulas_concluidas}/{d.total_aulas} concluídas</span>
                <span className="font-bold text-white">{d.progresso_pct}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div className={`h-full rounded-full ${d.situacao === 'concluida' ? 'bg-emerald-400' : 'bg-nexus-yellow'}`} style={{ width: `${d.progresso_pct}%` }} />
              </div>
            </div>
            <button type="button" onClick={() => navigate(`/aluno/ava/disciplinas/${d.id}`)}
              className={`w-full rounded-xl py-2.5 text-sm font-bold transition ${
                d.situacao === 'concluida' ? 'border border-slate-700 text-slate-200 hover:bg-slate-800' : 'bg-nexus-yellow text-ink hover:bg-nexus-yellow-hover'}`}>
              {cta}
            </button>
          </div>
        ) : (
          <div className="mt-auto space-y-2">
            <p className="text-xs text-slate-400">
              {d.situacao === 'em_breve' ? 'O conteúdo estará disponível em breve.'
                : d.situacao === 'pagamento_pendente' ? 'Aguardando a confirmação do pagamento.'
                  : d.situacao === 'prazo_expirado' ? 'O prazo de conclusão terminou.'
                    : 'Libere esta disciplina para começar a estudar.'}
            </p>
            {(d.situacao === 'bloqueada' || d.situacao === 'prazo_expirado' || d.situacao === 'pagamento_pendente') && (
              <Link to={`/aluno/compras?disciplina=${d.id}`} className="block w-full rounded-xl border border-nexus-yellow/50 py-2.5 text-center text-sm font-bold text-nexus-yellow hover:bg-nexus-yellow/10">
                {d.situacao === 'pagamento_pendente' ? 'Ver pagamento' : 'Liberar disciplina'}
              </Link>
            )}
          </div>
        )}
      </div>
    </article>
  );
};

/** Sala de Aula Virtual do aluno EAD: continuar de onde parou + disciplinas do curso. */
export const AvaHomePage: React.FC = () => {
  const navigate = useNavigate();
  const [dados, setDados] = useState<HomeAva | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<Filtro>('todas');
  const [perfil, setPerfil] = useState<PerfilGamificacao | null>(null);
  const [ranking, setRanking] = useState<Ranking | null>(null);

  useEffect(() => {
    avaAlunoApi.home().then(setDados).catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar a Sala de Aula Virtual.')));
    // A gamificação é complementar: se falhar, a página segue sem ela.
    gamificacaoApi.perfil().then(setPerfil).catch(() => undefined);
    gamificacaoApi.ranking('semana', null, 5).then(setRanking).catch(() => undefined);
  }, []);

  const lista = useMemo(() => {
    const ds = dados?.disciplinas ?? [];
    if (filtro === 'andamento') return ds.filter((d) => d.situacao === 'liberada');
    if (filtro === 'concluidas') return ds.filter((d) => d.situacao === 'concluida');
    if (filtro === 'bloqueadas') return ds.filter((d) => !ABERTAS.has(d.situacao));
    return ds;
  }, [dados, filtro]);

  if (erro) {
    return (
      <div role="alert" className="mx-auto mt-10 flex max-w-xl items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" /> {erro}
      </div>
    );
  }
  if (!dados) return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;

  const { continuar, resumo } = dados;
  const porCurso = lista.reduce<Record<string, DisciplinaAluno[]>>((acc, d) => {
    (acc[d.curso_nome || 'Disciplinas avulsas'] ||= []).push(d);
    return acc;
  }, {});
  const contagem: Record<Filtro, number> = {
    todas: dados.disciplinas.length,
    andamento: dados.disciplinas.filter((d) => d.situacao === 'liberada').length,
    concluidas: dados.disciplinas.filter((d) => d.situacao === 'concluida').length,
    bloqueadas: dados.disciplinas.filter((d) => !ABERTAS.has(d.situacao)).length,
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950 shadow-2xl">
        <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-nexus-yellow/10 blur-3xl" />
        <div className="relative grid gap-5 p-5 sm:gap-6 sm:p-8 lg:grid-cols-[1fr_minmax(0,420px)] lg:items-center">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <p className="flex items-center gap-2 text-sm font-semibold text-nexus-yellow"><Sparkles size={16} /> Sala de Aula Virtual</p>
              <SomToggle />
            </div>
            <h1 className="text-2xl font-extrabold leading-tight text-white sm:text-4xl">{saudacao()}, {dados.nome}!</h1>
            <p className="max-w-lg text-slate-300">
              {continuar ? 'Bora continuar? Sua próxima aula está te esperando.' : resumo.disciplinas_liberadas ? 'Escolha uma disciplina e comece a estudar.' : 'Assim que uma disciplina for liberada, ela aparece aqui.'}
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              {[
                { icone: CheckCircle2, valor: resumo.aulas_concluidas, rotulo: 'aulas concluídas' },
                { icone: GraduationCap, valor: resumo.disciplinas_concluidas, rotulo: 'disciplinas concluídas' },
                { icone: Clock, valor: formatarDuracao(resumo.minutos_estudados) || '0min', rotulo: 'de estudo' },
              ].map(({ icone: Icone, valor, rotulo }) => (
                <span key={rotulo} className="flex items-center gap-2 rounded-xl border border-slate-700/70 bg-slate-950/50 px-3 py-2">
                  <Icone size={16} className="text-nexus-yellow" />
                  <span className="text-sm font-bold text-white">{valor}</span>
                  <span className="text-xs text-slate-400">{rotulo}</span>
                </span>
              ))}
            </div>
          </div>

          {continuar && (
            <button type="button" onClick={() => navigate(`/aluno/ava/disciplinas/${continuar.disciplina_id}/aulas/${continuar.aula_id}`)}
              className="group overflow-hidden rounded-2xl border border-slate-700 bg-slate-950/70 text-left shadow-xl transition hover:border-nexus-yellow/60">
              <div className="relative aspect-[16/8]">
                <Capa url={continuar.capa_url} nome={continuar.disciplina_nome} />
                <span className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent" />
                <span className="absolute bottom-3 left-4 right-4">
                  <span className="block text-[11px] font-semibold uppercase tracking-wide text-nexus-yellow">Continuar de onde parei</span>
                  <span className="block truncate text-lg font-bold text-white">{continuar.aula_titulo}</span>
                  <span className="block truncate text-xs text-slate-300">{continuar.disciplina_nome} · {continuar.capitulo_titulo}</span>
                </span>
                <span className="absolute right-4 top-4 flex h-12 w-12 items-center justify-center rounded-full bg-nexus-yellow text-ink shadow-xl transition group-hover:scale-110">
                  <Play size={22} className="ml-0.5" />
                </span>
              </div>
              <div className="flex items-center gap-3 px-4 py-3">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full bg-nexus-yellow" style={{ width: `${continuar.progresso_pct}%` }} />
                </div>
                <span className="text-xs font-bold text-white">{continuar.progresso_pct}%</span>
              </div>
            </button>
          )}
        </div>
      </section>

      {/* Gamificação */}
      {perfil && (
        <section className="grid gap-4 lg:grid-cols-3">
          <Link to="/aluno/ava/conquistas"
            className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition hover:border-nexus-yellow/50">
            <div className="flex items-center gap-4">
              <AnelNivel nivel={perfil.nivel} />
              <BarraXp nivel={perfil.nivel} />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <StreakChip dias={perfil.streak_atual} hoje={perfil.estudou_hoje} />
              <span className="text-xs text-slate-400"><strong className="text-white">{perfil.xp_semana}</strong> XP nesta semana</span>
            </div>
          </Link>

          <Link to="/aluno/ava/conquistas"
            className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition hover:border-nexus-yellow/50">
            <p className="flex items-center justify-between text-sm font-bold text-white">
              <span className="flex items-center gap-2"><Award size={16} className="text-nexus-yellow" /> Medalhas</span>
              <span className="text-xs font-normal text-slate-400">
                {perfil.conquistas.filter((c) => c.obtida_em).length}/{perfil.conquistas.length}
              </span>
            </p>
            <div className="flex flex-1 items-center justify-around gap-2">
              {[...perfil.conquistas]
                .sort((a, b) => Number(!!b.obtida_em) - Number(!!a.obtida_em) || String(b.obtida_em).localeCompare(String(a.obtida_em)))
                .slice(0, 4)
                .map((c) => <ConquistaBadge key={c.codigo} conquista={c} tamanho="sm" mostrarTexto={false} />)}
            </div>
            <p className="text-xs text-slate-500">
              {perfil.conquistas.find((c) => !c.obtida_em)
                ? `Próxima: ${perfil.conquistas.find((c) => !c.obtida_em)!.nome} — ${perfil.conquistas.find((c) => !c.obtida_em)!.descricao}`
                : 'Você desbloqueou todas as medalhas! 🏆'}
            </p>
          </Link>

          <Link to="/aluno/ava/ranking"
            className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition hover:border-nexus-yellow/50">
            <p className="flex items-center gap-2 text-sm font-bold text-white"><Trophy size={16} className="text-nexus-yellow" /> Ranking da semana</p>
            {ranking && ranking.itens.length > 0 ? (
              <RankingLista itens={ranking.itens} minha={ranking.minha_posicao} compacto />
            ) : (
              <p className="flex-1 text-sm text-slate-400">Ninguém pontuou nesta semana ainda. Conclua uma aula e saia na frente!</p>
            )}
          </Link>
        </section>
      )}

      {/* Disciplinas */}
      <section className="space-y-5">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <h2 className="flex items-center gap-2 text-xl font-bold text-white"><BookOpenCheck size={20} className="text-nexus-yellow" /> Minhas disciplinas</h2>
          <div className="flex gap-1 overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 p-1">
            {([['todas', 'Todas'], ['andamento', 'Em andamento'], ['concluidas', 'Concluídas'], ['bloqueadas', 'Bloqueadas']] as const).map(([v, r]) => (
              <button key={v} type="button" onClick={() => setFiltro(v)}
                className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold ${filtro === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
                {r} <span className="opacity-60">{contagem[v]}</span>
              </button>
            ))}
          </div>
        </div>

        {dados.disciplinas.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700 p-12 text-center">
            <PlayCircle className="mx-auto mb-3 text-slate-600" size={36} />
            <p className="text-slate-300">Você ainda não tem disciplinas EAD.</p>
            <Link to="/aluno/compras" className="mt-3 inline-block text-sm font-semibold text-nexus-yellow hover:underline">Ver cursos e matrículas EAD</Link>
          </div>
        ) : lista.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-400">Nenhuma disciplina neste filtro.</p>
        ) : (
          Object.entries(porCurso).map(([curso, ds]) => (
            <div key={curso} className="space-y-3">
              {Object.keys(porCurso).length > 1 && <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{curso}</h3>}
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {ds.map((d) => <CardDisciplina key={d.id} d={d} />)}
              </div>
            </div>
          ))
        )}
      </section>
    </div>
  );
};
