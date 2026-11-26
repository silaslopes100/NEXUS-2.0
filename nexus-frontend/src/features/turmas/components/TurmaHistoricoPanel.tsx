import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Award, BarChart3, Loader2, Printer, Search, TrendingUp, Users } from 'lucide-react';
import { GraficoBarrasMensal, LinhaMensal } from '@/components/charts/GraficoBarrasMensal';
import { HistoricoTurma, cargaHorariaApi, erroApi } from '@/features/carga_horaria/api';

const num = (v?: number | null, casas = 1) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

const corIndice = (v?: number | null) =>
  v == null ? 'text-slate-400' : v >= 75 ? 'text-emerald-300' : v >= 50 ? 'text-amber-300' : 'text-red-300';

const Card: React.FC<{ rotulo: string; valor: string; detalhe?: string; icone: React.ElementType; destaque?: string }> = ({
  rotulo, valor, detalhe, icone: Icone, destaque = 'text-white',
}) => (
  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
    <p className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500"><Icone size={14} /> {rotulo}</p>
    <strong className={`mt-2 block text-3xl font-black ${destaque}`}>{valor}</strong>
    {detalhe && <p className="mt-1 text-xs text-slate-400">{detalhe}</p>}
  </div>
);

const Barra: React.FC<{ pct?: number | null; cor?: string }> = ({ pct, cor = 'bg-blue-500' }) => (
  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
    <div className={`h-full rounded-full ${cor}`} style={{ width: `${Math.max(0, Math.min(100, pct ?? 0))}%` }} />
  </div>
);

const SITUACAO = {
  bom: { rotulo: 'Bom', classe: 'bg-emerald-500/15 text-emerald-300' },
  atencao: { rotulo: 'Atenção', classe: 'bg-red-500/15 text-red-300' },
  sem_dados: { rotulo: 'Sem dados', classe: 'bg-slate-800 text-slate-400' },
} as const;

