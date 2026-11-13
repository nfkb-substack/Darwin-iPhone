// Essai des émissions écoutées et de leur synchronisation : node essai_ecoutees.js   (Playwright ; aucun appel à Vercel)
// Le vrai service (site/api/ecoutees.js) tourne ici avec un magasin Blob simulé en mémoire. Deux « appareils »
// (deux contextes de navigateur) partagent ce service ; le fichier audio est un wav d'une seconde fabriqué sur place.
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path'), Module = require('module');
const magasin = {texte: null, etag: 0, ecritures: 0};
const faux = { get: async () => magasin.texte == null ? null : {statusCode: 200, stream: new Response(magasin.texte).body, blob: {etag: String(magasin.etag)}},
  put: async (c, t, o) => { if (o.ifMatch && o.ifMatch !== String(magasin.etag)) { const e = new Error("Precondition failed"); e.name = "BlobPreconditionFailedError"; throw e; } magasin.texte = t; magasin.etag++; magasin.ecritures++; return {}; } };
const charge = Module._load; Module._load = function (nom, ...r) { return nom === '@vercel/blob' ? faux : charge.call(this, nom, ...r); };
const service = require('./site/api/ecoutees.js');
const types = {'.html':'text/html; charset=utf-8','.json':'application/json','.js':'text/javascript','.png':'image/png','.webmanifest':'application/manifest+json'};
let panne = false;
const srv = http.createServer((q, r) => { let p = q.url.split('?')[0];
  if (p === '/api/ecoutees') { if (panne) { r.writeHead(401, {'content-type': 'text/html'}); return r.end('<html>Authentication Required</html>'); } return service(q, r); }
  if (p === '/') p = '/index.html'; const f = path.join(__dirname, 'site', p); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f)); }).listen(8766);
