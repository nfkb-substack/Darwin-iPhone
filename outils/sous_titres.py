#!/usr/bin/env python3
"""Prépare le fichier de sous-titres à envoyer sur l'iPhone (AirDrop), pour la webapp Darwin-iPhone.

    python3 outils/sous_titres.py                 tous les épisodes -> sous-titres-darwin.ndjson
    python3 outils/sous_titres.py 313 314 470     seulement ces numéros

Source : ../lecteur/<n>.js (fabriqués par construire_lecteur.py du projet Darwin : phrases, instants, et
correspondance monologue -> original). Le fichier produit contient le texte des émissions : il reste sur le Mac
et sur l'iPhone, il n'est jamais mis en ligne. Une ligne par épisode."""
import json, re, sys
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
LECTEUR = ICI.parent / "lecteur"
SORTIE = ICI / "sous-titres-darwin.ndjson"

def main():
    voulus = {int(x) for x in sys.argv[1:]}
    nb = 0
    with open(SORTIE, "w", encoding="utf-8") as out:
        for f in sorted(LECTEUR.glob("*.js"), key=lambda p: int(p.stem)):
            n = int(f.stem)
            if voulus and n not in voulus:
                continue
            m = re.search(r"DARWIN_LEC\[\d+\]=(\{.*\});\s*$", f.read_text(encoding="utf-8"), re.S)
            if not m:
                print("ignoré :", f.name); continue
            d = json.loads(m.group(1))
            out.write(json.dumps({"n": n, "d": d.get("d"), "o": d.get("o", []), "s": d["s"], "od": d.get("od")}, ensure_ascii=False, separators=(",", ":")) + "\n")
            nb += 1
    print(f"{nb} épisodes -> {SORTIE} ({SORTIE.stat().st_size / 1e6:.1f} Mo)")

if __name__ == "__main__":
    main()
