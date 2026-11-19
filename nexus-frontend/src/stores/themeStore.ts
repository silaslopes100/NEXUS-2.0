import { create } from 'zustand';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'nexus-theme';

const lerTema = (): Theme => {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
};

const aplicarTema = (theme: Theme) => {
  const html = document.documentElement;
  if (theme === 'light') html.dataset.theme = 'light';
  else delete html.dataset.theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Sem storage (aba privada etc.): o tema vale só para esta sessão.
  }
};

interface ThemeState {
  theme: Theme;
  toggle: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: lerTema(),
  toggle: () => {
    const theme: Theme = get().theme === 'dark' ? 'light' : 'dark';
    aplicarTema(theme);
    set({ theme });
  },
}));
