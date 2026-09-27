const CACHE = 'eddy-sentences-v1';
const SHELL = ['./', './index.html', './style.css', './app.js', './data.json', './manifest.json', './icons/icon-192.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('eddy-sentences-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  if (url.pathname.endsWith('.mp3')) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => { if (response.status === 200 && !request.headers.has('range')) caches.open(CACHE).then(cache => cache.put(request, response.clone())); return response; })));
    return;
  }
  event.respondWith(fetch(request).then(response => { if (response.ok) caches.open(CACHE).then(cache => cache.put(request, response.clone())); return response; }).catch(() => caches.match(request)));
});
