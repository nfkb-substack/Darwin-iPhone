#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retélécharge depuis Radio France (avec yt-dlp) les émissions marquées « mauvaise qualité audio ».

Les numéros viennent de l'étiquette de l'appli (synchronisée), de plusieurs façons :
    python3 retelecharger.py --export ~/Downloads/darwin-ecoutees.json        fichier produit par « Exporter » (webapp ou site privé)
    python3 retelecharger.py --service CLE                                    ou : variable DARWIN_SYNC_KEY ; lit le service de synchronisation
    python3 retelecharger.py 12 45 245                                        ou numéros donnés à la main

Sans --telecharger : liste seulement (numéro, titre, lien, fichier actuel). Avec --telecharger : chaque émission est téléchargée
dans un NOUVEAU dossier <Darwin>/_retelechargement_AAAAMMJJ/, sous le nom du fichier « original » actuel (ou N-original-date-titre.mp3),
puis comparée à l'actuelle (durée, débit, VBR/CBR). Rien n'est remplacé : après comparaison à l'écoute, c'est vous qui
rangez le bon fichier dans original/. Le monologue (sans la musique) et ses sous-titres se refont ensuite avec monologue_seul.py.

Le script s'exécute sur le Mac (accès à radiofrance.fr), pas dans l'espace de travail de Claude. Prérequis : pip install -U yt-dlp ;
ffprobe (ffmpeg) pour la comparaison. Les liens viennent de site/catalogue.json (colonne « u »).
"""
import argparse, datetime, glob, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
try:
    import cbr
except Exception:      # comparaison VBR/CBR facultative
    cbr = None


def numeros_export(chemin):
    j = json.load(open(os.path.expanduser(chemin), encoding='utf-8'))
    if not isinstance(j, dict) or j.get('format') != 'darwin-ecoutees':
        sys.exit("%s n'est pas un fichier darwin-ecoutees.json" % chemin)
    return {int(n) for n, x in (j.get('qualite') or {}).items() if isinstance(x, dict) and x.get('d') and re.fullmatch(r'\d{1,5}', n)}


def numeros_service(cle):
    url = 'https://darwin-iphone.vercel.app/api/ecoutees?x-vercel-protection-bypass=' + cle
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'darwin-retelecharger'}), timeout=30) as r:
        j = json.load(r)
    return {int(n) for n, x in (j.get('qualite') or {}).items() if x.get('d')}


def commande_ytdlp():
    if os.environ.get('YTDLP'):
        return os.environ['YTDLP'].split()
    if shutil.which('yt-dlp'):
        return ['yt-dlp']
    r = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'], capture_output=True)
    if r.returncode == 0:
        return [sys.executable, '-m', 'yt_dlp']
    sys.exit("yt-dlp est introuvable. Installez-le : pip3 install -U yt-dlp")


def nom_cible(n, e, darwin):
    """Nom du fichier : celui de l'original actuel s'il existe, sinon N-original-AAAA-MM-JJ-titre.mp3 (titre = fin du lien)."""
    actuels = sorted(glob.glob(str(darwin / 'original' / ('%d-original-*.mp3' % n))))
    if actuels:
        return Path(actuels[0]).name, actuels[0]
    slug = re.sub(r'-\d{6,}$', '', e['u'].rstrip('/').rsplit('/', 1)[-1])
    return '%d-original-%s-%s.mp3' % (n, e['d'], slug), None


def sonde(chemin):
    """(durée en s, débit moyen en kbit/s, VBR ?) ; valeurs None si ffprobe manque."""
    d = b = None
    if shutil.which('ffprobe'):
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate', '-of', 'json', str(chemin)], capture_output=True, text=True)
        try:
            f = json.loads(r.stdout)['format']; d = float(f['duration']); b = int(f['bit_rate']) // 1000
        except Exception:
            pass
    v = None
    if cbr:
        try:
            v = cbr.analyse(str(chemin))[0]
        except Exception:
            pass
    return d, b, v


def resume(x):
    d, b, v = x
    return '%s, %s kbit/s, %s' % ('%d:%02d' % divmod(round(d), 60) if d else '?', b if b else '?', 'VBR' if v else 'CBR' if v is not None else '?')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('numeros', nargs='*', type=int, help="numéros d'émission")
    ap.add_argument('--export', help='fichier darwin-ecoutees.json (« Exporter »)')
    ap.add_argument('--service', metavar='CLE', nargs='?', const=os.environ.get('DARWIN_SYNC_KEY', ''), help='lire les étiquettes sur le service de synchronisation (clé, ou DARWIN_SYNC_KEY)')
    ap.add_argument('--darwin', default=str(ICI.parents[1]), help='dossier Darwin (contient original/ et Darwin-iPhone/)')
    ap.add_argument('--telecharger', action='store_true', help='télécharger (sinon : liste seulement)')
    ap.add_argument('--max', type=int, default=10, help='au plus N émissions par lancement (défaut 10)')
    ap.add_argument('--pause', type=float, default=5, help='secondes entre deux téléchargements (défaut 5)')
    ap.add_argument('--dossier', help='dossier de destination (défaut : <Darwin>/_retelechargement_AAAAMMJJ)')
    a = ap.parse_args()
    darwin = Path(a.darwin).expanduser()
    nums = set(a.numeros)
    if a.export: nums |= numeros_export(a.export)
    if a.service is not None:
        if not a.service: sys.exit("--service demande la clé de synchronisation (ou la variable DARWIN_SYNC_KEY)")
        nums |= numeros_service(a.service)
    if not nums:
        sys.exit("Aucun numéro : donnez-en, ou --export fichier.json, ou --service CLE.")
    cat = {e['n']: e for e in json.load(open(ICI.parent / 'site' / 'catalogue.json', encoding='utf-8'))['eps']}
    dest = Path(a.dossier).expanduser() if a.dossier else darwin / ('_retelechargement_' + datetime.date.today().strftime('%Y%m%d'))
    liste = sorted(nums)
    print('%d émission(s) :' % len(liste))
    a_faire = []
    for n in liste:
        e = cat.get(n)
        if not e or not e.get('u'):
            print('  n° %-4d  pas de lien Radio France dans le catalogue : à chercher à la main' % n); continue
        nom, actuel = nom_cible(n, e, darwin)
        print('  n° %-4d  %s\n           %s\n           fichier actuel : %s' % (n, e['t'], e['u'], actuel and Path(actuel).name or 'aucun original dans original/'))
        a_faire.append((n, e, nom, actuel))
    if not a.telecharger:
        print('\n(liste seulement ; ajouter --telecharger pour télécharger dans %s)' % dest); return
    if not a_faire: return
    yt = commande_ytdlp(); dest.mkdir(parents=True, exist_ok=True)
    print('\nDossier de destination : %s\n(à côté de original/ et monologue/, pas dedans ; rien n\'est remplacé)' % dest.resolve())
    # Les émissions déjà présentes dans le dossier ne comptent pas dans le lot : la relance passe aux suivantes.
    deja = [x for x in a_faire if (dest / x[2]).exists()]
    restantes = [x for x in a_faire if not (dest / x[2]).exists()]
    lot = restantes[:a.max]
    print('%d déjà téléchargée(s), %d à faire, %d cette fois.' % (len(deja), len(restantes), len(lot)))
    rapport = []
    for k, (n, e, nom, actuel) in enumerate(lot):
        if k: time.sleep(a.pause)
        sortie = dest / nom
        print('n° %d : téléchargement…' % n, flush=True)
        r = subprocess.run(yt + ['--no-playlist', '--no-overwrites', '--no-warnings', '-q', '-o', str(dest / (Path(nom).stem + '.%(ext)s')), e['u']], capture_output=True, text=True)
        fichiers = [f for f in dest.glob(glob.escape(Path(nom).stem) + '.*') if not f.name.endswith(('.part', '.ytdl'))]
        if r.returncode or not fichiers:
            ligne = 'n° %d : ÉCHEC (%s)' % (n, (r.stderr.strip().splitlines() or ['pas de fichier'])[-1][:150]); print(ligne); rapport.append(ligne); continue
        nouveau = fichiers[0]
        if nouveau.name != nom: nouveau = nouveau.rename(dest / (Path(nom).stem + nouveau.suffix))
        nv = sonde(nouveau); an = sonde(actuel) if actuel else (None, None, None)
        diff = ''
        if nv[0] and an[0] and abs(nv[0] - an[0]) > 1.5:
            diff = ' — durée différente de %+.1f s : autre version du fichier (coupes, jingle) : le monologue et le texte actuels ne correspondraient plus ; écouter avant de remplacer' % (nv[0] - an[0])
            if nv[0] < 0.8 * an[0]:
                diff += ' ; BEAUCOUP plus court : téléchargement incomplet ou découpage différent'
        ligne = 'n° %d : %s\n    actuel  : %s\n    nouveau : %s%s' % (n, nouveau.name, resume(an) if actuel else '—', resume(nv), diff)
        print(ligne); rapport.append(ligne)
    if len(restantes) > len(lot): print('\n%d émission(s) restent : relancer la même commande (celles déjà téléchargées sont sautées).' % (len(restantes) - len(lot)))
    elif restantes or deja: print('\nTout est téléchargé.')
    if rapport:
        with open(dest / 'rapport.txt', 'a', encoding='utf-8') as f:      # ajoute : un lancement ne perd pas le rapport du précédent
            f.write('— %s\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + '\n'.join(rapport) + '\n\n')
        print('\nRapport : %s\nFichiers : %s' % (dest.resolve() / 'rapport.txt', dest.resolve()))


if __name__ == '__main__':
    main()
