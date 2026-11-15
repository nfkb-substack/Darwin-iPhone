#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Liste les phrases du texte signalées comme erronées (drapeau ⚑ de la webapp ou du site privé), avec leur contexte.

    python3 signalements.py ~/Downloads/darwin-ecoutees.json        fichier produit par « Exporter »
    python3 signalements.py --service CLE                           ou variable DARWIN_SYNC_KEY : lit le service de synchronisation

Le service ne garde que n° d'émission + indice de phrase : le texte est lu ici, dans sous-titres-darwin.ndjson (local, jamais en ligne).
Résultat affiché et écrit dans signalements.txt (à côté de ce dossier ; ignoré par git). Pour corriger : modifier le .srt de
l'émission puis relancer construire_lecteur.py et sous_titres.py.
"""
import json, os, re, sys, urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
NDJSON = ICI / "sous-titres-darwin.ndjson"


def lire_signalements(args):
    if args and args[0] == "--service":
        cle = args[1] if len(args) > 1 else os.environ.get("DARWIN_SYNC_KEY", "")
        if not cle: sys.exit("--service demande la clé (ou la variable DARWIN_SYNC_KEY)")
        url = "https://darwin-iphone.vercel.app/api/ecoutees?x-vercel-protection-bypass=" + cle
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "darwin-signalements"}), timeout=30) as r:
            j = json.load(r)
    elif args:
        j = json.load(open(os.path.expanduser(args[0]), encoding="utf-8"))
    else:
        sys.exit(__doc__)
    if not isinstance(j, dict) or j.get("format") != "darwin-ecoutees": sys.exit("document inattendu (pas un darwin-ecoutees.json)")
    out = {}
    for cle, x in (j.get("err") or {}).items():
        m = re.fullmatch(r"(\d{1,5}):(\d{1,5})", cle)
        if m and isinstance(x, dict) and x.get("d"): out.setdefault(int(m[1]), []).append((int(m[2]), x))
    return out


def hms(t):
    t = int(t); return "%d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60) if t >= 3600 else "%d:%02d" % (t // 60, t % 60)


def main():
    sig = lire_signalements(sys.argv[1:])
    if not sig: print("Aucune phrase signalée."); return
    if not NDJSON.exists(): sys.exit("%s introuvable : lancez outils/sous_titres.py" % NDJSON)
    textes = {}
    with open(NDJSON, encoding="utf-8") as f:
        for ligne in f:
            d = json.loads(ligne)
            if d["n"] in sig: textes[d["n"]] = d["s"]
    cat = {}
    try: cat = {e["n"]: e for e in json.load(open(ICI / "site" / "catalogue.json", encoding="utf-8"))["eps"]}
    except Exception: pass
    lignes = []
    for n in sorted(sig):
        e = cat.get(n); lignes.append("n° %d%s" % (n, " — " + e["t"] if e else ""))
        s = textes.get(n)
        for i, x in sorted(sig[n]):
            if not s or i >= len(s):
                lignes.append("   phrase %d : texte introuvable (sous-titres absents ou refaits depuis)" % i); continue
            t = x.get("t")
            decale = t is not None and abs(s[i][0] - t) > 2   # le texte a changé depuis le signalement : l'indice a pu se décaler
            lignes.append("   [%s] phrase %d%s" % (hms(s[i][0]), i, "  (instant différent de celui du signalement : vérifier)" if decale else ""))
            if i > 0: lignes.append("        …%s" % s[i - 1][1])
            lignes.append("     ⚑  %s" % s[i][1])
            if i + 1 < len(s): lignes.append("        …%s" % s[i + 1][1])
        lignes.append("")
    texte = "\n".join(lignes)
    print(texte)
    (ICI / "signalements.txt").write_text(texte + "\n", encoding="utf-8")
    print("(écrit dans %s)" % (ICI / "signalements.txt"))


if __name__ == "__main__":
    main()
