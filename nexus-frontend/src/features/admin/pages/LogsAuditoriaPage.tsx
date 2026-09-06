import React, { useState, useEffect, useCallback } from 'react';
import {
  ScrollText,
  Filter,
  Calendar,
  Activity,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Loader2,
  FileJson,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { LogAuditoria } from '@/types/admin';

export const LogsAuditoriaPage: React.FC = () => {
  const [logs, setLogs] = useState<LogAuditoria[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filtros
  const [entidadeFilter, setEntidadeFilter] = useState('');
  const [acaoFilter, setAcaoFilter] = useState('');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');

  // Linhas expandidas para exibição lado a lado de dados_antes vs dados_depois
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const loadLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await adminApi.listAuditLogs({
        entidade: entidadeFilter || undefined,
        acao: acaoFilter || undefined,
        data_inicio: dataInicio ? `${dataInicio}T00:00:00Z` : undefined,
        data_fim: dataFim ? `${dataFim}T23:59:59Z` : undefined,
        limit: 100,
      });

      setLogs(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Erro ao carregar logs de auditoria:', err);
    } finally {
      setIsLoading(false);
    }
  }, [entidadeFilter, acaoFilter, dataInicio, dataFim]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const toggleExpand = (id: string) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  const getActionBadge = (acao: string) => {
    const a = acao.toLowerCase();
    if (a.includes('login_sucesso')) {
      return { label: 'Login Sucesso', bg: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' };
    }
    if (a.includes('bloqueado')) {
      return { label: 'Bloqueio (Tentativas)', bg: 'bg-red-500/20 text-red-400 border-red-500/40' };
    }
    if (a.includes('falha')) {
      return { label: 'Login Falha', bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30' };
    }
    if (a.includes('lazy_rehash')) {
      return { label: 'Lazy Rehash (Argon2id)', bg: 'bg-purple-500/15 text-purple-300 border-purple-500/30' };
    }
    if (a.includes('criado') || a.includes('create')) {
      return { label: acao, bg: 'bg-blue-500/15 text-blue-400 border-blue-500/30' };
    }
    if (a.includes('atualizado') || a.includes('update')) {
      return { label: acao, bg: 'bg-nexus-yellow/15 text-nexus-yellow border-nexus-yellow/30' };
    }
    if (a.includes('excluido') || a.includes('delete')) {
      return { label: acao, bg: 'bg-red-500/15 text-red-400 border-red-500/30' };
    }
    return { label: acao, bg: 'bg-slate-800 text-slate-300 border-slate-700' };
  };

  const renderJsonPretty = (obj: any) => {
    if (!obj || Object.keys(obj).length === 0) {
      return <span className="text-slate-600 italic text-xs">Nenhum dado registrado</span>;
    }
    return (
      <pre className="text-[11px] font-mono text-slate-300 bg-slate-950 p-3 rounded-xl border border-slate-800/80 overflow-x-auto whitespace-pre-wrap">
        {JSON.stringify(obj, null, 2)}
      </pre>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-blue/20 border border-nexus-blue/40 text-nexus-yellow text-xs font-bold uppercase tracking-wider mb-2">
          <ScrollText className="w-3.5 h-3.5 text-nexus-yellow" />
          Governança & Rastreabilidade
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Logs de Auditoria do Sistema
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-xl leading-relaxed">
          Rastreamento imutável de acessos, autenticações, alterações de permissões e atualizações de configurações gerais.
        </p>
      </div>

      {/* Filters Card */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span>Entidade:</span>
            </div>
            <select
              value={entidadeFilter}
              onChange={(e) => setEntidadeFilter(e.target.value)}
              className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
            >
              <option value="">Todas as entidades</option>
              <option value="usuarios">Usuários</option>
              <option value="usuario_permissoes">Permissões de Usuários</option>
              <option value="configuracoes">Configurações</option>
            </select>

            <div className="flex items-center gap-1.5 text-xs text-slate-400 ml-2">
              <span>Ação:</span>
            </div>
            <select
              value={acaoFilter}
              onChange={(e) => setAcaoFilter(e.target.value)}
              className="bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-nexus-yellow"
            >
              <option value="">Todas as ações</option>
              <option value="login_sucesso">Login Sucesso</option>
              <option value="login_falha">Login Falha</option>
              <option value="login_bloqueado">Login Bloqueado (429)</option>
              <option value="senha_lazy_rehash">Lazy Rehash Argon2id</option>
              <option value="usuario_criado">Usuário Criado</option>
              <option value="usuario_atualizado">Usuário Atualizado</option>
              <option value="usuario_permissoes_atualizadas">Permissões Alteradas</option>
              <option value="configuracao_atualizada">Configuração Atualizada</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              <input
                type="date"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                className="bg-transparent text-xs text-white focus:outline-none"
                title="Data Início"
              />
              <span className="text-slate-600">até</span>
              <input
                type="date"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
                className="bg-transparent text-xs text-white focus:outline-none"
                title="Data Fim"
              />
            </div>

            <button
              onClick={loadLogs}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors cursor-pointer"
              title="Filtrar"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Data / Hora</th>
                <th className="py-3.5 px-4">Ação</th>
                <th className="py-3.5 px-4">Entidade</th>
                <th className="py-3.5 px-4">Usuário Executor</th>
                <th className="py-3.5 px-4">IP</th>
                <th className="py-3.5 px-4 text-center">Detalhes (Antes/Depois)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-nexus-yellow" />
                    Carregando registros de auditoria...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    Nenhum registro de auditoria encontrado com os filtros selecionados.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const badge = getActionBadge(log.acao);
                  const isExpanded = expandedLogId === log.id;
                  const hasDetails = log.dados_antes || log.dados_depois;

                  return (
                    <React.Fragment key={log.id}>
                      <tr className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-4 whitespace-nowrap text-slate-400 font-mono">
                          {log.criado_em
                            ? new Date(log.criado_em).toLocaleString('pt-BR', {
                                dateStyle: 'short',
                                timeStyle: 'medium',
                              })
                            : '—'}
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${badge.bg}`}
                          >
                            {badge.label}
                          </span>
                        </td>

                        <td className="py-3.5 px-4">
                          <span className="font-mono text-slate-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-[11px]">
                            {log.entidade || '—'}
                          </span>
                        </td>

                        <td className="py-3.5 px-4">
                          {log.usuario_nome || log.usuario_email ? (
                            <div>
                              <p className="font-semibold text-white">{log.usuario_nome || 'Usuário'}</p>
                              <p className="text-[11px] text-slate-500">{log.usuario_email}</p>
                            </div>
                          ) : (
                            <span className="text-slate-500 italic text-[11px]">Sistema / Anônimo</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4 font-mono text-slate-400">
                          {log.ip || '127.0.0.1'}
                        </td>

                        <td className="py-3.5 px-4 text-center">
                          {hasDetails ? (
                            <button
                              onClick={() => toggleExpand(log.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950 hover:bg-slate-800 text-nexus-yellow border border-slate-800 text-xs font-medium transition-colors cursor-pointer"
                            >
                              <FileJson className="w-3.5 h-3.5" />
                              <span>{isExpanded ? 'Recolher' : 'Ver Antes / Depois'}</span>
                              {isExpanded ? (
                                <ChevronUp className="w-3 h-3" />
                              ) : (
                                <ChevronDown className="w-3 h-3" />
                              )}
                            </button>
                          ) : (
                            <span className="text-slate-600 text-[11px]">—</span>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Side-by-Side Diff Container */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80 border-y border-nexus-yellow/20 animate-fadeIn">
                          <td colSpan={6} className="p-4 sm:p-6">
                            <div className="flex items-center gap-2 mb-3 text-xs font-bold uppercase tracking-wider text-nexus-yellow">
                              <Activity className="w-4 h-4" />
                              <span>Detalhes Comparativos da Ação • ID {log.entidade_id || log.id}</span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {/* Dados Antes */}
                              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs font-semibold text-amber-300">
                                  <span>Estado Anterior (dados_antes)</span>
                                </div>
                                {renderJsonPretty(log.dados_antes)}
                              </div>

                              {/* Dados Depois */}
                              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs font-semibold text-emerald-300">
                                  <span>Estado Novo (dados_depois)</span>
                                </div>
                                {renderJsonPretty(log.dados_depois)}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span>Total de eventos: <strong>{total}</strong></span>
          <span>Exibindo até 100 registros mais recentes</span>
        </div>
      </div>
    </div>
  );
};
