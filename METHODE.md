# Darwin-iPhone — méthode et reprise du travail

Écrit le 13 novembre 2026 pour reprendre le travail dans une conversation neuve.
Le mode d'emploi pour l'utilisateur est dans `README.md` ; ce fichier-ci s'adresse à celui qui développe.

## Démarrer une nouvelle conversation

Message type : « Lis `Darwin/Darwin-iPhone/METHODE.md` et continue avec [la tâche]. »

La conversation doit :
- être liée au MacBook Air (dossier `~/Music/Darwin`), pour les sous-titres, les mp3 d'essai et la copie locale ;
- attacher en écriture le dépôt GitHub `nfkb-substack/Darwin-iPhone` (branche `main`), pour publier.

Commencer par comparer la copie du Mac avec le dépôt (`git log`, `VERSION` de `site/sw.js`) : la référence est
**le dépôt GitHub**. Le 13 novembre, la copie du Mac avait une version d'avance sur le dépôt (travail de l'étape 2
non publié) ; elle a été publiée, puis la vitesse de lecture a suivi (version `darwin-iphone-5`) ; copie du Mac et dépôt sont alignés.

## Ce qu'est le projet

Webapp d'une seule page pour écouter « Sur les épaules de Darwin » sur un iPhone SE 2020, sans réseau : catalogue,
résumés, lecteur, sous-titres synchronisés, playlists. Demandée légère : pas de moteur de thèmes, pas de
visualisation complexe, pas de bibliothèque (JavaScript sans dépendance).

Projet **strictement séparé** de l'index Darwin :

| | Darwin-iPhone | Index Darwin (ne pas toucher d'ici) |
|---|---|---|
| Dépôt | `nfkb-substack/Darwin-iPhone` (privé) | `nfkb-substack/darwin-index` |
| Vercel | projet `darwin-iphone`, id `prj_MLaSDVyaqaa3Z81odk9v2iFiOVGM`, équipe nfkb `team_VXD1IqWdXgiT7IxRe0PN5yGO` | projet `darwin-index` |
| Adresse | darwin-iphone-nfkb.vercel.app, **protégée par la connexion Vercel** (accord de Rémi) | darwin-index.vercel.app, publique |
| Sur le Mac | `Darwin/Darwin-iPhone/` | `Darwin/Index_themes/`, `Darwin/site_construction/` |

Vercel déploie à chaque push sur `main` (dossier racine du projet : `site/`). Vérifier que le déploiement passe à READY.

## Règle absolue

En ligne : seulement `site/` (page, catalogue, résumés déjà publics, icônes). **Jamais** de mp3 ni de texte transcrit.
`sous-titres-darwin.ndjson` (21,9 Mo, le texte des émissions) reste sur le Mac et sur l'iPhone ; `.gitignore`
exclut `*.ndjson`, `*.mp3` et `essai/`.

## Fichiers

- `site/index.html` : toute l'application (HTML, CSS, JS, ~38 Ko).
- `site/sw.js` : service worker. La réserve répond d'abord (la page s'ouvre sans réseau, même si la connexion
  Vercel a expiré), une copie fraîche est demandée en arrière-plan et sert à l'ouverture suivante.
  **Après toute modification de `site/`, augmenter `VERSION`** (actuellement `darwin-iphone-5`). Les appels `/api/`
  ne passent jamais par la réserve.
- `site/catalogue.json` : 612 diffusions (n°, date, titre, première diffusion, lien Radio France, résumé de la fiche).
- `site/api/ecoutees.js` + `_fusion.js`, `site/package.json` : service de l'historique d'écoute (voir plus bas).
- `site/manifest.webmanifest`, `site/icone-*.png`, `site/vercel.json` (noindex, no-cache).
- `outils/catalogue.py <labo_data.json> site/catalogue.json` : refait le catalogue à partir des données de l'index
  (`labo_data.json` est produit par `Darwin/site_construction/prep_labo.py`).
