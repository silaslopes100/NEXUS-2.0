import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  Code2,
  Sliders,
} from 'lucide-react';
import { adminApi } from '@/features/admin/api';
import { Configuracao } from '@/types/admin';

export const ConfiguracoesPage: React.FC = () => {
  const [configuracoes, setConfiguracoes] = useState<Configuracao[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Modal / Edição
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<string>('');
  const [formKey, setFormKey] = useState<string>('');
  const [formValueStr, setFormValueStr] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadConfiguracoes = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.listConfiguracoes();
      setConfiguracoes(data);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao carregar configurações gerais do sistema.',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfiguracoes();
  }, [loadConfiguracoes]);

  const handleOpenCreate = () => {
    setEditingKey('');
    setFormKey('');
    setFormValueStr('{\n  "descricao": "Novo parâmetro"\n}');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (cfg: Configuracao) => {
    setEditingKey(cfg.chave);
    setFormKey(cfg.chave);
    setFormValueStr(
      typeof cfg.valor === 'object'
        ? JSON.stringify(cfg.valor, null, 2)
        : String(cfg.valor)
    );
    setIsModalOpen(true);
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setFeedback(null);

    // Converte formValueStr para JSON se for um objeto ou mantém como string/número/booleano
    let parsedValue: any;
    try {
      parsedValue = JSON.parse(formValueStr);
    } catch {
      // Se não for JSON válido, grava como texto puro
      parsedValue = formValueStr;
    }

    try {
      const keyToSave = editingKey ? editingKey : formKey.trim();
      await adminApi.setConfiguracao(keyToSave, parsedValue);
      setFeedback({
        type: 'success',
        message: `Parâmetro "${keyToSave}" salvo com sucesso e registrado em auditoria!`,
      });
      setIsModalOpen(false);
      loadConfiguracoes();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || 'Erro ao gravar a configuração.',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const filteredConfigs = configuracoes.filter((c) =>
    c.chave.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-nexus-yellow/15 border border-nexus-yellow/30 text-nexus-yellow text-xs font-bold uppercase tracking-wider mb-2">
            <Sliders className="w-3.5 h-3.5" />
            Parâmetros do Sistema
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Configurações Gerais (Chave / Valor JSONB)
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl leading-relaxed">
            Ajuste parâmetros globais do NEXUS 2.0. Todas as alterações gravam automaticamente o estado anterior e posterior em auditoria.
          </p>
        </div>

        <button
          onClick={handleOpenCreate}
          className="py-3 px-5 bg-gradient-to-r from-nexus-yellow via-amber-500 to-amber-600 hover:from-nexus-yellow-hover hover:to-amber-500 text-slate-950 font-bold text-sm rounded-xl shadow-lg shadow-nexus-yellow/20 flex items-center justify-center gap-2 transition-all transform active:scale-95 cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Novo Parâmetro</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-sm animate-fadeIn ${
            feedback.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200'
              : 'bg-red-500/15 border-red-500/30 text-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="p-1 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Actions */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3 shadow-md">
        <div className="w-full sm:w-96 relative">
          <input
            type="text"
            placeholder="Filtrar por chave de configuração..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-nexus-yellow"
          />
        </div>

        <button
          onClick={loadConfiguracoes}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors cursor-pointer"
          title="Recarregar"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Configs Grid */}
      {isLoading ? (
        <div className="py-16 text-center text-slate-500">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-nexus-yellow" />
          Carregando parâmetros...
        </div>
      ) : filteredConfigs.length === 0 ? (
        <div className="p-12 text-center text-slate-500 rounded-2xl bg-slate-900/40 border border-slate-800">
          Nenhuma configuração cadastrada com este filtro.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredConfigs.map((cfg) => (
            <div
              key={cfg.chave}
              className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md flex flex-col justify-between hover:border-slate-700 transition-all"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-xs font-bold text-nexus-yellow bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 truncate">
                    {cfg.chave}
                  </span>
                  <button
                    onClick={() => handleOpenEdit(cfg)}
                    className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 text-xs flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <span>Editar</span>
                  </button>
                </div>

                <div className="mt-3">
                  <pre className="text-[11px] font-mono text-slate-300 bg-slate-950/90 p-3 rounded-xl border border-slate-800 max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {typeof cfg.valor === 'object'
                      ? JSON.stringify(cfg.valor, null, 2)
                      : String(cfg.valor)}
                  </pre>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
                <span>Tipo: {typeof cfg.valor === 'object' ? 'JSONB Object' : typeof cfg.valor}</span>
                {cfg.atualizado_em && (
                  <span>
                    Atualizado em: {new Date(cfg.atualizado_em).toLocaleDateString('pt-BR')}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal de Criação / Edição de Configuração */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl p-6 sm:p-8 animate-fadeIn">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-white font-bold text-base">
                <Code2 className="w-5 h-5 text-nexus-yellow" />
                <span>{editingKey ? `Editar: ${editingKey}` : 'Novo Parâmetro de Sistema'}</span>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveConfig} className="space-y-4 mt-4">
              {!editingKey && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Chave do Parâmetro *</label>
                  <input
                    type="text"
                    required
                    value={formKey}
                    onChange={(e) => setFormKey(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-nexus-yellow focus:outline-none focus:border-nexus-yellow"
                    placeholder="Ex: portal.manutencao ou vendas.desconto_maximo"
                  />
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">
                  Valor (Texto puro ou JSON/JSONB estruturado) *
                </label>
                <textarea
                  required
                  rows={8}
                  value={formValueStr}
                  onChange={(e) => setFormValueStr(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-nexus-yellow"
                  placeholder='{"parametro": "valor"}'
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2.5 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-xs rounded-xl shadow-lg transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Salvar Parâmetro</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
