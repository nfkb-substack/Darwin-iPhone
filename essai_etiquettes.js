// Essai des étiquettes (difficile, mauvaise qualité), du drapeau de signalement dans le transcript et de leur synchronisation.
// node essai_etiquettes.js   (Playwright, aucun réseau ; wav de 40 s fabriqué sur place, 40 phrases d'une seconde)
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const types = {'.html':'text/html; charset=utf-8','.json':'application/json','.js':'text/javascript','.png':'image/png','.webmanifest':'application/manifest+json'};
const srv = http.createServer((q, r) => { let p = q.url.split('?')[0]; if (p === '/') p = '/index.html'; const f = path.join(__dirname, 'site', p);
  if (!fs.existsSync(f) || !fs.statSync(f).isFile()) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f)); }).listen(8769);
function wav(sec) { const n = 8000 * sec, b = Buffer.alloc(44 + n, 128); b.write('RIFF', 0); b.writeUInt32LE(36 + n, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(8000, 24); b.writeUInt32LE(8000, 28); b.writeUInt16LE(1, 32); b.writeUInt16LE(8, 34); b.write('data', 36); b.writeUInt32LE(n, 40); return b; }
const U = 'http://localhost:8769/', ok = [], dit = (nom, v) => { ok.push(!!v); console.log(v ? 'OK ' : 'ÉCHEC', nom); };
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] }), errs = [];
  const ctx = await b.newContext({ viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' }), P = await ctx.newPage();
  P.on('pageerror', e => errs.push(e.message));
  const phrases = Array.from({length: 40}, (_, i) => [i, 'Phrase numéro ' + i + ' : un texte assez long pour occuper de la place à l\'écran et obliger la page à défiler.']);
  const nd = JSON.stringify({n: 313, d: '2016-09-03', o: [], s: phrases}) + '\n';
  await P.goto(U + '#fichiers'); await P.waitForSelector('#importer');
  await P.setInputFiles('#choix', [{name: '313-monologue-2016-09-03-essai.mp3', mimeType: 'audio/wav', buffer: wav(40)}, {name: 'sous-titres-essai.ndjson', mimeType: 'application/x-ndjson', buffer: Buffer.from(nd)}]);
  await P.waitForSelector('.info');
  await P.goto(U + '#e313'); await P.waitForSelector('#st p[data-i="5"]'); await P.waitForFunction(() => document.querySelector('#audio').readyState >= 1);
  const T = () => P.evaluate(() => document.querySelector('#audio').currentTime), ici = () => P.evaluate(() => { const p = document.querySelector('#st p.ici'); return p ? +p.dataset.i : -1; });
  // coin du drapeau d'une phrase : (x, y) en coordonnées de page, après l'avoir amenée à l'écran
  const coin = async i => { await P.evaluate(i => document.querySelector('#st p[data-i="' + i + '"]').scrollIntoView({block: 'center'}), i); return P.evaluate(i => { const r = document.querySelector('#st p[data-i="' + i + '"]').getBoundingClientRect(); return {x: r.right - 16, y: r.top + 16}; }, i); };
  const textes0 = await P.evaluate(() => [...document.querySelectorAll('#st p[data-i]')].map(p => p.textContent));
  // 1. cases de la fiche
  await P.check('#etqDif'); await P.check('#etqQua');
  dit('fiche : « difficile » et « mauvaise qualité » enregistrées', await P.evaluate(() => etqDate('difficile', '313') && etqDate('qualite', '313') && !etqDate('err', '313:1')));
  dit('mémoire locale : darwin-etiq1 écrit', await P.evaluate(() => { const o = JSON.parse(localStorage.getItem('darwin-etiq1')); return !!(o && o.difficile['313'] && o.qualite['313']); }));
  // 2. drapeau : un toucher dans le coin signale sans bouger l'audio
  await P.evaluate(() => { const a = document.querySelector('#audio'); a.currentTime = 5; a.pause(); });
  await P.waitForTimeout(200); const t0 = await T();
  let k2 = await coin(12); await P.mouse.click(k2.x, k2.y); await P.waitForTimeout(250);
  dit('drapeau : phrase 12 signalée (classe err, état, instant mémorisé)', await P.evaluate(() => document.querySelector('#st p[data-i="12"]').classList.contains('err') && ETQ.err['313:12'] && ETQ.err['313:12'].d && ETQ.err['313:12'].t === 12));
  dit('drapeau : l\'audio n\'a pas bougé', Math.abs(await T() - t0) < 0.3);
  dit('drapeau : le texte des phrases est inchangé', JSON.stringify(await P.evaluate(() => [...document.querySelectorAll('#st p[data-i]')].map(p => p.textContent))) === JSON.stringify(textes0));
  dit('drapeau : pas de bouton ni de texte ajouté dans la phrase', await P.evaluate(() => !document.querySelector('#st p button, #st p span') && document.querySelector('#st').children.length === 41));
  // 3. un toucher au milieu de la phrase emmène toujours l'audio
  await P.evaluate(() => document.querySelector('#st p[data-i="20"]').scrollIntoView({block: 'center'}));
  await P.click('#st p[data-i="20"]', {position: {x: 60, y: 30}}); await P.waitForTimeout(300);
  dit('toucher au milieu : l\'audio va à la phrase 20 et la surligne', Math.abs(await T() - 20) < 1.2 && await ici() === 20);
  // 4. le surlignement suit toujours la lecture, drapeaux présents
  await P.evaluate(() => { const a = document.querySelector('#audio'); a.currentTime = 12.2; });
  await P.waitForTimeout(300);
  dit('surlignement sur la phrase signalée (12) : les deux classes coexistent', await P.evaluate(() => { const p = document.querySelector('#st p[data-i="12"]'); return p.classList.contains('ici') && p.classList.contains('err'); }));
  // 5. retrait du signalement
  await P.evaluate(() => document.querySelector('#audio').pause());
  k2 = await coin(12); await P.mouse.click(k2.x, k2.y); await P.waitForTimeout(250);
  dit('second toucher : signalement retiré', await P.evaluate(() => !document.querySelector('#st p[data-i="12"]').classList.contains('err') && ETQ.err['313:12'].d === null));
  k2 = await coin(30); await P.mouse.click(k2.x, k2.y); await P.waitForTimeout(250);
  // 6. une sélection de texte ne contient pas le drapeau
  const copie = await P.evaluate(() => { const p = document.querySelector('#st p[data-i="30"]'), r = document.createRange(); r.selectNodeContents(p); const s = getSelection(); s.removeAllRanges(); s.addRange(r); const t = s.toString(); s.removeAllRanges(); return t; });
  dit('texte copié d\'une phrase signalée : sans symbole', !/[⚐⚑]/.test(copie) && copie.trim() === textes0[30].trim());
  // 7. catalogue : pastilles et filtres
  await P.goto(U + '#'); await P.waitForSelector('#liste li');
  await P.evaluate(() => { location.hash = ''; });
  await P.waitForTimeout(300);
  const liste = await P.evaluate(() => { const li = [...document.querySelectorAll('#liste li')].find(x => /n° 313\b/.test(x.textContent)); return li ? li.textContent : ''; });
  dit('catalogue : pastilles « difficile » et « qualité » sur le n° 313', /difficile/.test(liste) && /qualité/.test(liste));
  dit('catalogue : boutons de filtre présents', await P.evaluate(() => !!document.querySelector('#fDif') && !!document.querySelector('#fQua')));
  await P.click('#fDif'); await P.waitForTimeout(200);
  dit('filtre « Difficiles » : seule l\'émission étiquetée reste', await P.evaluate(() => document.querySelectorAll('#liste li a').length === 1));
  await P.click('#fDif'); await P.waitForTimeout(200);
  // 8. synchronisation : envoi des sections, fusion de la réponse d'un autre appareil, ancien format toléré
  let envoye = null, reponse = null;
  await P.route('**/api/ecoutees**', r => { if (r.request().method() === 'POST') envoye = JSON.parse(r.request().postData()); r.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(reponse(envoye))}); });
  reponse = e => ({format: 'darwin-ecoutees', v: 2, e: e.e, difficile: Object.assign({}, e.difficile, {'245': {d: '2026-11-15', m: Date.now()}}), qualite: e.qualite, err: Object.assign({}, e.err, {'313:3': {d: '2026-11-15', m: Date.now(), t: 3}})});
  await P.evaluate(() => synchro()); await P.waitForTimeout(700);
  dit('synchro : envoi de e, difficile, qualite, err (v2)', envoye && envoye.v === 2 && envoye.e && envoye.difficile['313'] && envoye.qualite['313'] && envoye.err['313:30'] && envoye.err['313:30'].t === 30);
  dit('synchro : étiquette et signalement venus d\'un autre appareil fusionnés', await P.evaluate(() => etqDate('difficile', '245') && etqDate('err', '313:3')));
  reponse = e => ({format: 'darwin-ecoutees', v: 2, e: {}});   // ancien service : aucune section ne doit être perdue
  await P.evaluate(() => synchro()); await P.waitForTimeout(700);
  dit('synchro avec une réponse sans sections : rien n\'est effacé', await P.evaluate(() => etqDate('difficile', '313') && etqDate('qualite', '313') && etqDate('err', '313:30')));
  // 9. fichier d'export / import
  const doc = await P.evaluate(() => JSON.stringify({format: 'darwin-ecoutees', v: 2, e: ECO, ...ETQ}));
  dit('export : le document contient les trois sections', (() => { const j = JSON.parse(doc); return j.difficile && j.qualite && j.err; })());
  await P.evaluate(() => { ETQ.difficile = {}; ETQ.qualite = {}; ETQ.err = {}; etqSauver(); });
  await P.evaluate(d => ecoLireFichier(d), doc);
  dit('import : étiquettes et signalements restaurés', await P.evaluate(() => etqDate('difficile', '313') && etqDate('qualite', '313') && etqDate('err', '313:30')));
  await P.unroute('**/api/ecoutees**');
  // 10. Fichiers : compte
  await P.goto(U + '#fichiers'); await P.waitForSelector('#etqNb');
  dit('Fichiers : compte des étiquettes affiché', /difficile.*mauvaise qualité.*signalée/.test(await P.textContent('#etqNb')));
  console.log(errs.length ? errs : 'aucune erreur de page'); await b.close(); srv.close();
  if (ok.includes(false) || errs.length) process.exit(1);
})().catch(e => { console.error(e); process.exit(1); });
