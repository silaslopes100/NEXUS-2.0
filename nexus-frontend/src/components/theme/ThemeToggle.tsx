import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useThemeStore } from '@/stores/themeStore';

export const ThemeToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { theme, toggle } = useThemeStore();
  const claro = theme === 'light';

  return (
    <button
      type="button"
      role="switch"
      aria-checked={claro}
      aria-label="Modo claro"
      title={claro ? 'Mudar para o modo escuro' : 'Mudar para o modo claro'}
      onClick={toggle}
      className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border border-slate-700/60 bg-slate-800/60 transition-colors hover:border-nexus-blue/50 ${className}`}
    >
      <span
        className={`absolute left-0.5 flex h-[22px] w-[22px] items-center justify-center rounded-full shadow transition-transform duration-200 ${
          claro ? 'translate-x-5 bg-nexus-yellow text-ink' : 'translate-x-0 bg-nexus-blue text-on-accent'
        }`}
      >
        {claro ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
      </span>
    </button>
  );
};
