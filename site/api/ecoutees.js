// Darwin-iPhone : historique d'écoute partagé entre l'iPhone et le site privé du Mac.
// Un seul document JSON, gardé dans un magasin Vercel Blob privé. GET le renvoie ; POST y fusionne l'état envoyé
// et renvoie le résultat. L'accès est filtré en amont par la protection Vercel du projet (connexion Vercel, ou clé
// « Protection Bypass for Automation » passée dans l'adresse) : ce service ne reçoit que des appels déjà autorisés.
// Il ne contient que des numéros d'émission et des dates.
const { get, put } = require("@vercel/blob");
const { fusion, propre, egal } = require("./_fusion.js");
// Les déploiements d'aperçu (essais) écrivent dans un document à part, jamais dans l'historique réel.
const CHEMIN = process.env.VERCEL_ENV === "production" ? "ecoutees.json" : "essai/ecoutees.json";

async function lireDoc() {
  const r = await get(CHEMIN, {access: "private", useCache: false});
  if (!r || r.statusCode !== 200 || !r.stream) return {e: {}, etag: null};
  let j = {}; try { j = JSON.parse(await new Response(r.stream).text()); } catch (x) {}
  return {e: propre(j.e), etag: r.blob.etag || null};
}
function corps(req) {
  if (req.body !== undefined) return Promise.resolve(typeof req.body === "string" ? req.body : Buffer.isBuffer(req.body) ? req.body.toString("utf8") : JSON.stringify(req.body));
  return new Promise((ok, ko) => { let t = "", o = 0; req.on("data", c => { o += c.length; if (o > 4e5) { ko(new Error("trop gros")); req.destroy(); } else t += c; }); req.on("end", () => ok(t)); req.on("error", ko); });
}
module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");        // le site privé s'ouvre en file:// (origine « null »)
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "content-type");
  res.setHeader("Cache-Control", "no-store");
  const rep = (code, o) => { res.statusCode = code; res.setHeader("Content-Type", "application/json; charset=utf-8"); res.end(JSON.stringify(o)); };
  try {
    if (req.method === "OPTIONS") { res.statusCode = 204; return res.end(); }
    if (req.method === "GET") return rep(200, {format: "darwin-ecoutees", v: 2, e: (await lireDoc()).e});
    if (req.method !== "POST") return rep(405, {erreur: "méthode non prise en charge"});
    const texte = await corps(req);
    if (texte.length > 4e5) return rep(413, {erreur: "document trop gros"});
    let j; try { j = JSON.parse(texte); } catch (x) { return rep(400, {erreur: "JSON illisible"}); }
    if (!j || j.format !== "darwin-ecoutees" || j.v !== 2) return rep(400, {erreur: "format inattendu"});
    const recu = propre(j.e, Date.now());
    for (let essai = 0; ; essai++) {
      const doc = await lireDoc(), tout = fusion(doc.e, recu);
      if (egal(tout, doc.e)) return rep(200, {format: "darwin-ecoutees", v: 2, e: tout});
      try {
        await put(CHEMIN, JSON.stringify({format: "darwin-ecoutees", v: 2, e: tout}), {access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json", cacheControlMaxAge: 60, ...(doc.etag ? {ifMatch: doc.etag} : {})});
        return rep(200, {format: "darwin-ecoutees", v: 2, e: tout});
      } catch (x) { if (essai >= 3 || !/Precondition/i.test([x && x.name, x && x.constructor && x.constructor.name, x && x.message].join(" "))) throw x; }   // écrit entre-temps par l'autre appareil : on relit
    }
  } catch (x) { console.error(x); rep(500, {erreur: "service indisponible"}); }
};
