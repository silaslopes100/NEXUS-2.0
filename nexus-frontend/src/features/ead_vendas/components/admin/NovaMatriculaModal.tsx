import React, { useEffect, useState } from 'react';
import { GraduationCap, Loader2, Search, UserPlus, X } from 'lucide-react';
import { mensagemErro } from '@/features/comunicacao/api';
import { AlunoEadBusca, TipoMatricula, TurmaEadOpcao, gestaoEadApi } from '../../adminApi';

const campo =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none';
const rotulo = 'mb-1 block text-[11px] font-semibold uppercase tracking-wider text-slate-400';

interface Props {
  turmas: TurmaEadOpcao[];
  onFechar: () => void;
  onCriada: (alunoId: string, convite?: boolean | null) => void;
}

/** Matrícula manual: aluno EAD existente ou novo, Turma EAD e tipo (Regular ou Bolsista). */
export const NovaMatriculaModal: React.FC<Props> = ({ turmas, onFechar, onCriada }) => {
  const [modo, setModo] = useState<'existente' | 'novo'>('existente');
  const [busca, setBusca] = useState('');
  const [resultados, setResultados] = useState<AlunoEadBusca[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [aluno, setAluno] = useState<AlunoEadBusca | null>(null);
  const [novo, setNovo] = useState({ nome: '', sobrenome: '', email: '', cpf: '', celular: '', data_nascimento: '' });
  const abertas = turmas.filter((t) => t.aberta);
  const [turmaId, setTurmaId] = useState(abertas[0]?.id ?? '');
  const [tipo, setTipo] = useState<TipoMatricula>('regular');
  const [observacao, setObservacao] = useState('');
  const [ignorarVagas, setIgnorarVagas] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (modo !== 'existente' || busca.trim().length < 2) { setResultados([]); return; }
    const t = window.setTimeout(() => {
      setBuscando(true);
      gestaoEadApi.buscarAlunos(busca).then(setResultados).catch(() => setResultados([])).finally(() => setBuscando(false));
    }, 300);
    return () => window.clearTimeout(t);
  }, [busca, modo]);

  const novoOk = novo.nome.trim() && novo.sobrenome.trim() && /\S+@\S+\.\S+/.test(novo.email)
    && novo.cpf.replace(/\D/g, '').length === 11 && novo.data_nascimento;
  const pronto = !!turmaId && (modo === 'existente' ? !!aluno : !!novoOk);

  const salvar = async () => {
    setEnviando(true);
    setErro(null);
    try {
      const r = await gestaoEadApi.matricular({
        turma_id: turmaId, tipo, observacao: observacao.trim() || undefined, ignorar_vagas: ignorarVagas,
        ...(modo === 'existente' ? { aluno_id: aluno!.aluno_id } : {
          novo_aluno: { ...novo, cpf: novo.cpf.replace(/\D/g, ''), celular: novo.celular.replace(/\D/g, '') || undefined },
        }),
      });
      onCriada(r.aluno_id, r.convite_enviado);
    } catch (e) {
      setErro(mensagemErro(e, 'Não foi possível matricular.'));
    } finally {
      setEnviando(false);
    }
  };

  const setN = (k: keyof typeof novo) => (e: React.ChangeEvent<HTMLInputElement>) => setNovo((x) => ({ ...x, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onMouseDown={onFechar}>
      <div className="flex max-h-[92vh] w-full max-w-2xl flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="flex items-center gap-2 text-lg font-bold text-white"><GraduationCap size={18} className="text-nexus-yellow" /> Nova matrícula manual</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"><X size={18} /></button>
        </header>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-6 py-5">
          <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1">
            {([['existente', 'Aluno EAD já cadastrado', Search], ['novo', 'Cadastrar aluno novo', UserPlus]] as const).map(([v, r, Icone]) => (
              <button key={v} type="button" onClick={() => setModo(v)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold ${modo === v ? 'bg-nexus-yellow text-ink' : 'text-slate-300 hover:bg-slate-800'}`}>
                <Icone size={14} /> {r}
              </button>
            ))}
          </div>

          {modo === 'existente' ? (
            <div className="space-y-2">
              {aluno ? (
                <div className="flex items-center justify-between rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3">
                  <div>
                    <p className="font-semibold text-white">{aluno.nome}</p>
                    <p className="text-xs text-slate-400">{[aluno.numero_matricula, aluno.email].filter(Boolean).join(' · ')}</p>
                  </div>
                  <button type="button" onClick={() => setAluno(null)} className="text-xs font-semibold text-slate-300 hover:text-white">Trocar</button>
                </div>
              ) : (
                <>
                  <div className="relative">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Nome, e-mail, CPF ou matrícula" className={`${campo} pl-9`} autoFocus />
                    {buscando && <Loader2 size={14} className="absolute right-3 top-3 animate-spin text-slate-400" />}
                  </div>
                  <ul className="max-h-52 divide-y divide-slate-800 overflow-y-auto rounded-xl border border-slate-800">
                    {resultados.map((a) => (
                      <li key={a.aluno_id}>
                        <button type="button" onClick={() => setAluno(a)} className="w-full px-3 py-2 text-left hover:bg-slate-800/60">
                          <p className="text-sm font-semibold text-white">{a.nome}</p>
                          <p className="text-[11px] text-slate-400">{[a.numero_matricula, a.email].filter(Boolean).join(' · ')}</p>
                        </button>
                      </li>
                    ))}
                    {busca.trim().length >= 2 && !buscando && !resultados.length && (
                      <li className="px-3 py-3 text-xs text-slate-500">Nenhum aluno EAD encontrado. Use “Cadastrar aluno novo”.</li>
                    )}
                  </ul>
                </>
              )}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <label><span className={rotulo}>Nome</span><input value={novo.nome} onChange={setN('nome')} className={campo} /></label>
              <label><span className={rotulo}>Sobrenome</span><input value={novo.sobrenome} onChange={setN('sobrenome')} className={campo} /></label>
              <label><span className={rotulo}>E-mail</span><input type="email" value={novo.email} onChange={setN('email')} className={campo} /></label>
              <label><span className={rotulo}>CPF</span><input value={novo.cpf} onChange={setN('cpf')} className={campo} inputMode="numeric" /></label>
              <label><span className={rotulo}>Nascimento</span><input type="date" value={novo.data_nascimento} onChange={setN('data_nascimento')} className={campo} /></label>
              <label><span className={rotulo}>Celular</span><input value={novo.celular} onChange={setN('celular')} className={campo} inputMode="tel" /></label>
              <p className="text-[11px] text-slate-500 sm:col-span-2">O aluno recebe por e-mail o convite para criar a senha de acesso.</p>
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="sm:col-span-2">
              <span className={rotulo}>Turma EAD</span>
              <select value={turmaId} onChange={(e) => setTurmaId(e.target.value)} className={campo}>
                {abertas.map((t) => <option key={t.id} value={t.id}>{t.nome} · {t.curso_nome}</option>)}
              </select>
              {!abertas.length && <span className="mt-1 block text-xs text-amber-300">Nenhuma Turma EAD aberta.</span>}
            </label>
            {(['regular', 'bolsista'] as const).map((v) => (
              <button key={v} type="button" onClick={() => setTipo(v)}
                className={`rounded-2xl border-2 p-3 text-left ${tipo === v ? 'border-nexus-yellow bg-nexus-yellow/10' : 'border-slate-800 hover:border-slate-600'}`}>
                <p className="font-bold text-white">{v === 'regular' ? 'Regular' : 'Bolsista (100%)'}</p>
                <p className="text-[11px] text-slate-400">
                  {v === 'regular' ? 'Compra cada disciplina na loja quando ela for liberada.' : 'Recebe cada disciplina sem custo, conforme o calendário da turma.'}
                </p>
              </button>
            ))}
            <label className="sm:col-span-2">
              <span className={rotulo}>Observação (opcional)</span>
              <textarea value={observacao} onChange={(e) => setObservacao(e.target.value)} rows={2} maxLength={2000} className={campo}
                placeholder="Ex.: bolsa social aprovada em 20/11, processo 123" />
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300 sm:col-span-2">
              <input type="checkbox" checked={ignorarVagas} onChange={(e) => setIgnorarVagas(e.target.checked)} />
              Matricular mesmo com a turma lotada
            </label>
          </div>

          {erro && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{erro}</p>}
        </div>

        <footer className="flex justify-end gap-2 border-t border-slate-800 px-6 py-4">
          <button type="button" onClick={onFechar} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Cancelar</button>
          <button type="button" disabled={!pronto || enviando} onClick={() => void salvar()}
            className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-5 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
            {enviando && <Loader2 size={14} className="animate-spin" />} Matricular
          </button>
        </footer>
      </div>
    </div>
  );
};
