import React, { useState } from 'react';
import { FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { useFiltrosUrl } from '@/components/filters/PeriodoFiltros';
import { financeiroApi } from '@/features/financeiro/api';
import { FiltrosPeriodo } from '@/features/financeiro/types';
import { baixarArquivo, erroDeBlob, nomeDoArquivo } from '@/lib/download';

interface Props {
  recurso: 'vendas' | 'pagamentos' | 'pedidos';
  /** Filtros fixos da tela (ex.: só livros no histórico da logística). */
  filtrosFixos?: FiltrosPeriodo;
}

/** Exporta o relatório da tela em PDF ou Excel com os filtros atuais (da URL). */
export const BotoesExportar: React.FC<Props> = ({ recurso, filtrosFixos }) => {
  const { filtros } = useFiltrosUrl();
  const [gerando, setGerando] = useState<'pdf' | 'xlsx' | null>(null);
  const [erro, setErro] = useState('');

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setGerando(formato);
    setErro('');
    try {
      const { blob, disposition } = await financeiroApi.exportar(recurso, formato, { ...filtros, ...(filtrosFixos || {}) });
      baixarArquivo(blob, nomeDoArquivo(disposition, `${recurso}.${formato}`));
    } catch (error) {
      setErro(await erroDeBlob(error, 'Não foi possível gerar o arquivo.'));
    } finally {
      setGerando(null);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex gap-2">
        <button onClick={() => exportar('pdf')} disabled={!!gerando} title="Exportar PDF com os filtros atuais" className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:text-white disabled:opacity-50">
          {gerando === 'pdf' ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} PDF
        </button>
        <button onClick={() => exportar('xlsx')} disabled={!!gerando} title="Exportar Excel com os filtros atuais" className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/50 px-3 py-2 text-xs font-semibold text-emerald-300 hover:text-white disabled:opacity-50">
          {gerando === 'xlsx' ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />} Excel
        </button>
      </div>
      {erro && <p className="max-w-xs text-right text-[11px] text-red-300">{erro}</p>}
    </div>
  );
};
