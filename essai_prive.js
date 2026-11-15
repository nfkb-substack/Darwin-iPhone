// Essai du site privé (étiquettes, drapeau dans le texte du lecteur, synchronisation) : node essai_prive.js
// Nécessite /tmp/prive_test/site_prive.html : copie de Darwin/site_prive.html dans laquelle on ajoute, juste avant la fin du script
// principal, window.__T={D,select,lecOuvrir,ECO,ECO2,ETQ,etqDate,ecoFiltre,ecoMarque,synchro,ecoLireFichier,L,setMode:v=>{ecoMode=v}};
// (le site livré n'expose rien). Voir METHODE.md.
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const R = '/tmp/prive_test/', ok = [], dit = (n, v) => { ok.push(!!v); console.log(v ? 'OK ' : 'ÉCHEC', n); };
function wav(sec) { const n = 8000 * sec, b = Buffer.alloc(44 + n, 128); b.write('RIFF', 0); b.writeUInt32LE(36 + n, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(8000, 24); b.writeUInt32LE(8000, 28); b.writeUInt16LE(1, 32); b.writeUInt16LE(8, 34); b.write('data', 36); b.writeUInt32LE(n, 40); return b; }
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--allow-file-access-from-files'] }), errs = [];
  const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } }), P = await ctx.newPage();
  P.on('pageerror', e => errs.push(e.message));
  await P.goto('file://' + R + 'site_prive.html'); await P.waitForTimeout(800);
  await P.evaluate(() => Object.assign(window, window.__T));
  const e = await P.evaluate(() => { const x = D.eps.find(x => x.F.m && !x.F.m[1]); return x ? {i: x.i, n: x.n, nom: x.F.m[0]} : null; });
  dit('un épisode avec monologue existe dans les données', !!e);
  const num = parseInt(e.nom, 10);
  fs.mkdirSync(R + 'lecteur', {recursive: true}); fs.mkdirSync(R + 'monologue', {recursive: true});
  const s = Array.from({length: 40}, (_, i) => [i, 'Phrase numéro ' + i + ' du texte d\'essai.']);
  fs.writeFileSync(R + 'lecteur/' + num + '.js', 'window.DARWIN_LEC=window.DARWIN_LEC||{};DARWIN_LEC[' + num + ']=' + JSON.stringify({f: e.nom, d: 40, o: [], s}) + ';\n');
  fs.writeFileSync(R + 'monologue/' + e.nom, wav(40));
  // 1. fiche
  await P.evaluate(i => select('ep', i), e.i); await P.waitForSelector('.eco-etiq input');
  dit('fiche : deux cases « Thème difficile » / « Mauvaise qualité audio »', await P.locator('.eco-etiq input').count() === 2);
  await P.check('.eco-etiq input[data-etq="difficile"]'); await P.check('.eco-etiq input[data-etq="qualite"]');
  dit('cases enregistrées (difficile, qualité) et clé darwin-etiq1', await P.evaluate(n => etqDate('difficile', String(n)) && etqDate('qualite', String(n)) && !!JSON.parse(localStorage.getItem('darwin-etiq1')).difficile[n], e.n));
  dit('« Écoutée en entier » toujours indépendante', await P.evaluate(n => !ECO[n], e.n));
  // 2. filtre
  { const h = fs.readFileSync(R + 'site_prive.html', 'utf8'); dit('filtre du catalogue : options « difficiles » et « mauvaise qualité » dans la barre', h.includes('<option value="dif">difficiles</option><option value="qua">mauvaise qualité</option>')); }
  dit('ecoFiltre : mode difficiles ne garde que l\'émission étiquetée', await P.evaluate(() => { __T.setMode('dif'); const k = D.eps.filter(ecoFiltre).length; __T.setMode('qua'); const q = D.eps.filter(ecoFiltre).length; __T.setMode(''); return k === 1 && q === 1; }));
  dit('marque dans le catalogue', await P.evaluate(n => /◆/.test(ecoMarque({n})) && /⚠/.test(ecoMarque({n})), e.n));
  // 3. lecteur et texte
  await P.evaluate(i => lecOuvrir(i, {src: 'm', texte: true}), e.i); await P.waitForSelector('.lec-texte .c'); await P.waitForTimeout(600);
  dit('texte : un drapeau par phrase', await P.locator('.lec-texte .drap').count() === 40);
  const t0 = await P.evaluate(() => L.a.currentTime);
  await P.hover('.lec-texte .c[data-i="12"]'); await P.click('.lec-texte .drap[data-d="12"]'); await P.waitForTimeout(200);
  dit('drapeau : phrase 12 signalée (état, instant)', await P.evaluate(n => { const x = ETQ.err[n + ':12']; return x && x.d && x.t === 12 && document.querySelector('.drap[data-d="12"]').classList.contains('on'); }, num));
  dit('drapeau : l\'audio n\'a pas bougé', Math.abs(await P.evaluate(() => L.a.currentTime) - t0) < 0.3);
  await P.click('.lec-texte .c[data-i="20"]'); await P.waitForTimeout(300);
  dit('clic sur la phrase : l\'audio y va', Math.abs(await P.evaluate(() => L.a.currentTime) - 20) < 1.2);
  dit('surlignement de la phrase courante toujours en place', await P.evaluate(() => !!document.querySelector('.lec-texte .c.cur')));
  const copie = await P.evaluate(() => { const p = document.querySelector('.lec-texte .c[data-i="12"]').parentNode, r = document.createRange(); r.selectNodeContents(p); const s = getSelection(); s.removeAllRanges(); s.addRange(r); const t = s.toString(); s.removeAllRanges(); return t; });
  dit('texte sélectionné : sans le symbole du drapeau', !/⚑/.test(copie) && /Phrase numéro 12/.test(copie));
  await P.click('.lec-texte .drap[data-d="12"]'); await P.waitForTimeout(150);
  dit('second clic : signalement retiré', await P.evaluate(n => ETQ.err[n + ':12'].d === null, num));
  await P.click('.lec-texte .drap[data-d="31"]');
  // 4. synchro (réponse simulée d'un autre appareil)
  let envoye = null;
  await P.route('https://darwin-iphone.vercel.app/**', r => { envoye = JSON.parse(r.request().postData()); r.fulfill({status: 200, contentType: 'application/json', headers: {'access-control-allow-origin': '*'}, body: JSON.stringify({format: 'darwin-ecoutees', v: 2, e: envoye.e, difficile: Object.assign({}, envoye.difficile, {'245': {d: '2026-11-15', m: Date.now()}}), qualite: envoye.qualite, err: Object.assign({}, envoye.err, {[num + ':3']: {d: '2026-11-15', m: Date.now(), t: 3}})})}); });
  await P.evaluate(() => { localStorage.setItem('darwin-synchro-cle', JSON.stringify('cle-essai')); synchro(); }); await P.waitForTimeout(800);
  dit('synchro : envoi des sections (v2)', envoye && envoye.v === 2 && envoye.difficile[e.n] && envoye.qualite[e.n] && envoye.err[num + ':31'] && envoye.err[num + ':31'].t === 31);
  dit('synchro : étiquette et signalement de l\'autre appareil fusionnés, drapeau 3 affiché', await P.evaluate(n => etqDate('difficile', '245') && etqDate('err', n + ':3') && document.querySelector('.drap[data-d="3"]').classList.contains('on'), num));
  // 5. export / import
  const doc = await P.evaluate(() => JSON.stringify({format: 'darwin-ecoutees', v: 2, e: ECO2, ...ETQ}));
  await P.evaluate(() => { for (const k of Object.keys(ETQ)) ETQ[k] = {}; });
  await P.evaluate(d => ecoLireFichier(d), doc);
  dit('import : sections restaurées', await P.evaluate(n => etqDate('difficile', String(n)) && etqDate('err', n + ':31'), num));
  // 6. ancien document (sans sections) accepté, rien d'effacé
  await P.evaluate(() => ecoLireFichier(JSON.stringify({format: 'darwin-ecoutees', v: 2, e: {}})));
  dit('ancien format : aucune étiquette perdue', await P.evaluate(n => etqDate('difficile', String(n)) && etqDate('err', n + ':31'), num));
  console.log(errs.length ? errs : 'aucune erreur de page'); await b.close();
  if (ok.includes(false) || errs.length) process.exit(1);
})().catch(e => { console.error(e); process.exit(1); });
