import React, { useState } from 'react';
import { Check, Download, ExternalLink, FileText, Loader2, Minus, X } from 'lucide-react';
import { apiErrorMessage, professoresApi } from '@/features/professores/api';
import { AlunoChamadaAula, MaterialAula } from '@/features/aulas/api';

/** Abre o link externo ou baixa o arquivo do material (endpoint já autorizado para admin e professor). */
export const MaterialItem: React.FC<{
  material: MaterialAula;
  onErro: (mensagem: string) => void;
  acoes?: React.ReactNode;
}> = ({ material, onErro, acoes }) => {
  const [baixando, setBaixando] = useState(false);
  const nome = material.descricao || material.arquivo_nome || 'Material';

  const baixar = async () => {
    setBaixando(true);
    try {
      const arquivo = await professoresApi.baixarMaterial(material.id);
      const url = URL.createObjectURL(arquivo);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = material.arquivo_nome || nome;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      onErro(apiErrorMessage(error, 'Não foi possível baixar o arquivo.'));
    } finally {
      setBaixando(false);
    }
  };

  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex min-w-0 items-center gap-2">
        <FileText className="h-4 w-4 shrink-0 text-emerald-300" />
        <div className="min-w-0">
          <p className="truncate text-sm text-slate-200">{nome}</p>
          {material.tem_arquivo && material.arquivo_nome && (
            <p className="truncate text-xs text-slate-500">{material.arquivo_nome}</p>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {material.tem_arquivo ? (
          <button
            type="button"
            onClick={() => void baixar()}
            disabled={baixando}
            aria-label={`Baixar ${nome}`}
            className="text-emerald-300 hover:text-emerald-200 disabled:opacity-50"
          >
            {baixando ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
          </button>
        ) : material.arquivo_url ? (
          <a
            href={material.arquivo_url}
            target="_blank"
            rel="noreferrer"
            aria-label={`Abrir ${nome}`}
            className="text-emerald-300 hover:text-emerald-200"
          >
            <ExternalLink size={16} />
          </a>
        ) : null}
        {acoes}
      </div>
    </li>
  );
};

/** Lista somente leitura da chamada (auditoria). */
export const ChamadaResumo: React.FC<{ chamada: AlunoChamadaAula[] }> = ({ chamada }) => {
  if (chamada.length === 0) {
    return <p className="text-sm text-slate-500">Nenhum aluno matriculado nesta turma.</p>;
  }
  return (
    <ul className="grid gap-1.5 sm:grid-cols-2">
      {chamada.map((aluno) => (
        <li key={aluno.aluno_id} className="flex items-center gap-2 text-sm text-slate-300">
          {aluno.presente === true ? (
            <Check className="h-4 w-4 shrink-0 text-emerald-400" aria-label="Presente" />
          ) : aluno.presente === false ? (
            <X className="h-4 w-4 shrink-0 text-amber-400" aria-label="Ausente" />
          ) : (
            <Minus className="h-4 w-4 shrink-0 text-slate-600" aria-label="Sem registro" />
          )}
          <span className="truncate">{aluno.nome}</span>
        </li>
      ))}
    </ul>
  );
};

/** Selo "presentes/total" ou "sem chamada". */
export const SeloPresenca: React.FC<{ presentes: number; total: number }> = ({ presentes, total }) =>
  total === 0 ? (
    <span className="text-xs text-slate-500">Sem chamada</span>
  ) : (
    <span className="text-xs font-semibold text-slate-200">
      {presentes}/{total} presentes
    </span>
  );

/** Selo de ata registrada ou pendente. */
export const SeloAta: React.FC<{ temAta: boolean }> = ({ temAta }) =>
  temAta ? (
    <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-semibold text-emerald-300">
      Ata registrada
    </span>
  ) : (
    <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-300">
      Ata pendente
    </span>
  );
