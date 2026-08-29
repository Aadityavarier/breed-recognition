const CACHE_NAME = 'pashupehchaan-app-v2';
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

// Fetch: Stale-While-Revalidate for app shell, Network-Only for prediction API
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // PREDICTION ENDPOINT — Network-Only, never cache.
  //
  // Do NOT clone or cache POST requests that carry a multipart FormData body
  // (the uploaded image). Cloning a consumed POST body stream causes the server
  // to receive an empty image, making every scan return the same region-fallback
  // breed. Returning a stale cached response from a previous scan is equally
  // wrong. Let these requests go straight to the network untouched.
  if (url.pathname.includes('/api/predict') || url.pathname.includes('/predict')) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return new Response(
            JSON.stringify({
              success: false,
              error: 'You appear to be offline. Please reconnect and try again.'
            }),
            { headers: { 'Content-Type': 'application/json' } }
          );
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
