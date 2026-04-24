const CACHE_NAME = 'aroid-cache-v1';
const urlsToCache = [
  './index.html',
  './database.js',
  './assets/background_2.png',
  './assets/ui_placeholder.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
          return cache.addAll(urlsToCache).catch(err => {
              console.warn("Failed to cache some files on install", err);
          });
      })
  );
});

self.addEventListener('fetch', event => {
  // Only intercept GET requests
  if (event.request.method !== 'GET') return;
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
            return response; // Return from cache
        }
        // Clone the request because it's a one-time use stream
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(
          response => {
            // Check if valid response
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            // Clone the response to cache it and return it
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            return response;
          }
        ).catch(() => {
            // If fetch fails (offline) and not in cache, we could return a fallback
        });
      })
  );
});
