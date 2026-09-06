// Service Worker pour Realm
// Gère le mode hors-ligne basique ET la réception des notifications push

const CACHE_NAME = "realm-cache-v1";

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
          if (event.request.method === "GET" && response.status === 200) {
            cache.put(event.request, response.clone());
          }
          return response;
        })
        .catch(() => cache.match(event.request))
    )
  );
});

// ---------- Notifications push ----------

self.addEventListener("push", (event) => {
  let donnees = { title: "Realm", body: "Nouvelle notification." };
  try {
    donnees = event.data.json();
  } catch (e) {
    // Si les données ne sont pas du JSON valide, on garde le message par défaut
  }

  event.waitUntil(
    self.registration.showNotification(donnees.title, {
      body: donnees.body,
      icon: "/static/icons/icon-192.png",
      badge: "/static/icons/icon-192.png",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      if (clientList.length > 0) {
        return clientList[0].focus();
      }
      return clients.openWindow("/");
    })
  );
});
