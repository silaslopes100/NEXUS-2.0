import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from '@/App';
import '@/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// App instalável (PWA): service worker só em produção (em dev atrapalharia o recarregamento do Vite).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => undefined);
  });
}
