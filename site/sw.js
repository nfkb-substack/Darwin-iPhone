// Darwin-iPhone : met la page et le catalogue en réserve pour un usage sans réseau.
const VERSION = "darwin-iphone-1";
const FICHIERS = ["./", "index.html", "catalogue.json", "manifest.webmanifest", "icone-180.png", "icone-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(FICHIERS)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(l => Promise.all(l.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  // réseau d'abord (pour recevoir les mises à jour), réserve si le réseau manque
  e.respondWith(fetch(e.request).then(r => { if (r.ok) { const copie = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copie)); } return r; })
    .catch(() => caches.match(e.request, {ignoreSearch: true}).then(r => r || caches.match("index.html"))));
});
