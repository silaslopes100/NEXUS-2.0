import defaultColors from 'tailwindcss/colors';
import plugin from 'tailwindcss/plugin';

/*
 * Tema claro/escuro via variáveis CSS.
 * As classes dos componentes continuam as mesmas (bg-slate-900, text-white, text-red-300...);
 * o que muda é o valor da cor, definido em :root (escuro, igual ao original) e em
 * html[data-theme="light"] (claro: branco, off-white bege e o azul do sistema).
 */

const hexToRgb = (hex) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
};
const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

const SLATE_SHADES = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950'];
const SLATE_LIGHT = {
  50: '#111827',
  100: '#1C2533',
  200: '#263142',
  300: '#3A4352',
  400: '#545D6B',
  500: '#737B88',
  600: '#A8AEB8',
  700: '#D6CFC1',
  800: '#E7E1D5',
  900: '#FFFFFF',
  950: '#F8F6F1',
};

const ACCENTS = [
  'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan',
  'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose',
];
// Tons claros (texto sobre fundo escuro) e tons muito escuros (gradientes) se espelham no tema claro.
// 500–700 (botões, tints com opacidade) permanecem fixos.
const ACCENT_MIRROR = { 50: '900', 100: '800', 200: '800', 300: '700', 400: '600', 800: '200', 900: '100', 950: '50' };

const PAGE = { dark: '#0B0F19', light: '#F3EFE6' };
const WHITE = { dark: '#FFFFFF', light: '#0F172A' };

const slate = Object.fromEntries(SLATE_SHADES.map((s) => [s, v(`slate-${s}`)]));
const accents = Object.fromEntries(
  ACCENTS.map((name) => [
    name,
    Object.fromEntries(
      Object.entries(defaultColors[name]).map(([shade, hex]) => [shade, ACCENT_MIRROR[shade] ? v(`${name}-${shade}`) : hex])
    ),
  ])
);

const darkVars = {
  '--c-white': hexToRgb(WHITE.dark),
  '--c-page': hexToRgb(PAGE.dark),
};
const lightVars = {
  '--c-white': hexToRgb(WHITE.light),
  '--c-page': hexToRgb(PAGE.light),
};
for (const s of SLATE_SHADES) {
  darkVars[`--c-slate-${s}`] = hexToRgb(defaultColors.slate[s]);
  lightVars[`--c-slate-${s}`] = hexToRgb(SLATE_LIGHT[s]);
}
for (const name of ACCENTS) {
  for (const [shade, mirror] of Object.entries(ACCENT_MIRROR)) {
    darkVars[`--c-${name}-${shade}`] = hexToRgb(defaultColors[name][shade]);
    lightVars[`--c-${name}-${shade}`] = hexToRgb(defaultColors[name][mirror]);
  }
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        white: v('white'),
        slate,
        ...accents,
        ink: '#0B0F19',
        'on-accent': '#FFFFFF',
        nexus: {
          page: v('page'),
          yellow: {
            DEFAULT: '#FFB800',
            hover: '#E5A600',
            light: '#FDE68A',
            glow: 'rgba(255, 184, 0, 0.25)',
          },
          blue: {
            DEFAULT: '#2563EB',
            dark: '#1D4ED8',
            deep: '#1E40AF',
            navy: '#0F172A',
            darker: '#0B0F19',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Montserrat', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'nexus-card': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'nexus-glow': '0 0 25px rgba(255, 184, 0, 0.15)',
        'nexus-blue-glow': '0 0 25px rgba(37, 99, 235, 0.25)',
      },
    },
  },
  plugins: [
    plugin(({ addBase }) => {
      addBase({
        ':root': { ...darkVars, 'color-scheme': 'dark' },
        'html[data-theme="light"]': { ...lightVars, 'color-scheme': 'light' },
      });
    }),
  ],
}
