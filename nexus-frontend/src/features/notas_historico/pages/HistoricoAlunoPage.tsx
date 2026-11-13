import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Award, CheckCircle2, Download, Loader2, RefreshCw } from 'lucide-react';
import {
  HistoricoItem,
  mensagemErroNotas,
  notasHistoricoApi,
} from '@/features/notas_historico/api';

export const HistoricoAlunoPage: React.FC = () => {
  const [historico, setHistorico] = useState<HistoricoItem[]>([]);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [baixando, setBaixando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      setHistorico(await notasHistoricoApi.meuHistorico());
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível carregar seu histórico.'));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const baixarPdf = async () => {
    setBaixando(true);
    setErro('');
    try {
      const blob = await notasHistoricoApi.baixarMeuHistoricoPdf();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'meu-historico-academico.pdf';
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) {
      setErro(mensagemErroNotas(error, 'Não foi possível gerar o PDF do histórico.'));
    } finally {
      setBaixando(false);
    }
  };

  const aprovadas = historico.filter((item) => item.status === 'aprovado').length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 p-6 shadow-xl sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-nexus-yellow/30 bg-nexus-yellow/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-nexus-yellow">
            <Award className="h-3.5 w-3.5" /> Ambiente do Aluno
          </div>
          <h1 className="text-2xl font-extrabold text-white sm:text-3xl">Notas &amp; Histórico</h1>
          <p className="mt-1 text-sm text-slate-400">Consulte suas notas finais e emita seu histórico acadêmico.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void carregar()} disabled={carregando} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${carregando ? 'animate-spin' : ''}`} /> Atualizar
          </button>
          <button type="button" onClick={() => void baixarPdf()} disabled={baixando} className="inline-flex items-center gap-2 rounded-xl bg-nexus-yellow px-3 py-2 text-sm font-bold text-slate-950 disabled:opacity-50">
            {baixando ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Baixar PDF
          </button>
        </div>
      </header>

      {erro && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-400" /> {erro}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Disciplinas no histórico</p>
          <p className="mt-2 text-3xl font-black text-white">{historico.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Aprovadas</p>
          <p className="mt-2 flex items-center gap-2 text-3xl font-black text-emerald-400"><CheckCircle2 className="h-6 w-6" />{aprovadas}</p>
        </div>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[650px] text-left text-sm text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-3">Curso</th>
                <th className="px-4 py-3">Disciplina</th>
                <th className="px-4 py-3">Nota final</th>
                <th className="px-4 py-3">Situação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {carregando ? (
                <tr><td colSpan={4} className="py-12 text-center text-slate-400"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />Carregando histórico...</td></tr>
              ) : historico.length === 0 ? (
                <tr><td colSpan={4} className="py-12 text-center text-slate-500">Ainda não há notas consolidadas no seu histórico.</td></tr>
              ) : historico.map((item) => (
                <tr key={item.id || `${item.aluno_id}-${item.disciplina_id}`}>
                  <td className="px-4 py-3 text-slate-400">{item.curso_nome || '—'}</td>
                  <td className="px-4 py-3 font-medium text-white">{item.disciplina_nome || item.disciplina_id || 'Disciplina'}</td>
                  <td className="px-4 py-3 font-bold text-white">{item.nota_final == null ? '—' : item.nota_final.toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                      item.status === 'aprovado'
                        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                        : item.status === 'reprovado'
                          ? 'border-red-500/30 bg-red-500/10 text-red-300'
                          : 'border-slate-700 bg-slate-800 text-slate-300'
                    }`}>
                      {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <p className="text-xs text-slate-500">A nota final é a maior nota registrada por disciplina. A média para aprovação é 6,0.</p>
    </div>
  );
};
