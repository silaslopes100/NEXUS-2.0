import React from 'react';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { ThemeToggle } from '@/components/theme/ThemeToggle';

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
    <div className="min-h-screen w-full flex bg-nexus-page relative overflow-hidden">
      {/* Background Decorative Glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-nexus-blue/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/3 w-[30rem] h-[30rem] bg-nexus-blue-deep/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 right-10 w-96 h-96 bg-nexus-yellow/10 rounded-full blur-3xl pointer-events-none" />

      {/* Grid Pattern Overlay */}
      <div
        className="absolute inset-0 bg-[linear-gradient(to_right,#1f293710_1px,transparent_1px),linear-gradient(to_bottom,#1f293710_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none"
      />

      <ThemeToggle className="absolute top-4 right-4 z-20" />

      {/* Conteúdo centralizado */}
      <div className="relative z-10 w-full min-h-screen flex flex-col justify-center items-center p-6 sm:p-10">
        <div className="w-full max-w-md">
          {/* Logo oficial */}
          <div className="flex justify-center mb-8">
            <NexusLogo size="lg" />
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
  );
};