/** Histórico (desempenho) da turma: notas finais, frequência e índice de desempenho. */
export const TurmaHistoricoPanel: React.FC<{ turmaId: string; turmaNome: string }> = ({ turmaId, turmaNome }) => {
  const [dados, setDados] = useState<HistoricoTurma | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState('');

  useEffect(() => {
    cargaHorariaApi.historico(turmaId).then(setDados).catch((e) => setErro(erroApi(e, 'Não foi possível carregar o histórico.')));
  }, [turmaId]);

  const alunos = useMemo(() => {
    const t = busca.trim().toLowerCase();
    return (dados?.alunos ?? []).filter((a) => !t || a.nome.toLowerCase().includes(t) || (a.numero_matricula || '').toLowerCase().includes(t));
  }, [dados, busca]);

  if (erro) {
    return <p role="alert" className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"><AlertCircle size={16} /> {erro}</p>;
  }
  if (!dados) return <div className="flex justify-center py-16 text-blue-400"><Loader2 className="animate-spin" /></div>;

  const r = dados.resumo;
  const formula = dados.frequencia_aplica
    ? `Índice: notas ${num(dados.peso_notas, 0)} · frequência ${num(dados.peso_frequencia, 0)} (pesos do ranking de Polos)`
    : 'Turma EAD: o índice usa só as notas';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Histórico da turma · {turmaNome}</h2>
          <p className="text-xs text-slate-400">Nota final = maior nota do aluno em cada disciplina · aprovação a partir de 6,0 · {formula}</p>
        </div>
        <button type="button" onClick={() => window.print()}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 print:hidden">
          <Printer size={14} /> Imprimir / PDF
        </button>
      </div>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Card icone={TrendingUp} rotulo="Índice de desempenho" valor={num(r.indice)} detalhe="0 a 100" destaque={corIndice(r.indice)} />
        <Card icone={Award} rotulo="Média geral" valor={num(r.media_geral)} detalhe={`${r.notas_lancadas} nota(s) final(is) · ${r.alunos} aluno(s)`} />
        <Card icone={BarChart3} rotulo="Aprovação" valor={r.aprovacao_pct == null ? '—' : `${num(r.aprovacao_pct)}%`} />
        <Card icone={Users} rotulo="Frequência média"
          valor={dados.frequencia_aplica ? (r.frequencia_media == null ? '—' : `${num(r.frequencia_media)}%`) : 'N/A'}
          detalhe={dados.frequencia_aplica ? `${r.abaixo_minimo} aluno(s) abaixo de ${num(r.minimo_pct, 0)}%` : 'Não se aplica à Turma EAD'} />
      </section>

      {dados.evolucao.length > 0 && (
        <GraficoBarrasMensal titulo="Média das notas por mês" subtitulo="Pelo mês de lançamento" series={[{ chave: 'media', rotulo: 'Média' }]}
          dados={dados.evolucao as unknown as LinhaMensal[]} formatar={(v) => num(v, 2)} detalhe={(l) => `${l.notas} nota(s)`} />
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <h3 className="border-b border-slate-800 p-4 font-bold text-white">Por disciplina</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="p-3">Disciplina</th><th className="p-3">Média</th><th className="p-3 text-center">Aprovados</th>
                <th className="p-3 text-center">Reprovados</th><th className="p-3 text-center">Sem nota</th>
                {dados.frequencia_aplica && <th className="p-3">Frequência</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {dados.disciplinas.map((d) => (
                <tr key={d.disciplina_id}>
                  <td className="p-3 text-white">{d.nome}{d.semestre ? <span className="ml-1 text-[11px] text-slate-500">{d.semestre}º sem.</span> : null}</td>
                  <td className="w-40 p-3">
                    <span className="font-semibold text-white">{num(d.media)}</span>
                    {d.media != null && <Barra pct={d.media * 10} cor={d.media >= 6 ? 'bg-emerald-500' : 'bg-red-500'} />}
                  </td>
                  <td className="p-3 text-center text-emerald-300">{d.aprovados}</td>
                  <td className="p-3 text-center text-red-300">{d.reprovados}</td>
                  <td className="p-3 text-center text-slate-500">{d.sem_nota}</td>
                  {dados.frequencia_aplica && <td className="p-3">{d.frequencia_media == null ? '—' : `${num(d.frequencia_media)}%`}</td>}
                </tr>
              ))}
              {!dados.disciplinas.length && <tr><td colSpan={6} className="p-8 text-center text-slate-500">O curso não tem disciplinas.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-4">
          <h3 className="font-bold text-white">Por aluno</h3>
          <div className="relative print:hidden">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar aluno"
              className="rounded-xl border border-slate-700 bg-slate-950 py-1.5 pl-8 pr-3 text-xs text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="p-3">Aluno</th><th className="p-3">Média</th><th className="p-3 text-center">Aprovadas</th>
                <th className="p-3 text-center">Reprovadas</th>{dados.frequencia_aplica && <th className="p-3">Frequência</th>}<th className="p-3">Situação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {alunos.map((a) => (
                <tr key={a.aluno_id}>
                  <td className="p-3"><p className="text-white">{a.nome}</p><p className="text-[11px] text-slate-500">{a.numero_matricula}</p></td>
                  <td className="p-3 font-semibold text-white">{num(a.media)}</td>
                  <td className="p-3 text-center text-emerald-300">{a.aprovadas}</td>
                  <td className="p-3 text-center text-red-300">{a.reprovadas}</td>
                  {dados.frequencia_aplica && (
                    <td className={`p-3 ${a.em_risco ? 'text-red-300' : ''}`}>{a.frequencia_pct == null ? '—' : `${num(a.frequencia_pct)}%`}</td>
                  )}
                  <td className="p-3"><span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${SITUACAO[a.situacao].classe}`}>{SITUACAO[a.situacao].rotulo}</span></td>
                </tr>
              ))}
              {!alunos.length && <tr><td colSpan={6} className="p-8 text-center text-slate-500">Nenhum aluno.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
