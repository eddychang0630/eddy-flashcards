const legacyScope = new URL(self.registration.scope);
const destination = new URL('/eddy-speaking/', legacyScope.origin).href;

self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || event.request.mode !== 'navigate') return;
  const url = new URL(event.request.url);
  if (url.origin === legacyScope.origin &&
      (url.pathname === legacyScope.pathname || url.pathname === legacyScope.pathname + 'index.html')) {
    event.respondWith(Response.redirect(destination, 302));
  }
});
