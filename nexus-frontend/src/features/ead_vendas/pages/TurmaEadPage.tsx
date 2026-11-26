import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle, ArrowLeft, BookMarked, BookOpen, CalendarDays, Check, ChevronDown, Clock, Eye, EyeOff, GraduationCap,
  Loader2, Lock, ShieldCheck,
} from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { soltarConfete } from '@/features/ava/utils/confete';
import { useAuthStore } from '@/stores/authStore';
import { CabecalhoPublico } from '../components/CabecalhoPublico';
import { DisciplinaVitrine, TurmaVitrineDetalhe, brl, dataBr, lojaApi, vitrineApi } from '../api';

const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none focus:ring-1 focus:ring-nexus-yellow/30';
const rotulo = 'mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-400';

const soDigitos = (v: string) => v.replace(/\D/g, '');
const mascaraCpf = (v: string) =>
  soDigitos(v).slice(0, 11).replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
const mascaraCelular = (v: string) => {
  const d = soDigitos(v).slice(0, 11);
  return d.length <= 10 ? d.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{4})(\d)/, '$1-$2')
    : d.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
};

const FAQ = [
  ['A matrícula tem custo?', 'Não. A inscrição na turma é gratuita: você paga apenas cada disciplina, quando ela for liberada.'],
  ['Como as disciplinas são liberadas?', 'Seguindo o calendário da turma. Cada disciplina tem um prazo para ser concluída; ao terminar o prazo, abre a próxima.'],
  ['E se eu não concluir no prazo?', 'A disciplina é encerrada e você pode comprá-la novamente para refazer, com um prazo novo.'],
  ['Preciso do livro físico?', 'Não. Todo o conteúdo está na plataforma. O livro é um complemento opcional, enviado para o seu endereço.'],
  ['Como faço as avaliações?', 'As avaliações são online, dentro da Sala de Aula Virtual.'],
];

const LinhaDisciplina: React.FC<{ d: DisciplinaVitrine; ordem: number; sequencial: boolean }> = ({ d, ordem, sequencial }) => (
  <li className="flex items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-500/15 text-sm font-bold text-blue-200">{ordem}</span>
    <div className="min-w-0 flex-1">
      <p className="truncate font-semibold text-white">{d.nome}</p>
      <p className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-slate-400">
        <span className="flex items-center gap-1"><CalendarDays size={11} />
          {d.libera_em_prevista ? `Libera em ${dataBr(d.libera_em_prevista)}` : sequencial ? 'Após a disciplina anterior' : 'No início da turma'}
        </span>
        {d.prazo_dias ? <span className="flex items-center gap-1"><Clock size={11} /> {d.prazo_dias} dias para concluir</span> : null}
        {d.carga_horaria ? <span>{d.carga_horaria}h</span> : null}
        {d.livro_disponivel && <span className="flex items-center gap-1 text-nexus-yellow"><BookMarked size={11} /> livro +{brl(d.valor_livro_ead)}</span>}
      </p>
    </div>
    <span className="shrink-0 text-sm font-bold text-white">{brl(d.valor_ead)}</span>
  </li>
);

