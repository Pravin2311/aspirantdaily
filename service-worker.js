const CACHE_NAME = "aspirant-daily-v2"; // increment version to force update
const OFFLINE_PAGES = ["/", "/index.html", "/quiz.html", "/result.html"];
const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/quiz.html",
  "/result.html",
  "/styles.css",     // ✅ matches your file
  "/js/quiz.js",     // ✅ your JS is in /js/
  "/js/result.js",
  "/manifest.webmanifest"
];
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([...OFFLINE_PAGES, ...STATIC_ASSETS]).catch(err => {
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

// Smart fetch handler
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 1. Ignore non-GET requests & non-HTTP(S)
  if (event.request.method !== "GET" || !url.origin.includes("aspirantdaily.com")) {
    return;
  }

  // 2. Bypass API calls — always fetch fresh
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // 3. For HTML pages with query params (e.g., /quiz.html?exam=ssc)
  // → Serve shell (/quiz.html) from cache, let JS fetch fresh data
  if (url.pathname.endsWith(".html")) {
    event.respondWith(
      caches.match(url.pathname).then((response) => {
        return response || fetch(event.request);
      })
    );
    return;
  }

  // 4. Default: cache-first for static assets
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});