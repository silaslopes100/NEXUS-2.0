import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, Clock, Loader2, Send, XCircle } from 'lucide-react';
import { avaliacoesApi, formatarNota, Resultado, Tentativa } from '@/features/avaliacoes/api';
import { cursosApiErrorMessage } from '@/features/cursos/api';

const LETRAS = 'ABCDEF';

const formatarTempo = (ms: number) => {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
};

interface Props {
  /** Abre (ou retoma) a tentativa. */
  iniciar: () => Promise<Tentativa>;
  /** Chave que reabre a tentativa quando muda (ex.: id da avaliação). */
  chave: string;
  rotuloVoltar: string;
  onVoltar: () => void;
  /** Chamado assim que a correção volta do servidor. */
  onResultado?: (resultado: Resultado) => void;
  /** Texto quando acabam as tentativas. */
  semTentativas?: string;
  /** Rótulo do link discreto para sair no meio da prova. */
  rotuloSair?: string;
}

/** Prova do aluno: uma questão por vez, salvamento automático e correção no servidor. */
export const RealizarAvaliacao: React.FC<Props> = ({
  iniciar, chave, rotuloVoltar, onVoltar, onResultado,
  semTentativas = 'Você não tem mais tentativas nesta avaliação. Procure seu Polo ou Escola.',
  rotuloSair = 'Sair e continuar depois (o tempo continua contando)',
}) => {
  const [tentativa, setTentativa] = useState<Tentativa | null>(null);
  const [respostas, setRespostas] = useState<Record<string, string>>({});
  const [atual, setAtual] = useState(0);
  const [revisando, setRevisando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [erro, setErro] = useState('');
  const [restante, setRestante] = useState<number | null>(null);
  const salvarTimer = useRef<number>();
  const finalizando = useRef(false);

  const iniciarRef = useRef(iniciar);
  iniciarRef.current = iniciar;
  useEffect(() => {
    iniciarRef
      .current()
      .then((t) => {
        setTentativa(t);
        setRespostas(t.respostas || {});
      })
      .catch((err) => setErro(cursosApiErrorMessage(err, 'Não foi possível abrir a avaliação.')));
  }, [chave]);

  const finalizar = useCallback(
    async (resp: Record<string, string>) => {
      if (!tentativa || finalizando.current) return;
      finalizando.current = true;
      window.clearTimeout(salvarTimer.current);
      setEnviando(true);
      setErro('');
      try {
        const r = await avaliacoesApi.finalizar(tentativa.tentativa_id, resp);
        setResultado(r);
        onResultado?.(r);
      } catch (err) {
        finalizando.current = false;
        setErro(cursosApiErrorMessage(err, 'Não foi possível enviar a avaliação. Tente novamente.'));
      } finally {
        setEnviando(false);
        setConfirmando(false);
      }
    },
    [tentativa, onResultado]
  );

  // Cronômetro: ao zerar, envia o que estiver respondido.
  const respostasRef = useRef(respostas);
  respostasRef.current = respostas;
  useEffect(() => {
    if (!tentativa?.expira_em || resultado) return;
    const fim = new Date(tentativa.expira_em).getTime();
    const tick = () => {
      const falta = fim - Date.now();
      setRestante(falta);
      if (falta <= 0) void finalizar(respostasRef.current);
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [tentativa, resultado, finalizar]);

  const responder = (questaoId: string, alternativaId: string) => {
    if (!tentativa) return;
    const novas = { ...respostas, [questaoId]: alternativaId };
    setRespostas(novas);
    window.clearTimeout(salvarTimer.current);
    salvarTimer.current = window.setTimeout(() => {
      avaliacoesApi.salvarRespostas(tentativa.tentativa_id, novas).catch(() => undefined);
    }, 600);
  };

  if (resultado) {
    return (
      <div className="mx-auto max-w-lg space-y-6 py-8 text-center">
        {resultado.aprovado ? (
          <CheckCircle2 className="mx-auto h-20 w-20 text-emerald-400" />
        ) : (
          <XCircle className="mx-auto h-20 w-20 text-amber-400" />
        )}
        <div>
          <h1 className="text-3xl font-bold text-white">{resultado.aprovado ? 'Aprovado!' : 'Não foi dessa vez'}</h1>
          <p className="mt-2 text-slate-400">{tentativa?.disciplina_nome}</p>
        </div>
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">Sua nota</p>
          <p className={`text-6xl font-bold ${resultado.aprovado ? 'text-emerald-300' : 'text-amber-300'}`}>
            {formatarNota(resultado.nota)}
          </p>
          <p className="mt-3 text-sm text-slate-400">
            {resultado.acertos} de {resultado.total_questoes} questões certas · mínimo para aprovação{' '}
            {formatarNota(resultado.nota_minima)}
          </p>
          {!resultado.aprovado && (
            <p className="mt-2 text-sm text-slate-300">
              {resultado.tentativas_restantes > 0
                ? `Você ainda tem ${resultado.tentativas_restantes} tentativa(s). Vale a maior nota.`
                : semTentativas}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onVoltar}
          className="inline-block rounded-xl bg-nexus-yellow px-6 py-3 font-bold text-ink hover:bg-nexus-yellow-hover"
        >
          {rotuloVoltar}
        </button>
      </div>
    );
  }

  if (!tentativa) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        {erro ? (
          <div className="space-y-4">
            <div className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-left text-sm text-amber-200">
              <AlertCircle size={18} className="mt-0.5 shrink-0" /> {erro}
            </div>
            <button type="button" onClick={onVoltar} className="text-sm text-blue-300 hover:underline">
              {rotuloVoltar}
            </button>
          </div>
        ) : (
          <Loader2 className="mx-auto animate-spin text-blue-400" />
        )}
      </div>
    );
  }

  const total = tentativa.questoes.length;
  const respondidas = tentativa.questoes.filter((q) => q.id && respostas[q.id]).length;
  const questao = tentativa.questoes[atual];
  const poucoTempo = restante != null && restante < 60_000;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm text-slate-400">{tentativa.disciplina_nome}</p>
            <h1 className="text-2xl font-bold text-white">{tentativa.titulo}</h1>
          </div>
          {restante != null && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 font-mono text-lg ${
                poucoTempo ? 'border-red-500/50 text-red-300' : 'border-slate-700 text-slate-200'
              }`}
              aria-live="polite"
            >
              <Clock size={18} /> {formatarTempo(restante)}
            </span>
          )}
        </div>
        {tentativa.instrucoes && atual === 0 && !revisando && (
          <p className="glass whitespace-pre-line rounded-xl border border-slate-800 bg-slate-900 p-3 text-sm text-slate-300">
            {tentativa.instrucoes}
          </p>
        )}
        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-400">
            <span>{respondidas} de {total} respondidas</span>
            <span>Suas respostas são salvas automaticamente</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full bg-nexus-yellow transition-all" style={{ width: `${total ? (respondidas / total) * 100 : 0}%` }} />
          </div>
        </div>
      </header>

      {erro && (
        <div className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          <AlertCircle size={16} className="mt-0.5 shrink-0" /> {erro}
        </div>
      )}

      {revisando ? (
        <section className="glass space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="font-semibold text-white">Revisar respostas</h2>
          <div className="grid grid-cols-5 gap-2 sm:grid-cols-10">
            {tentativa.questoes.map((q, i) => {
              const ok = !!(q.id && respostas[q.id]);
              return (
                <button
                  key={q.id}
                  type="button"
                  onClick={() => {
                    setAtual(i);
                    setRevisando(false);
                  }}
                  className={`rounded-lg border py-2 text-sm font-semibold ${
                    ok ? 'border-emerald-600/50 bg-emerald-500/10 text-emerald-200' : 'border-amber-500/50 text-amber-300'
                  }`}
                >
                  {i + 1}
                </button>
              );
            })}
          </div>
          {respondidas < total && (
            <p className="text-sm text-amber-300">Há {total - respondidas} questão(ões) sem resposta. Questão em branco conta como errada.</p>
          )}
        </section>
      ) : (
        questao && (
          <section className="glass rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-xs uppercase tracking-wide text-slate-500">Questão {atual + 1} de {total}</p>
            <h2 className="mt-2 whitespace-pre-line text-lg font-medium text-white">{questao.enunciado}</h2>
            <div className="mt-4 grid gap-3" role="radiogroup">
              {questao.alternativas.map((a, n) => {
                const marcada = !!questao.id && respostas[questao.id] === a.id;
                return (
                  <button
                    key={a.id}
                    type="button"
                    role="radio"
                    aria-checked={marcada}
                    onClick={() => questao.id && a.id && responder(questao.id, a.id)}
                    className={`flex items-start gap-3 rounded-xl border px-4 py-3.5 text-left text-base transition ${
                      marcada
                        ? 'border-nexus-yellow bg-nexus-yellow/10 text-white'
                        : 'border-slate-700 text-slate-200 hover:border-slate-500 hover:bg-slate-800/60'
                    }`}
                  >
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                        marcada ? 'bg-nexus-yellow text-ink' : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {LETRAS[n]}
                    </span>
                    <span className="pt-0.5">{a.texto}</span>
                  </button>
                );
              })}
            </div>
          </section>
        )
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3">
        {revisando ? (
          <button type="button" onClick={() => setRevisando(false)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-200 hover:bg-slate-800">
            <ArrowLeft size={16} /> Voltar às questões
          </button>
        ) : (
          <button type="button" disabled={atual === 0} onClick={() => setAtual((n) => n - 1)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-40">
            <ArrowLeft size={16} /> Anterior
          </button>
        )}
        <div className="flex gap-2">
          {!revisando && atual < total - 1 && (
            <button type="button" onClick={() => setAtual((n) => n + 1)}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-700 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-600">
              Próxima <ArrowRight size={16} />
            </button>
          )}
          {!revisando && atual === total - 1 && (
            <button type="button" onClick={() => setRevisando(true)}
              className="rounded-xl border border-slate-700 px-5 py-3 text-sm text-slate-200 hover:bg-slate-800">
              Revisar
            </button>
          )}
          {(revisando || atual === total - 1) && (
            <button type="button" disabled={enviando} onClick={() => setConfirmando(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-5 py-3 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
              <Send size={16} /> Enviar avaliação
            </button>
          )}
        </div>
      </footer>

      {confirmando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div role="dialog" aria-modal="true" className="glass w-full max-w-sm space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
            <h2 className="text-lg font-bold text-white">Enviar a avaliação?</h2>
            <p className="text-sm text-slate-300">
              {respondidas < total
                ? `Você respondeu ${respondidas} de ${total} questões. Depois de enviar não dá para alterar.`
                : 'Depois de enviar não dá para alterar as respostas.'}
            </p>
            <div className="flex justify-center gap-2">
              <button type="button" disabled={enviando} onClick={() => setConfirmando(false)}
                className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800">
                Continuar respondendo
              </button>
              <button type="button" disabled={enviando} onClick={() => void finalizar(respostas)}
                className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-ink disabled:opacity-50">
                {enviando && <Loader2 size={16} className="animate-spin" />} Enviar
              </button>
            </div>
          </div>
        </div>
      )}

      <button type="button" onClick={onVoltar} className="text-xs text-slate-500 hover:text-slate-300">
        {rotuloSair}
      </button>
    </div>
  );
};
