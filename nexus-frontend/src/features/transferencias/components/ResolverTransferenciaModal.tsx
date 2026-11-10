import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Loader2, X } from 'lucide-react';
import {
  Transferencia,
  tipoLabel,
  transferenciasApi,
  transferenciasErro,
} from '@/features/transferencias/api';

interface Props {
  transferencia: Transferencia;
  onClose: () => void;
  onSuccess: (mensagem: string) => void;
}

const Linha: React.FC<{ rotulo: string; valor: string }> = ({ rotulo, valor }) => (
  <div>
    <dt className="text-xs uppercase text-slate-500">{rotulo}</dt>
    <dd className="text-sm text-slate-200">{valor}</dd>
  </div>
);

const unidade = (polo?: string | null, escola?: string | null, modalidade?: string | null) =>
  modalidade === 'ead' ? 'EAD' : [polo, escola].filter(Boolean).join(' · ') || 'Não informado';

export const ResolverTransferenciaModal: React.FC<Props> = ({
  transferencia: t,
  onClose,
  onSuccess,
}) => {
  const [motivo, setMotivo] = useState('');
  const [confirmaChurn, setConfirmaChurn] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');

  const decidir = async (aprovado: boolean) => {
    setEnviando(true);
    setErro('');
    try {
      const resolvida = await transferenciasApi.resolver(t.id, {
        aprovado,
        motivo: motivo.trim() || undefined,
        confirmar_churn: aprovado && t.alerta_churn && confirmaChurn,
      });
      onSuccess(
        resolvida.status === 'churn'
          ? 'Aluno enviado para o Churn.'
          : aprovado
            ? 'Transferência aprovada.'
            : 'Solicitação rejeitada.'
      );
    } catch (err) {
      setErro(transferenciasErro(err, 'Não foi possível registrar a decisão.'));
      setEnviando(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !enviando) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="resolver-transferencia-titulo"
        className="my-auto w-full max-w-xl space-y-5 rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl sm:p-7"
      >
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 id="resolver-transferencia-titulo" className="text-xl font-bold text-white">
              Analisar solicitação
            </h2>
            <p className="mt-1 text-sm text-slate-400">{tipoLabel[t.tipo]}</p>
          </div>
          <button
            type="button"
            aria-label="Fechar análise"
            disabled={enviando}
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </header>

        {erro && (
          <div
            role="alert"
            className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200"
          >
            {erro}
          </div>
        )}

        <dl className="grid gap-3 sm:grid-cols-2">
          <Linha
            rotulo="Aluno"
            valor={[t.aluno_nome, t.numero_matricula].filter(Boolean).join(' · ') || 'Não informado'}
          />
          <Linha rotulo="Solicitado por" valor={t.solicitado_por_nome || 'Não informado'} />
          <Linha
            rotulo="Origem"
            valor={unidade(t.polo_origem_nome, t.escola_origem_nome, t.modalidade_origem)}
          />
          <Linha
            rotulo="Destino"
            valor={unidade(t.polo_destino_nome, t.escola_destino_nome, t.modalidade_destino)}
          />
          {t.observacao && (
            <div className="sm:col-span-2">
              <Linha rotulo="Observação" valor={t.observacao} />
            </div>
          )}
        </dl>

        {t.alerta_churn && (
          <div className="space-y-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
            <p className="flex items-start gap-2">
              <AlertTriangle size={17} className="mt-0.5 shrink-0" />
              Aluno sem movimentação há mais de 1 ano. Ao aprovar, ele não será transferido: ficará
              com status desistente, desvinculado do Polo e irá para a lista de Churn.
            </p>
            <label className="flex items-center gap-2 font-medium">
              <input
                type="checkbox"
                checked={confirmaChurn}
                onChange={(event) => setConfirmaChurn(event.target.checked)}
                className="h-4 w-4 rounded border-slate-600 bg-slate-900"
              />
              Confirmo o envio deste aluno para o Churn
            </label>
          </div>
        )}

        <label className="block space-y-1.5 text-sm text-slate-300">
          <span>Motivo da rejeição</span>
          <textarea
            rows={3}
            maxLength={1000}
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500"
          />
        </label>

        <footer className="flex flex-col-reverse justify-end gap-2 border-t border-slate-800 pt-4 sm:flex-row">
          <button
            type="button"
            disabled={enviando}
            onClick={() => void decidir(false)}
            className="rounded-xl border border-red-500/40 px-4 py-2.5 text-sm font-semibold text-red-200 hover:bg-red-500/10 disabled:opacity-50"
          >
            Rejeitar
          </button>
          {t.tipo === 'reingresso' ? (
            <Link
              to={`/admin/alunos?observacao=churn&q=${encodeURIComponent(t.numero_matricula || t.aluno_nome || '')}`}
              className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"
            >
              Gerar nova matrícula em Alunos
            </Link>
          ) : (
            <button
              type="button"
              disabled={enviando || (t.alerta_churn && !confirmaChurn)}
              onClick={() => void decidir(true)}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {enviando && <Loader2 size={16} className="animate-spin" />}
              {t.alerta_churn ? 'Enviar para o Churn' : 'Aprovar transferência'}
            </button>
          )}
        </footer>
      </section>
    </div>
  );
};
