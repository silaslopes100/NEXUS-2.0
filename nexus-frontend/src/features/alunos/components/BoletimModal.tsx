import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, Loader2, Pencil, Save, X } from 'lucide-react';
import { Academico, alunosGestaoApi, apiErrorMessage } from '@/features/alunos/api';
import { BarraProgresso } from '@/features/alunos/components/DisciplinasExpandidas';
import { AdminNota, mensagemErroNotas, notasHistoricoApi } from '@/features/notas_historico/api';

const situacaoLabel: Record<string, string> = {
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
  cursando: 'Cursando',
};

/** Tamanho de página fixo da API de notas do admin. */
const PAGINA_NOTAS = 30;

interface Props {
  alunoId: string;
  onClose: () => void;
  /** Admin: permite corrigir as notas lançadas (correção auditada no backend). */
  podeEditar?: boolean;
}

export const BoletimModal: React.FC<Props> = ({ alunoId, onClose, podeEditar = false }) => {
  const [dados, setDados] = useState<Academico | null>(null);
  const [cursoId, setCursoId] = useState('');
  const [erro, setErro] = useState('');
  const [baixando, setBaixando] = useState(false);

  // Edição de notas (admin)
  const [notas, setNotas] = useState<AdminNota[] | null>(null);
  const [erroNotas, setErroNotas] = useState('');
  const [editando, setEditando] = useState<string | null>(null);
  const [rascunhos, setRascunhos] = useState<Record<string, string>>({});
  const [salvandoId, setSalvandoId] = useState('');

  const carregarAcademico = useCallback(async (manterCurso: boolean) => {
    const resposta = await alunosGestaoApi.academico(alunoId);
    setDados(resposta);
    if (!manterCurso) setCursoId(resposta.cursos[0]?.id ?? '');
  }, [alunoId]);

  useEffect(() => {
    let ativo = true;
    alunosGestaoApi
      .academico(alunoId)
      .then((resposta) => {
        if (!ativo) return;
        setDados(resposta);
        setCursoId(resposta.cursos[0]?.id ?? '');
      })
      .catch((err: unknown) => {
        if (ativo) setErro(apiErrorMessage(err, 'Não foi possível carregar o boletim.'));
      });
    return () => {
      ativo = false;
    };
  }, [alunoId]);

  const carregarNotas = useCallback(async () => {
    setErroNotas('');
    try {
      const todas: AdminNota[] = [];
      let total = Infinity;
      for (let offset = 0; offset < total; offset += PAGINA_NOTAS) {
        const pagina = await notasHistoricoApi.listarNotasAdmin({ aluno_id: alunoId, limit: PAGINA_NOTAS, offset });
        total = pagina.total;
        todas.push(...pagina.items);
        if (pagina.items.length === 0) break;
      }
      setNotas(todas);
      setRascunhos(Object.fromEntries(todas.map((nota) => [nota.id, String(nota.valor)])));
    } catch (err: unknown) {
      setNotas([]);
      setErroNotas(mensagemErroNotas(err, 'Não foi possível carregar as notas lançadas.'));
    }
  }, [alunoId]);

  useEffect(() => {
    if (podeEditar) void carregarNotas();
  }, [podeEditar, carregarNotas]);

  const notasPorDisciplina = useMemo(() => {
    const mapa = new Map<string, AdminNota[]>();
    for (const nota of notas ?? []) {
      if (!nota.disciplina_id) continue;
      const lista = mapa.get(nota.disciplina_id) ?? [];
      lista.push(nota);
      mapa.set(nota.disciplina_id, lista);
    }
    return mapa;
  }, [notas]);

  const curso = dados?.cursos.find((item) => item.id === cursoId);

  const corrigir = async (nota: AdminNota) => {
    const texto = rascunhos[nota.id] ?? String(nota.valor);
    const valor = Number(texto.replace(',', '.'));
    if (!texto.trim() || !Number.isFinite(valor) || valor < 0 || valor > 10) {
      setErroNotas('Informe uma nota entre 0 e 10.');
      return;
    }
    setSalvandoId(nota.id);
    setErroNotas('');
    try {
      await notasHistoricoApi.corrigirNota(nota.id, valor);
      await Promise.all([carregarNotas(), carregarAcademico(true)]);
    } catch (err: unknown) {
      setErroNotas(mensagemErroNotas(err, 'Não foi possível corrigir a nota.'));
    } finally {
      setSalvandoId('');
    }
  };

  const baixarPdf = async () => {
    if (!dados) return;
    setBaixando(true);
    setErro('');
    try {
      const blob = await alunosGestaoApi.boletimPdf(alunoId, cursoId || undefined);
      const identificador = (dados.numero_matricula || dados.aluno_nome || alunoId)
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .replace(/[^A-Za-z0-9_-]+/g, '_');
      const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `boletim-${identificador}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setErro(apiErrorMessage(err, 'Não foi possível gerar o PDF do boletim.'));
    } finally {
      setBaixando(false);
    }
  };

  const colunas = podeEditar ? 6 : 5;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="boletim-titulo"
        className="glass my-auto max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-blue-300">Histórico Escolar</p>
            <h2 id="boletim-titulo" className="mt-1 text-xl font-bold text-white">
              Boletim {dados ? `de ${dados.aluno_nome}` : ''}
            </h2>
            {dados && (
              <p className="mt-1 text-sm text-slate-400">
                Matrícula: {dados.numero_matricula || 'não informada'}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {dados && dados.cursos.length > 0 && (
              <button
                type="button"
                onClick={baixarPdf}
                disabled={baixando}
                className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {baixando ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                <span>{baixando ? 'Gerando...' : 'Baixar PDF'}</span>
              </button>
            )}
            <button
              type="button"
              aria-label="Fechar boletim"
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        {erro && (
          <div role="alert" className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {erro}
          </div>
        )}
        {erroNotas && (
          <div role="alert" className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
            {erroNotas}
          </div>
        )}
        {!dados && !erro && (
          <div className="flex justify-center py-12 text-blue-400">
            <Loader2 className="animate-spin" />
          </div>
        )}
        {dados && dados.cursos.length === 0 && (
          <p className="py-12 text-center text-sm text-slate-500">
            Nenhuma disciplina registrada para este aluno.
          </p>
        )}

        {dados && dados.cursos.length > 0 && (
          <div className="mt-5 space-y-4">
            <label className="block space-y-1.5 text-sm text-slate-300">
              <span>Curso</span>
              <select
                value={cursoId}
                onChange={(event) => setCursoId(event.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
              >
                {dados.cursos.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nome}
                  </option>
                ))}
              </select>
            </label>

            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full min-w-[560px] text-left text-sm text-slate-300">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="p-3">Disciplina</th>
                    <th className="p-3">Semestre</th>
                    <th className="p-3">Nota</th>
                    <th className="p-3">Situação</th>
                    <th className="p-3">Progresso</th>
                    {podeEditar && <th className="p-3 text-right">Editar</th>}
                  </tr>
                </thead>
                <tbody>
                  {curso?.disciplinas.map((disciplina) => {
                    const aberta = editando === disciplina.id;
                    const lancamentos = notasPorDisciplina.get(disciplina.id) ?? [];
                    return (
                      <React.Fragment key={disciplina.id}>
                        <tr className="border-b border-slate-800/60 last:border-0">
                          <td className="p-3 font-medium text-white">{disciplina.nome}</td>
                          <td className="p-3">{disciplina.semestre ?? '—'}</td>
                          <td className="p-3">
                            {disciplina.nota != null ? disciplina.nota.toFixed(1) : '—'}
                          </td>
                          <td className="p-3">
                            {situacaoLabel[disciplina.situacao] ?? disciplina.situacao}
                          </td>
                          <td className="p-3">
                            <BarraProgresso disciplina={disciplina} />
                          </td>
                          {podeEditar && (
                            <td className="p-3 text-right">
                              <button
                                type="button"
                                onClick={() => setEditando(aberta ? null : disciplina.id)}
                                aria-expanded={aberta}
                                aria-label={`Editar nota de ${disciplina.nome}`}
                                title="Editar nota"
                                className={`rounded-lg border p-2 ${aberta ? 'border-nexus-yellow/50 text-nexus-yellow' : 'border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white'}`}
                              >
                                <Pencil size={14} />
                              </button>
                            </td>
                          )}
                        </tr>
                        {podeEditar && aberta && (
                          <tr className="border-b border-slate-800/60 bg-slate-950/40">
                            <td colSpan={colunas} className="p-3">
                              {notas === null ? (
                                <p className="flex items-center gap-2 text-xs text-slate-400">
                                  <Loader2 className="h-4 w-4 animate-spin" /> Carregando lançamentos...
                                </p>
                              ) : lancamentos.length === 0 ? (
                                <p className="text-xs text-slate-500">
                                  Nenhuma nota lançada nesta disciplina. O lançamento é feito pelo professor.
                                </p>
                              ) : (
                                <div className="space-y-2">
                                  <p className="text-xs text-slate-400">
                                    Lançamentos da disciplina. O boletim considera a maior nota; cada correção fica registrada na auditoria.
                                  </p>
                                  {lancamentos.map((nota) => {
                                    const rascunho = rascunhos[nota.id] ?? String(nota.valor);
                                    const alterada = Number(rascunho.replace(',', '.')) !== nota.valor;
                                    return (
                                      <div key={nota.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 px-3 py-2">
                                        <div className="min-w-0 flex-1 text-xs">
                                          <p className="text-slate-200">{nota.turma_nome || 'Sem turma'}</p>
                                          <p className="text-slate-500">
                                            {nota.origem === 'ava' ? 'AVA' : 'Manual'}
                                            {nota.lancado_em ? ` · ${new Date(nota.lancado_em).toLocaleDateString('pt-BR')}` : ''}
                                          </p>
                                        </div>
                                        <input
                                          type="number"
                                          min="0"
                                          max="10"
                                          step="0.01"
                                          value={rascunho}
                                          onChange={(event) => setRascunhos((atuais) => ({ ...atuais, [nota.id]: event.target.value }))}
                                          aria-label={`Nota de ${disciplina.nome}`}
                                          className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-white"
                                        />
                                        <button
                                          type="button"
                                          onClick={() => void corrigir(nota)}
                                          disabled={Boolean(salvandoId) || !alterada}
                                          className="inline-flex items-center gap-1.5 rounded-lg bg-nexus-yellow px-3 py-1.5 text-xs font-bold text-ink disabled:opacity-40"
                                        >
                                          {salvandoId === nota.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                                          Salvar
                                        </button>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
