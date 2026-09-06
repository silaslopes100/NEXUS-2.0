import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  X,
  Percent,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { EtlSyncRun, EtlErro } from '@/types/admin';

export const ExecucoesBatchPage: React.FC = () => {
  const [execucoes, setExecucoes] = useState<EtlSyncRun[]>([]);
  const [taxaSucesso, setTaxaSucesso] = useState<number | null>(null);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  // Modal de Detalhes dos Erros
  const [selectedRun, setSelectedRun] = useState<EtlSyncRun | null>(null);
  const [erros, setErros] = useState<EtlErro[]>([]);
  const [isLoadingErros, setIsLoadingErros] = useState(false);
  const [isErrorsModalOpen, setIsErrorsModalOpen] = useState(false);

  const loadExecucoes = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await adminApi.listEtlExecucoes({
        status: statusFilter || undefined,
        limit: 50,
      });
      setExecucoes(res.items || []);
      setTotal(res.total || 0);
      setTaxaSucesso(res.taxa_sucesso_geral !== undefined ? res.taxa_sucesso_geral : null);
    } catch (err) {
      console.error('Erro ao carregar execuções do batch ETL:', err);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadExecucoes();
  }, [loadExecucoes]);

  const handleOpenErros = async (run: EtlSyncRun) => {
    setSelectedRun(run);
    setIsErrorsModalOpen(true);
    setIsLoadingErros(true);
    try {
      const data = await adminApi.getEtlExecucaoErros(run.id, { limit: 100 });
      setErros(data);
    } catch (err) {
      console.error('Erro ao carregar erros da execução:', err);
      setErros([]);
    } finally {
      setIsLoadingErros(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('sucesso')) {
      return {
        label: status,
        bg: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
        icon: CheckCircle2,
      };
    }
    if (s.includes('rodando') || s.includes('running')) {
      return {
        label: 'Em Execução',
        bg: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
        icon: RefreshCw,
      };
    }
    if (s.includes('erro') || s.includes('falh')) {
      return {
        label: 'Falha',
        bg: 'bg-red-500/15 text-red-400 border-red-500/30',
        icon: XCircle,
      };
    }
    return {
      label: status,
      bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
      icon: AlertTriangle,
    };
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-blue/20 border border-nexus-blue/40 text-nexus-yellow text-xs font-bold uppercase tracking-wider mb-2">
          <Database className="w-3.5 h-3.5 text-nexus-yellow" />
          Sincronização Legado MySQL → NeonDB
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Saúde do Batch de Sincronização Diária
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-xl leading-relaxed">
          Acompanhamento das cargas iniciais e incrementais diárias executadas pelo motor ETL, com registro de totais e auditoria de divergências.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Total de Execuções</span>
            <Database className="w-4 h-4 text-nexus-yellow" />
          </div>
          <div className="text-2xl font-black text-white mt-2">{total}</div>
          <p className="text-xs text-slate-400 mt-1">Cargas registradas no banco</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Taxa de Sucesso Geral</span>
            <Percent className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white mt-2">
            {taxaSucesso !== null ? `${taxaSucesso}%` : '100%'}
          </div>
          <p className="text-xs text-emerald-400 mt-1">Registros inseridos com integridade</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Rotina Diária Sugerida</span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-black text-white mt-2">03:00 BRT</div>
          <p className="text-xs text-slate-400 mt-1">Modo incremental automático</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Filtrar por status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
          >
            <option value="">Todos os status</option>
            <option value="sucesso">Sucesso</option>
            <option value="rodando">Em Execução</option>
            <option value="falhou">Falha</option>
          </select>
        </div>

        <button
          onClick={loadExecucoes}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors cursor-pointer"
          title="Recarregar"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Executions Table */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">ID & Modo</th>
                <th className="py-3.5 px-4">Início / Término</th>
                <th className="py-3.5 px-4">Duração</th>
                <th className="py-3.5 px-4 text-center">Lidos / Inseridos</th>
                <th className="py-3.5 px-4 text-center">Atualizados</th>
                <th className="py-3.5 px-4 text-center">Erros</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-nexus-yellow" />
                    Carregando histórico do batch de sincronização...
                  </td>
                </tr>
              ) : execucoes.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    Nenhuma execução do batch ETL encontrada.
                  </td>
                </tr>
              ) : (
                execucoes.map((run) => {
                  const statusInfo = getStatusBadge(run.status);
                  const StatusIcon = statusInfo.icon;
                  const hasErrors = run.total_erro > 0 || (run.total_erros_detalhados && run.total_erros_detalhados > 0);

                  return (
                    <tr key={run.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-white">#{run.id}</span>
                          <span className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 font-mono text-[10px] uppercase text-nexus-yellow">
                            {run.modo}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-400">
                        <p className="font-medium text-slate-200">
                          {new Date(run.iniciado_em).toLocaleDateString('pt-BR')} às{' '}
                          {new Date(run.iniciado_em).toLocaleTimeString('pt-BR')}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {run.finalizado_em
                            ? `Fim: ${new Date(run.finalizado_em).toLocaleTimeString('pt-BR')}`
                            : 'Em andamento...'}
                        </p>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {run.duracao_segundos !== undefined && run.duracao_segundos !== null
                          ? `${Math.round(run.duracao_segundos)}s`
                          : '—'}
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono">
                        <span className="text-slate-400">{run.total_lido.toLocaleString()}</span>
                        <span className="text-slate-600 mx-1">/</span>
                        <span className="text-emerald-400 font-semibold">{run.total_inserido.toLocaleString()}</span>
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono text-blue-400 font-semibold">
                        {run.total_atualizado.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4 text-center font-mono">
                        <span className={run.total_erro > 0 ? 'text-red-400 font-bold' : 'text-slate-500'}>
                          {run.total_erro}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${statusInfo.bg}`}>
                          <StatusIcon className="w-3 h-3" />
                          <span>{statusInfo.label}</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        {hasErrors ? (
                          <button
                            onClick={() => handleOpenErros(run)}
                            className="px-2.5 py-1 bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 rounded-lg text-xs font-semibold transition-colors cursor-pointer inline-flex items-center gap-1"
                          >
                            <AlertCircle className="w-3 h-3" />
                            <span>Ver Erros</span>
                          </button>
                        ) : (
                          <span className="text-slate-600 text-[11px]">Sem erros</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Detalhes dos Erros da Execução */}
      {isErrorsModalOpen && selectedRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden shadow-2xl flex flex-col p-6 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span>Erros Registrados na Execução #{selectedRun.id} ({selectedRun.modo})</span>
              </div>
              <button
                onClick={() => setIsErrorsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-3 custom-scrollbar">
              {isLoadingErros ? (
                <div className="py-12 text-center text-slate-500">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-red-400" />
                  Carregando registros detalhados de erros em etl_erros...
                </div>
              ) : erros.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  Nenhum registro detalhado encontrado para esta execução.
                </div>
              ) : (
                erros.map((err) => (
                  <div
                    key={err.id}
                    className="p-4 rounded-xl bg-slate-950 border border-red-500/20 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-nexus-yellow">
                          Tabela: {err.tabela_origem || 'origem'}
                        </span>
                        <span className="text-slate-500">•</span>
                        <span className="text-slate-400 font-mono">ID Origem: {err.id_origem || '—'}</span>
                      </div>
                      <span className="text-[10px] text-slate-500">
                        {err.criado_em ? new Date(err.criado_em).toLocaleTimeString('pt-BR') : ''}
                      </span>
                    </div>

                    <p className="text-red-300 font-medium">{err.erro}</p>

                    {err.linha_raw && (
                      <pre className="text-[10px] font-mono text-slate-400 bg-slate-900 p-2.5 rounded-lg border border-slate-800 overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(err.linha_raw, null, 2)}
                      </pre>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setIsErrorsModalOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl transition-colors cursor-pointer"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
