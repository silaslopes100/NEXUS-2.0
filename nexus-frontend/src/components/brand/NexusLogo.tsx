import React from 'react';
import nexusLogo from '@/assets/nexus-logo.png';
import nexusLogoNegativo from '@/assets/nexus-logo-negativo.png';
import { useThemeStore } from '@/stores/themeStore';

interface NexusLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showSubtitle?: boolean;
  className?: string;
}

export const NexusLogo: React.FC<NexusLogoProps> = ({
  size = 'md',
  showSubtitle = false,
  className = '',
}) => {
  const theme = useThemeStore((state) => state.theme);
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-12',
    lg: 'h-16',
    xl: 'h-24',
  };

  return (
    <div className={`flex flex-col items-center select-none ${className}`}>
      <img
        src={theme === 'light' ? nexusLogoNegativo : nexusLogo}
        alt="NEXUS"
        draggable={false}
        className={`${sizeClasses[size]} w-auto max-w-full object-contain`}
      />

      {showSubtitle && (
        <span className="mt-2 text-xs font-semibold tracking-widest text-nexus-yellow uppercase opacity-90">
          Plataforma Educacional Integrada 2.0
        </span>
      )}
    </div>
  );
};
