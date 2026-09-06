import React from 'react';

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
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-12',
    lg: 'h-16',
    xl: 'h-24',
  };

  const textSizes = {
    sm: 'text-2xl',
    md: 'text-4xl',
    lg: 'text-5xl',
    xl: 'text-7xl',
  };

  return (
    <div className={`flex flex-col items-center select-none ${className}`}>
      {/* SVG Stylized Brand Logo faithful to official graphic */}
      <div className={`relative flex items-center justify-center font-display font-black tracking-wider ${textSizes[size]}`}>
        <svg
          viewBox="0 0 520 160"
          className={`${sizeClasses[size]} w-auto drop-shadow-[0_4px_12px_rgba(37,99,235,0.35)]`}
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Defs for gradients and 3D bevel filters */}
          <defs>
            <linearGradient id="nexusYellowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFC72C" />
              <stop offset="100%" stopColor="#FF9900" />
            </linearGradient>
            <linearGradient id="nexusBlue3D" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#2563EB" />
              <stop offset="100%" stopColor="#1E3A8A" />
            </linearGradient>
            <filter id="glowYellow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#FFB800" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* 3D Blue Shadow Layers */}
          {/* N */}
          <path d="M 35 125 L 35 30 L 68 30 L 102 95 L 102 30 L 126 30 L 126 125 L 94 125 L 59 60 L 59 125 Z" fill="#1D4ED8" transform="translate(4, 5)" />
          {/* E */}
          <path d="M 145 125 L 145 30 L 210 30 L 210 52 L 172 52 L 172 67 L 204 67 L 204 88 L 172 88 L 172 103 L 212 103 L 212 125 Z" fill="#1D4ED8" transform="translate(4, 5)" />
          {/* X (Yellow Shadow) */}
          <path d="M 230 125 L 260 77 L 232 30 L 260 30 L 275 58 L 290 30 L 318 30 L 290 77 L 320 125 L 292 125 L 275 96 L 258 125 Z" fill="#B45309" transform="translate(4, 5)" />
          {/* U */}
          <path d="M 335 30 L 360 30 L 360 95 C 360 108 370 114 382 114 C 394 114 404 108 404 95 L 404 30 L 429 30 L 429 95 C 429 119 408 128 382 128 C 356 128 335 119 335 95 Z" fill="#1D4ED8" transform="translate(4, 5)" />
          {/* S */}
          <path d="M 445 106 C 450 112 458 116 469 116 C 479 116 486 111 486 104 C 486 96 478 93 464 89 C 445 83 437 76 437 60 C 437 42 452 30 472 30 C 488 30 499 36 507 46 L 492 60 C 486 53 479 50 471 50 C 463 50 458 54 458 59 C 458 66 465 69 479 73 C 499 79 507 88 507 103 C 507 122 491 135 469 135 C 452 135 439 125 431 113 Z" fill="#1D4ED8" transform="translate(4, 5)" />

          {/* Front White & Yellow Lettering */}
          {/* N */}
          <path d="M 35 125 L 35 30 L 68 30 L 102 95 L 102 30 L 126 30 L 126 125 L 94 125 L 59 60 L 59 125 Z" fill="#FFFFFF" />
          {/* E */}
          <path d="M 145 125 L 145 30 L 210 30 L 210 52 L 172 52 L 172 67 L 204 67 L 204 88 L 172 88 L 172 103 L 212 103 L 212 125 Z" fill="#FFFFFF" />
          {/* X - Vibrant Yellow / Gold */}
          <path d="M 230 125 L 260 77 L 232 30 L 260 30 L 275 58 L 290 30 L 318 30 L 290 77 L 320 125 L 292 125 L 275 96 L 258 125 Z" fill="url(#nexusYellowGrad)" filter="url(#glowYellow)" />
          {/* U */}
          <path d="M 335 30 L 360 30 L 360 95 C 360 108 370 114 382 114 C 394 114 404 108 404 95 L 404 30 L 429 30 L 429 95 C 429 119 408 128 382 128 C 356 128 335 119 335 95 Z" fill="#FFFFFF" />
          {/* S */}
          <path d="M 445 106 C 450 112 458 116 469 116 C 479 116 486 111 486 104 C 486 96 478 93 464 89 C 445 83 437 76 437 60 C 437 42 452 30 472 30 C 488 30 499 36 507 46 L 492 60 C 486 53 479 50 471 50 C 463 50 458 54 458 59 C 458 66 465 69 479 73 C 499 79 507 88 507 103 C 507 122 491 135 469 135 C 452 135 439 125 431 113 Z" fill="#FFFFFF" />

          {/* Underline Gold / Yellow Accent Bar */}
          <rect x="30" y="142" width="480" height="6" rx="3" fill="url(#nexusYellowGrad)" />
        </svg>
      </div>

      {showSubtitle && (
        <span className="mt-1 text-xs font-semibold tracking-widest text-nexus-yellow uppercase opacity-90">
          Plataforma Educacional Integrada 2.0
        </span>
      )}
    </div>
  );
};
