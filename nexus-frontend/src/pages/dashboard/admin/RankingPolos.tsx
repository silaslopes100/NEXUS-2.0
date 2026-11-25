import React, { useState } from 'react';
import { ArrowDown, FileSpreadsheet, FileText, Loader2, Trophy } from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { formatBRL } from '@/features/financeiro/types';
import { baixarArquivo, erroDeBlob, nomeDoArquivo } from '@/lib/download';
import { FiltrosDashboard, OrdenacaoRanking, RankingPolos as Ranking } from '@/types/admin';
import { fmtInt, fmtPct } from './formato';

const COLUNAS: { chave: OrdenacaoRanking; rotulo: string }[] = [
  { chave: 'novas_licencas', rotulo: 'Novas licenças' },
  { chave: 'receita_paga', rotulo: 'Receita paga' },
  { chave: 'alunos_ativos', rotulo: 'Alunos ativos' },
  { chave: 'presenca_pct', rotulo: 'Presença' },
];
const TOP_INICIAL = 10;

interface Props {
  ranking: Ranking | null;
  erro: boolean;
  carregando: boolean;
  ordenarPor: OrdenacaoRanking;
  onOrdenar: (chave: OrdenacaoRanking) => void;
  filtros: FiltrosDashboard;
}

/** Ranking de Polos no período (requisito 1.2), ordenável e exportável em PDF/Excel. */
export const RankingPolos: React.FC<Props> = ({ ranking, erro, carregando, ordenarPor, onOrdenar, filtros }) => {
  const [todos, setTodos] = useState(false);
  const [gerando, setGerando] = useState<'pdf' | 'xlsx' | null>(null);
  const [erroExportar, setErroExportar] = useState('');
  const itens = ranking?.items || [];
  const visiveis = todos ? itens : itens.slice(0, TOP_INICIAL);

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

  const valorColuna = (chave: OrdenacaoRanking, i: Ranking['items'][number]) =>
    chave === 'receita_paga' ? formatBRL(i.receita_paga)
      : chave === 'presenca_pct' ? fmtPct(i.presenca_pct)
        : fmtInt(i[chave]);

  return (
    <section className="glass overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-5">
        <div>
          <h2 className="flex items-center gap-2 text-base font-bold text-white">
            <Trophy className="h-5 w-5 text-nexus-yellow" /> Ranking de Polos
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Clique no título de uma coluna para reordenar. Licenças e receita: pedidos pagos no período.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex gap-2">
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
          <table className="w-full min-w-[640px] text-left text-sm">
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
                  <td className="max-w-[260px] truncate p-3 font-semibold text-white" title={i.polo_nome}>{i.polo_nome}</td>
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
    </section>
  );
};
