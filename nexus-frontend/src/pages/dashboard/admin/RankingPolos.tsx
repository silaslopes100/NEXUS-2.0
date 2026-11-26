import React, { useState } from 'react';
import { ArrowDown, FileSpreadsheet, FileText, Loader2, Settings2, Trophy, X } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { formatBRL } from '@/features/financeiro/types';
import { baixarArquivo, erroDeBlob, nomeDoArquivo } from '@/lib/download';
import { FiltrosDashboard, OrdenacaoRanking, PesosRanking, RankingPolos as Ranking } from '@/types/admin';
import { fmtInt, fmtPct } from './formato';

const COLUNAS: { chave: OrdenacaoRanking; rotulo: string }[] = [
  { chave: 'indice', rotulo: 'Índice' },
  { chave: 'notas_media', rotulo: 'Notas' },
  { chave: 'presenca_pct', rotulo: 'Presença' },
  { chave: 'compras_qtd', rotulo: 'Compras' },
  { chave: 'novas_licencas', rotulo: 'Novas licenças' },
  { chave: 'receita_paga', rotulo: 'Receita paga' },
  { chave: 'alunos_ativos', rotulo: 'Alunos ativos' },
];
const TOP_INICIAL = 10;

const fmt1 = (v?: number | null, casas = 1) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

type Pesos = Omit<PesosRanking, 'atualizado_em'>;

