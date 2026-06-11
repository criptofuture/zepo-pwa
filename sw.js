const CACHE_NAME = 'zepo-v137';
// Only cache external CDN scripts. Don't pre-cache HTML/manifest — let them be network-first
// so the user always gets the latest version when online.
const ASSETS = [
  'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    // Delete ALL old caches (not just non-matching) to be safe
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin === 'https://vchaxqisbypwwtyjjnjr.supabase.co') return;
  if (url.hostname.endsWith('.google.com') || url.hostname.endsWith('.googleapis.com')) return;

  // Network-first for HTML and SW-related files (always get fresh)
  const isHTML = e.request.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname === '/pwa/' || url.pathname === '/pwa/index.html';
  const isManifest = url.pathname.endsWith('manifest.json');

  if (isHTML || isManifest) {
    e.respondWith(
      fetch(e.request)
        .then(resp => {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
          return resp;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // Cache-first for everything else (icons, CDN scripts, fonts)
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
      const clone = resp.clone();
      caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
      return resp;
    }))
  );
});

self.addEventListener('push', e => {
  let data = {
    title: 'Zepo',
    body: '¿Registraste todos tus gastos de hoy?',
    icon: '/pwa/icons/icon-192.png',
    badge: '/pwa/icons/favicon-32.png',
    url: '/pwa/',
  };
  if (e.data) {
    try { Object.assign(data, e.data.json()); } catch {}
  }
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
      data: { url: data.url },
      vibrate: [200, 100, 200],
      tag: data.tag || 'zepo-push',
      renotify: true,
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/pwa/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes('/pwa/') && 'focus' in c) return c.focus();
      }
      return clients.openWindow(url);
    })
  );
});
