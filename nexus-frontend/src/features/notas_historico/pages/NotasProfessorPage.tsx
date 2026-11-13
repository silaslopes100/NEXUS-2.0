import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, Award, Loader2, RefreshCw, Save } from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { turmasApi, AlunoTurma } from '@/features/turmas/api';
import {
  mensagemErroNotas,
  Nota,
  notasHistoricoApi,
} from '@/features/notas_historico/api';
import { ProfessorDisciplinaResumo } from '@/types/professor';

export const NotasProfessorPage: React.FC = () => {
  const [disciplinas, setDisciplinas] = useState<ProfessorDisciplinaResumo[]>([]);
  const [turmaSelecionada, setTurmaSelecionada] = useState('');
  const [alunos, setAlunos] = useState<AlunoTurma[]>([]);
  const [notas, setNotas] = useState<Nota[]>([]);
  const [alunoId, setAlunoId] = useState('');
  const [valor, setValor] = useState('');
  const [rascunhos, setRascunhos] = useState<Record<string, string>>({});
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [atualizacao, setAtualizacao] = useState(0);

  const opcoes = useMemo(
    () =>
      disciplinas.flatMap((disciplina) =>
        disciplina.turmas.map((turma) => ({
          chave: `${disciplina.id}:${turma.id}`,
          disciplinaId: disciplina.id,
          disciplinaNome: disciplina.nome,
          turmaId: turma.id,
          turmaNome: turma.nome,
        }))
      ),
    [disciplinas]
  );
  const selecionada = opcoes.find((opcao) => opcao.chave === turmaSelecionada);

  const carregarDisciplinas = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const resposta = await professoresApi.minhasDisciplinas();
      setDisciplinas(resposta.items);
    } catch (error) {
      setErro(apiErrorMessage(error, 'Não foi possível carregar suas disciplinas.'));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregarDisciplinas();
  }, [carregarDisciplinas]);

  useEffect(() => {
    if (!opcoes.some((opcao) => opcao.chave === turmaSelecionada)) {
      setTurmaSelecionada(opcoes[0]?.chave ?? '');
    }
  }, [opcoes, turmaSelecionada]);

  useEffect(() => {
    if (!selecionada) {
      setAlunos([]);
      setNotas([]);
      return;
    }
    let ativo = true;
    setCarregando(true);
    setErro('');
    Promise.all([
      turmasApi.listarAlunos(selecionada.turmaId),
      notasHistoricoApi.listarNotas({
        turma_id: selecionada.turmaId,
        disciplina_id: selecionada.disciplinaId,
      }),
    ])
      .then(([respostaAlunos, respostaNotas]) => {
        if (!ativo) return;
        setAlunos(respostaAlunos.items);
        setNotas(respostaNotas);
        setRascunhos(
          Object.fromEntries(respostaNotas.map((nota) => [nota.id, String(nota.valor)]))
        );
      })
      .catch((error: unknown) => {
        if (ativo) {
          setErro(mensagemErroNotas(error, 'Não foi possível carregar as notas desta turma.'));
        }
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [selecionada?.disciplinaId, selecionada?.turmaId, atualizacao]);

  const lancar = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selecionada || !alunoId) return;
    const nota = Number(valor);
    if (!Number.isFinite(nota) || nota < 0 || nota > 10) {
      setErro('Informe uma nota entre 0 e 10.');
      return;
    }
    setSalvando(true);
    setErro('');
    try {
      await notasHistoricoApi.lancarNota({
        aluno_id: alunoId,
        disciplina_id: selecionada.disciplinaId,
        turma_id: selecionada.turmaId,
        origem: 'manual',
        valor: nota,
      });
      setValor('');
      setAtualizacao((atual) => atual + 1);
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível lançar a nota.'));
    } finally {
      setSalvando(false);
    }
  };

  const corrigir = async (notaId: string) => {
    const textoNota = rascunhos[notaId] ?? '';
    const nota = Number(textoNota);
    if (!textoNota.trim() || !Number.isFinite(nota) || nota < 0 || nota > 10) {
      setErro('Informe uma nota entre 0 e 10.');
      return;
    }
    setSalvando(true);
    setErro('');
    try {
      await notasHistoricoApi.corrigirNota(notaId, nota);
      setAtualizacao((atual) => atual + 1);
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível corrigir a nota.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-nexus-yellow/30 bg-nexus-yellow/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-nexus-yellow">
            <Award className="h-3.5 w-3.5" /> Espaço do Docente
          </div>
          <h1 className="text-2xl font-extrabold text-white sm:text-3xl">Lançamento de Notas</h1>
          <p className="mt-1 text-sm text-slate-400">
            Lance e corrija notas apenas nas turmas e disciplinas vinculadas ao seu perfil.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAtualizacao((atual) => atual + 1)}
          disabled={carregando}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} /> Atualizar
        </button>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
        <label className="block max-w-xl text-xs font-semibold uppercase tracking-wide text-slate-400">
          Disciplina e turma
          <select
            value={turmaSelecionada}
            onChange={(event) => setTurmaSelecionada(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white"
          >
            {opcoes.length === 0 && <option value="">Nenhuma turma vinculada</option>}
            {opcoes.map((opcao) => (
              <option key={opcao.chave} value={opcao.chave}>
                {opcao.disciplinaNome} · {opcao.turmaNome}
              </option>
            ))}
          </select>
        </label>

        {selecionada && (
          <form onSubmit={lancar} className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 sm:grid-cols-[minmax(0,1fr)_160px_auto] sm:items-end">
            <label className="text-xs font-semibold text-slate-400">
              Aluno
              <select
                required
                value={alunoId}
                onChange={(event) => setAlunoId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white"
              >
                <option value="">Selecione um aluno</option>
                {alunos.map((aluno) => (
                  <option key={aluno.aluno_id} value={aluno.aluno_id}>
                    {aluno.nome || aluno.numero_matricula || aluno.aluno_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold text-slate-400">
              Nota (0 a 10)
              <input
                required
                type="number"
                min="0"
                max="10"
                step="0.01"
                value={valor}
                onChange={(event) => setValor(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white"
              />
            </label>
            <button
              type="submit"
              disabled={salvando || !alunos.length}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-slate-950 hover:brightness-105 disabled:opacity-50"
            >
              {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Lançar nota
            </button>
          </form>
        )}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Aluno</th>
                <th className="px-4 py-3">Origem / Data</th>
                <th className="px-4 py-3">Nota</th>
                <th className="px-4 py-3">Correção</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {carregando ? (
                <tr><td colSpan={4} className="py-12 text-center text-slate-400"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Carregando notas...</td></tr>
              ) : notas.length === 0 ? (
                <tr><td colSpan={4} className="py-12 text-center text-slate-500">Nenhuma nota lançada para esta turma e disciplina.</td></tr>
              ) : notas.map((nota) => (
                <tr key={nota.id}>
                  <td className="px-4 py-3 font-medium text-white">{nota.aluno_nome || alunos.find((aluno) => aluno.aluno_id === nota.aluno_id)?.nome || nota.aluno_id}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {nota.origem === 'ava' ? 'AVA' : 'Manual'}
                    {nota.lancado_em ? ` · ${new Date(nota.lancado_em).toLocaleDateString('pt-BR')}` : ''}
                  </td>
                  <td className="px-4 py-3 font-bold text-white">{nota.valor.toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="0"
                        max="10"
                        step="0.01"
                        aria-label={`Corrigir nota de ${nota.aluno_nome || nota.aluno_id}`}
                        value={rascunhos[nota.id] ?? nota.valor}
                        onChange={(event) => setRascunhos((atuais) => ({ ...atuais, [nota.id]: event.target.value }))}
                        className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-white"
                      />
                      <button
                        type="button"
                        onClick={() => void corrigir(nota.id)}
                        disabled={salvando || Number(rascunhos[nota.id] ?? nota.valor) === nota.valor}
                        className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-200 hover:bg-slate-700 disabled:opacity-40"
                        aria-label="Salvar correção"
                      >
                        <Save className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
