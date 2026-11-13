# Darwin-iPhone

Webapp légère pour écouter « Sur les épaules de Darwin » sur un iPhone, sans réseau : catalogue des émissions,
résumé, lecteur (−15 s / +30 s, vitesse, reprise de position, commandes de l'écran verrouillé), pochette et notes
du fichier, sous-titres qui suivent la lecture (toucher une phrase pour y aller).

Projet **séparé** de l'index (dossier Darwin, dépôt darwin-index, projet Vercel darwin-index).
Pour reprendre le développement dans une nouvelle conversation : lire `METHODE.md`.

## Ce qui est en ligne, ce qui ne l'est pas

- En ligne (dossier `site/`) : la page, le catalogue et les résumés des fiches (déjà publics). Aucun texte transcrit.
- Sur le Mac et l'iPhone seulement : les mp3 et `sous-titres-darwin.ndjson` (texte des émissions).

## Utilisation sur l'iPhone

1. Ouvrir l'adresse de la webapp dans Safari, puis Partager › « Sur l'écran d'accueil » (le stockage d'une page
   ouverte depuis l'écran d'accueil n'est pas vidé par iOS au bout de quelques jours).
2. Envoyer sur l'iPhone (AirDrop, iCloud Drive, câble) les mp3 voulus et, une fois, `sous-titres-darwin.ndjson`.
3. Dans la webapp : Fichiers › « Importer des fichiers… ». Les mp3 sont reconnus à leur nom
   (`313-monologue-….mp3`, `313-original-….mp3`) et rangés en deux rayons. Ils sont copiés dans le stockage de la
   page : on peut ensuite les supprimer de l'app Fichiers.
4. Une émission absente affiche un message et propose l'autre version, la même émission sous un autre numéro
   (rediffusion) ou l'épisode disponible le plus proche.

## Playlists

Les playlists `.m3u8` créées par l'index Darwin (trajet, thème, saison) s'importent comme les autres fichiers
(Catalogue › Playlists, ou Fichiers). Chaque ligne est reconnue au nom du mp3 (`313-monologue-….mp3`), quel que
soit le dossier indiqué. Les émissions s'enchaînent dans l'ordre ; une émission absente de l'iPhone est sautée, et
si seule l'autre version (original / monologue) est présente, c'est elle qui est lue.

## Vitesse de lecture

Le bouton de vitesse (à droite de +30 s) ouvre le choix : 0,6×, 0,7×, 0,75×, 0,8×, 0,85×, 0,9×, 1×, 1,25×, 1,5× (la voix
ralentit sans devenir grave). Les premières émissions, dont la diction diffère, peuvent avoir leur propre vitesse :
saisir dans le panneau « jusqu'au n° … » ; la vitesse choisie s'applique alors à ce groupe, l'autre garde la sienne.

## Émissions écoutées

Une émission est marquée « écoutée en entier » quand la lecture atteint la fin ; la case de la fiche permet de la
cocher ou décocher à la main. Le catalogue affiche un ✓ et un filtre « Pas encore écoutées ». L'historique est
synchronisé avec le site privé du Mac par un petit service du même projet (`site/api/ecoutees.js`, numéros et dates
seulement). La clé du projet se colle une fois dans Fichiers › « Clé de synchronisation ». Sans réseau, rien ne se
perd : la synchronisation se fait au retour. « Exporter » produit `darwin-ecoutees.json`, qui s'importe comme les
autres fichiers (et dans le site privé).

## Mise à jour

- Catalogue : `python3 outils/catalogue.py <labo_data.json> site/catalogue.json` (après une mise à jour de l'index).
- Sous-titres : sur le Mac, `python3 outils/sous_titres.py` (lit `../lecteur/*.js` du dossier Darwin), puis
  réimporter le fichier sur l'iPhone.
- Après toute modification de `site/`, augmenter `VERSION` dans `site/sw.js`.

## Essais

`node essai.js` (Playwright) : import de vrais extraits, lecture, sous-titres, messages d'absence, hors ligne.
`node essai_playlist.js <dossier des extraits> <playlist.m3u8>` : import, affichage et enchaînement d'une playlist.
`node essai_vitesse.js` : vitesses de lecture et groupe des premières émissions (sans extraits).
`node essai_ecoutees.js` : émissions écoutées et synchronisation entre deux appareils (magasin simulé, sans Vercel).
