const CACHE_NAME = 'eddy-chunks-v5';
const urlsToCache = ['./', './index.html', './data.js', './manifest.json', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)).then(() => self.skipWaiting()));
});

// 同源資源：網路優先（部署新版立即生效），離線時退回快取
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  // 只處理 /speaking/ 範圍內的請求；YouTube 等外部資源不快取
  if (url.origin !== self.location.origin || !url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  event.respondWith(
    fetch(request, { cache: 'no-store' }) // 跳過瀏覽器 HTTP 快取，部署新版立即生效
      .then(response => {
        if (response.ok) { const copy = response.clone(); caches.open(CACHE_NAME).then(c => c.put(request, copy)); }
        return response;
      })
      .catch(() => caches.match(request).then(r => r || caches.match('./index.html')))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names => Promise.all(names.filter(n => n.startsWith('eddy-chunks-') && n !== CACHE_NAME).map(n => caches.delete(n)))).then(() => self.clients.claim())
  );
});
