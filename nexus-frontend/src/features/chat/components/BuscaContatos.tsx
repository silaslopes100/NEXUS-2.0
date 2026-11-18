import React, { useEffect, useState } from 'react';
import { Loader2, Search } from 'lucide-react';
import { Contato, chatApi } from '../api';
import { rotuloPerfil } from '../utils';
import { Avatar } from './Avatar';

interface Props {
  onEscolher: (c: Contato) => void;
  onCancelar?: () => void;
  excluir?: Set<string>;
  ocultarAlunos?: boolean;
  autoFocus?: boolean;
}

/** Busca de usuários elegíveis para conversa (o backend já remove alunos quando quem busca é aluno). */
export const BuscaContatos: React.FC<Props> = ({ onEscolher, onCancelar, excluir, ocultarAlunos, autoFocus = true }) => {
  const [busca, setBusca] = useState('');
  const [itens, setItens] = useState<Contato[] | null>(null);

  useEffect(() => {
    let vivo = true;
    setItens(null);
    const id = window.setTimeout(() => {
      chatApi.contatos(busca.trim()).then((r) => vivo && setItens(r)).catch(() => vivo && setItens([]));
    }, 300);
    return () => { vivo = false; window.clearTimeout(id); };
  }, [busca]);

  const visiveis = (itens ?? []).filter(
    (c) => !excluir?.has(c.id) && !(ocultarAlunos && c.perfil?.toLowerCase() === 'aluno'),
  );

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2">
        <Search size={14} className="text-slate-500" />
        <input autoFocus={autoFocus} value={busca} onChange={(e) => setBusca(e.target.value)}
          placeholder="Nome ou e-mail"
          className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none" />
        {onCancelar && (
          <button type="button" onClick={onCancelar} className="text-xs text-slate-400 hover:text-white">Cancelar</button>
        )}
      </label>
      <div className="max-h-72 overflow-y-auto rounded-xl border border-slate-800">
        {itens === null ? (
          <div className="flex justify-center p-4 text-slate-400"><Loader2 size={16} className="animate-spin" /></div>
        ) : visiveis.length === 0 ? (
          <p className="p-4 text-center text-xs text-slate-500">Ninguém encontrado.</p>
        ) : (
          visiveis.map((c) => (
            <button key={c.id} type="button" onClick={() => onEscolher(c)}
              className="flex w-full items-center gap-3 border-b border-slate-800/60 px-3 py-2 text-left last:border-0 hover:bg-slate-800/60">
              <Avatar nome={c.nome} fotoUrl={c.foto_url} tamanho="sm" />
              <div className="min-w-0">
                <p className="truncate text-sm text-white">{c.nome}</p>
                <p className="truncate text-[11px] text-slate-400">
                  {[rotuloPerfil(c.perfil), c.escola_nome || c.polo_nome].filter(Boolean).join(' · ')}
                </p>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
};
