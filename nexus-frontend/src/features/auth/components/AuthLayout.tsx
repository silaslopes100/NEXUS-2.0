import React from 'react';
import { NexusLogo } from '@/components/brand/NexusLogo';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
import { useThemeStore } from '@/stores/themeStore';
import bgDark from '@/assets/BG TELA DE LOGIN DARK.mp4';
import bgLight from '@/assets/BG TELA DE LOGIN LIGHT.mp4';

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
  const theme = useThemeStore((state) => state.theme);
  return (
    <div className="min-h-screen w-full flex bg-nexus-page relative overflow-hidden">
      {/* Vídeo de fundo (um por tema), com opacidade média */}
      <video
        key={theme}
        className="absolute inset-0 h-full w-full object-cover opacity-50 pointer-events-none"
        src={theme === 'light' ? bgLight : bgDark}
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
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
          <div className="auth-glass rounded-2xl p-7 sm:p-9 relative">
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
