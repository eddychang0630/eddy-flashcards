const CACHE_NAME = 'eddy-flashcard-v4';
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

// Always check the network for the app shell so a new deployment is visible.
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const isAudio = url.origin === self.location.origin && url.pathname.includes('/audio/') && url.pathname.endsWith('.mp3');
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
  const isAppPage = request.mode === 'navigate' || (
    url.origin === self.location.origin &&
    (url.pathname.endsWith('/') || url.pathname.endsWith('/index.html'))
  );

  if (isAppPage) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => caches.match(request)
          .then(response => response || caches.match('./index.html')))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(response => response || fetch(request))
  );
});

// 更新 Service Worker 時清除舊快取
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys()
      .then(cacheNames => Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      ))
      .then(() => self.clients.claim())
  );
});
