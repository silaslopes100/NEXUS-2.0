import React, { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MessageSquare } from 'lucide-react';
import { normalizeUserRole, useAuthStore } from '@/stores/authStore';
import { Conversa, ConversaDetalhe, chatApi } from '../api';
import { ConversaJanela } from '../components/ConversaJanela';
import { ConversaLista } from '../components/ConversaLista';
import { NovaConversaModal } from '../components/NovaConversaModal';
import { useIntervalo } from '../hooks/useIntervalo';

const INTERVALO_LISTA_MS = 20_000;

/** Chat Interno: lista de conversas + conversa aberta (?c=<id>). */
export const ChatPage: React.FC = () => {
  const { user, perfil } = useAuthStore();
  const papel = normalizeUserRole(perfil?.nome || user?.perfil?.nome);
  const meuId = user?.id ?? '';
  const [params, setParams] = useSearchParams();
  const selecionadaId = params.get('c');
  const [conversas, setConversas] = useState<Conversa[] | null>(null);
  const [nova, setNova] = useState(false);

  const recarregar = useCallback(() => {
    chatApi.listar().then(setConversas).catch(() => setConversas((c) => c ?? []));
  }, []);

  useIntervalo(recarregar, INTERVALO_LISTA_MS);

  const selecionar = (id: string | null) => {
    const p = new URLSearchParams(params);
    if (id) p.set('c', id);
    else p.delete('c');
    setParams(p, { replace: !id });
  };

  const aoAbrir = (c: ConversaDetalhe) => {
    setNova(false);
    recarregar();
    selecionar(c.id);
  };

  return (
    <div className="-m-6 h-[calc(100dvh-4rem)] lg:-m-8">
      <div className="flex h-full min-h-0 overflow-hidden border-slate-800 bg-slate-900/60">
        <section className={`h-full min-h-0 w-full border-r border-slate-800 lg:block lg:w-[340px] lg:shrink-0 ${selecionadaId ? 'hidden' : 'block'}`}>
          <ConversaLista conversas={conversas} selecionadaId={selecionadaId} meuId={meuId}
            onSelecionar={selecionar} onNova={() => setNova(true)} />
        </section>
        <section className={`h-full min-h-0 min-w-0 flex-1 ${selecionadaId ? 'block' : 'hidden lg:block'}`}>
          {selecionadaId ? (
            <ConversaJanela
              key={selecionadaId}
              conversaId={selecionadaId}
              meuId={meuId}
              isAdmin={papel === 'admin'}
              onVoltar={() => selecionar(null)}
              onMudou={recarregar}
              onOcultada={() => { selecionar(null); recarregar(); }}
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center text-slate-500">
              <MessageSquare size={40} className="text-slate-700" />
              <p className="text-sm">Selecione uma conversa ou inicie uma nova.</p>
              <p className="max-w-sm text-xs text-slate-600">
                As mensagens ficam disponíveis por 90 dias. Conversas entre alunos acontecem apenas nos grupos das turmas.
              </p>
            </div>
          )}
        </section>
      </div>
      {nova && <NovaConversaModal souAluno={papel === 'aluno'} onFechar={() => setNova(false)} onAberta={aoAbrir} />}
    </div>
  );
};
