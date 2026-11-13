// Essai de la vitesse de lecture (ralentissement, groupe « émissions du début ») : node essai_vitesse.js   (Playwright, aucun réseau)
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const types = {'.html':'text/html; charset=utf-8','.json':'application/json','.js':'text/javascript','.png':'image/png','.webmanifest':'application/manifest+json'};
const srv = http.createServer((q, r) => { let p = q.url.split('?')[0]; if (p === '/') p = '/index.html'; const f = path.join(__dirname, 'site', p);
  if (!fs.existsSync(f) || !fs.statSync(f).isFile()) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f)); }).listen(8767);
function wav(sec) { const n = 8000 * sec, b = Buffer.alloc(44 + n, 128); b.write('RIFF', 0); b.writeUInt32LE(36 + n, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(8000, 24); b.writeUInt32LE(8000, 28); b.writeUInt16LE(1, 32); b.writeUInt16LE(8, 34); b.write('data', 36); b.writeUInt32LE(n, 40); return b; }
const U = 'http://localhost:8767/', ok = [], dit = (nom, v) => { ok.push(!!v); console.log(v ? 'OK ' : 'ÉCHEC', nom); };
(async () => {
  const b = await chromium.launch(), errs = [];
  const c = await b.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' }), P = await c.newPage();
  P.on('pageerror', e => errs.push(e.message));
  const rate = () => P.evaluate(() => document.querySelector('#audio').playbackRate), bouton = async () => (await P.textContent('#vit')).trim();
  const va = async n => { await P.goto(U + '#e' + n); await P.waitForSelector('#vit'); await P.waitForFunction(() => document.querySelector('#audio').readyState >= 0); await P.waitForTimeout(150); };
  await P.goto(U + '#fichiers'); await P.waitForSelector('#importer');
  await P.setInputFiles('#choix', [{name: '3-monologue-2010-09-18-essai.mp3', mimeType: 'audio/wav', buffer: wav(1)}, {name: '313-monologue-2016-09-03-essai.mp3', mimeType: 'audio/wav', buffer: wav(1)}]);
  await P.waitForSelector('.info');
  await va(313);
  dit('départ : 1×, panneau fermé', await rate() === 1 && await bouton() === '1×' && await P.isHidden('#vitPan'));
  await P.click('#vit'); dit('le bouton ouvre le panneau', await P.isVisible('#vitPan') && (await P.getAttribute('#vit', 'aria-expanded')) === 'true');
  dit('9 vitesses dont 0,6× et 0,75×', (await P.locator('#vitPan [data-v]').count()) === 9 && await P.isVisible('#vitPan [data-v="0.6"]') && await P.isVisible('#vitPan [data-v="0.75"]'));
  dit('une seule vitesse au départ (libellé)', /toutes les émissions/.test(await P.textContent('#vitQui')));
  await P.click('#vitPan [data-v="0.8"]');
  dit('0,8× : lecteur, bouton, case enfoncée', await rate() === 0.8 && await bouton() === '0,8×' && (await P.getAttribute('#vitPan [data-v="0.8"]', 'aria-pressed')) === 'true' && (await P.getAttribute('#vitPan [data-v="1"]', 'aria-pressed')) === 'false');
  dit('le panneau se referme après le choix', await P.isHidden('#vitPan') && (await P.getAttribute('#vit', 'aria-expanded')) === 'false');
  dit('la voix garde sa hauteur (preservesPitch)', await P.evaluate(() => document.querySelector('#audio').preservesPitch === true));
  await P.reload(); await P.waitForSelector('#vit'); await P.waitForTimeout(150);
  dit('retenue après rechargement', await rate() === 0.8 && await bouton() === '0,8×');
  // groupe « émissions du début »
  await P.click('#vit'); await P.fill('#vitN', '40'); await P.dispatchEvent('#vitN', 'change');
  dit('n° 313 hors du groupe : reste à 0,8×, libellé « à partir du n° 41 »', await rate() === 0.8 && /à partir du n° 41/.test(await P.textContent('#vitQui')));
  await va(3);
  dit('n° 3 dans le groupe : 0,85× par défaut', await rate() === 0.85 && await bouton() === '0,85×');
  await P.click('#vit'); dit('libellé « n° 1 à 40 »', /n° 1 à 40/.test(await P.textContent('#vitQui')));
  await P.click('#vitPan [data-v="0.7"]');
  dit('0,7× règle le groupe du début', await rate() === 0.7);
  await va(313); dit('n° 313 inchangé à 0,8×', await rate() === 0.8);
  await va(3); dit('n° 3 retrouve 0,7×', await rate() === 0.7);
  await P.click('#vit'); await P.fill('#vitN', ''); await P.dispatchEvent('#vitN', 'change');
  dit('seuil vidé : une seule vitesse (0,8×)', await rate() === 0.8 && /toutes les émissions/.test(await P.textContent('#vitQui')));
  await P.fill('#vitN', '-5'); await P.dispatchEvent('#vitN', 'change'); dit('seuil négatif ignoré', await rate() === 0.8 && (await P.inputValue('#vitN')) === '');
  // lecture réelle à vitesse lente : la durée écoulée suit la vitesse
  await va(313); await P.click('#jouer'); await P.waitForTimeout(600); const t = await P.evaluate(() => document.querySelector('#audio').currentTime);
  dit('lecture à 0,8× : avance moins vite que le temps réel', t > 0.2 && t < 0.58);
  // mise en page sur un écran étroit (320 px)
  await P.click('#vit'); await P.waitForTimeout(50);
  const l = await P.evaluate(() => { const r = document.querySelector('#vitPan').getBoundingClientRect(), bt = [...document.querySelectorAll('#vitPan .btn')].map(x => x.getBoundingClientRect()); return {droite: Math.max(...bt.map(x => x.right)), largeur: innerWidth, h: Math.min(...bt.map(x => x.height))}; });
  dit('panneau sans débordement à 320 px, boutons de 40 px au moins', l.droite <= l.largeur && l.h >= 40);
  console.log(errs.length ? errs : 'aucune erreur de page'); await b.close(); srv.close();
  if (ok.includes(false) || errs.length) process.exit(1);
})().catch(e => { console.error(e); process.exit(1); });
