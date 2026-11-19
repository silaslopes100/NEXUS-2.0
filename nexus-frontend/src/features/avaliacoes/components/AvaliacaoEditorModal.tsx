import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Copy,
  Eye,
  Loader2,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { avaliacoesApi, AvaliacaoSalvar } from '@/features/avaliacoes/api';
import { cursosApiErrorMessage } from '@/features/cursos/api';

type AltForm = { texto: string; correta: boolean };
type QuestaoForm = { enunciado: string; peso: string; alternativas: AltForm[] };

const novaQuestao = (): QuestaoForm => ({
  enunciado: '',
  peso: '1',
  alternativas: [
    { texto: '', correta: true },
    { texto: '', correta: false },
    { texto: '', correta: false },
    { texto: '', correta: false },
  ],
});

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500';
const LETRAS = 'ABCDEF';

interface Props {
  disciplinaId: string;
  disciplinaNome: string;
  onClose: () => void;
  onSalvo: (ativo: boolean) => void;
}

/** Questionário da disciplina: usado na prova do aluno (licença) e, no futuro, no AVA. */
export const AvaliacaoEditorModal: React.FC<Props> = ({ disciplinaId, disciplinaNome, onClose, onSalvo }) => {
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [previa, setPrevia] = useState(false);
  const [origem, setOrigem] = useState<string | null>(null);
  const [titulo, setTitulo] = useState(`Avaliação — ${disciplinaNome}`);
  const [instrucoes, setInstrucoes] = useState('');
  const [tempo, setTempo] = useState('');
  const [tentativas, setTentativas] = useState('2');
  const [notaMinima, setNotaMinima] = useState('6');
  const [embaralhar, setEmbaralhar] = useState(true);
  const [ativo, setAtivo] = useState(false);
  const [questoes, setQuestoes] = useState<QuestaoForm[]>([novaQuestao()]);

  useEffect(() => {
    avaliacoesApi
      .daDisciplina(disciplinaId)
      .then((av) => {
        if (!av) return;
        setOrigem(av.origem);
        setTitulo(av.titulo);
        setInstrucoes(av.instrucoes || '');
        setTempo(av.tempo_limite_min ? String(av.tempo_limite_min) : '');
        setTentativas(String(av.tentativas_max));
        setNotaMinima(String(av.nota_minima));
        setEmbaralhar(av.embaralhar);
        setAtivo(av.ativo);
        setQuestoes(
          av.questoes.length
            ? av.questoes.map((q) => ({
                enunciado: q.enunciado,
                peso: String(q.peso),
                alternativas: q.alternativas.map((a) => ({ texto: a.texto, correta: !!a.correta })),
              }))
            : [novaQuestao()]
        );
      })
      .catch((err) => setErro(cursosApiErrorMessage(err, 'Não foi possível carregar a avaliação.')))
      .finally(() => setCarregando(false));
  }, [disciplinaId]);

  const alterarQuestao = (i: number, mudanca: Partial<QuestaoForm>) =>
    setQuestoes((qs) => qs.map((q, n) => (n === i ? { ...q, ...mudanca } : q)));

  const alterarAlternativa = (qi: number, ai: number, texto: string) =>
    alterarQuestao(qi, {
      alternativas: questoes[qi].alternativas.map((a, n) => (n === ai ? { ...a, texto } : a)),
    });

  const marcarCorreta = (qi: number, ai: number) =>
    alterarQuestao(qi, { alternativas: questoes[qi].alternativas.map((a, n) => ({ ...a, correta: n === ai })) });

  const mover = (i: number, delta: number) =>
    setQuestoes((qs) => {
      const j = i + delta;
      if (j < 0 || j >= qs.length) return qs;
      const copia = [...qs];
      [copia[i], copia[j]] = [copia[j], copia[i]];
      return copia;
    });

  const validar = (ativar: boolean): string | null => {
    if (titulo.trim().length < 3) return 'Informe o título da avaliação.';
    const preenchidas = questoes.filter((q) => q.enunciado.trim() || q.alternativas.some((a) => a.texto.trim()));
    if (ativar && !preenchidas.length) return 'Cadastre ao menos uma questão antes de ativar.';
    for (const [n, q] of questoes.entries()) {
      if (!preenchidas.includes(q)) continue;
      if (q.enunciado.trim().length < 3) return `Escreva o enunciado da questão ${n + 1}.`;
      const alts = q.alternativas.filter((a) => a.texto.trim());
      if (alts.length < 2) return `A questão ${n + 1} precisa de pelo menos 2 alternativas.`;
      if (alts.filter((a) => a.correta).length !== 1)
        return `A questão ${n + 1} precisa de uma alternativa correta preenchida.`;
      const peso = Number(q.peso.replace(',', '.'));
      if (!(peso > 0)) return `O peso da questão ${n + 1} deve ser maior que zero.`;
    }
    const nota = Number(notaMinima.replace(',', '.'));
    if (!(nota >= 0 && nota <= 10)) return 'A nota mínima deve estar entre 0 e 10.';
    if (!(Number(tentativas) >= 1)) return 'Informe ao menos 1 tentativa.';
    return null;
  };

  const salvar = async (ativar: boolean) => {
    const problema = validar(ativar);
    if (problema) {
      setErro(problema);
      return;
    }
    const dados: AvaliacaoSalvar = {
      titulo: titulo.trim(),
      instrucoes: instrucoes.trim() || null,
      tempo_limite_min: tempo.trim() ? Number(tempo) : null,
      tentativas_max: Number(tentativas),
      nota_minima: Number(notaMinima.replace(',', '.')),
      embaralhar,
      ativo: ativar,
      questoes: questoes
        .filter((q) => q.enunciado.trim())
        .map((q) => ({
          enunciado: q.enunciado.trim(),
          peso: Number(q.peso.replace(',', '.')),
          alternativas: q.alternativas
            .filter((a) => a.texto.trim())
            .map((a) => ({ texto: a.texto.trim(), correta: a.correta })),
        })),
    };
    setSalvando(true);
    setErro('');
    try {
      await avaliacoesApi.salvar(disciplinaId, dados);
      onSalvo(ativar);
    } catch (err) {
      setErro(cursosApiErrorMessage(err, 'Não foi possível salvar a avaliação.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(e) => e.target === e.currentTarget && !salvando && onClose()}
    >
      <div className="my-6 w-full max-w-4xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-800 p-5">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Avaliação da disciplina</p>
            <h2 className="text-xl font-bold text-white">{disciplinaNome}</h2>
            <p className="mt-1 text-sm text-slate-400">
              Usada na prova do aluno com licença e disponível para o AVA.
              {origem === 'demo' && <span className="ml-2 text-amber-300">(questionário de demonstração)</span>}
            </p>
          </div>
          <button type="button" aria-label="Fechar" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800">
            <X size={18} />
          </button>
        </header>

        {carregando ? (
          <div className="flex justify-center p-12 text-slate-400">
            <Loader2 className="animate-spin" />
          </div>
        ) : previa ? (
          <div className="space-y-4 p-5">
            <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-3 text-sm text-blue-200">
              Assim o aluno verá a prova (sem indicar a resposta certa).
            </div>
            <h3 className="text-lg font-semibold text-white">{titulo}</h3>
            {instrucoes && <p className="whitespace-pre-line text-sm text-slate-300">{instrucoes}</p>}
            {questoes
              .filter((q) => q.enunciado.trim())
              .map((q, i) => (
                <div key={i} className="rounded-xl border border-slate-800 p-4">
                  <p className="font-medium text-white">
                    {i + 1}. {q.enunciado}
                  </p>
                  <div className="mt-3 grid gap-2">
                    {q.alternativas
                      .filter((a) => a.texto.trim())
                      .map((a, n) => (
                        <div key={n} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200">
                          <span className="mr-2 font-bold text-slate-400">{LETRAS[n]})</span>
                          {a.texto}
                        </div>
                      ))}
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="space-y-5 p-5">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="md:col-span-2">
                <span className="mb-1 block text-xs text-slate-400">Título</span>
                <input className={inputClass} value={titulo} onChange={(e) => setTitulo(e.target.value)} />
              </label>
              <label className="md:col-span-2">
                <span className="mb-1 block text-xs text-slate-400">Instruções para o aluno (opcional)</span>
                <textarea rows={2} className={inputClass} value={instrucoes} onChange={(e) => setInstrucoes(e.target.value)} />
              </label>
              <div className="grid grid-cols-3 gap-3 md:col-span-2">
                <label>
                  <span className="mb-1 block text-xs text-slate-400">Tempo limite (min)</span>
                  <input className={inputClass} inputMode="numeric" placeholder="Livre" value={tempo}
                    onChange={(e) => setTempo(e.target.value.replace(/\D/g, ''))} />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-slate-400">Tentativas</span>
                  <input className={inputClass} inputMode="numeric" value={tentativas}
                    onChange={(e) => setTentativas(e.target.value.replace(/\D/g, ''))} />
                </label>
                <label>
                  <span className="mb-1 block text-xs text-slate-400">Nota mínima (0–10)</span>
                  <input className={inputClass} inputMode="decimal" value={notaMinima} onChange={(e) => setNotaMinima(e.target.value)} />
                </label>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="checkbox" checked={embaralhar} onChange={(e) => setEmbaralhar(e.target.checked)} />
                Embaralhar a ordem das questões e alternativas para cada aluno
              </label>
              <p className="text-sm text-slate-400 md:text-right">
                Situação:{' '}
                {ativo ? <span className="font-semibold text-emerald-300">ativa</span> : <span className="text-slate-300">rascunho</span>}
              </p>
            </div>

            <div className="space-y-4">
              {questoes.map((q, qi) => (
                <div key={qi} className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-white">Questão {qi + 1}</span>
                    <div className="flex items-center gap-1">
                      <label className="mr-2 flex items-center gap-1 text-xs text-slate-400">
                        Peso
                        <input className="w-14 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-sm text-white"
                          inputMode="decimal" value={q.peso} onChange={(e) => alterarQuestao(qi, { peso: e.target.value })} />
                      </label>
                      <button type="button" aria-label="Subir questão" disabled={qi === 0} onClick={() => mover(qi, -1)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 disabled:opacity-30"><ArrowUp size={15} /></button>
                      <button type="button" aria-label="Descer questão" disabled={qi === questoes.length - 1} onClick={() => mover(qi, 1)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 disabled:opacity-30"><ArrowDown size={15} /></button>
                      <button type="button" aria-label="Duplicar questão"
                        onClick={() => setQuestoes((qs) => [...qs.slice(0, qi + 1), structuredClone(q), ...qs.slice(qi + 1)])}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800"><Copy size={15} /></button>
                      <button type="button" aria-label="Remover questão"
                        onClick={() => setQuestoes((qs) => (qs.length > 1 ? qs.filter((_, n) => n !== qi) : [novaQuestao()]))}
                        className="rounded-lg p-1.5 text-red-300 hover:bg-red-500/10"><Trash2 size={15} /></button>
                    </div>
                  </div>
                  <textarea rows={2} className={inputClass} placeholder="Enunciado da questão" value={q.enunciado}
                    onChange={(e) => alterarQuestao(qi, { enunciado: e.target.value })} />
                  <p className="mb-2 mt-3 text-xs text-slate-500">Marque a alternativa correta:</p>
                  <div className="space-y-2">
                    {q.alternativas.map((a, ai) => (
                      <div key={ai} className="flex items-center gap-2">
                        <input type="radio" name={`correta-${qi}`} aria-label={`Alternativa ${LETRAS[ai]} é a correta`}
                          checked={a.correta} onChange={() => marcarCorreta(qi, ai)} className="h-4 w-4 accent-emerald-500" />
                        <span className="w-5 text-sm font-bold text-slate-400">{LETRAS[ai]}</span>
                        <input className={`${inputClass} ${a.correta ? 'border-emerald-600/60' : ''}`} value={a.texto}
                          placeholder={`Alternativa ${LETRAS[ai]}`} onChange={(e) => alterarAlternativa(qi, ai, e.target.value)} />
                        {q.alternativas.length > 2 && (
                          <button type="button" aria-label={`Remover alternativa ${LETRAS[ai]}`}
                            onClick={() => {
                              const restantes = q.alternativas.filter((_, n) => n !== ai);
                              if (a.correta) restantes[0] = { ...restantes[0], correta: true };
                              alterarQuestao(qi, { alternativas: restantes });
                            }}
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800"><X size={14} /></button>
                        )}
                      </div>
                    ))}
                  </div>
                  {q.alternativas.length < 6 && (
                    <button type="button"
                      onClick={() => alterarQuestao(qi, { alternativas: [...q.alternativas, { texto: '', correta: false }] })}
                      className="mt-2 text-xs text-blue-300 hover:underline">+ alternativa</button>
                  )}
                </div>
              ))}
              <button type="button" onClick={() => setQuestoes((qs) => [...qs, novaQuestao()])}
                className="inline-flex items-center gap-2 rounded-xl border border-dashed border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:border-blue-500 hover:text-white">
                <Plus size={16} /> Adicionar questão
              </button>
            </div>
          </div>
        )}

        {erro && (
          <div className="mx-5 mb-3 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            <AlertCircle size={16} className="mt-0.5 shrink-0" /> {erro}
          </div>
        )}

        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 p-5">
          <button type="button" disabled={carregando} onClick={() => setPrevia((v) => !v)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800">
            <Eye size={16} /> {previa ? 'Voltar a editar' : 'Pré-visualizar como aluno'}
          </button>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={salvando || carregando} onClick={() => void salvar(false)}
              className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50">
              {ativo ? 'Salvar e desativar' : 'Salvar rascunho'}
            </button>
            <button type="button" disabled={salvando || carregando} onClick={() => void salvar(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-on-accent hover:bg-emerald-500 disabled:opacity-50">
              {salvando ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
              {ativo ? 'Salvar (ativa)' : 'Salvar e ativar'}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};
