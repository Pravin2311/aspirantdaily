const CACHE_NAME = "aspirant-daily-v3"; // bump version after fix

const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/quiz.html",
  "/result.html",
  "/styles.css",
  "/js/quiz.js",
  "/js/result.js",
  "/manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(err => {
        console.warn("Cache addAll failed:", err);
      });
    })
  );
  self.skipWaiting();
});

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

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET or cross-origin requests
  if (event.request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // Bypass API calls
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Serve HTML shells from cache (ignore query params)
  if (url.pathname.endsWith(".html")) {
    event.respondWith(
      caches.match(url.pathname).then(response => response || fetch(event.request))
    );
    return;
  }

  // Cache-first for everything else
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});