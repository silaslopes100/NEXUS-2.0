import React, { useMemo, useState } from 'react';
import { Loader2, Lock, Plus, Search } from 'lucide-react';
import { Conversa } from '../api';
import { horaCurta, rotuloPerfil } from '../utils';
import { Avatar } from './Avatar';

type Aba = 'todas' | 'individual' | 'grupo';

interface Props {
  conversas: Conversa[] | null;
  selecionadaId: string | null;
  meuId: string;
  onSelecionar: (id: string) => void;
  onNova: () => void;
}

export const ConversaLista: React.FC<Props> = ({ conversas, selecionadaId, meuId, onSelecionar, onNova }) => {
  const [aba, setAba] = useState<Aba>('todas');
  const [filtro, setFiltro] = useState('');

  const visiveis = useMemo(() => {
    const termo = filtro.trim().toLowerCase();
    return (conversas ?? []).filter(
      (c) => (aba === 'todas' || c.tipo === aba) && (!termo || c.titulo.toLowerCase().includes(termo)),
    );
  }, [conversas, aba, filtro]);

  const naoLidasAba = (a: Aba) =>
    (conversas ?? []).filter((c) => (a === 'todas' || c.tipo === a) && c.nao_lidas > 0).length;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 p-3">
        <h2 className="text-base font-semibold text-white">Conversas</h2>
        <button type="button" onClick={onNova}
          className="inline-flex items-center gap-1.5 rounded-xl bg-nexus-yellow px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-nexus-yellow/90">
          <Plus size={14} /> Nova
        </button>
      </div>
      <div className="space-y-2 border-b border-slate-800 p-3">
        <label className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
          <Search size={14} className="text-slate-500" />
          <input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="Buscar conversa"
            className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none" />
        </label>
        <div className="grid grid-cols-3 gap-1 rounded-xl bg-slate-950/60 p-1 text-xs">
          {([['todas', 'Todas'], ['individual', 'Individuais'], ['grupo', 'Grupos']] as [Aba, string][]).map(([v, r]) => (
            <button key={v} type="button" onClick={() => setAba(v)}
              className={`relative rounded-lg py-1.5 font-medium ${aba === v ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`}>
              {r}
              {naoLidasAba(v) > 0 && <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-nexus-yellow" />}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {conversas === null ? (
          <div className="flex justify-center p-8 text-slate-400"><Loader2 className="animate-spin" size={18} /></div>
        ) : visiveis.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-500">
            {conversas.length === 0 ? 'Nenhuma conversa ainda. Clique em “Nova” para começar.' : 'Nada encontrado.'}
          </p>
        ) : (
          visiveis.map((c) => {
            const ativa = c.id === selecionadaId;
            const prefixo = c.ultima_remetente_id === meuId && c.ultima_mensagem ? 'Você: ' : '';
            return (
              <button key={c.id} type="button" onClick={() => onSelecionar(c.id)}
                className={`flex w-full items-center gap-3 border-b border-slate-800/60 px-3 py-3 text-left transition-colors ${ativa ? 'bg-slate-800/80' : 'hover:bg-slate-800/40'}`}>
                <Avatar nome={c.titulo} fotoUrl={c.outro?.foto_url} grupo={c.tipo === 'grupo'} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className={`truncate text-sm ${c.nao_lidas ? 'font-semibold text-white' : 'font-medium text-slate-200'}`}>
                      {c.titulo}
                    </p>
                    <span className={`shrink-0 text-[11px] ${c.nao_lidas ? 'text-nexus-yellow' : 'text-slate-500'}`}>
                      {horaCurta(c.ultima_mensagem_em ?? c.criado_em)}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center justify-between gap-2">
                    <p className="truncate text-xs text-slate-400">
                      {c.status === 'encerrada' && <Lock size={11} className="mr-1 inline text-slate-500" />}
                      {c.ultima_mensagem
                        ? `${prefixo}${c.ultima_mensagem}`
                        : c.tipo === 'individual' ? rotuloPerfil(c.outro?.perfil) : `${c.total_membros} participantes`}
                    </p>
                    {c.nao_lidas > 0 && (
                      <span className="min-w-[20px] shrink-0 rounded-full bg-nexus-yellow px-1.5 text-center text-[10px] font-bold leading-5 text-slate-950">
                        {c.nao_lidas > 99 ? '99+' : c.nao_lidas}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
