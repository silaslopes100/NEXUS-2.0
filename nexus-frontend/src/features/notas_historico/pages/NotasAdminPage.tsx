import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Award, ChevronLeft, ChevronRight, Download, FileText, Loader2, RefreshCw, Save, Search, X } from 'lucide-react';
import { Academico, alunosGestaoApi } from '@/features/alunos/api';
import {
  AdminNota,
  mensagemErroNotas,
  notasHistoricoApi,
} from '@/features/notas_historico/api';

export const NotasAdminPage: React.FC = () => {
  const [notas, setNotas] = useState<AdminNota[]>([]);
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
      const resposta = await notasHistoricoApi.listarNotasAdmin({
        q: buscaFiltro || undefined,
        disciplina_nome: disciplinaNomeFiltro || undefined,
        limit: 30,
        offset,
      });
      setNotas(resposta.items);
      setTotal(resposta.total);
      setRascunhos(
        Object.fromEntries(resposta.items.map((nota) => [nota.id, String(nota.valor)]))
      );
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível carregar as notas.'));
    } finally {
      setCarregando(false);
    }
  }, [buscaFiltro, disciplinaNomeFiltro, offset]);

  useEffect(() => {
    void carregar();
  }, [carregar, atualizacao]);

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
      setErro('Informe uma nota entre 0 e 10.');
      return;
    }
    setSalvandoId(nota.id);
    setErro('');
    try {
      await notasHistoricoApi.corrigirNota(nota.id, valor);
      setAtualizacao((atual) => atual + 1);
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível corrigir a nota.'));
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
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-nexus-yellow/30 bg-nexus-yellow/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-nexus-yellow">
            <Award className="h-3.5 w-3.5" /> Gestão Acadêmica
          </div>
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
        <button type="submit" className="inline-flex items-center justify-center gap-2 rounded-xl bg-nexus-yellow px-4 py-2.5 text-sm font-bold text-slate-950">
          <Search className="h-4 w-4" /> Filtrar
        </button>
      </form>
      <p className="text-xs text-slate-500">
        Exibindo {total ? offset + 1 : 0}–{Math.min(offset + notas.length, total)} de {total} registros,
        ordenados pela atualização mais recente.
      </p>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Aluno / matrícula</th>
                <th className="px-4 py-3">Disciplina / Turma</th>
                <th className="px-4 py-3">Origem / Data</th>
                <th className="px-4 py-3">Nota</th>
                <th className="px-4 py-3">Correção auditada</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {carregando ? (
                <tr><td colSpan={5} className="py-12 text-center text-slate-400"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Carregando notas...</td></tr>
              ) : notas.length === 0 ? (
                <tr><td colSpan={5} className="py-12 text-center text-slate-500">Nenhuma nota encontrada com os filtros selecionados.</td></tr>
              ) : notas.map((nota) => (
                <tr key={nota.id}>
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => void abrirHistorico(nota.aluno_id)} className="font-medium text-white underline decoration-slate-600 underline-offset-2 hover:text-nexus-yellow">
                      {nota.aluno_nome || nota.aluno_id}
                    </button>
                    <div className="mt-1 text-xs text-slate-500">
                      {[nota.aluno_matricula, nota.aluno_email].filter(Boolean).join(' · ')}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-white">{nota.disciplina_nome || nota.disciplina_id || '—'}</div>
                    <div className="text-xs text-slate-500">{nota.turma_nome || nota.turma_id || '—'}</div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {nota.origem === 'ava' ? 'AVA' : 'Manual'}
                    {nota.lancado_em ? ` · ${new Date(nota.lancado_em).toLocaleDateString('pt-BR')}` : ''}
                  </td>
                  <td className="px-4 py-3 font-bold text-white">{nota.valor.toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <input type="number" min="0" max="10" step="0.01" value={rascunhos[nota.id] ?? nota.valor} onChange={(event) => setRascunhos((atuais) => ({ ...atuais, [nota.id]: event.target.value }))} aria-label={`Corrigir nota de ${nota.aluno_nome || nota.aluno_id}`} className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-white" />
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
      </section>
      <nav className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/80 p-3" aria-label="Paginação das notas">
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
                <button type="button" onClick={() => void baixarHistorico()} disabled={baixandoHistorico} className="inline-flex items-center gap-2 rounded-lg bg-nexus-yellow px-3 py-2 text-xs font-bold text-slate-950 disabled:opacity-50">
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
