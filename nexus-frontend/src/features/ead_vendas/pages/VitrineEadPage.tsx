import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle, ArrowRight, BookOpen, CalendarDays, CreditCard, GraduationCap, Laptop, Loader2, Sparkles, Trophy, Users,
} from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { CabecalhoPublico } from '../components/CabecalhoPublico';
import { TurmaVitrine, brl, dataBr, vitrineApi } from '../api';

const PASSOS = [
  { icone: Users, titulo: 'Escolha sua turma', texto: 'Inscrição gratuita: crie seu acesso em menos de 2 minutos.' },
  { icone: CalendarDays, titulo: 'Siga o calendário', texto: 'As disciplinas são liberadas em sequência, no ritmo da turma.' },
  { icone: CreditCard, titulo: 'Pague por disciplina', texto: 'Pix ou boleto, só quando a disciplina abrir. Sem mensalidade.' },
  { icone: Trophy, titulo: 'Estude e conquiste', texto: 'Videoaulas, materiais, avaliações online, XP e ranking.' },
];

const CardTurma: React.FC<{ t: TurmaVitrine }> = ({ t }) => {
  const ultimas = t.vagas_restantes != null && t.vagas_restantes > 0 && t.vagas_restantes <= 10;
  const lotada = t.vagas_restantes === 0;
  return (
    <article className="group flex flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/70 shadow-xl transition hover:-translate-y-1 hover:border-nexus-yellow/50 hover:shadow-nexus-glow">
      <div className="relative bg-gradient-to-br from-blue-900 via-indigo-950 to-slate-950 p-6">
        <div className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full bg-nexus-yellow/10 blur-2xl" />
        <div className="relative flex items-start justify-between gap-3">
          <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-nexus-yellow">
            {t.codigo || 'Turma EAD'}
          </span>
          {lotada ? (
            <span className="rounded-full bg-red-500/20 px-3 py-1 text-[11px] font-bold text-red-200">Vagas esgotadas</span>
          ) : ultimas ? (
            <span className="animate-pulse rounded-full bg-amber-500/20 px-3 py-1 text-[11px] font-bold text-amber-200">
              Últimas {t.vagas_restantes} vagas
            </span>
          ) : null}
        </div>
        <h3 className="relative mt-4 text-2xl font-extrabold text-white">{t.nome}</h3>
        <p className="relative mt-1 text-sm font-semibold text-blue-200">{t.curso_nome}</p>
      </div>
      <div className="flex flex-1 flex-col gap-4 p-6">
        {t.curso_descricao && <p className="line-clamp-3 text-sm text-slate-400">{t.curso_descricao}</p>}
        <ul className="grid grid-cols-2 gap-3 text-xs text-slate-300">
          <li className="flex items-center gap-2"><CalendarDays size={14} className="text-nexus-yellow" />
            {t.data_inicio ? `Início ${dataBr(t.data_inicio)}` : 'Início imediato'}</li>
          <li className="flex items-center gap-2"><BookOpen size={14} className="text-nexus-yellow" /> {t.total_disciplinas} disciplinas</li>
          {t.semestres ? <li className="flex items-center gap-2"><GraduationCap size={14} className="text-nexus-yellow" /> {t.semestres} semestres</li> : null}
          <li className="flex items-center gap-2"><Laptop size={14} className="text-nexus-yellow" /> 100% online</li>
        </ul>
        <div className="mt-auto flex items-end justify-between gap-3 border-t border-slate-800 pt-4">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-slate-500">Matrícula gratuita</p>
            <p className="text-sm text-slate-300">
              <span className="text-2xl font-extrabold text-white">{brl(t.valor_minimo ?? 45)}</span> / disciplina
            </p>
          </div>
        </div>
        <Link to={`/matricula-ead/${t.id}`}
          className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3.5 text-sm font-extrabold transition ${
            lotada ? 'pointer-events-none border border-slate-700 text-slate-500' : 'bg-nexus-yellow text-ink hover:bg-nexus-yellow-hover group-hover:gap-3'}`}>
          {lotada ? 'Turma lotada' : <>Matricule-se na {t.nome} <ArrowRight size={16} /></>}
        </Link>
      </div>
    </article>
  );
};

/** Página pública de vendas do EAD: Turmas EAD abertas para matrícula. */
export const VitrineEadPage: React.FC = () => {
  const [turmas, setTurmas] = useState<TurmaVitrine[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'Matrícula EAD · NEXUS';
    vitrineApi.turmas().then(setTurmas).catch((e) => setErro(mensagemErro(e, 'Não foi possível carregar as turmas agora.')));
  }, []);

  return (
    <div className="min-h-screen bg-nexus-page text-slate-100">
      <CabecalhoPublico />

      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute -left-40 top-0 h-[28rem] w-[28rem] rounded-full bg-blue-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -right-32 top-20 h-80 w-80 rounded-full bg-nexus-yellow/10 blur-3xl" />
        <div className="relative mx-auto max-w-6xl px-4 pb-14 pt-14 text-center sm:pt-20">
          <p className="mx-auto inline-flex items-center gap-2 rounded-full border border-nexus-yellow/30 bg-nexus-yellow/10 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-nexus-yellow">
            <Sparkles size={14} /> Inscrições abertas
          </p>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-extrabold leading-tight text-white sm:text-5xl">
            Estude de onde estiver, <span className="text-nexus-yellow">no seu ritmo</span>.
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-300">
            Matrícula <b className="text-white">gratuita</b>. Você só paga cada disciplina quando ela for liberada:
            <b className="text-white"> {turmas?.length ? `a partir de ${brl(Math.min(...turmas.map((t) => t.valor_minimo ?? 45)))}` : 'R$ 45,00'}</b>,
            com o livro físico opcional.
          </p>
          <a href="#turmas" className="mt-8 inline-flex items-center gap-2 rounded-2xl bg-nexus-yellow px-6 py-4 text-base font-extrabold text-ink shadow-lg shadow-nexus-yellow/20 hover:bg-nexus-yellow-hover">
            Ver turmas abertas <ArrowRight size={18} />
          </a>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 sm:grid-cols-2 lg:grid-cols-4">
        {PASSOS.map((p, i) => (
          <div key={p.titulo} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300"><p.icone size={20} /></span>
            <p className="mt-3 text-[11px] font-bold uppercase tracking-wider text-slate-500">Passo {i + 1}</p>
            <p className="font-bold text-white">{p.titulo}</p>
            <p className="mt-1 text-sm text-slate-400">{p.texto}</p>
          </div>
        ))}
      </section>

      <section id="turmas" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16">
        <h2 className="text-3xl font-extrabold text-white">Turmas EAD abertas</h2>
        <p className="mt-1 text-slate-400">Escolha a turma e garanta sua vaga.</p>
        <div className="mt-8">
          {erro ? (
            <p role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
              <AlertCircle size={18} /> {erro}
            </p>
          ) : !turmas ? (
            <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>
          ) : turmas.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-700 p-12 text-center">
              <GraduationCap className="mx-auto mb-3 text-slate-600" size={40} />
              <p className="text-slate-300">Nenhuma turma com inscrições abertas no momento. Volte em breve!</p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {turmas.map((t) => <CardTurma key={t.id} t={t} />)}
            </div>
          )}
        </div>
      </section>

      <footer className="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
        NEXUS 2.0 · ETADEMP — Educação a Distância
      </footer>
    </div>
  );
};
