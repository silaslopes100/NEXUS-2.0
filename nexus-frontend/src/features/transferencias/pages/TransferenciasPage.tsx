import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeftRight,
  CheckCircle2,
  Clock,
  Loader2,
  Plus,
  Search,
  X,
} from 'lucide-react';
import {
  StatusTransferencia,
  TipoTransferencia,
  Transferencia,
  tipoLabel,
  transferenciasApi,
  transferenciasErro,
} from '@/features/transferencias/api';
import { ResolverTransferenciaModal } from '@/features/transferencias/components/ResolverTransferenciaModal';
import { SolicitarTransferenciaModal } from '@/features/transferencias/components/SolicitarTransferenciaModal';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { useTransferenciasStore } from '@/stores/transferenciasStore';

const PAGE_SIZE = 20;

const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500';

const statusInfo: Record<StatusTransferencia, { label: string; className: string }> = {
  pendente: { label: 'Pendente', className: 'border-amber-500/30 bg-amber-500/10 text-amber-200' },
  aprovada: { label: 'Aprovada', className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' },
  rejeitada: { label: 'Rejeitada', className: 'border-red-500/30 bg-red-500/10 text-red-200' },
  churn: { label: 'Churn', className: 'border-purple-500/30 bg-purple-500/10 text-purple-200' },
};

const unidade = (polo?: string | null, escola?: string | null, modalidade?: string | null) =>
  modalidade === 'ead' ? 'EAD' : [polo, escola].filter(Boolean).join(' · ') || '—';

const dataCurta = (valor?: string | null) =>
  valor ? new Date(valor).toLocaleDateString('pt-BR') : '—';

interface Props {
  modo?: 'aluno';
}

export const TransferenciasPage: React.FC<Props> = ({ modo }) => {
  const modoAluno = modo === 'aluno';
  const { user, perfil } = useAuthStore();
  const role = normalizeUserRole(perfil?.nome ?? user?.perfil?.nome);
  const isAdmin = role === 'admin' && !modoAluno;
  const podeSolicitar = modoAluno || role === 'polo' || role === 'escola';
  const { total: pendentes, carregar: atualizarSino } = useTransferenciasStore();

  const [itens, setItens] = useState<Transferencia[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState<StatusTransferencia | ''>('');
  const [tipo, setTipo] = useState<TipoTransferencia | ''>('');
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [solicitando, setSolicitando] = useState(false);
  const [analisando, setAnalisando] = useState<Transferencia | null>(null);

  useEffect(() => {
    const termo = busca.trim();
    if (termo === buscaAplicada) return;
    const timeout = window.setTimeout(() => {
      setOffset(0);
      setBuscaAplicada(termo);
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [busca, buscaAplicada]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');
    try {
      const pagina = await transferenciasApi.listar({
        status: status || undefined,
        tipo: tipo || undefined,
        q: buscaAplicada || undefined,
        escopo: modoAluno ? 'aluno' : undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setItens(pagina.items);
      setTotal(pagina.total);
    } catch (err) {
      setErro(transferenciasErro(err, 'Não foi possível carregar as transferências.'));
    } finally {
      setCarregando(false);
    }
  }, [buscaAplicada, modoAluno, offset, status, tipo]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const aposDecisao = (mensagem: string) => {
    setAnalisando(null);
    setSucesso(mensagem);
    void carregar();
    void atualizarSino();
  };

  const aposSolicitar = () => {
    setSolicitando(false);
    setSucesso('Solicitação enviada para análise da Secretaria Geral.');
    void carregar();
  };

  const colunas = isAdmin ? 6 : 5;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-blue-950/30 p-6 shadow-xl sm:flex-row sm:items-center sm:p-8">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300">
            <ArrowLeftRight size={16} />
            Movimentação de alunos
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            {modoAluno ? 'Minhas Transferências' : 'Transferências'}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Troca de Polo e Migração de Modalidade, sem nova matrícula.
          </p>
        </div>
        {podeSolicitar && (
          <button
            type="button"
            onClick={() => {
              setSucesso('');
              setSolicitando(true);
            }}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"
          >
            <Plus size={17} />
            Nova solicitação
          </button>
        )}
      </header>

      {isAdmin && pendentes > 0 && (
        <button
          type="button"
          onClick={() => {
            setOffset(0);
            setStatus('pendente');
          }}
          className="flex w-full items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-left text-sm text-amber-100 hover:bg-amber-500/15"
        >
          <Clock size={18} className="shrink-0" />
          <span>
            <strong>{pendentes}</strong> solicitação(ões) aguardando sua análise. Clique para
            filtrar.
          </span>
        </button>
      )}

      {sucesso && (
        <div
          role="status"
          className="flex items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200"
        >
          <span className="flex items-center gap-2">
            <CheckCircle2 size={17} />
            {sucesso}
          </span>
          <button type="button" aria-label="Fechar mensagem" onClick={() => setSucesso('')}>
            <X size={16} />
          </button>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="grid gap-3 border-b border-slate-800 p-4 md:grid-cols-3">
          <label className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              aria-label="Buscar por aluno ou matrícula"
              className={`${inputClass} pl-9`}
              placeholder="Buscar por aluno ou matrícula"
              value={busca}
              onChange={(event) => setBusca(event.target.value)}
            />
          </label>
          <select
            aria-label="Filtrar por status"
            className={inputClass}
            value={status}
            onChange={(event) => {
              setOffset(0);
              setStatus(event.target.value as StatusTransferencia | '');
            }}
          >
            <option value="">Todos os status</option>
            {(Object.keys(statusInfo) as StatusTransferencia[]).map((valor) => (
              <option key={valor} value={valor}>
                {statusInfo[valor].label}
              </option>
            ))}
          </select>
          <select
            aria-label="Filtrar por tipo"
            className={inputClass}
            value={tipo}
            onChange={(event) => {
              setOffset(0);
              setTipo(event.target.value as TipoTransferencia | '');
            }}
          >
            <option value="">Todos os tipos</option>
            {(Object.keys(tipoLabel) as TipoTransferencia[]).map((valor) => (
              <option key={valor} value={valor}>
                {tipoLabel[valor]}
              </option>
            ))}
          </select>
        </div>

        {erro && (
          <div
            role="alert"
            className="m-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"
          >
            <AlertCircle size={17} className="shrink-0" />
            {erro}
          </div>
        )}

        {carregando ? (
          <div className="flex justify-center py-16 text-blue-400">
            <Loader2 className="animate-spin" />
          </div>
        ) : !erro ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
                <tr>
                  <th className="p-4">Aluno</th>
                  <th className="p-4">Solicitação</th>
                  <th className="p-4">Origem → Destino</th>
                  <th className="p-4">Solicitado por</th>
                  <th className="p-4">Status</th>
                  {isAdmin && <th className="p-4 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {itens.map((item) => (
                  <tr key={item.id} className="text-slate-300 hover:bg-slate-800/40">
                    <td className="p-4">
                      <p className="font-semibold text-white">{item.aluno_nome || 'Não informado'}</p>
                      <p className="text-xs text-slate-500">{item.numero_matricula || 'Sem matrícula'}</p>
                    </td>
                    <td className="p-4">{tipoLabel[item.tipo] ?? item.tipo}</td>
                    <td className="p-4">
                      <p>{unidade(item.polo_origem_nome, item.escola_origem_nome, item.modalidade_origem)}</p>
                      <p className="text-xs text-slate-500">
                        → {unidade(item.polo_destino_nome, item.escola_destino_nome, item.modalidade_destino)}
                      </p>
                    </td>
                    <td className="p-4">
                      <p>{item.solicitado_por_nome || '—'}</p>
                      <p className="text-xs text-slate-500">{dataCurta(item.criado_em)}</p>
                    </td>
                    <td className="p-4">
                      <span
                        className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusInfo[item.status].className}`}
                      >
                        {statusInfo[item.status].label}
                      </span>
                      {item.alerta_churn && (
                        <p className="mt-1 flex items-center gap-1 text-xs text-amber-300">
                          <AlertTriangle size={12} />
                          Mais de 1 ano parado
                        </p>
                      )}
                      {item.motivo_rejeicao && (
                        <p className="mt-1 max-w-xs text-xs text-slate-400">{item.motivo_rejeicao}</p>
                      )}
                    </td>
                    {isAdmin && (
                      <td className="p-4 text-right">
                        {item.status === 'pendente' && (
                          <button
                            type="button"
                            onClick={() => {
                              setSucesso('');
                              setAnalisando(item);
                            }}
                            className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-semibold text-blue-200 hover:bg-blue-500/20"
                          >
                            Analisar
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {itens.length === 0 && (
                  <tr>
                    <td colSpan={colunas} className="p-12 text-center text-slate-500">
                      Nenhuma solicitação encontrada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : null}

        {!carregando && !erro && total > 0 && (
          <footer className="flex flex-col gap-3 border-t border-slate-800 px-4 py-3 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Exibindo {offset + 1}–{Math.min(offset + itens.length, total)} de {total}
            </span>
            <div className="flex items-center justify-between gap-3 sm:justify-end">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset((atual) => Math.max(0, atual - PAGE_SIZE))}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset((atual) => atual + PAGE_SIZE)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Próxima
              </button>
            </div>
          </footer>
        )}
      </section>

      {solicitando && (
        <SolicitarTransferenciaModal
          modoAluno={modoAluno}
          onClose={() => setSolicitando(false)}
          onSuccess={aposSolicitar}
        />
      )}
      {analisando && (
        <ResolverTransferenciaModal
          transferencia={analisando}
          onClose={() => setAnalisando(null)}
          onSuccess={aposDecisao}
        />
      )}
    </div>
  );
};
