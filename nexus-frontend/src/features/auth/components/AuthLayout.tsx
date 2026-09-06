import React from 'react';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { ShieldCheck, Sparkles, BookOpen, Layers } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title,
  subtitle,
}) => {
  return (
    <div className="min-h-screen w-full flex bg-[#0B0F19] relative overflow-hidden">
      {/* Background Decorative Glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-nexus-blue/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/3 w-[30rem] h-[30rem] bg-nexus-blue-deep/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 right-10 w-96 h-96 bg-nexus-yellow/10 rounded-full blur-3xl pointer-events-none" />

      {/* Grid Pattern Overlay */}
      <div 
        className="absolute inset-0 bg-[linear-gradient(to_right,#1f293710_1px,transparent_1px),linear-gradient(to_bottom,#1f293710_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" 
      />

      {/* Main Container */}
      <div className="relative z-10 w-full flex flex-col lg:flex-row min-h-screen">
        
        {/* Left Side: Brand & Visual Hero */}
        <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 lg:p-16 border-r border-slate-800/60 bg-gradient-to-b from-[#0F172A]/80 via-[#0B0F19]/90 to-[#070A12] backdrop-blur-xl">
          <div>
            <div className="flex items-center gap-3">
              <NexusLogo size="sm" />
            </div>

            <div className="mt-16 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-nexus-blue/10 border border-nexus-blue/30 text-nexus-yellow text-xs font-semibold uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5 text-nexus-yellow animate-pulse" />
                Nova Versão 2.0 • Ecossistema Unificado
              </div>

              <h1 className="text-4xl xl:text-5xl font-extrabold text-white tracking-tight leading-tight">
                Gestão educacional de <br />
                <span className="bg-gradient-to-r from-white via-slate-100 to-nexus-yellow bg-clip-text text-transparent">
                  alta performance.
                </span>
              </h1>

              <p className="text-slate-400 text-base max-w-lg leading-relaxed">
                Acesse o ambiente integrado de Polos, Escolas, Professores e Alunos com segurança em Argon2id e controle em tempo real.
              </p>
            </div>

            {/* Feature Highlights */}
            <div className="mt-12 space-y-4">
              <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
                <div className="p-2 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">Segurança de Próxima Geração</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Criptografia Argon2id, tokens com rotação automática e auditoria contínua.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
                <div className="p-2 rounded-lg bg-amber-500/20 border border-amber-500/30 text-nexus-yellow">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">18 Módulos Integrados</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    AVA, Acadêmico, Licenças, Pagamentos Asaas, Livros, Chat e Feed em um só lugar.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
                <div className="p-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">Controle Multi-Perfil</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Ambientes customizados para Admin, Polo, Escola, Docentes e Discentes.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-500">
            <span>© 2026 NEXUS 2.0 • Todos os direitos reservados.</span>
            <span className="text-slate-400 font-medium">v2.0.0</span>
          </div>
        </div>

        {/* Right Side: Form View */}
        <div className="w-full lg:w-1/2 flex flex-col justify-center items-center p-6 sm:p-10 lg:p-16">
          <div className="w-full max-w-md">
            
            {/* Mobile Header Logo */}
            <div className="lg:hidden flex flex-col items-center mb-8">
              <NexusLogo size="md" showSubtitle />
            </div>

            {/* Card Form */}
            <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-7 sm:p-9 shadow-2xl backdrop-blur-xl relative">
              <div className="mb-6 text-center sm:text-left">
                <h2 className="text-2xl font-bold text-white tracking-tight">
                  {title}
                </h2>
                {subtitle && (
                  <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">
                    {subtitle}
                  </p>
                )}
              </div>

              {children}
            </div>

            <div className="mt-6 text-center text-xs text-slate-500">
              Precisa de suporte? Entre em contato com a equipe de administração do seu polo.
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
