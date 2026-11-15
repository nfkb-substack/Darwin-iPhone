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
non publié) ; elle a été publiée, puis la vitesse de lecture et la vérification de version (`darwin-iphone-7`) ; copie du Mac et dépôt sont alignés.

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
  **Après toute modification de `site/`, augmenter `VERSION`** (actuellement `darwin-iphone-9`, à répercuter dans `VERSION_PAGE` de `site/index.html`). Les appels `/api/`
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
  1,25 · 1,5), `preservesPitch` activé. Deux groupes : les émissions du début (n° 1 à `vitN`, 9 par défaut d'après Rémi : la diction change à partir de la 10e émission ; modifiable dans
  le panneau, vide = aucun groupe) et les autres. Toucher une vitesse règle celle du groupe de l'émission affichée et referme le panneau.
  Clés `localStorage` : `vit` (autres, 1 par défaut), `vitP` (début, 0,85 par défaut), `vitN` (9 par défaut ; 0 = aucun groupe). Par appareil, non synchronisé.
- **Émissions écoutées** (`eco…`) : marquées à la fin de la lecture (`ended`, monologue, original ou playlist), case
  « Écoutée en entier » dans la fiche, ✓ et filtre « Pas encore écoutées » dans le catalogue, section de la page
  Fichiers (synchroniser, exporter, clé). **Synchronisation** (`synchro`) : POST vers `api/ecoutees` après chaque
  changement (délai 1,5 s), au retour du réseau, à l'ouverture et au retour au premier plan. Sans réseau, l'état
  reste dans la page et part plus tard.
- **Étiquettes et signalements** (`etq…`, mémoire `darwin-etiq1`) : « Thème difficile » et « Mauvaise qualité audio » (cases de la
  fiche, pastilles et filtres du catalogue, compte dans Fichiers) ; **drapeau ⚐/⚑** en haut à droite de chaque phrase du texte
  pour signaler une erreur de transcription. Le drapeau est un pseudo-élément CSS `#st p::after` : le DOM, le texte copié et l'ordre
  des `<p>` (`#st` enfant i+1) ne changent pas ; un toucher dans le coin (40 px, haut droit de la phrase) signale sans déplacer
  l'audio, ailleurs le toucher emmène l'audio comme avant. Synchronisés comme les écoutées, **sans texte** : clé `n°:indice` + instant `t`.
- **Texte synchronisé** (`majLecteur`, `recaler`) : la phrase surlignée est celle dont le début précède `versMono(currentTime)`.
  Recalé à chaque `play` (le texte revient à la phrase lue), au retour au premier plan et à `pageshow` (iOS fige la page :
  le surlignement pouvait rester sur l'ancienne phrase). Un toucher sur une phrase déplace l'audio, sauf s'il y avait une
  sélection avant le toucher ou s'il dure plus de 500 ms (sélection / copie de texte). Signalé le 15 novembre : décalages
  après une pause ou une copie de texte ; causes probables traitées ici, **non reproduites sur iPhone réel**.
- **Version / mise à jour** (`majApp`, page Fichiers) : affiche `VERSION_PAGE` et compare avec `sw.js` du serveur ; dit si le
  serveur refuse l'accès (connexion Vercel expirée), si une version plus récente est disponible (`reg.update()`).
  **Piège connu** : la page s'ouvre depuis la réserve, donc sans jamais redemander la connexion Vercel ; si le cookie
  de l'app de l'écran d'accueil a expiré, elle reste sur son ancienne version sans message (constaté le 13 novembre).
- **Vues** : catalogue (`vueListe`), fiche (`vueEpisode`), fichiers (`vueFichiers`), routage par `location.hash`
  dans `afficher`.

## Essais

Dans le dossier du projet, avec Playwright :
- `node essai.js` : import de vrais extraits, lecture, sous-titres, correspondance original/monologue, messages
  d'absence, fonctionnement hors ligne (fenêtre de la taille d'un iPhone SE).