- `outils/sous_titres.py [n…]` (sur le Mac) : lit `Darwin/lecteur/*.js` → `sous-titres-darwin.ndjson`.
- `essai.js`, `essai_playlist.js`, `essai_ecoutees.js` : essais Playwright (voir plus bas). Extraits d'essai sur le Mac dans `essai/`
  (313 monologue et original, 470 monologue, `sous-titres-essai.ndjson`).

## Fonctionnement de `site/index.html`

- **Stockage** : IndexedDB `darwin-iphone` version 2, magasins `meta`, `son` (le mp3 entier), `pochette`, `st`
  (sous-titres), `pl` (playlists). Clés des sons : `m:313` (monologue) ou `o:313` (original). Préférences et
  positions de lecture dans `localStorage` via l'objet `mem` ; émissions écoutées sous `darwin-ecoutees2`, clé de
  synchronisation sous `darwin-synchro-cle`.
- **Import** (`importer`) : par le sélecteur de fichiers d'iOS. Les mp3 sont reconnus à leur nom
  (`313-monologue-….mp3`, `313-original-….mp3`) ; `lireID3` extrait pochette (APIC), notes (COMM) et paroles (USLT).
  Un `.ndjson` passe par `importerSousTitres` ; un `.m3u8` par `lirePlaylist` ; un `.json` par `ecoLireFichier`.
- **Sous-titres** : une ligne par émission `{"n", "d", "o", "s", "od"}` ; `s` = phrases et instants du monologue,
  `o` = coupes (musiques retirées) qui permettent de suivre aussi l'original (`versMono`, `depuisMono`).
- **Lecteur** : −15 s / +30 s, reprise de position, MediaSession (écran verrouillé, sauts 15/30 s).
- **Émission absente** (`suggestion`) : message simple, puis l'autre version, une rediffusion présente ou
  l'épisode disponible le plus proche.
- **Playlists** : vues `#listes` et `#l<id>` ; `dispo`, `contexte`, `voisinListe`, `allerDansListe` ; lecture
  enchaînée sur `ended`, émissions absentes sautées, autre version utilisée si elle seule est présente.
- **Vitesse** (dans `vueEpisode`) : le bouton « n× » ouvre un panneau de 9 vitesses (0,6 · 0,7 · 0,75 · 0,8 · 0,85 · 0,9 · 1 ·
  1,25 · 1,5), `preservesPitch` activé. Deux groupes : les émissions du début (n° 1 à `vitN`, saisi dans le panneau ; vide =
  aucun groupe) et les autres. Toucher une vitesse règle celle du groupe de l'émission affichée et referme le panneau.
  Clés `localStorage` : `vit` (autres, 1 par défaut), `vitP` (début, 0,85 par défaut), `vitN`. Par appareil, non synchronisé.
- **Émissions écoutées** (`eco…`) : marquées à la fin de la lecture (`ended`, monologue, original ou playlist), case
  « Écoutée en entier » dans la fiche, ✓ et filtre « Pas encore écoutées » dans le catalogue, section de la page
  Fichiers (synchroniser, exporter, clé). **Synchronisation** (`synchro`) : POST vers `api/ecoutees` après chaque
  changement (délai 1,5 s), au retour du réseau, à l'ouverture et au retour au premier plan. Sans réseau, l'état
  reste dans la page et part plus tard.
- **Vues** : catalogue (`vueListe`), fiche (`vueEpisode`), fichiers (`vueFichiers`), routage par `location.hash`
  dans `afficher`.

## Essais

Dans le dossier du projet, avec Playwright :
- `node essai.js` : import de vrais extraits, lecture, sous-titres, correspondance original/monologue, messages
  d'absence, fonctionnement hors ligne (fenêtre de la taille d'un iPhone SE).
