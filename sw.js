const CACHE_NAME = 'zepo-v35';
const ASSETS = [
  './manifest.json',
  'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin === 'https://vchaxqisbypwwtyjjnjr.supabase.co') return;

  // HTML (documento principal): network-only, sin caché, para evitar versiones viejas
  const isDoc = e.request.mode === 'navigate'
    || url.pathname.endsWith('/')
    || url.pathname.endsWith('.html');
  if (isDoc) {
    e.respondWith(
      fetch(e.request, { cache: 'no-store' }).catch(() => caches.match(e.request))
    );
    return;
  }

  // Resto (CSS/JS/fuentes): cache-first con refresh en background
  e.respondWith(
    caches.match(e.request).then(cached => {
      const networkFetch = fetch(e.request).then(resp => {
        if (resp && resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => cached);
      return cached || networkFetch;
    })
  );
});

// ── Push Notifications ────────────────────────────────────────────

self.addEventListener('push', e => {
  let data = { title: 'Zepo 💸', body: '¿Registraste todos tus gastos de hoy?', url: '/' };
  try {
    const parsed = e.data?.json();
    if (parsed) data = { ...data, ...parsed };
  } catch {}

  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/favicon-32.png',
      tag: 'zepo-reminder',          // reemplaza notificación anterior si no fue vista
      renotify: false,
      data: { url: data.url || '/' },
      actions: [
        { action: 'open',    title: 'Abrir Zepo' },
        { action: 'dismiss', title: 'Descartar' },
      ],
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;

  const targetUrl = (e.notification.data?.url) || '/';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      // Si la app ya está abierta, enfocarla
      for (const c of clients) {
        if (c.url.includes('zepo.lynoia.com') && 'focus' in c) return c.focus();
      }
      // Si no, abrir nueva ventana
      if (self.clients.openWindow) return self.clients.openWindow(targetUrl);
    })
  );
});