- `node essai_playlist.js <dossier des extraits> <playlist.m3u8>` : import, affichage, enchaînement d'une playlist.
- `node essai_texte.js` : sélection sans déplacer l'audio, reprise après pause, retour au premier plan (40 phrases, wav factice).
- `node essai_vitesse.js` : vitesses, groupe du début, retenue après rechargement, lecture ralentie, vérification de version, largeur 320 px (sans extraits).
- `node essai_etiquettes.js` : cases, pastilles, filtres, drapeau (audio inchangé, texte inchangé, copie sans symbole), synchro, export/import.
- `node essai_prive.js` : mêmes contrôles sur le site privé (voir l'en-tête du fichier pour la copie de test).
- `node essai_ecoutees.js` : écoutées et synchronisation entre deux « appareils », avec le vrai `api/ecoutees.js` et un
  magasin Blob simulé en mémoire (aucun appel à Vercel ; Playwright suffit, pas d'extraits à fournir).

Les extraits d'essai sont des mp3 tronqués : la fin n'est jamais atteinte, l'essai déclenche `ended` lui-même.
Ces essais tournent sous Chromium ; Safari iOS n'a jamais été testé par Claude (voir « À vérifier »).

## Mettre à jour l'iPhone

Ouvrir la webapp depuis son icône, avec du réseau ; la fermer complètement ; la rouvrir. Si rien ne change, la
connexion Vercel a expiré : ouvrir l'adresse dans Safari, se connecter, recommencer. Ne jamais effacer les
données du site dans les réglages de Safari (les mp3 importés seraient perdus).

## À faire

### Point d'étape du 15 novembre 2026 au soir — reprendre ici
**Fait aujourd'hui** (app version 9 en ligne, site privé reconstruit, outils sur le Mac) : étiquettes « difficile » / « mauvaise qualité » et drapeaux de
phrase synchronisés ; conversion CBR de 51 mp3 ; `signalements.py`, `corriger.py`, `retelecharger.py` (corrigé : la relance passe aux suivantes, dossier affiché).

**Retéléchargement des mauvaises qualités.** Rémi a étiqueté 34–41. Inventaire des 593 originaux (`outils/analyse_originaux/`) : 326 stéréo 44,1 kHz,
252 stéréo 48 kHz, 11 mono 44,1 kHz avec souffle plat vers −21 dB de 14 à 20 kHz (30–38, 42, 43), 4 à 16 kHz mono coupés vers 5,75 kHz (39, 40, 41 à 24 kb/s ; 60 à 16 kb/s).
Candidats non étiquetés : 30, 31, 32, 33, 42, 43, 60 (et 220, un peu faible en dynamique). Les nouveaux fichiers Radio France sont propres (stéréo 44,1 kHz 128 kb/s, sans souffle).
Téléchargés dans `Darwin/_retelechargement_20261115/` : 30 à 43 et 60 (tous). Comparaison faite avec `outils/analyse_originaux/cmp.py` (voir `LISEZMOI.txt`).
Résultat pour les cinq derniers, **en attente de décision de Rémi** : 41 et 42 alignés à 0,0 s, 60 à −0,2 s (60 : le monologue est un lien dur vers l'original, à refaire en lien) ; 40 et 41 n'ont ni monologue ni texte (rediffusions) donc aucune contrainte ; 40 : nouveau = ancien −8,7 s puis −10,7 s (sans conséquence faute de texte) ; 43 : nouveau = ancien −3,5 s sur tout le fichier (l'ancien commence par 3,5 s de bande-annonce « A suivre sur les épaules de Darwin avec », première phrase du .srt) et +7 s en fin : monologue refaisable avec les coupes décalées de −3,5 s et 3,5 s de silence au début, la première phrase du texte devenant un fantôme à supprimer.



**Remplacés le 15 novembre : 32, 33, 38, 39** (nouvel audio aligné sur l'ancien à 0,5 s près, sous-titres inchangés). Anciens fichiers, anciens monologues et caches de coupes
dans `Darwin/_avant_remplacement_20261115/` (journal et `refaire_monologues.py` dedans). Nouveaux originaux = audio Radio France + étiquettes et pochette de l'ancien fichier.
Monologues 32, 33, 38 refaits avec exactement les mêmes coupes, en CBR 128 kb/s avec entête Info. 33 : 37 s ajoutées en fin chez Radio France, écartées. 39 : pas de monologue
(rediffusion non traitée), seul l'original change.

**Pas touchés, décision à prendre** — la nouvelle version contient des blocs absents de l'ancienne, donc les sous-titres glisseraient après le bloc :
| n° | bloc ajouté dans la NOUVELLE version (de … à …) |
|---|---|
| 30 | 104 s, de 42:29 à 44:13, puis +43 s en fin de fichier |
| 31 | 3 s, de 19:59 à 20:02 (suite décalée de 2,3 s), +42 s en fin |
| 34 | 26 s, de 43:50 à 44:16 |
| 36 | début décalé de −5 s, 131 s de 44:04 à 46:15 |
| 37 | 45 s, de 47:05 à 47:50, +26 s en fin |
| 35 | la nouvelle version ne dure que 26,6 min (première moitié seulement) : ne pas remplacer |
Instants lus par corrélation d'enveloppe (temps de la nouvelle version, `_retelechargement_20261115/`) : écouter ces plages pour savoir si c'est une annonce, une chronique ou du contenu manquant
à l'ancienne. Si c'est du contenu à garder : refaire monologue, transcription et sous-titres de l'épisode ; sinon, couper le bloc dans le nouvel original avant d'en refaire le monologue.

**À faire sur l'iPhone et le Mac** : réimporter dans l'app les monologues 32, 33, 38 (nouveaux) et les 51 fichiers réencodés en CBR ; coller la clé de synchronisation sur le site privé du Mac
si ce n'est pas fait ; réimporter `sous-titres-darwin.ndjson` seulement après une correction de texte (`corriger.py`).

**Propositions en attente de Rémi** : fichier d'import qui étiquette 30, 31, 32, 33, 42, 43, 60 en « mauvaise qualité » (32 et 33 sont maintenant réglés) ; suppression de `Darwin-iPhone/mp3-cbr/` (96 Mo, essai CBR, nécessite
l'autorisation de supprimer) ; sous-titres et `_retelechargement_20261115/` à garder jusqu'à la fin des comparaisons.

### Étape 2 du plan général — émissions écoutées partagées avec le site privé : FAIT, mise en service à terminer
Code écrit le 12 novembre, publié le 13 novembre. Détail des décisions de Rémi (stockage Vercel Blob, accès par la
clé du projet, un décochage se propage) : `Darwin/site_construction/PLAN.md`, section « Fait le 12 novembre (étape 2) ».
- Service `site/api/ecoutees.js` : un document JSON dans le magasin Blob privé `darwin-ecoutees`
  (`store_wZ28tDyqq2Pu9PhZ`, relié au projet `darwin-iphone`). Ne contient que des numéros et des dates.
  Les déploiements d'aperçu écrivent dans `essai/ecoutees.json`, jamais dans l'historique réel (`ecoutees.json`).
- Format v2 : `{"format": "darwin-ecoutees", "v": 2, "e": {"188": {"d": "2026-11-12", "m": 1794516394311}}}` ;
  `d` = jour d'écoute ou `null` (décochée), `m` = modification. Depuis la version 9, sections **facultatives** de même forme :
  `difficile` et `qualite` (clé = n°), `err` (clé = `"n°:indice de phrase"`, + `t` = instant de la phrase). `v` reste 2 : un ancien
  client qui n'envoie que `e` ne fait rien perdre aux autres sections (`fusionPlus` dans `_fusion.js`). Importer accepte aussi la v1 (`{"ecoutees": {"188": "2026-11-12"}}`).
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

### Décalage après un saut en arrière (traité le 15 novembre ; à confirmer sur l'iPhone)
Cause : certains mp3 sont en **VBR** (80–128 kbit/s, entête Xing). Un saut (`currentTime`) dans un VBR passe par la table Xing (résolution 1 %) :
erreur de −1,4 s en moyenne, jusqu'à 6 s ; le surlignement suit `currentTime`, donc il est juste mais l'audio est ailleurs. Les mp3 en CBR
128 kbit/s avec entête Info sont exacts.
Traitement : `outils/cbr.py` (détecte les VBR par les débits des trames sur deux fenêtres, réencode en CBR 128 kbit/s avec
`-write_xing 1`, vérifie durée à 0,2 s, débit unique, entête Info, pochette ; range l'original dans `Darwin/_avant_cbr_AAAAMMJJ/` et remplace
le fichier sous le même nom). Fait le 15 novembre : **51 fichiers** (monologues 1–16, 20–22, 24–29 ; originaux 1–16, 20–29), 0 échec,
journal dans `_avant_cbr_20261115/journal.txt`. Les autres (CBR 128 sans entête pour 388 d'entre eux : l'iPhone estime alors la durée d'après
la taille, étiquette de pochette comprise, +9 à +15 s) n'ont pas été touchés. **Les fichiers réencodés doivent être réimportés sur l'iPhone**
(Fichiers › importer) pour remplacer les anciens. Dans la VM de l'espace de travail, un appel `device_bash` ne dépasse pas ~120 s et ses
processus sont coupés à la fin : lancer `cbr.py --appliquer --max 6` plusieurs fois (idempotent).

### Retélécharger les mp3 de mauvaise qualité et relire les signalements (outils du Mac, version 9)
- `outils/retelecharger.py` : numéros pris dans l'étiquette « Mauvaise qualité audio » (`--export darwin-ecoutees.json`, ou `--service CLE`, ou à la main) ;
  liens Radio France de `site/catalogue.json` (extracteur yt-dlp `FranceCultureIE`, motif `…/podcasts/<émission>/<titre>-<id>`) ; télécharge dans
  un **nouveau** dossier `Darwin/_retelechargement_AAAAMMJJ/` sous le nom de l'original actuel, compare durée / débit / VBR, écrit `rapport.txt`.
  Ne remplace rien. À lancer sur le Mac (radiofrance.fr est refusé depuis l'espace de travail de Claude : 403). Sans `--telecharger` : liste seulement.
  Exécuté contre Radio France le 15 novembre (30 à 39 téléchargés ; relance corrigée : `--max` ne compte que les fichiers restants). Le fichier téléchargé est un original : le monologue se refait ensuite (`monologue_seul.py`) ; le texte reste valable si le nouvel audio est aligné sur l'ancien (sinon voir le point d'étape).
- `outils/signalements.py` : lit `--export` ou `--service`, retrouve les phrases dans `sous-titres-darwin.ndjson` (local), les affiche avec la phrase
  avant et après, écrit `signalements.txt` (ignoré par git). Le service ne contient jamais le texte.
- `outils/corriger.py` : passe sur les phrases signalées une à une (`--export fichier.json` ou `--service CLE`). Affiche n° d'émission, titre, **instant dans le
  monologue et dans l'original** (avec les coupes de `lecteur/<n>.js`), 2 phrases de contexte avant/après (`c` : 6). Commandes : Entrée passer, `e` réécrire la
  phrase (pré-remplie seulement avec GNU readline ; `libedit` du Mac l'ignore), `/ancien/nouveau/`, `=` phrase juste, `q`. Modifie `Transcripts/<n>-monologue-….srt`
  (mêmes indices que le site : tri par début, blocs vides ignorés ; BOM et fins de ligne conservés) et la ligne identique du `.txt` si unique, jamais le nombre de
  phrases. Copie préalable dans `Transcripts/_avant_corrections_AAAAMMJJ/`, journal `Darwin-iPhone/corrections_AAAAMMJJ.txt` (local). Retire les drapeaux traités
  (POST `err` avec `d: null` si clé, sinon `darwin-ecoutees-corrections.json` à importer), puis relance `construire_lecteur.py --n …` et `sous_titres.py` **sans numéro**
  (avec des numéros il réécrit le .ndjson avec ces seuls épisodes). Reste à réimporter le .ndjson dans l'app. Testé sur données fictives, pas sur les vrais `.srt`.
- Site public (index Darwin) : pas de lecteur ni de texte, donc ni étiquettes ni drapeau ; ils existent dans la webapp et le site privé.

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
