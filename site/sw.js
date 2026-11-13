// Darwin-iPhone : met la page et le catalogue en réserve pour un usage sans réseau.
// La réserve répond d'abord (la page s'ouvre sans réseau, et même si la connexion Vercel a expiré) ;
// une copie fraîche est demandée en arrière-plan et servira à l'ouverture suivante.
const VERSION = "darwin-iphone-5";
const FICHIERS = ["./", "index.html", "catalogue.json", "manifest.webmanifest", "icone-180.png", "icone-512.png"];
const bonne = r => r && r.ok && !r.redirected && r.type === "basic";
self.addEventListener("install", e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(FICHIERS)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(l => Promise.all(l.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;   // le service de synchronisation ne passe jamais par la réserve
  e.respondWith(caches.open(VERSION).then(async c => {
    const cle = e.request.mode === "navigate" ? "index.html" : e.request;
    const enReserve = await c.match(cle, {ignoreSearch: true});
    const frais = fetch(e.request, {credentials: "same-origin"}).then(r => { if (bonne(r)) c.put(cle, r.clone()); return r; });
    if (enReserve) { e.waitUntil(frais.catch(() => {})); return enReserve; }
    return frais;
  }));
});
