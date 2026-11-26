import React from 'react';
import { EVENTO, MovimentacaoEad } from '../../adminApi';
import { brl } from '../../api';

const dataHora = (d?: string | null) =>
  d ? new Date(d).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';

/** Linha do tempo das movimentações EAD (geral ou de um aluno). */
export const ListaMovimentacoes: React.FC<{
  itens: MovimentacaoEad[];
  mostrarAluno?: boolean;
  onAbrirAluno?: (alunoId: string) => void;
}> = ({ itens, mostrarAluno = true, onAbrirAluno }) => {
  if (!itens.length) return <p className="py-8 text-center text-sm text-slate-500">Nenhuma movimentação.</p>;
  return (
    <ol className="relative space-y-4 border-l border-slate-800 pl-6">
      {itens.map((m, i) => {
        const ev = EVENTO[m.evento] ?? { rotulo: m.evento, cor: 'bg-slate-500' };
        return (
          <li key={`${m.evento}-${m.data}-${i}`} className="relative">
            <span className={`absolute -left-[29px] top-1.5 h-3 w-3 rounded-full ring-4 ring-slate-950 ${ev.cor}`} />
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <p className="text-sm font-semibold text-white">
                {ev.rotulo}
                {m.disciplina_nome && <span className="font-normal text-slate-300"> · {m.disciplina_nome}</span>}
              </p>
              <span className="text-[11px] text-slate-500">{dataHora(m.data)}</span>
            </div>
            <p className="text-xs text-slate-400">
              {mostrarAluno && m.aluno_nome && (
                <button type="button" disabled={!onAbrirAluno || !m.aluno_id} onClick={() => m.aluno_id && onAbrirAluno?.(m.aluno_id)}
                  className="font-semibold text-blue-300 hover:underline disabled:no-underline">
                  {m.aluno_nome}{m.numero_matricula ? ` (${m.numero_matricula})` : ''}
                </button>
              )}
              {mostrarAluno && m.aluno_nome && (m.turma_nome || m.detalhe || m.valor != null) ? ' · ' : ''}
              {[m.turma_nome, m.detalhe, m.valor != null && m.valor > 0 ? brl(m.valor) : null, m.autor_nome ? `por ${m.autor_nome}` : null]
                .filter(Boolean).join(' · ')}
            </p>
          </li>
        );
      })}
    </ol>
  );
};

/** Modal simples para pedir um motivo (cancelar matrícula, revogar liberação). */
export const MotivoModal: React.FC<{
  titulo: string;
  descricao?: string;
  rotuloConfirmar: string;
  perigo?: boolean;
  onConfirmar: (motivo: string) => Promise<void>;
  onFechar: () => void;
}> = ({ titulo, descricao, rotuloConfirmar, perigo, onConfirmar, onFechar }) => {
  const [motivo, setMotivo] = React.useState('');
  const [enviando, setEnviando] = React.useState(false);
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4 overflow-y-auto" onMouseDown={onFechar}>
      <div className="my-auto w-full max-w-md space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white">{titulo}</h3>
        {descricao && <p className="text-sm text-slate-400">{descricao}</p>}
        <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} maxLength={500} autoFocus
          placeholder="Motivo (fica registrado nas movimentações)"
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-nexus-yellow focus:outline-none" />
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onFechar} className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800">Voltar</button>
          <button type="button" disabled={motivo.trim().length < 3 || enviando}
            onClick={async () => { setEnviando(true); try { await onConfirmar(motivo.trim()); } finally { setEnviando(false); } }}
            className={`rounded-xl px-4 py-2 text-sm font-bold disabled:opacity-50 ${perigo ? 'bg-red-600 text-white hover:bg-red-500' : 'bg-nexus-yellow text-ink hover:bg-nexus-yellow-hover'}`}>
            {enviando ? 'Salvando…' : rotuloConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
};