- `node essai_playlist.js <dossier des extraits> <playlist.m3u8>` : import, affichage, enchaînement d'une playlist.
- `node essai_vitesse.js` : vitesses, groupe du début, retenue après rechargement, lecture ralentie, largeur 320 px (sans extraits).
- `node essai_ecoutees.js` : écoutées et synchronisation entre deux « appareils », avec le vrai `api/ecoutees.js` et un
  magasin Blob simulé en mémoire (aucun appel à Vercel ; Playwright suffit, pas d'extraits à fournir).

Les extraits d'essai sont des mp3 tronqués : la fin n'est jamais atteinte, l'essai déclenche `ended` lui-même.
Ces essais tournent sous Chromium ; Safari iOS n'a jamais été testé par Claude (voir « À vérifier »).

## Mettre à jour l'iPhone

Ouvrir la webapp depuis son icône, avec du réseau ; la fermer complètement ; la rouvrir. Si rien ne change, la
connexion Vercel a expiré : ouvrir l'adresse dans Safari, se connecter, recommencer. Ne jamais effacer les
données du site dans les réglages de Safari (les mp3 importés seraient perdus).

## À faire

### Étape 2 du plan général — émissions écoutées partagées avec le site privé : FAIT, mise en service à terminer
Code écrit le 12 novembre, publié le 13 novembre. Détail des décisions de Rémi (stockage Vercel Blob, accès par la
clé du projet, un décochage se propage) : `Darwin/site_construction/PLAN.md`, section « Fait le 12 novembre (étape 2) ».
- Service `site/api/ecoutees.js` : un document JSON dans le magasin Blob privé `darwin-ecoutees`
  (`store_wZ28tDyqq2Pu9PhZ`, relié au projet `darwin-iphone`). Ne contient que des numéros et des dates.
  Les déploiements d'aperçu écrivent dans `essai/ecoutees.json`, jamais dans l'historique réel (`ecoutees.json`).
- Format v2 : `{"format": "darwin-ecoutees", "v": 2, "e": {"188": {"d": "2026-11-12", "m": 1794516394311}}}` ;
  `d` = jour d'écoute ou `null` (décochée), `m` = modification. Importer accepte aussi la v1 (`{"ecoutees": {"188": "2026-11-12"}}`).
- Accès : clé « Protection Bypass for Automation » du projet (Vercel › darwin-iphone › Settings › Deployment
  Protection), passée dans l'adresse de l'appel. Elle n'est écrite dans aucun fichier du dépôt.
- **Reste à faire par Rémi** : coller la clé dans Fichiers › « Clé de synchronisation » sur l'iPhone, et via
  « Clé… » dans le Catalogue du site privé sur le Mac. Tant que ce n'est pas fait : « Pas de synchronisation… ».

### À vérifier sur l'iPhone réel (retours de Rémi attendus)
- connexion Vercel depuis l'icône de l'écran d'accueil (sinon : envisager de lever la protection, le site ne
  contenant que le catalogue et des résumés déjà publics) ;
- commandes de l'écran verrouillé, et enchaînement d'une playlist écran verrouillé ;
- import d'un lot de 5 à 10 mp3 (mémoire et durée) ;
- usage sans réseau.

### Entretien
- Après chaque mise à jour de l'index : refaire `site/catalogue.json`, augmenter `VERSION`, pousser.
- Après `transcrire_monologues.py --nettoyer` puis `construire_lecteur.py` (dossier Darwin) : refaire
  `sous-titres-darwin.ndjson` et le réimporter sur l'iPhone.
- Restes à supprimer sur le Mac si Rémi l'autorise : `essai/st-essai-313.txt`, `essai/st-essai-470.txt`, le
  dossier en double `darwin-iphone/`, `darwin-iphone.zip`, `site/index.html.avant_playlists`.

## Consignes de Rémi

- Garder l'application légère (iPhone SE 2020, stockage limité : jamais tous les fichiers sur l'appareil).
- Messages d'erreur simples, avec une proposition d'autre émission.
- Réponses sobres, peu de compliments. En cas de doute, demander.
