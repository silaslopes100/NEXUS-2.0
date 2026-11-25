import React, { useState } from 'react';
import { AlertCircle, Check, Edit2, Loader2, X } from 'lucide-react';
import { mensagemErro } from './fichaUtils';

interface SecaoEditavelProps {
  titulo: string;
  icone: React.ReactNode;
  /** Prepara o rascunho do formulário a partir dos dados atuais. */
  aoEditar?: () => void;
  /** Salva o rascunho; lança erro para manter o formulário aberto com a mensagem. */
  aoSalvar?: () => Promise<void>;
  leitura: React.ReactNode;
  edicao?: React.ReactNode;
  acoesExtras?: React.ReactNode;
  aviso?: React.ReactNode;
}

/** Bloco da ficha que alterna entre leitura e formulário, com Salvar/Cancelar próprios. */
export const SecaoEditavel: React.FC<SecaoEditavelProps> = ({
  titulo, icone, aoEditar, aoSalvar, leitura, edicao, acoesExtras, aviso,
}) => {
  const [editando, setEditando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const editavel = Boolean(aoSalvar && edicao);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aoSalvar) return;
    setSalvando(true);
    setErro(null);
    try {
      await aoSalvar();
      setEditando(false);
    } catch (err) {
      setErro(mensagemErro(err, 'Não foi possível salvar esta seção.'));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <section className="glass rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <span className="text-nexus-yellow">{icone}</span>
          {titulo}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {!editando && acoesExtras}
          {editavel && !editando && (
            <button
              type="button"
              onClick={() => {
                aoEditar?.();
                setErro(null);
                setEditando(true);
              }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-lg flex items-center gap-1.5"
            >
              <Edit2 className="w-3.5 h-3.5" /> Editar
            </button>
          )}
        </div>
      </div>
      {aviso}
      {editando ? (
        <form onSubmit={salvar} className="space-y-4" noValidate>
          {edicao}
          {erro && (
            <p role="alert" className="flex items-start gap-2 text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
              <AlertCircle className="w-4 h-4 shrink-0" /> {erro}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              disabled={salvando}
              onClick={() => setEditando(false)}
              className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg font-medium flex items-center gap-1.5 disabled:opacity-50"
            >
              <X className="w-3.5 h-3.5" /> Cancelar
            </button>
            <button
              type="submit"
              disabled={salvando}
              className="px-4 py-1.5 bg-nexus-yellow hover:bg-nexus-yellow-hover text-ink text-xs font-bold rounded-lg flex items-center gap-1.5 disabled:opacity-60"
            >
              {salvando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
              Salvar
            </button>
          </div>
        </form>
      ) : (
        leitura
      )}
    </section>
  );
};

export const DadoItem: React.FC<{ icon?: React.ReactNode; label: string; value: React.ReactNode; className?: string }> = ({
  icon, label, value, className = '',
}) => (
  <div className={`p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 min-w-0 ${className}`}>
    <p className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1 mb-1">
      {icon}
      {label}
    </p>
    <p className="text-xs font-semibold text-white break-words">{value}</p>
  </div>
);

export const Campo: React.FC<{ label: string; children: React.ReactNode; className?: string; obrigatorio?: boolean }> = ({
  label, children, className = '', obrigatorio,
}) => (
  <label className={`block space-y-1 ${className}`}>
    <span className="text-xs font-semibold text-slate-300">
      {label}
      {obrigatorio && ' *'}
    </span>
    {children}
  </label>
);

export const MetricaCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  accent?: string;
  selo?: React.ReactNode;
}> = ({ icon, label, value, accent = 'text-nexus-yellow', selo }) => (
  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center gap-3 min-w-0">
    <div className={`glass p-2.5 rounded-lg bg-slate-900 border border-slate-800 ${accent}`}>{icon}</div>
    <div className="min-w-0">
      <p className="text-lg font-extrabold text-white leading-none flex items-center gap-2 flex-wrap">
        {value}
        {selo}
      </p>
      <p className="text-[11px] text-slate-400 mt-1">{label}</p>
    </div>
  </div>
);
