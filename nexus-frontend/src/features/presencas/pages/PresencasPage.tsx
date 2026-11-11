import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, CalendarDays, Check, Loader2, RefreshCw, Save, Users, X } from 'lucide-react';
import { apiErrorMessage } from '@/features/professores/api';
import { AlunoChamada, presencasApi, PresencaVinculo } from '@/features/presencas/api';

const dataLocalHoje = (): string => {
  const hoje = new Date();
  const ano = hoje.getFullYear();
  const mes = String(hoje.getMonth() + 1).padStart(2, '0');
  const dia = String(hoje.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
};

export const PresencasPage: React.FC = () => {
  const [vinculos, setVinculos] = useState<PresencaVinculo[]>([]);
  const [vinculoId, setVinculoId] = useState('');
  const [dataAula, setDataAula] = useState(dataLocalHoje);
  const [numeroAula, setNumeroAula] = useState(1);
  const [alunos, setAlunos] = useState<AlunoChamada[]>([]);
  const [carregandoVinculos, setCarregandoVinculos] = useState(true);
  const [carregandoAlunos, setCarregandoAlunos] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const requestId = useRef(0);

  const carregarVinculos = useCallback(async () => {
    setCarregandoVinculos(true);
    setErro('');
    try {
      const resultado = await presencasApi.listarVinculos();
      setVinculos(resultado);
      setVinculoId((atual) =>
        resultado.some((vinculo) => vinculo.id === atual) ? atual : resultado[0]?.id || ''
      );
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar as turmas vinculadas.'));
    } finally {
      setCarregandoVinculos(false);
    }
  }, []);

  useEffect(() => {
    void carregarVinculos();
  }, [carregarVinculos]);

  const carregarAlunos = useCallback(async () => {
    const atual = ++requestId.current;
    if (!vinculoId || !dataAula || numeroAula < 1) {
      setAlunos([]);
      setCarregandoAlunos(false);
      return;
    }
    setCarregandoAlunos(true);
    setErro('');
    setSucesso('');
    try {
      const resultado = await presencasApi.listarAlunos(vinculoId, dataAula, numeroAula);
      if (atual === requestId.current) setAlunos(resultado);
    } catch (error) {
      if (atual === requestId.current) {
        setErro(apiErrorMessage(error, 'Não foi possível carregar a lista de alunos.'));
      }
    } finally {
      if (atual === requestId.current) setCarregandoAlunos(false);
    }
  }, [dataAula, numeroAula, vinculoId]);

  useEffect(() => {
    void carregarAlunos();
  }, [carregarAlunos]);

  const todosMarcados = useMemo(
    () => alunos.length > 0 && alunos.every((aluno) => typeof aluno.presente === 'boolean'),
    [alunos]
  );

  const marcarTodos = (presente: boolean) => {
    setAlunos((atuais) => atuais.map((aluno) => ({ ...aluno, presente })));
    setSucesso('');
  };

  const marcarAluno = (alunoId: string, presente: boolean) => {
    setAlunos((atuais) =>
      atuais.map((aluno) => (aluno.aluno_id === alunoId ? { ...aluno, presente } : aluno))
    );
    setSucesso('');
  };

  const salvar = async () => {
    if (!vinculoId || !todosMarcados) return;
    setSalvando(true);
    setErro('');
    setSucesso('');
    try {
      const resposta = await presencasApi.salvarChamada({
        professor_disciplina_id: vinculoId,
        data_aula: dataAula,
        numero_aula: numeroAula,
        presencas: alunos
          .filter((aluno): aluno is AlunoChamada & { presente: boolean } => aluno.presente !== null)
          .map((aluno) => ({ aluno_id: aluno.aluno_id, presente: aluno.presente })),
      });
      setAlunos((atuais) =>
        atuais.map((aluno) => {
          const salva = resposta.presencas.find((item) => item.aluno_id === aluno.aluno_id);
          return salva ? { ...aluno, presente: salva.presente } : aluno;
        })
      );
      setSucesso('Chamada salva. Você pode reabri-la para fazer correções.');
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível salvar a chamada.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 p-6 shadow-xl sm:p-8">
        <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-300">
          <CalendarDays className="h-3.5 w-3.5" />
          Área acadêmica
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          Diário de presença
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">
          Registre a chamada de uma turma por aula. Uma chamada salva pode ser reaberta e corrigida.
        </p>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
          {erro}
        </div>
      )}
      {sucesso && (
        <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
          {sucesso}
        </div>
      )}

      <section className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-md sm:p-6">
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_180px_140px]">
          <label className="space-y-1.5 text-sm text-slate-300">
            <span>Disciplina e turma</span>
            <select
              value={vinculoId}
              onChange={(event) => setVinculoId(event.target.value)}
              disabled={carregandoVinculos || vinculos.length === 0}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-emerald-400 disabled:opacity-60"
            >
              {vinculos.length === 0 && <option value="">Nenhum vínculo disponível</option>}
              {vinculos.map((vinculo) => (
                <option key={vinculo.id} value={vinculo.id}>
                  {vinculo.disciplina_nome || vinculo.disciplina_id} — {vinculo.turma_nome || vinculo.turma_id}
                  {vinculo.professor_nome ? ` · ${vinculo.professor_nome}` : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5 text-sm text-slate-300">
            <span>Data da aula</span>
            <input
              type="date"
              value={dataAula}
              onChange={(event) => setDataAula(event.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-emerald-400"
            />
          </label>

          <label className="space-y-1.5 text-sm text-slate-300">
            <span>Número da aula</span>
            <input
              type="number"
              min={1}
              step={1}
              value={numeroAula}
              onChange={(event) => setNumeroAula(Number(event.target.value))}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-emerald-400"
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Users className="h-4 w-4 text-blue-400" />
            {carregandoAlunos ? 'Carregando alunos...' : `${alunos.length} aluno(s) matriculado(s)`}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => marcarTodos(true)}
              disabled={alunos.length === 0 || carregandoAlunos}
              className="rounded-lg border border-emerald-500/30 px-3 py-2 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-50"
            >
              Marcar todos presentes
            </button>
            <button
              type="button"
              onClick={() => marcarTodos(false)}
              disabled={alunos.length === 0 || carregandoAlunos}
              className="rounded-lg border border-amber-500/30 px-3 py-2 text-xs font-semibold text-amber-200 hover:bg-amber-500/10 disabled:opacity-50"
            >
              Marcar todos ausentes
            </button>
            <button
              type="button"
              onClick={() => void carregarAlunos()}
              disabled={carregandoAlunos || !vinculoId}
              aria-label="Atualizar lista de alunos"
              className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${carregandoAlunos ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-800">
          {carregandoVinculos ? (
            <div className="p-10 text-center text-sm text-slate-400">
              <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin text-emerald-400" />
              Carregando vínculos...
            </div>
          ) : !vinculoId ? (
            <div className="p-10 text-center text-sm text-slate-400">
              Nenhuma turma vinculada está disponível para chamada.
            </div>
          ) : carregandoAlunos ? (
            <div className="p-10 text-center text-sm text-slate-400">
              <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin text-emerald-400" />
              Carregando alunos da turma...
            </div>
          ) : alunos.length === 0 ? (
            <div className="p-10 text-center text-sm text-slate-400">
              Nenhum aluno ativo está matriculado nesta turma.
            </div>
          ) : (
            <ul className="divide-y divide-slate-800">
              {alunos.map((aluno) => (
                <li key={aluno.aluno_id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-white">{aluno.nome}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {aluno.numero_matricula || 'Sem matrícula informada'}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      aria-pressed={aluno.presente === true}
                      onClick={() => marcarAluno(aluno.aluno_id, true)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold ${
                        aluno.presente === true
                          ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-200'
                          : 'border-slate-700 text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <Check className="h-3.5 w-3.5" />
                      Presente
                    </button>
                    <button
                      type="button"
                      aria-pressed={aluno.presente === false}
                      onClick={() => marcarAluno(aluno.aluno_id, false)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold ${
                        aluno.presente === false
                          ? 'border-amber-500/50 bg-amber-500/15 text-amber-200'
                          : 'border-slate-700 text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <X className="h-3.5 w-3.5" />
                      Ausente
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col gap-2 border-t border-slate-800 pt-4 sm:flex-row sm:items-center sm:justify-between">
          {!todosMarcados && alunos.length > 0 && (
            <p className="text-xs text-amber-200">
              Marque cada aluno como presente ou ausente antes de salvar.
            </p>
          )}
          <button
            type="button"
            onClick={() => void salvar()}
            disabled={!todosMarcados || salvando || carregandoAlunos}
            className="inline-flex items-center justify-center gap-2 self-end rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Salvar chamada
          </button>
        </div>
      </section>
    </div>
  );
};
