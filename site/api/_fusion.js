// Historique et étiquettes : règles communes au service, à la webapp et au site privé (qui en portent une copie).
// Chaque section est un état {clé: {d, m}} ; d = jour de la pose "AAAA-MM-JJ", ou null si retiré ; m = date de modification (ms).
//   e        : émissions écoutées en entier      (clé = numéro d'émission)
//   difficile: émissions aux thèmes difficiles   (clé = numéro)
//   qualite  : émissions à mauvaise qualité audio (clé = numéro)
//   err      : phrases du transcript signalées   (clé = "numéro:indice de la phrase", + t = instant de la phrase en s)
// Fusion, clé par clé : deux poses -> jour le plus ancien ; sinon la modification la plus récente l'emporte.
// Un client ancien qui n'envoie que « e » ne fait rien perdre aux autres sections.
const SECTIONS = {e: /^\d{1,5}$/, difficile: /^\d{1,5}$/, qualite: /^\d{1,5}$/, err: /^\d{1,5}:\d{1,5}$/};
const fusion1 = (a, b) => !a ? b : !b ? a : a.d && b.d ? {...(b.m > a.m ? b : a), d: a.d < b.d ? a.d : b.d, m: Math.max(a.m, b.m)} : b.m > a.m || (b.m === a.m && b.d) ? b : a;
function propre(E, maintenant, re = SECTIONS.e) {
  const o = {}; let k = 0;
  if (E && typeof E === "object" && !Array.isArray(E)) for (const [n, x] of Object.entries(E)) {
    if (!re.test(n) || !x || typeof x !== "object" || ++k > 5000) continue;
    const d = typeof x.d === "string" && /^\d{4}-\d\d-\d\d$/.test(x.d) ? x.d : null;
    let m = Number.isFinite(x.m) && x.m > 0 ? Math.floor(x.m) : 0;
    if (maintenant && m > maintenant) m = maintenant;      // horloge d'un appareil en avance
    o[n] = {d, m};
    if (Number.isFinite(x.t) && x.t >= 0 && x.t < 1e5) o[n].t = Math.round(x.t * 10) / 10;
  }
  return o;
}
function fusion(A, B) { const o = {}; for (const n of new Set([...Object.keys(A), ...Object.keys(B)])) o[n] = fusion1(A[n], B[n]); return o; }
const egal = (A, B) => { const a = Object.keys(A), b = Object.keys(B); return a.length === b.length && a.every(n => B[n] && A[n].d === B[n].d && A[n].m === B[n].m && A[n].t === B[n].t); };
// Document complet : {e, difficile, qualite, err}, chaque section nettoyée (toujours présente, éventuellement vide).
const proprePlus = (j, maintenant) => Object.fromEntries(Object.entries(SECTIONS).map(([s, re]) => [s, propre(j && j[s], maintenant, re)]));
const fusionPlus = (A, B) => Object.fromEntries(Object.keys(SECTIONS).map(s => [s, fusion(A[s], B[s])]));
const egalPlus = (A, B) => Object.keys(SECTIONS).every(s => egal(A[s], B[s]));
module.exports = {SECTIONS, fusion1, fusion, propre, egal, proprePlus, fusionPlus, egalPlus};
