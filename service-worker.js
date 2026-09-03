// Service Worker basique pour KmerGestion
// Permet un fonctionnement minimal hors-ligne (cache des pages déjà visitées)

const CACHE_NAME = "kmergestion-cache-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      fetch(event.request)
        .then((response) => {
          // Si la requête réussit, on met à jour le cache
          if (event.request.method === "GET" && response.status === 200) {
            cache.put(event.request, response.clone());
          }
          return response;
        })
        .catch(() => {
          // Si pas de connexion, on sert la version en cache si elle existe
          return cache.match(event.request);
        })
    )
  );
});
