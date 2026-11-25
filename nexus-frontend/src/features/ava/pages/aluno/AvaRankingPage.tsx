import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Crown, EyeOff, Loader2, Trophy, Users } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { Ranking, RankingItem, gamificacaoApi } from '../../alunoApi';
import { AvatarRanking, RankingLista } from '../../components/gamificacao/Gamificacao';

const ALTURAS = ['h-32', 'h-24', 'h-20'];
const CORES = ['from-yellow-400/40 border-yellow-400/60', 'from-slate-300/30 border-slate-300/50', 'from-amber-600/30 border-amber-600/50'];

const Podio: React.FC<{ itens: RankingItem[] }> = ({ itens }) => {
  const ordem = [itens[1], itens[0], itens[2]].filter(Boolean) as RankingItem[];
  return (
    <div className="flex items-end justify-center gap-3 sm:gap-6">
      {ordem.map((i) => (
        <div key={i.usuario_id} className="flex w-24 flex-col items-center gap-2 sm:w-32">
          {i.posicao === 1 && <Crown className="text-yellow-400" size={26} />}
          <AvatarRanking item={i} tamanho={i.posicao === 1 ? 'h-16 w-16' : 'h-12 w-12'} />
          <span className={`w-full truncate text-center text-sm ${i.eu ? 'font-bold text-nexus-yellow' : 'font-semibold text-white'}`}>{i.nome}</span>
          <div className={`flex w-full flex-col items-center justify-start rounded-t-2xl border-x border-t bg-gradient-to-b to-transparent pt-3 ${CORES[i.posicao - 1]} ${ALTURAS[i.posicao - 1]}`}>
            <span className="text-2xl font-black text-white">{i.posicao}º</span>
            <span className="text-xs font-bold text-nexus-yellow">{i.xp} XP</span>
          </div>
        </div>
      ))}
    </div>
  );
};

/** Ranking do curso: semana corrente (zera toda segunda) ou geral. */
export const AvaRankingPage: React.FC = () => {
  const [periodo, setPeriodo] = useState<'semana' | 'geral'>('semana');
  const [cursoId, setCursoId] = useState<string | null>(null);
  const [dados, setDados] = useState<Ranking | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setDados(await gamificacaoApi.ranking(periodo, cursoId, 50));
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível carregar o ranking.'));
    } finally {
      setCarregando(false);
    }
  }, [periodo, cursoId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const alternarVisibilidade = async () => {
    if (!dados) return;
    try {
      await gamificacaoApi.definirRankingVisivel(!dados.ranking_visivel);
      await carregar();
    } catch (e) {
      setErro(mensagemErro(e));
    }
  };

  const itens = dados?.itens ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link to="/aluno/ava" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Sala de Aula Virtual</Link>

      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-extrabold text-white"><Trophy className="text-nexus-yellow" /> Ranking</h1>
          <p className="mt-1 text-sm text-slate-400">
            {periodo === 'semana' ? 'Quem mais estudou nesta semana. O placar zera toda segunda-feira.' : 'XP acumulado desde o início do curso.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {dados && dados.cursos.length > 1 && (
            <select value={dados.curso?.id ?? ''} onChange={(e) => setCursoId(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-nexus-yellow focus:outline-none">
              {dados.cursos.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          )}
          <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900/60 p-1">
            {([['semana', 'Semana'], ['geral', 'Geral']] as const).map(([v, r]) => (
              <button key={v} type="button" onClick={() => setPeriodo(v)}
                className={`rounded-lg px-4 py-1.5 text-sm font-semibold ${periodo === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
                {r}
              </button>
            ))}
          </div>
        </div>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      {carregando && !dados ? (
        <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
      ) : dados && !dados.curso ? (
        <p className="rounded-2xl border border-dashed border-slate-700 p-10 text-center text-sm text-slate-400">O ranking aparece quando você estiver matriculado em um curso EAD.</p>
      ) : dados ? (
        <>
          <section className={`space-y-6 rounded-3xl border border-slate-800 bg-gradient-to-b from-blue-950/40 to-slate-900/60 p-6 transition-opacity ${carregando ? 'opacity-60' : ''}`}>
            <p className="flex items-center justify-center gap-2 text-xs text-slate-400">
              <Users size={14} /> {dados.curso?.nome} · {dados.total_participantes} participante(s)
            </p>
            {itens.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">Ninguém pontuou ainda {periodo === 'semana' ? 'nesta semana' : ''}. Seja o primeiro! 🚀</p>
            ) : (
              <>
                <Podio itens={itens.slice(0, 3)} />
                {itens.length > 3 && <RankingLista itens={itens.slice(3)} minha={dados.minha_posicao} />}
                {itens.length <= 3 && dados.minha_posicao && !itens.some((i) => i.eu) && (
                  <RankingLista itens={[]} minha={dados.minha_posicao} />
                )}
              </>
            )}
          </section>

          <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:flex-row sm:items-center">
            <EyeOff size={18} className="shrink-0 text-slate-400" />
            <p className="flex-1 text-sm text-slate-300">
              {dados.ranking_visivel
                ? 'Seu nome aparece no ranking (primeiro nome e inicial do sobrenome).'
                : 'Você não aparece para os colegas no ranking. Seu XP e suas medalhas continuam contando.'}
            </p>
            <button type="button" onClick={() => void alternarVisibilidade()}
              className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800">
              {dados.ranking_visivel ? 'Sair do ranking' : 'Voltar ao ranking'}
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
};
