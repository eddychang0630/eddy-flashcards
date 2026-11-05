const CACHE_PREFIX = 'eddy-flashcard-';
const CACHE_NAME = 'eddy-flashcard-v5';
const APP_PATH = new URL(self.registration.scope).pathname;
const SUB_APP_PATHS = ['sentences', 'speaking'].map(name => APP_PATH + name);
const urlsToCache = [
  './',
  './index.html',
  './manifest.json',
  './icon-192-v2.png',
  './icon-512-v2.png',
  './apple-touch-icon-v2.png',
  './favicon-v2.ico'
];

// 安裝 Service Worker 並快取資源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

async function loadAppPage(request) {
  try {
    const response = await fetch(request, { cache: 'no-store' });
    if (response.ok) {
      await caches.open(CACHE_NAME)
        .then(cache => cache.put(request, response.clone()))
        .catch(() => {});
    }
    return response;
  } catch {
    const cached = await caches.open(CACHE_NAME)
      .then(async cache => (await cache.match(request)) || (await cache.match('./index.html')))
      .catch(() => null);
    return cached || new Response('暫時無法連上單字 App。請確認網路後重新整理。', {
      status: 503,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(APP_PATH) ||
      SUB_APP_PATHS.some(path => url.pathname === path || url.pathname.startsWith(path + '/'))) return;

  const isAudio = url.pathname.includes('/audio/') && url.pathname.endsWith('.mp3');
  if (isAudio) {
    const cacheKey = new Request(url.href);
    event.respondWith(
      caches.open(CACHE_NAME).then(async cache => {
        const cached = await cache.match(cacheKey);
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok && response.status === 200) {
          event.waitUntil(cache.put(cacheKey, response.clone()));
        } else if (response.status === 206) {
          event.waitUntil(
            fetch(cacheKey).then(full => {
              if (full.ok && full.status === 200) return cache.put(cacheKey, full.clone());
            }).catch(() => {})
          );
        }
        return response;
      })
    );
    return;
  }
  const isAppPage = request.mode === 'navigate' || url.pathname === APP_PATH || url.pathname === APP_PATH + 'index.html';

  if (isAppPage) {
    event.respondWith(loadAppPage(request));
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then(cache => cache.match(request)).catch(() => null)
      .then(response => response || fetch(request))
  );
});

// 更新 Service Worker 時清除舊快取
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(cacheNames => Promise.all(cacheNames
        .filter(name => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
        .map(name => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});
