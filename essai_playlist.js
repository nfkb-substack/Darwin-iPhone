// essai des playlists : node essai_playlist.js <dossier des extraits> <playlist.m3u8>
const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const E = process.argv[2], PLF = process.argv[3];
const types = {'.html':'text/html; charset=utf-8','.json':'application/json','.js':'text/javascript','.png':'image/png','.webmanifest':'application/manifest+json'};
const srv = http.createServer((q, r) => { let p = q.url.split('?')[0]; if (p === '/') p = '/index.html'; const f = path.join(__dirname, 'site', p); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f)); }).listen(8766);
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const ctx = await b.newContext({ viewport: { width: 375, height: 667 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, colorScheme: 'dark' });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  const U = 'http://localhost:8766/';
  await p.goto(U + '#listes'); await p.waitForSelector('#importer');
  await p.setInputFiles('#choix', [PLF]); await p.waitForSelector('h2'); console.log('playlist seule:', await p.textContent('h2'), '|', (await p.textContent('.message')).trim());
  await p.goto(U + '#fichiers'); await p.waitForSelector('#importer');
  await p.setInputFiles('#choix', fs.readdirSync(E).filter(f => /mp3$|essai\.ndjson$/.test(f)).map(f => path.join(E, f))); await p.waitForSelector('.info');
  await p.goto(U + '#listes'); await p.waitForSelector('ul.liste a'); console.log('listes:', (await p.textContent('ul.liste')).trim().replace(/\s+/g, ' '));
  await p.click('ul.liste a'); await p.waitForSelector('#lirePl');
  console.log('lignes:', await p.$$eval('ul.liste .s', l => l.map(x => x.textContent)), '|', (await p.textContent('.message')).trim());
  await p.screenshot({ path: 'pl1.png', fullPage: true });
  await p.click('#lirePl'); await p.waitForSelector('#lecteur[data-cle="m:313"]'); await p.waitForTimeout(1200);
  console.log('lecture 313:', await p.evaluate(() => !document.querySelector('#audio').paused), '| bandeau:', (await p.textContent('.info')).trim().replace(/\s+/g, ' '));
  await p.screenshot({ path: 'pl2.png' });
  // fin du fichier -> émission suivante disponible (314 absente sautée, 470 lue en monologue)
  await p.evaluate(() => document.querySelector('#audio').dispatchEvent(new Event('ended')));   // extraits tronqués : la fin réelle n'est pas atteignable
  await p.waitForSelector('#lecteur[data-cle="m:470"]', { timeout: 20000 }); await p.waitForTimeout(1200);
  console.log('enchaînement -> 470:', await p.evaluate(() => !document.querySelector('#audio').paused), (await p.textContent('.info')).trim().replace(/\s+/g, ' '), '| suivant désactivé:', await p.$eval('#plSuiv', x => x.disabled));
  await p.click('#plPrec'); await p.waitForSelector('#lecteur[data-cle="m:313"]'); console.log('précédent -> 313 ok');
  await p.click('#retour'); await p.waitForSelector('#lirePl'); console.log('retour -> playlist:', await p.textContent('#lirePl'), '| repère:', await p.$$eval('ul.liste .t', l => l.map(x => x.textContent.slice(0, 12))));
  await p.click('ul.liste a[data-i="1"]'); await p.waitForSelector('.message'); console.log('absente:', (await p.textContent('.message')).trim().replace(/\s+/g, ' '));
  await p.goto(U + '#'); await p.waitForSelector('#fListes'); console.log('catalogue:', await p.textContent('#fListes'));
  console.log('erreurs:', errs); await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
