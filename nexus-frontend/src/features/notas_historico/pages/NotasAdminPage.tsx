import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ChevronLeft, ChevronRight, Download, FileText, Loader2, RefreshCw, Save, Search, X } from 'lucide-react';
import { Academico, alunosGestaoApi } from '@/features/alunos/api';
import {
  AdminAlunoNota,
  AdminNota,
  mensagemErroNotas,
  notasHistoricoApi,
} from '@/features/notas_historico/api';

export const NotasAdminPage: React.FC = () => {
  const [alunos, setAlunos] = useState<AdminAlunoNota[]>([]);
  const [notas, setNotas] = useState<AdminNota[]>([]);
  const [alunoNotas, setAlunoNotas] = useState<AdminAlunoNota | null>(null);
  const [offsetNotas, setOffsetNotas] = useState(0);
  const [totalNotas, setTotalNotas] = useState(0);
  const [carregandoNotas, setCarregandoNotas] = useState(false);
  const [erroNotas, setErroNotas] = useState('');
  const [busca, setBusca] = useState('');
  const [disciplinaNome, setDisciplinaNome] = useState('');
  const [buscaFiltro, setBuscaFiltro] = useState('');
  const [disciplinaNomeFiltro, setDisciplinaNomeFiltro] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [rascunhos, setRascunhos] = useState<Record<string, string>>({});
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [salvandoId, setSalvandoId] = useState('');
  const [atualizacao, setAtualizacao] = useState(0);
  const [historicoAluno, setHistoricoAluno] = useState<{ id: string; dados: Academico } | null>(null);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [baixandoHistorico, setBaixandoHistorico] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const resposta = await notasHistoricoApi.listarAlunosAdmin({
        q: buscaFiltro || undefined,
        disciplina_nome: disciplinaNomeFiltro || undefined,
        limit: 30,
        offset,
      });
      setAlunos(resposta.items);
      setTotal(resposta.total);
      if (offset > 0 && offset >= resposta.total) {
        setOffset(Math.max(0, Math.ceil(resposta.total / 30) * 30 - 30));
      }
    } catch (error) {
      setAlunos([]);
      setTotal(0);
      setErro(mensagemErroNotas(error, 'Não foi possível carregar os alunos.'));
    } finally {
      setCarregando(false);
    }
  }, [buscaFiltro, disciplinaNomeFiltro, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar, atualizacao]);

  useEffect(() => {
    if (!alunoNotas) return;
    let ativa = true;
    setCarregandoNotas(true);
    setErroNotas('');
    notasHistoricoApi.listarNotasAdmin({ aluno_id: alunoNotas.aluno_id, limit: 30, offset: offsetNotas })
      .then((resposta) => {
        if (!ativa) return;
        setNotas(resposta.items);
        setTotalNotas(resposta.total);
        setRascunhos(Object.fromEntries(resposta.items.map((nota) => [nota.id, String(nota.valor)])));
        if (offsetNotas > 0 && offsetNotas >= resposta.total) {
          setOffsetNotas(Math.max(0, Math.ceil(resposta.total / 30) * 30 - 30));
        }
      })
      .catch((error: unknown) => {
        if (ativa) {
          setNotas([]);
          setTotalNotas(0);
          setErroNotas(mensagemErroNotas(error, 'Não foi possível carregar as notas deste aluno.'));
        }
      })
      .finally(() => {
        if (ativa) setCarregandoNotas(false);
      });
    return () => { ativa = false; };
  }, [alunoNotas, offsetNotas, atualizacao]);

  const filtrar = (event: React.FormEvent) => {
    event.preventDefault();
    setBuscaFiltro(busca.trim());
    setDisciplinaNomeFiltro(disciplinaNome.trim());
    setOffset(0);
  };

  const corrigir = async (nota: AdminNota) => {
    const textoValor = rascunhos[nota.id] ?? String(nota.valor);
    const valor = Number(textoValor);
    if (!textoValor.trim() || !Number.isFinite(valor) || valor < 0 || valor > 10) {
      setErroNotas('Informe uma nota entre 0 e 10.');
      return;
    }
    setSalvandoId(nota.id);
    setErroNotas('');
    try {
      await notasHistoricoApi.corrigirNota(nota.id, valor);
      setAtualizacao((atual) => atual + 1);
    } catch (error) {
      setErroNotas(mensagemErroNotas(error, 'Não foi possível corrigir a nota.'));
    } finally {
      setSalvandoId('');
    }
  };

  const abrirHistorico = async (id: string) => {
    setCarregandoHistorico(true);
    setErro('');
    try {
      const dados = await alunosGestaoApi.academico(id);
      setHistoricoAluno({ id, dados });
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível carregar o histórico deste aluno.'));
    } finally {
      setCarregandoHistorico(false);
    }
  };

  const baixarHistorico = async () => {
    if (!historicoAluno) return;
    setBaixandoHistorico(true);
    setErro('');
    try {
      const arquivo = await alunosGestaoApi.boletimPdf(historicoAluno.id);
      const url = URL.createObjectURL(arquivo);
      const link = document.createElement('a');
      link.href = url;
      link.download = `boletim-${historicoAluno.dados.numero_matricula || historicoAluno.id}.pdf`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível gerar o PDF do histórico.'));
    } finally {
      setBaixandoHistorico(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <h1 className="text-2xl font-extrabold text-white sm:text-3xl">Notas &amp; Histórico Unificado</h1>
          <p className="mt-1 text-sm text-slate-400">
            Acompanhe lançamentos e corrija valores com registro de auditoria.
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

      <form onSubmit={filtrar} className="grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <label className="text-xs font-semibold text-slate-400">
          Buscar por nome, e-mail, matrícula ou CPF
          <input
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            maxLength={100}
            placeholder="Digite nome, e-mail, matrícula ou CPF"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white"
          />
        </label>
        <label className="text-xs font-semibold text-slate-400">
          Nome da disciplina
          <input
            value={disciplinaNome}
            onChange={(event) => setDisciplinaNome(event.target.value)}
            maxLength={255}
            placeholder="Digite o nome ou parte dele"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white"
          />
        </label>
        <button type="submit" className="inline-flex items-center justify-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-ink">
          <Search className="h-4 w-4" /> Filtrar
        </button>
      </form>
      <p className="text-xs text-slate-500">
        Exibindo {total ? Math.min(offset + 1, total) : 0}–{Math.min(offset + alunos.length, total)} de {total} alunos,
        ordenados pela atualização mais recente.
      </p>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Aluno / matrícula</th>
                <th className="px-4 py-3">Última atualização</th>
                <th className="px-4 py-3">Notas</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {carregando ? (
                <tr><td colSpan={3} className="py-12 text-center text-slate-400"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Carregando alunos...</td></tr>
              ) : alunos.length === 0 && !erro ? (
                <tr><td colSpan={3} className="py-12 text-center text-slate-500">Nenhum aluno com notas encontrado com os filtros selecionados.</td></tr>
              ) : alunos.map((aluno) => (
                <tr key={aluno.aluno_id}>
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => void abrirHistorico(aluno.aluno_id)} className="font-medium text-white underline decoration-slate-600 underline-offset-2 hover:text-nexus-yellow">
                      {aluno.aluno_nome || aluno.aluno_id}
                    </button>
                    <div className="mt-1 text-xs text-slate-500">
                      {[aluno.aluno_matricula, aluno.aluno_email].filter(Boolean).join(' · ')}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {aluno.atualizado_em ? new Date(aluno.atualizado_em).toLocaleString('pt-BR') : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => { setNotas([]); setTotalNotas(0); setOffsetNotas(0); setAlunoNotas(aluno); }} className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 hover:bg-slate-700">
                      Gerenciar notas
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <nav className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/80 p-3" aria-label="Paginação dos alunos">
        <button
          type="button"
          onClick={() => setOffset((atual) => Math.max(0, atual - 30))}
          disabled={offset === 0 || carregando}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4" /> Anterior
        </button>
        <span className="text-xs text-slate-400">
          Página {total ? Math.floor(offset / 30) + 1 : 0} de {Math.ceil(total / 30)}
        </span>
        <button
          type="button"
          onClick={() => setOffset((atual) => atual + 30)}
          disabled={offset + 30 >= total || carregando}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Próxima <ChevronRight className="h-4 w-4" />
        </button>
      </nav>
      <p className="text-xs text-slate-500">O histórico unificado considera a maior nota registrada por disciplina; aprovação a partir de 6,0.</p>

      {alunoNotas && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4" role="dialog" aria-modal="true" aria-labelledby="notas-aluno-titulo">
          <section className="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-slate-800 p-5">
              <div>
                <h2 id="notas-aluno-titulo" className="text-xl font-bold text-white">Notas do aluno</h2>
                <p className="mt-1 text-sm text-slate-400">{alunoNotas.aluno_nome || alunoNotas.aluno_id} · {alunoNotas.aluno_matricula || alunoNotas.aluno_id}</p>
              </div>
              <button type="button" onClick={() => setAlunoNotas(null)} className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800" aria-label="Fechar notas">
                <X className="h-4 w-4" />
              </button>
            </header>
            <div className="space-y-4 p-5">
              <p className="text-xs text-slate-400">Todas as disciplinas deste aluno são exibidas, independentemente do filtro da lista.</p>
              {erroNotas && <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">{erroNotas}</div>}
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full min-w-[700px] text-left text-sm text-slate-300">
                  <thead className="bg-slate-950/70 text-xs uppercase text-slate-400">
                    <tr><th className="px-4 py-3">Disciplina / Turma</th><th className="px-4 py-3">Origem / Data</th><th className="px-4 py-3">Nota</th><th className="px-4 py-3">Correção auditada</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70">
                    {carregandoNotas ? (
                      <tr><td colSpan={4} className="py-12 text-center text-slate-400"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Carregando notas...</td></tr>
                    ) : notas.length === 0 && !erroNotas ? (
                      <tr><td colSpan={4} className="py-12 text-center text-slate-500">Nenhuma nota encontrada.</td></tr>
                    ) : notas.map((nota) => (
                      <tr key={nota.id}>
                        <td className="px-4 py-3"><div className="text-white">{nota.disciplina_nome || nota.disciplina_id || '—'}</div><div className="text-xs text-slate-500">{nota.turma_nome || nota.turma_id || '—'}</div></td>
                        <td className="px-4 py-3 text-xs text-slate-400">{nota.origem === 'ava' ? 'AVA' : 'Manual'}{nota.lancado_em ? ` · ${new Date(nota.lancado_em).toLocaleDateString('pt-BR')}` : ''}</td>
                        <td className="px-4 py-3 font-bold text-white">{nota.valor.toLocaleString('pt-BR')}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <input type="number" min="0" max="10" step="0.01" value={rascunhos[nota.id] ?? nota.valor} onChange={(event) => setRascunhos((atuais) => ({ ...atuais, [nota.id]: event.target.value }))} aria-label={`Corrigir nota de ${nota.disciplina_nome || nota.disciplina_id || nota.id}`} className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-white" />
                            <button type="button" onClick={() => void corrigir(nota)} disabled={Boolean(salvandoId) || Number(rascunhos[nota.id] ?? nota.valor) === nota.valor} className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-200 hover:bg-slate-700 disabled:opacity-40" aria-label="Salvar correção">
                              {salvandoId === nota.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <nav className="flex items-center justify-between gap-3" aria-label="Paginação das notas do aluno">
                <button type="button" onClick={() => setOffsetNotas((atual) => Math.max(0, atual - 30))} disabled={offsetNotas === 0 || carregandoNotas} className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /> Anterior</button>
                <span className="text-xs text-slate-400">Página {totalNotas ? Math.floor(offsetNotas / 30) + 1 : 0} de {Math.ceil(totalNotas / 30)}</span>
                <button type="button" onClick={() => setOffsetNotas((atual) => atual + 30)} disabled={offsetNotas + 30 >= totalNotas || carregandoNotas} className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 disabled:opacity-40">Próxima <ChevronRight className="h-4 w-4" /></button>
              </nav>
            </div>
          </section>
        </div>
      )}

      {carregandoHistorico && (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900 p-5 text-sm text-slate-300">
          <Loader2 className="h-4 w-4 animate-spin" /> Carregando histórico do aluno...
        </div>
      )}

      {historicoAluno && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4" role="dialog" aria-modal="true" aria-labelledby="historico-aluno-titulo">
          <section className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-slate-800 p-5">
              <div>
                <h2 id="historico-aluno-titulo" className="text-xl font-bold text-white">Histórico acadêmico</h2>
                <p className="mt-1 text-sm text-slate-400">
                  {historicoAluno.dados.aluno_nome} · {historicoAluno.dados.numero_matricula || historicoAluno.id}
                </p>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => void baixarHistorico()} disabled={baixandoHistorico} className="inline-flex items-center gap-2 rounded-lg bg-nexus-yellow px-3 py-2 text-xs font-bold text-ink disabled:opacity-50">
                  {baixandoHistorico ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} PDF
                </button>
                <button type="button" onClick={() => setHistoricoAluno(null)} className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-800" aria-label="Fechar histórico">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </header>
            <div className="space-y-5 p-5">
              {historicoAluno.dados.cursos.length === 0 ? (
                <p className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 text-center text-sm text-slate-400">Nenhum registro acadêmico disponível.</p>
              ) : historicoAluno.dados.cursos.map((curso) => (
                <section key={curso.id} className="space-y-2">
                  <h3 className="flex items-center gap-2 font-semibold text-white"><FileText className="h-4 w-4 text-blue-300" />{curso.nome}</h3>
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full min-w-[450px] text-left text-xs text-slate-300">
                      <thead className="bg-slate-950/70 text-slate-400">
                        <tr><th className="px-3 py-2">Disciplina</th><th className="px-3 py-2">Nota</th><th className="px-3 py-2">Situação</th></tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/70">
                        {curso.disciplinas.map((disciplina) => (
                          <tr key={disciplina.id}>
                            <td className="px-3 py-2 text-white">{disciplina.nome}</td>
                            <td className="px-3 py-2">{disciplina.nota == null ? '—' : disciplina.nota.toLocaleString('pt-BR')}</td>
                            <td className="px-3 py-2">{disciplina.situacao}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
};
