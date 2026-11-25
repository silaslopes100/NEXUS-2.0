import React from 'react';
import {
  BookOpen,
  CheckCircle2,
  Crown,
  Flame,
  GraduationCap,
  Lock,
  Medal,
  Play,
  Rocket,
  Star,
  Trophy,
  Zap,
} from 'lucide-react';
import { urlArquivo } from '@/lib/uploadDireto';
import { Conquista, Nivel, RankingItem } from '../../alunoApi';

const ICONES: Record<string, React.ElementType> = {
  play: Play,
  rocket: Rocket,
  zap: Zap,
  book: BookOpen,
  check: CheckCircle2,
  star: Star,
  graduation: GraduationCap,
  trophy: Trophy,
  flame: Flame,
  crown: Crown,
  medal: Medal,
};

export const iconeConquista = (nome: string) => ICONES[nome] || Medal;

/** Medalha de conquista (colorida quando obtida, cinza com cadeado quando bloqueada). */
export const ConquistaBadge: React.FC<{ conquista: Conquista; tamanho?: 'sm' | 'md' | 'lg'; mostrarTexto?: boolean }> = ({
  conquista: c, tamanho = 'md', mostrarTexto = true,
}) => {
  const Icone = iconeConquista(c.icone);
  const obtida = !!c.obtida_em;
  const dim = { sm: 'h-10 w-10', md: 'h-16 w-16', lg: 'h-24 w-24' }[tamanho];
  const ic = { sm: 18, md: 28, lg: 44 }[tamanho];
  return (
    <div className={`flex flex-col items-center text-center ${mostrarTexto ? 'gap-2' : ''}`} title={`${c.nome}: ${c.descricao}`}>
      <span className={`relative flex ${dim} items-center justify-center rounded-full border-2 ${obtida ? '' : 'border-slate-700 bg-slate-900 text-slate-600'}`}
        style={obtida ? { borderColor: c.cor, background: `${c.cor}22`, color: c.cor, boxShadow: `0 0 24px ${c.cor}33` } : undefined}>
        <Icone size={ic} />
        {!obtida && (
          <span className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-slate-400">
            <Lock size={10} />
          </span>
        )}
      </span>
      {mostrarTexto && (
        <span>
          <span className={`block text-xs font-bold ${obtida ? 'text-white' : 'text-slate-400'}`}>{c.nome}</span>
          <span className="block text-[11px] leading-tight text-slate-500">{c.descricao}</span>
          {c.xp_bonus > 0 && <span className="mt-0.5 block text-[10px] font-semibold text-nexus-yellow">+{c.xp_bonus} XP</span>}
        </span>
      )}
    </div>
  );
};

/** Anel de nível com o número no centro. */
export const AnelNivel: React.FC<{ nivel: Nivel; tamanho?: number }> = ({ nivel, tamanho = 64 }) => {
  const r = (tamanho - 8) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center" style={{ width: tamanho, height: tamanho }}>
      <svg width={tamanho} height={tamanho} className="-rotate-90">
        <circle cx={tamanho / 2} cy={tamanho / 2} r={r} fill="none" stroke="currentColor" strokeWidth={6} className="text-slate-800" />
        <circle cx={tamanho / 2} cy={tamanho / 2} r={r} fill="none" stroke="#FFB800" strokeWidth={6} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={circ * (1 - nivel.progresso_pct / 100)} className="transition-all duration-700" />
      </svg>
      <span className="absolute flex flex-col items-center leading-none">
        <span className="text-[9px] font-semibold uppercase text-slate-400">nível</span>
        <span className="text-xl font-black text-white">{nivel.nivel}</span>
      </span>
    </span>
  );
};

