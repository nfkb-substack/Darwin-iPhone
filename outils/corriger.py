#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige, une par une, les phrases du texte signalées par le drapeau ⚑ (webapp ou site privé).

    python3 corriger.py ~/Downloads/darwin-ecoutees.json        fichier produit par « Exporter »
    python3 corriger.py --service CLE                           ou variable DARWIN_SYNC_KEY : lit (et met à jour) le service de synchronisation

Pour chaque phrase, le script donne le n° d'émission, le titre et l'INSTANT dans le monologue (et dans l'original, quand l'émission
a des coupes) : vous écoutez à cet instant, avec le contexte autour, puis vous corrigez.

    Entrée       passer (le drapeau reste)
    e            réécrire la phrase entière (texte pré-rempli et modifiable si le terminal le permet ; sinon : copier, corriger, coller)
    /ancien/nouveau/   remplacer un mot ou un groupe de mots dans la phrase
    =            la phrase est juste : retirer le drapeau sans rien changer
    c            plus de contexte (6 phrases avant et après)
    q            quitter (tout ce qui est fait est conservé)

Ce que le script fait : modifie Transcripts/<n>-monologue-….srt (et le .txt voisin quand la phrase s'y retrouve), sans jamais ajouter,
supprimer ni fusionner de phrase (les indices des drapeaux restent donc valables). Chaque fichier est d'abord copié dans
Transcripts/_avant_corrections_AAAAMMJJ/. Les corrections sont consignées dans Darwin-iPhone/corrections_AAAAMMJJ.txt (local).
Les drapeaux traités sont retirés : sur le service si la clé est donnée, sinon par un fichier darwin-ecoutees-corrections.json à
importer dans l'app ou le site privé (« Importer »). À la fin : construire_lecteur.py (site privé) puis sous_titres.py (iPhone) sont relancés ;
il reste à réimporter sous-titres-darwin.ndjson dans l'app (Fichiers).
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import signalements

HORAIRE = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{1,3})")
try:
    import readline
except ImportError:
    readline = None
# Le pré-remplissage de la ligne n'est fiable qu'avec GNU readline ; libedit (Python du Mac) l'ignore : on le désactive alors.
PREREMPLIR = bool(readline) and "libedit" not in (readline.__doc__ or "")


