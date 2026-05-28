// KAMIKAZE SW — auto-desinstala SWs viejos
// Browsers con SW viejo (v50-v53) checkean este URL para updates.
// Este file se instala como "nuevo SW", luego se auto-desinstala y limpia todo.
// Next page load = no SW = browser fetcha HTML fresh de CF.

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', async (e) => {
  e.waitUntil((async () => {
    // 1. Borrar TODOS los caches
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k)));
    } catch {}
    // 2. Auto-unregister
    try { await self.registration.unregister(); } catch {}
    // 3. Reload todas las pestañas/PWA abiertas
    try {
      const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const c of clients) {
        try { c.navigate(c.url); } catch { try { c.postMessage({ type: 'force-reload' }); } catch {} }
      }
    } catch {}
  })());
});

// Pass-through fetch (no cache)
self.addEventListener('fetch', e => {
  // Don't intercept anything, let browser do default
});
