import React from 'react';
import { Activity, KeyRound } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

/** Parâmetros de autenticação e sessão do NEXUS 2.0 (informativo, somente leitura). */
export const SegurancaSistemaCard: React.FC = () => {
  const { user } = useAuthStore();
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-bold text-white">Segurança</h2>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
          <div className="mb-4 flex items-center gap-2 text-nexus-yellow">
            <KeyRound className="h-5 w-5" />
            <h3 className="text-base font-bold text-white">Status da Autenticação</h3>
          </div>
          <div className="space-y-3 text-sm text-slate-300">
            <div className="flex items-center justify-between border-b border-slate-800 py-2">
              <span className="text-slate-400">Algoritmo de Senha Ativo</span>
              <span className="rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1 font-mono text-xs text-nexus-yellow">
                Argon2id (com Lazy Rehash)
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-slate-800 py-2">
              <span className="text-slate-400">Tempo de Expiração do Access Token</span>
              <span className="font-semibold text-white">15 minutos</span>
            </div>
            <div className="flex items-center justify-between border-b border-slate-800 py-2">
              <span className="text-slate-400">Validade do Refresh Token (Uso Único)</span>
              <span className="font-semibold text-white">7 dias</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-slate-400">Bloqueio Preventivo de Força Bruta</span>
              <span className="font-semibold text-emerald-400">Ativo (5 tentativas / 15 min)</span>
            </div>
          </div>
        </div>

        <div className="glass rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
          <div className="mb-4 flex items-center gap-2 text-blue-400">
            <Activity className="h-5 w-5" />
            <h3 className="text-base font-bold text-white">Sessão em Memória</h3>
          </div>
          <p className="text-xs leading-relaxed text-slate-400">
            O NEXUS 2.0 armazena o access_token estritamente na memória da aplicação (Zustand authStore).
            Isso elimina vulnerabilidades de persistência no <code>localStorage</code> contra ataques XSS e garante renovação automática via Axios Interceptor.
          </p>
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
            <p><strong>Usuário Logado:</strong> {user?.email || '-'}</p>
            <p><strong>ID:</strong> {user?.id || '-'}</p>
          </div>
        </div>
      </div>
    </section>
  );
};
