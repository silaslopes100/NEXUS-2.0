import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import {
  Users,
  Building2,
  GraduationCap,
  CreditCard,
  ShieldCheck,
  Activity,
  KeyRound,
  ArrowUpRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const AdminDashboardPage: React.FC = () => {
  const { user } = useAuthStore();

  const stats = [
    { label: 'Usuários Ativos', val: '17.903+', icon: Users, change: '+12% este mês', color: 'text-blue-400' },
    { label: 'Polos Integrados', val: '48', icon: Building2, change: '100% migrados', color: 'text-nexus-yellow' },
    { label: 'Professores / Tutores', val: '124', icon: GraduationCap, change: 'Corpo docente', color: 'text-emerald-400' },
    { label: 'Faturamento & Licenças', val: 'R$ 184.500', icon: CreditCard, change: 'Via Asaas Gateway', color: 'text-purple-400' },
  ];

  return (
    <div className="space-y-8 max-w-7xl">
      {/* Welcome Banner */}
      <div className="p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-2xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-nexus-yellow/15 border border-nexus-yellow/30 text-nexus-yellow text-xs font-bold uppercase tracking-wider mb-3">
              <ShieldCheck className="w-3.5 h-3.5" />
              Painel Administrativo NEXUS 2.0
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Bem-vindo, {user?.nome || 'Administrador'}!
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              Visão executiva em tempo real de acessos, segurança, matrículas e finanças do ecossistema.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/admin/usuarios"
              className="py-2.5 px-4 bg-nexus-yellow hover:bg-nexus-yellow-hover text-slate-950 font-bold text-xs rounded-xl shadow-lg transition-colors flex items-center gap-1.5"
            >
              <Users className="w-4 h-4" />
              Gerenciar Usuários
            </Link>
            <Link
              to="/admin/auditoria"
              className="py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Activity className="w-4 h-4 text-nexus-yellow" />
              Logs de Auditoria
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-md hover:border-slate-700 transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {s.label}
                </span>
                <div className={`p-2 rounded-xl bg-slate-950 border border-slate-800 ${s.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-black text-white mt-3">{s.val}</div>
              <div className="flex items-center gap-1 text-xs text-slate-400 mt-2">
                <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
                <span>{s.change}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Security & Architecture Facts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center gap-2 mb-4 text-nexus-yellow">
            <KeyRound className="w-5 h-5" />
            <h2 className="text-base font-bold text-white">Status da Autenticação</h2>
          </div>
          <div className="space-y-3 text-sm text-slate-300">
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Algoritmo de Senha Ativo</span>
              <span className="font-mono text-xs bg-slate-950 px-2.5 py-1 rounded-md text-nexus-yellow border border-slate-800">
                Argon2id (com Lazy Rehash)
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Tempo de Expiração do Access Token</span>
              <span className="font-semibold text-white">15 minutos</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-800">
              <span className="text-slate-400">Validade do Refresh Token (Uso Único)</span>
              <span className="font-semibold text-white">7 dias</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">Bloqueio Preventivo de Força Bruta</span>
              <span className="text-emerald-400 font-semibold">Ativo (5 tentativas / 15 min)</span>
            </div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center gap-2 mb-4 text-blue-400">
            <Activity className="w-5 h-5" />
            <h2 className="text-base font-bold text-white">Sessão em Memória</h2>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            O NEXUS 2.0 armazena o access_token estritamente na memória da aplicação (Zustand authStore).
            Isso elimina vulnerabilidades de persistência no <code>localStorage</code> contra ataques XSS e garante renovação automática via Axios Interceptor.
          </p>
          <div className="mt-4 p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-400">
            <p><strong>Usuário Logado:</strong> {user?.email || '-'}</p>
            <p><strong>ID:</strong> {user?.id || '-'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
