import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { MessageSquare } from 'lucide-react';
import { chatApi } from '../api';
import { useIntervalo } from '../hooks/useIntervalo';

const INTERVALO_MS = 30_000;

/** Atalho do topo para o chat, com o total de mensagens não lidas. */
export const ChatBadge: React.FC = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [naoLidas, setNaoLidas] = useState(0);

  useIntervalo(() => {
    chatApi.resumo().then((r) => setNaoLidas(r.nao_lidas)).catch(() => undefined);
  }, INTERVALO_MS);

  return (
    <button type="button" onClick={() => navigate('/chat')}
      aria-label={`Chat${naoLidas ? ` (${naoLidas} mensagens não lidas)` : ''}`}
      className={`relative rounded-xl border p-2 transition-colors ${pathname === '/chat'
        ? 'border-nexus-yellow/40 bg-slate-800 text-nexus-yellow'
        : 'border-slate-700/60 bg-slate-800/60 text-slate-300 hover:border-nexus-yellow/30 hover:text-nexus-yellow'}`}>
      <MessageSquare className="h-4 w-4" />
      {naoLidas > 0 && (
        <span className="absolute -right-1 -top-1 min-w-[18px] rounded-full bg-nexus-yellow px-1 text-center text-[10px] font-bold leading-[18px] text-ink">
          {naoLidas > 99 ? '99+' : naoLidas}
        </span>
      )}
    </button>
  );
};
