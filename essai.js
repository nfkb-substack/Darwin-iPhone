const { chromium, webkit } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const E = '/mnt/user-data/uploads/Darwin/Darwin-iPhone/essai/';
const types = {'.html':'text/html; charset=utf-8','.json':'application/json','.js':'text/javascript','.png':'image/png','.webmanifest':'application/manifest+json'};
const srv = http.createServer((q, r) => { let p = q.url.split('?')[0]; if (p === '/') p = '/index.html'; const f = path.join('site', p); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': types[path.extname(f)] || 'application/octet-stream'}); r.end(fs.readFileSync(f)); }).listen(8765);
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const ctx = await b.newContext({ viewport: { width: 375, height: 667 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, colorScheme: 'dark' });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', e => errs.push('ERR ' + e.message)); p.on('console', m => { if (m.type() === 'error') errs.push('console ' + m.text()); });
  await p.goto('http://localhost:8765/'); await p.waitForSelector('#liste li');
  console.log('liste:', await p.$$eval('#liste li', l => l.length), await p.textContent('#compte'));
  await p.screenshot({ path: 'c1_liste_vide.png' });
  // épisode absent, rien d'importé
  await p.goto('http://localhost:8765/#e313'); await p.waitForSelector('.message'); console.log('absent/vide:', (await p.textContent('.message')).trim());
  // import
  await p.goto('http://localhost:8765/#fichiers'); await p.waitForSelector('#importer');
  await p.setInputFiles('#choix', fs.readdirSync(E).filter(f => /mp3$|essai\.ndjson$/.test(f)).map(f => E + f).concat(['site/vercel.json']));
  await p.waitForSelector('.message, .info', { timeout: 30000 }); console.log('bilan:', (await p.textContent('.message, .info')).trim().replace(/\s+/g, ' '));
  console.log('rayons:', await p.$$eval('h3', l => l.map(x => x.textContent)));
  await p.screenshot({ path: 'c2_fichiers.png', fullPage: true });
  // épisode présent
  await p.goto('http://localhost:8765/#e313'); await p.waitForSelector('#st p[data-i]');
  await p.waitForFunction(() => document.querySelector('#dur').textContent !== '–');
  console.log('durée:', await p.textContent('#dur'), '| lignes:', await p.$$eval('#st p[data-i]', l => l.length), '| pochette:', await p.$eval('.entete img', i => i.naturalWidth + 'x' + i.naturalHeight), '| notes:', (await p.$eval('pre.notes', x => x.textContent.length)));
  await p.click('#jouer'); await p.waitForTimeout(1500); await p.click('#p30'); await p.waitForTimeout(1200);
  console.log('après +30:', await p.textContent('#tps'), '| ligne active:', await p.$eval('#st p.ici', x => x.textContent.slice(0, 60)).catch(() => 'aucune'));
  await p.click('#st p[data-i="9"]'); await p.waitForTimeout(800);
  console.log('touche ligne 9 ->', await p.evaluate(() => document.querySelector('#audio').currentTime.toFixed(1)), await p.$eval('#st p.ici', x => x.dataset.i));
  await p.click('#m15'); await p.waitForTimeout(500); console.log('après −15:', await p.evaluate(() => document.querySelector('#audio').currentTime.toFixed(1)));
  await p.screenshot({ path: 'c3_episode.png' });
  // correspondance original
  console.log('carte original:', await p.evaluate(async () => { await ouvrirSon(313, 'o', false); const r = [versMono(100), versMono(929.5), versMono(929 + 199 + 10), depuisMono(900), depuisMono(940), depuisMono(1700)]; return r; }));
  await p.goto('http://localhost:8765/#e313o'); await p.waitForSelector('#lecteur[data-cle="o:313"]'); console.log('original ouvert, lignes:', await p.$$eval('#st p[data-i]', l => l.length));
  // absent avec suggestions
  for (const h of ['#e470o', '#e314', '#e338m', '#e9999']) { await p.goto('http://localhost:8765/' + h); await p.waitForSelector('.message'); console.log(h, '=>', (await p.textContent('.message')).trim().replace(/\s+/g, ' ')); }
  // liste filtrée + recherche
  await p.goto('http://localhost:8765/#'); await p.waitForSelector('#fSeul'); await p.click('#fSeul'); await p.waitForTimeout(200); console.log('sur iPhone:', await p.textContent('#compte'), await p.$$eval('#liste .pastille', l => l.map(x => x.textContent).join('')));
  await p.click('#fTous'); await p.fill('#q', 'memoire 2012'); await p.waitForTimeout(200); console.log('recherche:', await p.textContent('#compte'));
  // reprise de position + hors ligne
  await p.waitForTimeout(1500);
  console.log('sw:', await p.evaluate(async () => !!(await navigator.serviceWorker.ready)));
  await p.reload(); await ctx.setOffline(true); await p.goto('http://localhost:8765/#e470'); await p.waitForSelector('#st p[data-i]'); console.log('hors ligne OK, titre:', await p.textContent('h2'));
  await p.screenshot({ path: 'c4_horsligne.png' });
  console.log('erreurs:', errs);
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
