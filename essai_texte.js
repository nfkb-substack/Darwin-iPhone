// Essai du texte synchronisé : sélection/copie sans déplacer l'audio, recalage à la reprise et au retour au premier plan.
// node essai_texte.js   (Playwright, aucun réseau ; wav de 40 s fabriqué sur place, 40 phrases d'une seconde)
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const types = {'.html':'text/html; charset=utf-8','.json':'application/json','.js':'text/javascript','.png':'image/png','.webmanifest':'application/manifest+json'};
const srv = http.createServer((q, r) => { let p = q.url.split('?')[0]; if (p === '/') p = '/index.html'; const f = path.join(__dirname, 'site', p);
  if (!fs.existsSync(f) || !fs.statSync(f).isFile()) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f)); }).listen(8769);
function wav(sec) { const n = 8000 * sec, b = Buffer.alloc(44 + n, 128); b.write('RIFF', 0); b.writeUInt32LE(36 + n, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(8000, 24); b.writeUInt32LE(8000, 28); b.writeUInt16LE(1, 32); b.writeUInt16LE(8, 34); b.write('data', 36); b.writeUInt32LE(n, 40); return b; }
const U = 'http://localhost:8769/', ok = [], dit = (nom, v) => { ok.push(!!v); console.log(v ? 'OK ' : 'ÉCHEC', nom); };
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] }), errs = [];
  const c = await b.newContext({ viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' }), P = await c.newPage();
  P.on('pageerror', e => errs.push(e.message));
  const phrases = Array.from({length: 40}, (_, i) => [i, 'Phrase numéro ' + i + ' : un texte assez long pour occuper de la place à l\'écran et obliger la page à défiler.']);
  const nd = JSON.stringify({n: 313, d: '2016-09-03', o: [], s: phrases}) + '\n';
  await P.goto(U + '#fichiers'); await P.waitForSelector('#importer');
  await P.setInputFiles('#choix', [{name: '313-monologue-2016-09-03-essai.mp3', mimeType: 'audio/wav', buffer: wav(40)}, {name: 'sous-titres-essai.ndjson', mimeType: 'application/x-ndjson', buffer: Buffer.from(nd)}]);
  await P.waitForSelector('.info');
  await P.goto(U + '#e313'); await P.waitForSelector('#st p[data-i="5"]'); await P.waitForFunction(() => document.querySelector('#audio').readyState >= 1);
  const T = () => P.evaluate(() => document.querySelector('#audio').currentTime), ici = () => P.evaluate(() => { const p = document.querySelector('#st p.ici'); return p ? +p.dataset.i : -1; });
  // 1. un toucher simple emmène l'audio à la phrase
  await P.evaluate(() => document.querySelector('#st p[data-i="10"]').scrollIntoView({block: 'center'}));
  await P.click('#st p[data-i="10"]'); await P.waitForTimeout(300);
  dit('toucher simple : l\'audio va à la phrase 10 et la lit', Math.abs(await T() - 10) < 1.2 && await ici() === 10);
  await P.click('#jouer'); await P.waitForTimeout(200);   // pause
  const t0 = await T();
  // 2. sélection (puis copie) : le toucher qui la termine ne bouge pas l'audio
  await P.evaluate(() => { const p = document.querySelector('#st p[data-i="12"]'), r = document.createRange(); r.selectNodeContents(p); const s = getSelection(); s.removeAllRanges(); s.addRange(r); });
  await P.click('#st p[data-i="20"]'); await P.waitForTimeout(300);
  dit('toucher avec une sélection présente : audio inchangé, toujours en pause', Math.abs(await T() - t0) < 0.3 && await P.evaluate(() => document.querySelector('#audio').paused));
  await P.click('#st p[data-i="20"]'); await P.waitForTimeout(300);
  dit('toucher suivant (sélection retirée) : l\'audio va à la phrase 20', Math.abs(await T() - 20) < 1.2);
  // 3. appui long sans sélection : ignoré
  await P.evaluate(() => document.querySelector('#audio').pause()); const t1 = await T();
  await P.dispatchEvent('#st p[data-i="30"]', 'pointerdown'); await P.waitForTimeout(650); await P.dispatchEvent('#st p[data-i="30"]', 'click'); await P.waitForTimeout(200);
  dit('appui long : audio inchangé', Math.abs(await T() - t1) < 0.3);
  // 4. reprise après une pause : le texte revient à la phrase lue même s'il a défilé et que le surlignement est périmé
  await P.evaluate(() => { document.querySelector('#audio').currentTime = 25; });
  await P.waitForTimeout(200);
  await P.evaluate(() => { window.scrollTo(0, 0); defilementManuel = Date.now(); document.querySelectorAll('#st p.ici').forEach(p => p.classList.remove('ici')); EN_COURS.ligne = 3; });
  dit('état périmé fabriqué (aucun surlignement, ligne 3 mémorisée)', await ici() === -1);
  await P.click('#jouer'); await P.waitForTimeout(1200);
  const vu = await P.evaluate(() => { const p = document.querySelector('#st p.ici'); if (!p) return null; const r = p.getBoundingClientRect(); return {i: +p.dataset.i, dans: r.bottom > 0 && r.top < innerHeight}; });
  dit('reprise : la phrase lue (25) est surlignée et ramenée à l\'écran', vu && vu.i >= 25 && vu.i <= 26 && vu.dans);
  // 5. retour au premier plan : surlignement recalé sans événement audio
  await P.evaluate(() => document.querySelector('#audio').pause());
  await P.evaluate(() => { document.querySelectorAll('#st p.ici').forEach(p => p.classList.remove('ici')); EN_COURS.ligne = 2; });
  await P.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  const a = await T();
  dit('retour au premier plan : surlignement sur la phrase de la position réelle', Math.abs(await ici() - Math.floor(a)) <= 1);
  console.log(errs.length ? errs : 'aucune erreur de page'); await b.close(); srv.close();
  if (ok.includes(false) || errs.length) process.exit(1);
})().catch(e => { console.error(e); process.exit(1); });
