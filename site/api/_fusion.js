// Émissions écoutées : règles communes au service, à la webapp et au site privé (qui en portent une copie).
// État : {n: {d, m}} ; d = jour d'écoute "AAAA-MM-JJ", ou null si l'émission a été décochée ; m = date de modification (ms).
// Fusion, émission par émission : deux écoutes -> jour le plus ancien ; sinon la modification la plus récente l'emporte.
const fusion1 = (a, b) => !a ? b : !b ? a : a.d && b.d ? {d: a.d < b.d ? a.d : b.d, m: Math.max(a.m, b.m)} : b.m > a.m || (b.m === a.m && b.d) ? b : a;
function propre(E, maintenant) {
  const o = {}; let k = 0;
  if (E && typeof E === "object" && !Array.isArray(E)) for (const [n, x] of Object.entries(E)) {
    if (!/^\d{1,5}$/.test(n) || !x || typeof x !== "object" || ++k > 5000) continue;
    const d = typeof x.d === "string" && /^\d{4}-\d\d-\d\d$/.test(x.d) ? x.d : null;
    let m = Number.isFinite(x.m) && x.m > 0 ? Math.floor(x.m) : 0;
    if (maintenant && m > maintenant) m = maintenant;      // horloge d'un appareil en avance
    o[n] = {d, m};
  }
  return o;
}
function fusion(A, B) { const o = {}; for (const n of new Set([...Object.keys(A), ...Object.keys(B)])) o[n] = fusion1(A[n], B[n]); return o; }
const egal = (A, B) => { const a = Object.keys(A), b = Object.keys(B); return a.length === b.length && a.every(n => B[n] && A[n].d === B[n].d && A[n].m === B[n].m); };
module.exports = {fusion1, fusion, propre, egal};
