const CACHE_NAME = 'pashudhan-app-v1';
const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/static/sw.js'
];

// Install: precache app shell safely (per-file try/catch resilience)
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      for (const assetUrl of PRECACHE_ASSETS) {
        try {
          await cache.add(assetUrl);
        } catch (err) {
          console.warn(`[SW Cache Warning]: Failed to precache ${assetUrl}:`, err);
        }
      }
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Stale-While-Revalidate for app shell, Network-First for API with cache fallback
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API calls: Network-First, cache last successful result
  if (url.pathname.includes('/api/predict') || url.pathname.includes('/predict')) {
    event.respondWith(
      fetch(event.request.clone())
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put('/api/last_prediction_result', copy);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match('/api/last_prediction_result').then((cached) => {
            if (cached) return cached;
            return new Response(
              JSON.stringify({
                success: false,
                error: "Offline mode: Local edge AI model ready."
              }),
              { headers: { 'Content-Type': 'application/json' } }
            );
          });
        })
    );
    return;
  }

  // App shell & static assets: Stale-While-Revalidate
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
