// ===============================
// sw.js – FINAL PRODUCTION VERSION
// ===============================

const CACHE_NAME = "aspirant-daily-v4"; // 🔥 bump on every deploy

const STATIC_ASSETS = [
  "/styles.css",
  "/manifest.webmanifest"
];

// --------------------------------
// INSTALL
// --------------------------------
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// --------------------------------
// ACTIVATE
// --------------------------------
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      )
    )
  );
  self.clients.claim();
});

// --------------------------------
// FETCH
// --------------------------------
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 🚫 Ignore non-GET and cross-origin
  if (req.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // 🚫 NEVER cache API calls
  if (url.pathname.startsWith("/api") || url.search.includes("exam=")) {
    return;
  }

  // 🚫 NEVER cache HTML or JS
  if (
    req.destination === "document" ||
    req.destination === "script"
  ) {
    event.respondWith(fetch(req));
    return;
  }

  // ✅ Cache-first ONLY for static assets (CSS, images, etc.)
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((networkRes) => {
        return caches.open(CACHE_NAME).then((cache) => {
          cache.put(req, networkRes.clone());
          return networkRes;
        });
      });
    })
  );
});