/** Barra de XP até o próximo nível. */
export const BarraXp: React.FC<{ nivel: Nivel }> = ({ nivel }) => (
  <div className="min-w-0 flex-1">
    <div className="mb-1 flex items-baseline justify-between gap-2">
      <span className="truncate text-sm font-bold text-white">{nivel.nome}</span>
      <span className="shrink-0 text-[11px] text-slate-400">
        <strong className="text-nexus-yellow">{nivel.xp_total}</strong> / {nivel.xp_proximo} XP
      </span>
    </div>
    <div className="h-2 overflow-hidden rounded-full bg-slate-800">
      <div className="h-full rounded-full bg-gradient-to-r from-nexus-yellow to-orange-400 transition-all duration-700" style={{ width: `${nivel.progresso_pct}%` }} />
    </div>
    <p className="mt-1 text-[11px] text-slate-500">Faltam {Math.max(0, nivel.xp_proximo - nivel.xp_total)} XP para o nível {nivel.nivel + 1}</p>
  </div>
);

/** Chip da sequência de dias de estudo. */
export const StreakChip: React.FC<{ dias: number; hoje: boolean }> = ({ dias, hoje }) => (
  <span className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 ${dias ? 'border-orange-500/40 bg-orange-500/10' : 'border-slate-700 bg-slate-900/60'}`}
    title={hoje ? 'Você já estudou hoje' : dias ? 'Conclua uma aula hoje para manter a sequência' : 'Conclua uma aula para começar uma sequência'}>
    <Flame size={18} className={dias ? (hoje ? 'text-orange-400' : 'animate-pulse text-orange-300') : 'text-slate-500'} />
    <span className="text-sm font-black text-white">{dias}</span>
    <span className="text-xs text-slate-400">{dias === 1 ? 'dia seguido' : 'dias seguidos'}</span>
  </span>
);

const MEDALHAS = ['#FACC15', '#CBD5E1', '#F59E0B'];

const Avatar: React.FC<{ item: RankingItem; tamanho?: string }> = ({ item, tamanho = 'h-9 w-9' }) =>
  item.foto_url ? (
    <img src={urlArquivo(item.foto_url)} alt="" className={`${tamanho} shrink-0 rounded-full object-cover`} />
  ) : (
    <span className={`${tamanho} flex shrink-0 items-center justify-center rounded-full bg-blue-600/30 text-xs font-bold text-blue-100`}>
      {item.nome.slice(0, 1).toUpperCase()}
    </span>
  );

/** Lista do ranking (com destaque para o próprio aluno). */
export const RankingLista: React.FC<{ itens: RankingItem[]; minha?: RankingItem | null; compacto?: boolean }> = ({ itens, minha, compacto }) => (
  <ol className="space-y-1.5">
    {itens.map((i) => (
      <li key={i.usuario_id}
        className={`flex items-center gap-3 rounded-xl px-3 ${compacto ? 'py-1.5' : 'py-2.5'} ${i.eu ? 'border border-nexus-yellow/40 bg-nexus-yellow/10' : 'bg-slate-900/60'}`}>
        <span className="flex w-6 shrink-0 justify-center text-sm font-black" style={{ color: MEDALHAS[i.posicao - 1] || '#94A3B8' }}>
          {i.posicao <= 3 ? <Medal size={18} /> : i.posicao}
        </span>
        <Avatar item={i} tamanho={compacto ? 'h-7 w-7' : 'h-9 w-9'} />
        <span className="min-w-0 flex-1">
          <span className={`block truncate text-sm ${i.eu ? 'font-bold text-white' : 'text-slate-200'}`}>{i.nome}{i.eu && ' (você)'}</span>
          {!compacto && <span className="text-[11px] text-slate-500">Nível {i.nivel}</span>}
        </span>
        <span className="shrink-0 text-sm font-bold text-nexus-yellow">{i.xp} XP</span>
      </li>
    ))}
    {minha && !itens.some((i) => i.eu) && (
      <>
        <li className="py-0.5 text-center text-xs text-slate-600">⋯</li>
        <li className="flex items-center gap-3 rounded-xl border border-nexus-yellow/40 bg-nexus-yellow/10 px-3 py-2">
          <span className="w-6 shrink-0 text-center text-sm font-black text-slate-300">{minha.posicao}</span>
          <Avatar item={minha} tamanho="h-7 w-7" />
          <span className="min-w-0 flex-1 truncate text-sm font-bold text-white">{minha.nome} (você)</span>
          <span className="shrink-0 text-sm font-bold text-nexus-yellow">{minha.xp} XP</span>
        </li>
      </>
    )}
  </ol>
);

export { Avatar as AvatarRanking };