/** Detalhe público da Turma EAD com a grade, o calendário previsto e a inscrição gratuita. */
export const TurmaEadPage: React.FC = () => {
  const { turmaId = '' } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, user, setSession } = useAuthStore();
  const [turma, setTurma] = useState<TurmaVitrineDetalhe | null>(null);
  const [erroCarga, setErroCarga] = useState<string | null>(null);
  const [etapa, setEtapa] = useState<1 | 2>(1);
  const [form, setForm] = useState({ nome: '', sobrenome: '', cpf: '', data_nascimento: '', celular: '', email: '', senha: '', confirmar: '', site: '' });
  const [aceite, setAceite] = useState(false);
  const [verSenha, setVerSenha] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [faq, setFaq] = useState<number | null>(0);

  useEffect(() => {
    vitrineApi.turma(turmaId).then((t) => { setTurma(t); document.title = `${t.nome} · Matrícula EAD`; })
      .catch((e) => setErroCarga(mensagemErro(e, 'Turma não encontrada.')));
  }, [turmaId]);

  const semestres = useMemo(() => {
    const grupos = new Map<number, DisciplinaVitrine[]>();
    (turma?.disciplinas ?? []).forEach((d) => {
      const s = d.semestre || 0;
      grupos.set(s, [...(grupos.get(s) ?? []), d]);
    });
    return [...grupos.entries()].sort(([a], [b]) => a - b);
  }, [turma]);

  const alunoEad = isAuthenticated && !!user?.aluno_ead;
  const logadoOutro = isAuthenticated && !user?.aluno_ead;
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    let v = e.target.value;
    if (k === 'cpf') v = mascaraCpf(v);
    if (k === 'celular') v = mascaraCelular(v);
    setForm((f) => ({ ...f, [k]: v }));
  };

  const etapa1Ok = form.nome.trim().length >= 2 && form.sobrenome.trim() && soDigitos(form.cpf).length === 11
    && form.data_nascimento && soDigitos(form.celular).length >= 10;
  const etapa2Ok = /\S+@\S+\.\S+/.test(form.email) && form.senha.length >= 8 && form.senha === form.confirmar && aceite;

  const concluir = (destino: string) => {
    soltarConfete(2600);
    navigate(destino, { replace: true });
  };

  const inscrever = async () => {
    if (!turma) return;
    setEnviando(true);
    setErro(null);
    try {
      const r = await vitrineApi.inscrever({
        turma_id: turma.id, nome: form.nome.trim(), sobrenome: form.sobrenome.trim(), email: form.email.trim(),
        cpf: soDigitos(form.cpf), celular: soDigitos(form.celular), data_nascimento: form.data_nascimento,
        senha: form.senha, aceite_termos: aceite, site: form.site,
      });
      setSession(r.access_token, r.refresh_token, r.usuario, r.perfil || r.usuario.perfil, r.permissoes || []);
      concluir('/aluno/compras?bemvindo=1');
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível concluir a inscrição.'));
    } finally {
      setEnviando(false);
    }
  };

  const entrarComoAluno = async () => {
    if (!turma) return;
    setEnviando(true);
    setErro(null);
    try {
      await lojaApi.entrarNaTurma(turma.id);
      concluir('/aluno/compras?bemvindo=1');
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível entrar na turma.'));
    } finally {
      setEnviando(false);
    }
  };

  if (erroCarga) {
    return (
      <div className="min-h-screen bg-nexus-page text-slate-100">
        <CabecalhoPublico />
        <div className="mx-auto max-w-xl space-y-4 px-4 py-16 text-center">
          <AlertCircle className="mx-auto text-red-400" size={36} />
          <p className="text-slate-300">{erroCarga}</p>
          <Link to="/matricula-ead" className="inline-flex items-center gap-1 font-semibold text-nexus-yellow"><ArrowLeft size={15} /> Ver turmas abertas</Link>
        </div>
      </div>
    );
  }
  if (!turma) return <div className="flex min-h-screen items-center justify-center bg-nexus-page text-blue-400"><Loader2 className="animate-spin" /></div>;

  const lotada = turma.vagas_restantes === 0;
  const sequencial = turma.liberacao !== 'todas_no_inicio';
  let ordem = 0;

  return (
    <div className="min-h-screen bg-nexus-page text-slate-100">
      <CabecalhoPublico />

      <section className="relative overflow-hidden border-b border-slate-800 bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950">
        <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-nexus-yellow/10 blur-3xl" />
        <div className="relative mx-auto max-w-6xl px-4 py-10">
          <Link to="/matricula-ead" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white"><ArrowLeft size={14} /> Turmas abertas</Link>
          <p className="mt-5 text-xs font-bold uppercase tracking-widest text-nexus-yellow">{turma.codigo || 'Turma EAD'}</p>
          <h1 className="mt-1 text-3xl font-extrabold text-white sm:text-4xl">{turma.nome}</h1>
          <p className="mt-1 text-lg font-semibold text-blue-200">{turma.curso_nome}</p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-white/10 px-3 py-1.5 text-slate-200">
              <CalendarDays size={12} className="mr-1 inline" />{turma.data_inicio ? `Início ${dataBr(turma.data_inicio)}` : 'Início imediato'}
            </span>
            <span className="rounded-full bg-white/10 px-3 py-1.5 text-slate-200"><BookOpen size={12} className="mr-1 inline" />{turma.total_disciplinas} disciplinas</span>
            {turma.carga_horaria_total ? <span className="rounded-full bg-white/10 px-3 py-1.5 text-slate-200">{turma.carga_horaria_total}h</span> : null}
            {turma.vagas_restantes != null && (
              <span className={`rounded-full px-3 py-1.5 font-bold ${turma.vagas_restantes <= 10 ? 'bg-amber-500/20 text-amber-200' : 'bg-emerald-500/15 text-emerald-200'}`}>
                {lotada ? 'Vagas esgotadas' : `${turma.vagas_restantes} vagas restantes`}
              </span>
            )}
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 lg:grid-cols-[1fr_400px]">
        <div className="space-y-10">
          {turma.curso_descricao && (
            <section>
              <h2 className="text-xl font-bold text-white">Sobre o curso</h2>
              <p className="mt-2 whitespace-pre-line text-slate-300">{turma.curso_descricao}</p>
            </section>
          )}

          <section className="space-y-4">
            <div>
              <h2 className="text-xl font-bold text-white">Grade e calendário previsto</h2>
              <p className="text-sm text-slate-400">
                Datas previstas para quem se matricula hoje. Cada disciplina é comprada quando for liberada.
              </p>
            </div>
            {semestres.map(([s, lista]) => (
              <div key={s} className="space-y-2">
                {s > 0 && <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{s}º semestre</p>}
                <ul className="space-y-2">
                  {lista.map((d) => { ordem += 1; return <LinhaDisciplina key={d.id} d={d} ordem={ordem} sequencial={sequencial} />; })}
                </ul>
              </div>
            ))}
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-bold text-white">Perguntas frequentes</h2>
            {FAQ.map(([p, r], i) => (
              <div key={p} className="rounded-2xl border border-slate-800 bg-slate-900/60">
                <button type="button" onClick={() => setFaq(faq === i ? null : i)}
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold text-white">
                  {p} <ChevronDown size={16} className={`shrink-0 transition ${faq === i ? 'rotate-180' : ''}`} />
                </button>
                {faq === i && <p className="px-4 pb-4 text-sm text-slate-400">{r}</p>}
              </div>
            ))}
          </section>
        </div>

        <aside className="order-first lg:sticky lg:top-20 lg:order-none lg:self-start">
          <div className="space-y-5 rounded-3xl border border-slate-700 bg-slate-900/90 p-6 shadow-2xl">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-300">Matrícula gratuita</p>
              <p className="text-sm text-slate-300">
                Disciplinas a partir de <span className="text-2xl font-extrabold text-white">{brl(turma.valor_minimo ?? 45)}</span>
              </p>
              <ul className="mt-3 space-y-1.5 text-xs text-slate-300">
                {['Pague só quando a disciplina abrir (Pix ou boleto)', 'Videoaulas, materiais e avaliações online', 'Livro físico opcional, entregue em casa'].map((x) => (
                  <li key={x} className="flex items-start gap-2"><Check size={14} className="mt-0.5 shrink-0 text-emerald-400" /> {x}</li>
                ))}
              </ul>
            </div>

            {erro && <p role="alert" className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200"><AlertCircle size={16} className="mt-0.5 shrink-0" /> {erro}</p>}

            {lotada ? (
              <p className="rounded-xl border border-slate-700 p-4 text-center text-sm text-slate-300">As vagas desta turma esgotaram.</p>
            ) : alunoEad ? (
              <button type="button" onClick={() => void entrarComoAluno()} disabled={enviando}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-nexus-yellow py-4 text-sm font-extrabold text-ink hover:bg-nexus-yellow-hover disabled:opacity-60">
                {enviando && <Loader2 size={16} className="animate-spin" />} Entrar na {turma.nome}
              </button>
            ) : logadoOutro ? (
              <p className="rounded-xl border border-slate-700 p-4 text-sm text-slate-300">
                Você está conectado com um perfil que não é de aluno EAD. Saia da conta para se matricular com outro cadastro.
              </p>
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); if (etapa === 1 && etapa1Ok) setEtapa(2); else if (etapa === 2 && etapa2Ok) void inscrever(); }}
                className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold">
                  {(['Seus dados', 'Acesso'] as const).map((r, i) => (
                    <React.Fragment key={r}>
                      {i > 0 && <span className="h-px flex-1 bg-slate-700" />}
                      <span className={`flex items-center gap-1.5 ${etapa === i + 1 ? 'text-nexus-yellow' : 'text-slate-500'}`}>
                        <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${etapa > i + 1 ? 'bg-emerald-500 text-white' : etapa === i + 1 ? 'bg-nexus-yellow text-ink' : 'bg-slate-800'}`}>
                          {etapa > i + 1 ? <Check size={11} /> : i + 1}
                        </span>
                        {r}
                      </span>
                    </React.Fragment>
                  ))}
                </div>

                {/* honeypot: invisível para pessoas */}
                <input type="text" tabIndex={-1} autoComplete="off" value={form.site} onChange={set('site')}
                  className="absolute -left-[9999px] h-0 w-0 opacity-0" aria-hidden="true" />

                {etapa === 1 ? (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <label><span className={rotulo}>Nome</span><input value={form.nome} onChange={set('nome')} className={campo} autoComplete="given-name" maxLength={120} /></label>
                      <label><span className={rotulo}>Sobrenome</span><input value={form.sobrenome} onChange={set('sobrenome')} className={campo} autoComplete="family-name" maxLength={160} /></label>
                    </div>
                    <label className="block"><span className={rotulo}>CPF</span><input value={form.cpf} onChange={set('cpf')} className={campo} inputMode="numeric" placeholder="000.000.000-00" /></label>
                    <div className="grid grid-cols-2 gap-3">
                      <label><span className={rotulo}>Nascimento</span><input type="date" value={form.data_nascimento} onChange={set('data_nascimento')} className={campo} /></label>
                      <label><span className={rotulo}>Celular</span><input value={form.celular} onChange={set('celular')} className={campo} inputMode="tel" placeholder="(11) 90000-0000" autoComplete="tel" /></label>
                    </div>
                    <button type="submit" disabled={!etapa1Ok}
                      className="w-full rounded-2xl bg-nexus-yellow py-3.5 text-sm font-extrabold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
                      Continuar
                    </button>
                  </>
                ) : (
                  <>
                    <label className="block"><span className={rotulo}>E-mail</span><input type="email" value={form.email} onChange={set('email')} className={campo} autoComplete="email" /></label>
                    <label className="block">
                      <span className={rotulo}>Crie uma senha</span>
                      <span className="relative block">
                        <input type={verSenha ? 'text' : 'password'} value={form.senha} onChange={set('senha')} className={`${campo} pr-10`} autoComplete="new-password" placeholder="Mínimo 8 caracteres" />
                        <button type="button" tabIndex={-1} onClick={() => setVerSenha((v) => !v)} className="absolute inset-y-0 right-0 px-3 text-slate-500 hover:text-slate-300">
                          {verSenha ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </span>
                    </label>
                    <label className="block">
                      <span className={rotulo}>Confirme a senha</span>
                      <input type={verSenha ? 'text' : 'password'} value={form.confirmar} onChange={set('confirmar')} className={campo} autoComplete="new-password" />
                      {form.confirmar && form.confirmar !== form.senha && <span className="mt-1 block text-xs text-red-300">As senhas não conferem.</span>}
                    </label>
                    <label className="flex items-start gap-2 text-xs text-slate-300">
                      <input type="checkbox" checked={aceite} onChange={(e) => setAceite(e.target.checked)} className="mt-0.5" />
                      Li e aceito os termos de matrícula e a política de privacidade (LGPD).
                    </label>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setEtapa(1)} className="rounded-2xl border border-slate-700 px-4 text-sm font-semibold text-slate-300 hover:bg-slate-800">Voltar</button>
                      <button type="submit" disabled={!etapa2Ok || enviando}
                        className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-nexus-yellow py-3.5 text-sm font-extrabold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
                        {enviando ? <Loader2 size={16} className="animate-spin" /> : <GraduationCap size={16} />} Matricule-se grátis
                      </button>
                    </div>
                  </>
                )}
                <p className="flex items-center justify-center gap-1.5 text-[11px] text-slate-500"><ShieldCheck size={12} /> Seus dados ficam protegidos.</p>
                <p className="text-center text-xs text-slate-400">
                  Já tem cadastro? <Link to="/auth/login" className="font-semibold text-nexus-yellow">Entrar</Link>
                </p>
              </form>
            )}
            {!alunoEad && !logadoOutro && !lotada && (
              <p className="flex items-center gap-1.5 text-[11px] text-slate-500"><Lock size={11} /> Nenhuma cobrança na inscrição.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};
