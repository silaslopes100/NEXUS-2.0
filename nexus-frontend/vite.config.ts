import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: (req) => {
          if (req.headers.accept?.includes('text/html')) {
            return '/index.html';
          }
          return undefined;
        },
      },
      '/polos': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/escolas': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/unidades': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/professores': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/alunos': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/cursos-disciplinas': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/turmas': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ead': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/notas-historico': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/certificados': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/presencas': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/licencas': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/financeiro': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/cupons': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/pedidos-livros': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/transferencias': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/comunicacao': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
