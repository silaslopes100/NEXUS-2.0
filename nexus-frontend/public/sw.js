/* Service worker do NEXUS 2.0 (PWA).
 * - Navegação: rede primeiro; sem conexão, a última página da aplicação ou a página offline.
 * - /assets/* (arquivos com hash do Vite) e /icons/*: cache primeiro (são imutáveis).
 * - Chamadas de API e outras origens NUNCA passam pelo cache (dados sempre atuais e privados).
 * Troque VERSAO para descartar os caches antigos.
 */
const VERSAO = 'nexus-v1';
const CACHE_ESTATICO = `${VERSAO}-estatico`;
const CACHE_PAGINAS = `${VERSAO}-paginas`;
const PRE_CACHE = ['/offline.html', '/icons/icon-192.png', '/manifest.webmanifest'];
// Prefixos de API servidos pelo mesmo domínio (proxy de desenvolvimento) — nunca cachear.
const API = ['/auth', '/admin/', '/ava/', '/ead/', '/financeiro', '/turmas', '/polos', '/escolas', '/alunos', '/chat',
  '/comunicacao', '/notas-historico', '/presencas', '/licencas', '/avaliacoes', '/cursos-disciplinas', '/professores'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_ESTATICO).then((c) => c.addAll(PRE_CACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(chaves.filter((k) => !k.startsWith(VERSAO)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // API em outro domínio, fontes, vídeos: direto da rede

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(CACHE_PAGINAS).then((c) => c.put('/', copia)).catch(() => undefined);
          return resp;
        })
        .catch(async () => (await caches.match('/', { cacheName: CACHE_PAGINAS })) || caches.match('/offline.html')),
    );
    return;
  }

  if (API.some((p) => url.pathname.startsWith(p))) return;

  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/')) {
    event.respondWith(
      caches.match(req).then((emCache) => emCache || fetch(req).then((resp) => {
        if (resp.ok) {
          const copia = resp.clone();
          caches.open(CACHE_ESTATICO).then((c) => c.put(req, copia)).catch(() => undefined);
        }
        return resp;
      })),
    );
  }
});
