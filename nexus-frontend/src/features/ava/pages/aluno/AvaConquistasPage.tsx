import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Award, Flame, History, Loader2, TrendingUp, Trophy } from 'lucide-react';
import { mensagemErro, tempoRelativo } from '@/features/comunicacao/api';
import { PerfilGamificacao, gamificacaoApi } from '../../alunoApi';
import { AnelNivel, BarraXp, ConquistaBadge, StreakChip } from '../../components/gamificacao/Gamificacao';

const XP_POR_ACAO = [
  ['Concluir uma aula', '+10 XP'],
  ['Concluir um capítulo', '+50 XP'],
  ['Ser aprovado numa avaliação', '+100 XP'],
  ['Nota 9 ou mais na avaliação', '+50 XP'],
  ['Concluir uma disciplina', '+200 XP'],
  ['Estudar todo dia (sequência)', 'até +35 XP/dia'],
] as const;

/** Nível, sequência de dias, conquistas e histórico de XP do aluno. */
export const AvaConquistasPage: React.FC = () => {
  const [perfil, setPerfil] = useState<PerfilGamificacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    gamificacaoApi.perfil().then(setPerfil).catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar suas conquistas.')));
  }, []);

  if (erro) {
    return (
      <div role="alert" className="mx-auto mt-10 flex max-w-xl items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" /> {erro}
      </div>
    );
  }
  if (!perfil) return <div className="flex justify-center py-24 text-blue-400"><Loader2 className="animate-spin" /></div>;

  const obtidas = perfil.conquistas.filter((c) => c.obtida_em).length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link to="/aluno/ava" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Sala de Aula Virtual</Link>

      <section className="grid gap-4 rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-900 to-blue-950/50 p-6 md:grid-cols-[auto_1fr_auto] md:items-center">
        <AnelNivel nivel={perfil.nivel} tamanho={110} />
        <div className="space-y-3">
          <h1 className="text-3xl font-extrabold text-white">Minhas conquistas</h1>
          <BarraXp nivel={perfil.nivel} />
        </div>
        <div className="flex flex-wrap gap-2 md:flex-col">
          <StreakChip dias={perfil.streak_atual} hoje={perfil.estudou_hoje} />
          <span className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2">
            <TrendingUp size={18} className="text-emerald-400" />
            <span className="text-sm font-black text-white">{perfil.xp_semana}</span>
            <span className="text-xs text-slate-400">XP nesta semana</span>
          </span>
          <span className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-3 py-2">
            <Flame size={18} className="text-red-400" />
            <span className="text-sm font-black text-white">{perfil.streak_recorde}</span>
            <span className="text-xs text-slate-400">recorde de dias</span>
          </span>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><Award size={18} className="text-nexus-yellow" /> Medalhas</h2>
          <span className="text-sm text-slate-400"><strong className="text-white">{obtidas}</strong> de {perfil.conquistas.length}</span>
        </div>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {perfil.conquistas.map((c) => <ConquistaBadge key={c.codigo} conquista={c} />)}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><History size={18} className="text-nexus-yellow" /> Últimos ganhos</h2>
          {perfil.historico.length === 0 ? (
            <p className="text-sm text-slate-500">Conclua sua primeira aula para começar a ganhar XP.</p>
          ) : (
            <ul className="divide-y divide-slate-800">
              {perfil.historico.map((e, i) => (
                <li key={`${e.tipo}-${i}`} className="flex items-center gap-3 py-2.5">
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm text-slate-200">{e.rotulo}</span>
                    {e.descricao && <span className="block truncate text-[11px] text-slate-500">{e.descricao}</span>}
                  </span>
                  {e.criado_em && <span className="shrink-0 text-[11px] text-slate-500">{tempoRelativo(e.criado_em)}</span>}
                  <span className="w-16 shrink-0 text-right text-sm font-bold text-nexus-yellow">+{e.xp}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><Trophy size={18} className="text-nexus-yellow" /> Como ganhar XP</h2>
          <ul className="divide-y divide-slate-800">
            {XP_POR_ACAO.map(([acao, xp]) => (
              <li key={acao} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                <span className="text-slate-300">{acao}</span>
                <span className="shrink-0 font-bold text-nexus-yellow">{xp}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500">As medalhas também dão XP de bônus. Cada aula conta uma vez só.</p>
          <Link to="/aluno/ava/ranking" className="inline-block text-sm font-semibold text-nexus-yellow hover:underline">Ver o ranking do curso →</Link>
        </section>
      </div>
    </div>
  );
};
