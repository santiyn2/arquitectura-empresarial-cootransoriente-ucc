/* Service worker: guarda la "cáscara" de la app para abrirla sin señal.
   Los datos (viajes, manifiestos, cola) viven en localStorage, no aquí.
   Las llamadas /api/ nunca se cachean. */
const VERSION = "ct-movil-v1";
const CASCARA = ["./", "index.html", "app.js", "styles.css", "manifest.webmanifest", "icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(CASCARA)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  // Con red se trae lo más nuevo (y se actualiza la copia); sin red se usa la copia.
  e.respondWith(
    fetch(e.request)
      .then((r) => {
        if (r.ok) { const copia = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copia)); }
        return r;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true })));
});