/** Pesos do índice de desempenho: notas, frequência e compras (viram proporção da soma). */
const PesosModal: React.FC<{ atual?: PesosRanking | null; onFechar: () => void; onSalvo: () => void }> = ({ atual, onFechar, onSalvo }) => {
  const [p, setP] = useState<Pesos>({
    peso_notas: atual?.peso_notas ?? 40, peso_frequencia: atual?.peso_frequencia ?? 30, peso_compras: atual?.peso_compras ?? 30,
  });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const soma = p.peso_notas + p.peso_frequencia + p.peso_compras;
  const pct = (v: number) => (soma > 0 ? Math.round((v * 100) / soma) : 0);
  const campos: { chave: keyof Pesos; rotulo: string; ajuda: string }[] = [
    { chave: 'peso_notas', rotulo: 'Notas', ajuda: 'Média das notas finais dos alunos das turmas do Polo e das Escolas dele, no período.' },
    { chave: 'peso_frequencia', rotulo: 'Frequência', ajuda: 'Presença média nas chamadas do período.' },
    { chave: 'peso_compras', rotulo: 'Compras', ajuda: 'Licenças e livros pagos pelo Polo + solicitações atendidas das Escolas, em relação ao Polo que mais comprou.' },
  ];

  const salvar = async () => {
    setSalvando(true);
    setErro('');
    try {
      await adminApi.salvarPesosRanking(p);
      onSalvo();
    } catch {
      setErro('Não foi possível salvar os pesos.');
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 overflow-y-auto" onMouseDown={onFechar}>
      <div className="my-auto w-full max-w-lg space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-white">Pesos do índice de desempenho</h3>
            <p className="text-xs text-slate-400">
              Índice (0 a 100) = média ponderada dos três componentes; componente sem dados conta 0. Os pesos de notas e
              frequência também valem para o Histórico das turmas.
            </p>
          </div>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="rounded-lg p-1 text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        {campos.map((c) => (
          <label key={c.chave} className="block space-y-1.5">
            <span className="flex items-center justify-between text-sm font-semibold text-white">
              {c.rotulo} <span className="text-xs font-bold text-nexus-yellow">{pct(p[c.chave])}%</span>
            </span>
            <span className="flex items-center gap-3">
              <input type="range" min={0} max={100} step={5} value={p[c.chave]}
                onChange={(e) => setP((x) => ({ ...x, [c.chave]: Number(e.target.value) }))} className="flex-1 accent-amber-400" />
              <input type="number" min={0} max={1000} value={p[c.chave]}
                onChange={(e) => setP((x) => ({ ...x, [c.chave]: Math.max(0, Number(e.target.value) || 0) }))}
                className="w-20 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-right text-sm text-white" />
            </span>
            <span className="block text-[11px] text-slate-500">{c.ajuda}</span>
          </label>
        ))}
        {erro && <p className="text-sm text-red-300">{erro}</p>}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <button type="button" onClick={() => setP({ peso_notas: 40, peso_frequencia: 30, peso_compras: 30 })}
            className="text-xs font-semibold text-slate-400 hover:text-white">Restaurar 40 / 30 / 30</button>
          <div className="flex gap-2">
            <button type="button" onClick={onFechar} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Cancelar</button>
            <button type="button" disabled={soma <= 0 || salvando} onClick={() => void salvar()}
              className="rounded-xl bg-nexus-yellow px-4 py-2 text-sm font-bold text-ink hover:bg-nexus-yellow-hover disabled:opacity-50">
              {salvando ? 'Salvando…' : 'Salvar e recalcular'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

interface Props {
  ranking: Ranking | null;
  erro: boolean;
  carregando: boolean;
  ordenarPor: OrdenacaoRanking;
  onOrdenar: (chave: OrdenacaoRanking) => void;
  filtros: FiltrosDashboard;
  onPesosSalvos?: () => void;
}

/** Ranking de Polos no período: índice de desempenho (notas, frequência, compras) e indicadores, exportável. */
export const RankingPolos: React.FC<Props> = ({ ranking, erro, carregando, ordenarPor, onOrdenar, filtros, onPesosSalvos }) => {
  const [todos, setTodos] = useState(false);
  const [pesosAberto, setPesosAberto] = useState(false);
  const [gerando, setGerando] = useState<'pdf' | 'xlsx' | null>(null);
  const [erroExportar, setErroExportar] = useState('');
  const itens = ranking?.items || [];
  const visiveis = todos ? itens : itens.slice(0, TOP_INICIAL);
  const pesos = ranking?.pesos;

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setGerando(formato);
    setErroExportar('');
    try {
      const { blob, disposition } = await adminApi.exportarRankingPolos(filtros, ordenarPor, formato);
      baixarArquivo(blob, nomeDoArquivo(disposition, `ranking-polos.${formato}`));
    } catch (error) {
      setErroExportar(await erroDeBlob(error, 'Não foi possível gerar o arquivo.'));
    } finally {
      setGerando(null);
    }
  };

  const valorColuna = (chave: OrdenacaoRanking, i: Ranking['items'][number]): React.ReactNode => {
    if (chave === 'indice') {
      const v = i.indice ?? 0;
      const cor = i.indice == null ? 'bg-slate-700' : v >= 75 ? 'bg-emerald-500' : v >= 50 ? 'bg-amber-400' : 'bg-red-500';
      return (
        <span className="inline-flex w-24 flex-col items-end gap-1"
          title={`Notas ${fmt1(i.notas_media, 2)} · Presença ${fmtPct(i.presenca_pct)} · Compras ${fmt1(i.compras_pct)}% do líder`}>
          <span className="font-bold text-white">{fmt1(i.indice)}</span>
          <span className="block h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <span className={`block h-full ${cor}`} style={{ width: `${Math.min(100, v)}%` }} />
          </span>
        </span>
      );
    }
    if (chave === 'notas_media') return fmt1(i.notas_media, 2);
    if (chave === 'compras_qtd') {
      return <span title={`Polo: ${fmtInt(i.compras_polo)} · Solicitações das Escolas: ${fmtInt(i.solicitacoes_escolas)}`}>{fmtInt(i.compras_qtd)}</span>;
    }
    if (chave === 'receita_paga') return formatBRL(i.receita_paga);
    if (chave === 'presenca_pct') return fmtPct(i.presenca_pct);
    return fmtInt(i[chave]);
  };

  return (
    <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-5">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-white">
            <Trophy className="h-5 w-5 text-nexus-yellow" /> Ranking de Polos
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Índice de desempenho = notas {fmt1(pesos?.peso_notas ?? 40, 0)} · frequência {fmt1(pesos?.peso_frequencia ?? 30, 0)} · compras{' '}
            {fmt1(pesos?.peso_compras ?? 30, 0)}. Compras incluem as solicitações atendidas das Escolas. Clique numa coluna para reordenar.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex gap-2">
            <button type="button" onClick={() => setPesosAberto(true)} title="Pesos do índice"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:text-white">
              <Settings2 size={14} /> Pesos
            </button>
            <button type="button" onClick={() => exportar('pdf')} disabled={!!gerando || !itens.length} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:text-white disabled:opacity-50">
              {gerando === 'pdf' ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} PDF
            </button>
            <button type="button" onClick={() => exportar('xlsx')} disabled={!!gerando || !itens.length} className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/50 px-3 py-2 text-xs font-semibold text-emerald-300 hover:text-white disabled:opacity-50">
              {gerando === 'xlsx' ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />} Excel
            </button>
          </div>
          {erroExportar && <p className="max-w-xs text-right text-[11px] text-red-300">{erroExportar}</p>}
        </div>
      </div>

      {erro ? (
        <p className="p-5 text-sm text-slate-500">Dados indisponíveis no momento.</p>
      ) : !ranking ? (
        <p className="p-5 text-sm text-slate-500">Carregando...</p>
      ) : !itens.length ? (
        <p className="p-8 text-center text-sm text-slate-500">Nenhum polo ativo.</p>
      ) : (
        <div className={`overflow-x-auto ${carregando ? 'opacity-60' : ''}`}>
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
              <tr>
                <th className="w-12 p-3">#</th>
                <th className="p-3">Polo</th>
                {COLUNAS.map((c) => (
                  <th key={c.chave} className="p-3 text-right" aria-sort={ordenarPor === c.chave ? 'descending' : 'none'}>
                    <button
                      type="button"
                      onClick={() => onOrdenar(c.chave)}
                      className={`inline-flex items-center gap-1 uppercase hover:text-white ${ordenarPor === c.chave ? 'text-nexus-yellow' : ''}`}
                    >
                      {c.rotulo} {ordenarPor === c.chave && <ArrowDown className="h-3 w-3" />}
                    </button>
                  </th>
                ))}
                <th className="p-3 text-right">Escolas</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {visiveis.map((i) => (
                <tr key={i.polo_id}>
                  <td className="p-3 text-xs font-bold text-slate-500">{i.posicao}º</td>
                  <td className="max-w-[240px] truncate p-3 font-semibold text-white" title={i.polo_nome}>{i.polo_nome}</td>
                  {COLUNAS.map((c) => (
                    <td key={c.chave} className={`p-3 text-right ${ordenarPor === c.chave ? 'font-semibold text-white' : ''}`}>
                      {valorColuna(c.chave, i)}
                    </td>
                  ))}
                  <td className="p-3 text-right">{fmtInt(i.escolas_ativas)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {itens.length > TOP_INICIAL && (
            <button type="button" onClick={() => setTodos(!todos)} className="w-full border-t border-slate-800 p-3 text-xs font-semibold text-nexus-yellow hover:bg-slate-800/40">
              {todos ? `Mostrar só os ${TOP_INICIAL} primeiros` : `Ver todos os ${fmtInt(itens.length)} polos`}
            </button>
          )}
        </div>
      )}
      {pesosAberto && (
        <PesosModal atual={pesos} onFechar={() => setPesosAberto(false)}
          onSalvo={() => { setPesosAberto(false); onPesosSalvos?.(); }} />
      )}
    </section>
  );
};
