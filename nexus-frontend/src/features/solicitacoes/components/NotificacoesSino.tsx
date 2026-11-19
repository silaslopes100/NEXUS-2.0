import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Loader2 } from 'lucide-react';
import { Notificacao, notificacoesApi } from '@/features/solicitacoes/api';

const INTERVALO_MS = 60_000;

const tempo = (v?: string | null) => {
  if (!v) return '';
  const min = Math.round((Date.now() - new Date(v).getTime()) / 60000);
  if (min < 1) return 'agora';
  if (min < 60) return `há ${min} min`;
  if (min < 1440) return `há ${Math.round(min / 60)} h`;
  return new Date(v).toLocaleDateString('pt-BR');
};

/** Sino do topo: notificações do usuário e da unidade (Polo/Escola), consultado a cada 60 s. */
export const NotificacoesSino: React.FC = () => {
  const navigate = useNavigate();
  const [naoLidas, setNaoLidas] = useState(0);
  const [aberto, setAberto] = useState(false);
  const [itens, setItens] = useState<Notificacao[] | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let ativo = true;
    const atualizar = () => {
      if (document.hidden) return;
      notificacoesApi.resumo().then((r) => ativo && setNaoLidas(r.nao_lidas)).catch(() => undefined);
    };
    atualizar();
    const id = window.setInterval(atualizar, INTERVALO_MS);
    return () => {
      ativo = false;
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!aberto) return;
    setItens(null);
    notificacoesApi.listar().then(setItens).catch(() => setItens([]));
    const fora = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setAberto(false);
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setAberto(false);
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', esc);
    };
  }, [aberto]);

  const abrir = async (n: Notificacao) => {
    setAberto(false);
    if (!n.lida) {
      notificacoesApi.marcarLida(n.id).then((r) => setNaoLidas(r.nao_lidas)).catch(() => undefined);
    }
    if (n.link) navigate(n.link);
  };

  return (
    <div ref={ref} className="relative">
      <button type="button" aria-label={`Notificações${naoLidas ? ` (${naoLidas} não lidas)` : ''}`}
        onClick={() => setAberto((v) => !v)}
        className="relative rounded-xl border border-slate-700/60 bg-slate-800/60 p-2 text-slate-300 transition-colors hover:border-nexus-yellow/30 hover:text-nexus-yellow">
        <Bell className="h-4 w-4" />
        {naoLidas > 0 && (
          <span className="absolute -right-1 -top-1 min-w-[18px] rounded-full bg-nexus-yellow px-1 text-center text-[10px] font-bold leading-[18px] text-ink">
            {naoLidas > 9 ? '9+' : naoLidas}
          </span>
        )}
      </button>
      {aberto && (
        <div className="glass absolute right-0 z-40 mt-2 w-80 overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <span className="text-sm font-semibold text-white">Notificações</span>
            {naoLidas > 0 && (
              <button type="button" className="text-xs text-blue-300 hover:underline"
                onClick={() => notificacoesApi.marcarTodas().then(() => {
                  setNaoLidas(0);
                  setItens((l) => l?.map((n) => ({ ...n, lida: true })) ?? l);
                }).catch(() => undefined)}>
                Marcar todas como lidas
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {itens === null ? (
              <div className="flex justify-center p-6 text-slate-400"><Loader2 className="animate-spin" size={18} /></div>
            ) : itens.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-500">Nenhuma notificação.</p>
            ) : (
              itens.map((n) => (
                <button key={n.id} type="button" onClick={() => void abrir(n)}
                  className={`block w-full border-b border-slate-800/70 px-4 py-3 text-left hover:bg-slate-800/60 ${n.lida ? 'opacity-60' : ''}`}>
                  <p className="flex items-start gap-2 text-sm font-medium text-white">
                    {!n.lida && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-nexus-yellow" />}
                    {n.titulo}
                  </p>
                  {n.mensagem && <p className="mt-0.5 text-xs text-slate-400">{n.mensagem}</p>}
                  <p className="mt-1 text-[11px] text-slate-500">{tempo(n.criado_em)}</p>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