def secondes(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def hms(t):
    t = int(t)
    return "%d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60)


class Srt:
    """Un .srt lu comme construire_lecteur.py : phrases triées par début, blocs sans texte ignorés (mêmes indices que le site)."""
    def __init__(self, chemin):
        brut = Path(chemin).read_bytes().decode("utf-8")
        self.bom = brut.startswith("﻿")
        self.crlf = "\r\n" in brut
        self.chemin = Path(chemin)
        texte = brut.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
        self.morceaux = re.split(r"(\n\s*\n)", texte)      # blocs aux indices pairs, séparateurs aux impairs
        cues = []
        for k in range(0, len(self.morceaux), 2):
            lignes = [l for l in self.morceaux[k].split("\n") if l.strip()]
            for j, l in enumerate(lignes):
                m = HORAIRE.search(l)
                if m:
                    t = re.sub(r"\s+", " ", " ".join(lignes[j + 1:])).strip()
                    if t:
                        cues.append((secondes(*m.group(1, 2, 3, 4)), secondes(*m.group(5, 6, 7, 8)), t, k))
                    break
        self.cues = sorted(cues, key=lambda c: c[0])         # tri stable, comme construire_lecteur.py

    def remplacer(self, i, nouveau):
        k = self.cues[i][3]
        lignes = self.morceaux[k].split("\n")
        for j, l in enumerate(lignes):
            if HORAIRE.search(l):
                self.morceaux[k] = "\n".join(lignes[:j + 1] + [nouveau])
                break
        a, b, _, kk = self.cues[i]
        self.cues[i] = (a, b, nouveau, kk)

    def ecrire(self):
        texte = "".join(self.morceaux)
        if self.crlf:
            texte = texte.replace("\n", "\r\n")
        self.chemin.write_bytes((("﻿" if self.bom else "") + texte).encode("utf-8"))


def raccords(darwin, n):
    """Coupes de l'original, [[instant du raccord dans le monologue, secondes retirées]] ; [] si pas de données."""
    f = darwin / "lecteur" / ("%d.js" % n)
    try:
        m = re.search(r"DARWIN_LEC\[\d+\]=(\{.*\});\s*$", f.read_text(encoding="utf-8"), re.S)
        return json.loads(m.group(1)).get("o", []) if m else []
    except (OSError, ValueError):
        return []


def vers_original(t, o):
    return t + sum(r for m, r in o if m <= t)


def montre(srt, i, o, large=False):
    pas = 6 if large else 2
    for j in range(max(0, i - pas), min(len(srt.cues), i + pas + 1)):
        a, _, t, _ = srt.cues[j]
        print("   %s %6s  %s" % ("⚑" if j == i else " ", hms(a), t))


def saisir(invite, prerempli=""):
    if PREREMPLIR and prerempli:
        readline.set_startup_hook(lambda: readline.insert_text(prerempli))
    try:
        return input(invite)
    finally:
        if readline:
            readline.set_startup_hook(None)


def sauvegarde(dossier, fichier, vus):
    if fichier in vus:
        return
    vus.add(fichier)
    dest = dossier / ("_avant_corrections_" + datetime.date.today().strftime("%Y%m%d"))
    dest.mkdir(exist_ok=True)
    if not (dest / fichier.name).exists():
        shutil.copy2(fichier, dest / fichier.name)


def maj_txt(srt_chemin, ancien, nouveau, vus, dossier):
    """Le .txt voisin porte une phrase par ligne : on remplace la ligne identique à l'ancienne phrase, si elle est unique."""
    txt = srt_chemin.with_suffix(".txt")
    if not txt.is_file():
        return "pas de .txt"
    brut = txt.read_bytes().decode("utf-8")
    lignes = brut.split("\n")
    cibles = [k for k, l in enumerate(lignes) if re.sub(r"\s+", " ", l).strip() == ancien]
    if len(cibles) != 1:
        return ".txt non modifié (%s)" % ("phrase introuvable" if not cibles else "phrase en %d exemplaires" % len(cibles))
    sauvegarde(dossier, txt, vus)
    fin = "\r" if lignes[cibles[0]].endswith("\r") else ""
    lignes[cibles[0]] = nouveau + fin
    txt.write_bytes("\n".join(lignes).encode("utf-8"))
    return ".txt mis à jour"


def retirer_drapeaux(cles, cle_service, hors_ligne_json):
    """Marque les drapeaux comme retirés (d = null, modification la plus récente) : sur le service, ou dans un fichier à importer."""
    if not cles:
        return
    m = int(time.time() * 1000)
    doc = {"format": "darwin-ecoutees", "v": 2, "e": {}, "err": {c: {"d": None, "m": m, "t": t} for c, t in cles.items()}}
    if cle_service:
        url = os.environ.get("DARWIN_SYNC_URL", "https://darwin-iphone.vercel.app/api/ecoutees") + "?x-vercel-protection-bypass=" + cle_service
        try:
            req = urllib.request.Request(url, data=json.dumps(doc).encode(), headers={"content-type": "text/plain", "User-Agent": "darwin-corriger"}, method="POST")
            urllib.request.urlopen(req, timeout=30).read()
            print("  %d drapeau(x) retiré(s) sur le service de synchronisation." % len(cles))
            return
        except Exception as e:
            print("  Service injoignable (%s) : drapeaux écrits dans un fichier à importer." % e)
    hors_ligne_json.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  %d drapeau(x) à retirer : importez %s dans l'app (Fichiers) et dans le site privé (Importer)." % (len(cles), hors_ligne_json))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", nargs="?", help="fichier darwin-ecoutees.json (« Exporter »)")
    ap.add_argument("--service", metavar="CLE", nargs="?", const=os.environ.get("DARWIN_SYNC_KEY", ""), help="lire / mettre à jour le service (clé, ou DARWIN_SYNC_KEY)")
    ap.add_argument("--darwin", default=str(ICI.parents[1]), help="dossier Darwin (contient Transcripts/ et lecteur/)")
    ap.add_argument("--n", help="ne traiter que ces émissions (ex. 313,18)")
    ap.add_argument("--sans-regeneration", action="store_true", help="ne pas relancer construire_lecteur.py et sous_titres.py à la fin")
    a = ap.parse_args()
    darwin = Path(a.darwin).expanduser()
    textes = darwin / "Transcripts"
    if a.service is not None:
        if not a.service:
            sys.exit("--service demande la clé de synchronisation (ou la variable DARWIN_SYNC_KEY)")
        sig = signalements.lire_signalements(["--service", a.service])
    elif a.export:
        sig = signalements.lire_signalements([a.export])
    else:
        sys.exit(__doc__)
    if a.n:
        sig = {n: v for n, v in sig.items() if n in {int(x) for x in a.n.split(",")}}
    if not sig:
        print("Aucune phrase signalée."); return
    if not textes.is_dir():
        sys.exit("Dossier introuvable : %s" % textes)
    try:
        cat = {e["n"]: e for e in json.load(open(ICI.parent / "site" / "catalogue.json", encoding="utf-8"))["eps"]}
    except Exception:
        cat = {}
    jour = datetime.date.today().strftime("%Y%m%d")
    journal = ICI.parent / ("corrections_%s.txt" % jour)
    total = sum(len(v) for v in sig.values())
    print("%d phrase(s) signalée(s) dans %d émission(s).\n" % (total, len(sig)))
    sauvegardes, retirer, modifies, fait, quitter = set(), {}, set(), 0, False
    for n in sorted(sig):
        fichiers = sorted(f for f in textes.iterdir() if re.match(r"^%d-monologue-.+\.srt$" % n, f.name, re.I))
        titre = cat.get(n, {}).get("t", "")
        print("═" * 72 + "\nÉmission n° %d%s\n%s" % (n, " — " + titre if titre else "", fichiers[0].name if fichiers else ""))
        if not fichiers:
            print("  Pas de .srt « %d-monologue-… » dans %s : émission ignorée." % (n, textes)); continue
        srt, o = Srt(fichiers[0]), raccords(darwin, n)
        for i, x in sorted(sig[n]):
            if i >= len(srt.cues):
                print("\n  phrase %d : n'existe plus dans le .srt (%d phrases) : ignorée." % (i, len(srt.cues))); continue
            a0 = srt.cues[i][0]
            alerte = x.get("t") is not None and abs(a0 - x["t"]) > 2
            while True:
                orig = "   (original : %s)" % hms(vers_original(a0, o)) if o else ""
                print("\n── n° %d · phrase %d · monologue %s%s%s" % (n, i, hms(a0), orig, "  ⚠ instant différent du signalement (%s) : le texte a changé depuis, vérifiez" % hms(x["t"]) if alerte else ""))
                montre(srt, i, o, large=False)
                try:
                    rep = input("   [Entrée passer · e éditer · /ancien/nouveau/ · = juste · c contexte · q quitter] > ")
                except EOFError:
                    rep = "q"
                r = rep.strip()
                ancien = srt.cues[i][2]
                if r == "c":
                    print(); montre(srt, i, o, large=True); continue
                if r == "q":
                    quitter = True; break
                if r == "":
                    break
                if r == "=":
                    retirer["%d:%d" % (n, i)] = x.get("t", a0); fait += 1; break
                if r == "e":
                    if not PREREMPLIR:
                        print("   Copiez la phrase ci-dessus, corrigez-la, collez-la ici en entier (vide = annuler).")
                    nouveau = re.sub(r"\s+", " ", saisir("   phrase > ", ancien)).strip()
                elif r.startswith("/") and r.count("/") >= 2:
                    _, vieux, neuf = (r.split("/") + ["", ""])[:3]
                    if not vieux or vieux not in ancien:
                        print("   « %s » n'est pas dans la phrase." % vieux); continue
                    nouveau = ancien.replace(vieux, neuf)
                else:
                    print("   Commande inconnue."); continue
                if not nouveau or nouveau == ancien:
                    print("   Rien à changer."); continue
                print("   avant : %s\n   après : %s" % (ancien, nouveau))
                if input("   Valider ? [O/n] ").strip().lower() in ("n", "non"):
                    continue
                sauvegarde(textes, fichiers[0], sauvegardes)
                srt.remplacer(i, nouveau); srt.ecrire(); modifies.add(n)
                note = maj_txt(fichiers[0], ancien, nouveau, sauvegardes, textes)
                with open(journal, "a", encoding="utf-8") as j:
                    j.write("n° %d · phrase %d · %s\n  avant : %s\n  après : %s\n\n" % (n, i, hms(a0), ancien, nouveau))
                print("   Corrigé (%s)." % note)
                retirer["%d:%d" % (n, i)] = x.get("t", a0); fait += 1
                break
            if quitter:
                break
        if quitter:
            break
    print("\n" + "═" * 72)
    retirer_drapeaux(retirer, a.service if a.service is not None else "", darwin / "Darwin-iPhone" / "darwin-ecoutees-corrections.json")
    if not fait:
        print("Aucune phrase traitée."); return
    print("%d phrase(s) traitée(s)%s." % (fait, ", journal : %s" % journal if journal.exists() else ""))
    if modifies and not a.sans_regeneration:
        print("\nRégénération des données du lecteur…")
        cl = darwin / "construire_lecteur.py"
        if cl.is_file():
            subprocess.run([sys.executable, str(cl), str(darwin), "--n", ",".join(str(n) for n in sorted(modifies))])
        else:
            print("  construire_lecteur.py introuvable dans %s : à lancer à la main." % darwin)
        subprocess.run([sys.executable, str(ICI / "sous_titres.py")])
        print("\nIl reste à : réimporter Darwin-iPhone/sous-titres-darwin.ndjson dans l'app (Fichiers) ;\nle site privé est à jour (recharger la page). Si l'index de mots lit les textes : relancer Index_themes/sources/mots_index.py.")
    elif modifies:
        print("\nÀ lancer : construire_lecteur.py --n %s, puis outils/sous_titres.py (sans numéro), puis réimporter le .ndjson dans l'app." % ",".join(str(n) for n in sorted(modifies)))


if __name__ == "__main__":
    main()