function wav(sec) { const n = 8000 * sec, b = Buffer.alloc(44 + n, 128); b.write('RIFF', 0); b.writeUInt32LE(36 + n, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(8000, 24); b.writeUInt32LE(8000, 28); b.writeUInt16LE(1, 32); b.writeUInt16LE(8, 34); b.write('data', 36); b.writeUInt32LE(n, 40); return b; }
const U = 'http://localhost:8766/', ok = [], dit = (nom, v) => { ok.push(!!v); console.log(v ? 'OK ' : 'ÉCHEC', nom); };
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] }), errs = [];
  const appareil = async () => { const c = await b.newContext({ viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' }); const p = await c.newPage(); p.on('pageerror', e => errs.push(e.message)); return [c, p]; };
  const etat = p => p.evaluate(() => JSON.parse(localStorage.getItem('darwin-ecoutees2') || '{}'));
  const [cA, A] = await appareil(), [cB, B] = await appareil();
  // A : importe un son, le lit jusqu'au bout
  await A.goto(U + '#fichiers'); await A.waitForSelector('#importer');
  await A.setInputFiles('#choix', [{name: '313-monologue-2016-09-03-essai.mp3', mimeType: 'audio/wav', buffer: wav(1)}]);
  await A.waitForSelector('.info');
  await A.goto(U + '#e313'); await A.waitForSelector('#jouer');
  dit('case décochée au départ', !(await A.isChecked('#eco')));
  await A.click('#jouer'); await A.waitForFunction(() => document.querySelector('#eco').checked, null, {timeout: 8000});
  dit('fin de lecture : case cochée, date affichée', /\(le \d/.test(await A.textContent('#ecoDate')));
  await A.waitForTimeout(2200);
  dit('envoyé au service', JSON.parse(magasin.texte).e['313'].d);
  // A coche 188 à la main ; B démarre et reçoit les deux
  await A.goto(U + '#e188'); await A.waitForSelector('#eco'); await A.check('#eco'); await A.waitForTimeout(2200);
  await B.goto(U); await B.waitForSelector('#liste li'); await B.waitForFunction(() => document.querySelectorAll('#liste .ok').length === 2, null, {timeout: 5000});
  dit('B reçoit 313 et 188 (✓ dans le catalogue)', true);
  // B décoche 188 -> A le voit décoché
  await B.goto(U + '#e188'); await B.waitForSelector('#eco'); await B.waitForTimeout(50); await B.uncheck('#eco'); await B.waitForTimeout(2200);
  await A.goto(U + '#fichiers'); await A.waitForSelector('#synGo'); await A.click('#synGo'); await A.waitForFunction(() => /Synchronisé à/.test(document.querySelector('#synEtat').textContent));
  const eA = await etat(A); dit('décochage propagé de B vers A', eA['188'].d === null && eA['313'].d);
  dit('compteur de la page Fichiers', /^1 émission écoutée/.test(await A.textContent('#ecoNb')));
  // hors ligne : A coche 190, rien ne se perd, synchronisation au retour
  const avant = magasin.ecritures;
  await cA.setOffline(true); await A.goto(U + '#e190').catch(() => {}); await A.evaluate(() => { ecoPoser(190, true); }); await A.waitForTimeout(2200);
  dit('hors ligne : gardé dans la page, message', (await etat(A))['190'].d && /Hors ligne/.test(await A.evaluate(() => SYN.etat)) && magasin.ecritures === avant);
  await cA.setOffline(false); await A.waitForFunction(() => /Synchronisé/.test(SYN.etat), null, {timeout: 8000});
  dit('retour du réseau : envoyé', JSON.parse(magasin.texte).e['190'].d);
  // modifications simultanées : B recoche 188 pendant que A décoche 313
  await B.evaluate(() => { ecoPoser(188, true); }); await A.evaluate(() => { ecoPoser(313, false); }); await A.waitForTimeout(2500);
  await B.evaluate(() => synchro()); await B.waitForTimeout(600); await A.evaluate(() => synchro()); await A.waitForTimeout(600);
  const fA = await etat(A), fB = await etat(B);
  dit('les deux appareils convergent', JSON.stringify(Object.entries(fA).sort()) === JSON.stringify(Object.entries(fB).sort()) && fA['188'].d && !fA['313'].d && fA['190'].d);
  // synchronisation sans changement : pas d'écriture
  const w = magasin.ecritures; await A.evaluate(() => synchro()); await A.waitForTimeout(500); dit('sans changement, pas d\'écriture dans le magasin', magasin.ecritures === w);
  // clé refusée
  panne = true; await A.evaluate(() => { mem.set('darwin-synchro-cle', 'mauvaise'); return synchro(); }); dit('refus : message clair', /clé refusée/.test(await A.evaluate(() => SYN.etat))); panne = false;
  // import d'un fichier version 1 (site privé d'avant) et d'un .json étranger
  await B.goto(U + '#fichiers'); await B.waitForSelector('#importer');
  await B.setInputFiles('#choix', [{name: 'darwin-ecoutees.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({format: 'darwin-ecoutees', v: 1, ecoutees: {'1': '2026-11-01', '188': '2026-10-01'}}))}, {name: 'vercel.json', mimeType: 'application/json', buffer: Buffer.from('{"headers":[]}')}]);
  await B.waitForSelector('.message'); const bilan = (await B.textContent('.message')).replace(/\s+/g, ' ');
  const gB = await etat(B); dit('import v1 : ajoute, garde le jour le plus ancien, refuse le .json étranger', gB['1'].d === '2026-11-01' && gB['188'].d === '2026-10-01' && /1 émission ajoutée/.test(bilan) && /vercel\.json : import impossible/.test(bilan));
  // filtre « pas encore écoutées » du catalogue (état de B : 1 et 190/313/188 selon les étapes précédentes)
  await B.goto(U + '#'); await B.waitForSelector('#fNeuf');
  const tousN = await B.evaluate(() => document.querySelectorAll('#liste li').length), coches = await B.evaluate(() => document.querySelectorAll('#liste .ok').length);
  await B.click('#fNeuf'); await B.waitForSelector('#fNeuf[aria-pressed="true"]');
  const neufN = await B.evaluate(() => document.querySelectorAll('#liste li').length), cochesN = await B.evaluate(() => document.querySelectorAll('#liste .ok').length);
  dit('filtre « pas encore écoutées » : retire les ✓ et eux seuls', coches > 0 && cochesN === 0 && neufN === tousN - coches);
  await B.click('#fNeuf'); await B.waitForSelector('#fNeuf[aria-pressed="false"]');
  dit('filtre désactivé : tout revient', (await B.evaluate(() => document.querySelectorAll('#liste li').length)) === tousN);
  // service : entrées invalides et format
  const post = async o => (await fetch(U + 'api/ecoutees', {method: 'POST', headers: {'content-type': 'text/plain'}, body: typeof o === 'string' ? o : JSON.stringify(o)}));
  dit('service : format inattendu refusé', (await post({v: 1})).status === 400 && (await post('{')).status === 400);
  const r = await (await post({format: 'darwin-ecoutees', v: 2, e: {'7': {d: '2026-11-12', m: 9e15}, 'x': {d: 'z'}}})).json();
  dit('service : horloge en avance ramenée à maintenant, clé invalide ignorée', r.e['7'].m <= Date.now() && !('x' in r.e));
  const g = await fetch(U + 'api/ecoutees'); dit('service : GET et en-têtes', g.headers.get('access-control-allow-origin') === '*' && g.headers.get('cache-control') === 'no-store' && (await g.json()).v === 2);
  console.log(errs.length ? errs : 'aucune erreur de page'); await b.close(); srv.close();
  if (ok.includes(false) || errs.length) process.exit(1);
})().catch(e => { console.error(e); process.exit(1); });
