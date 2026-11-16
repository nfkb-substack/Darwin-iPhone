#!/usr/bin/env python3
"""Ajoute l'étiquette « préféré » au site privé (Darwin/site_construction/prive_lecteur.js).

Usage : python3 ajouter_prefere_prive.py <prive_lecteur.js> [autre fichier…]
Puis, dans Darwin/site_construction : python3 build_prive.py (et copier le résultat dans Darwin/site_prive.html, comme d'habitude).

Même logique que la webapp (version 10) : section « prefere » du document synchronisé, case « Préféré » dans la fiche, marque ★ dans le
catalogue, option « préférés » du filtre Écoute. Chaque remplacement doit trouver son texte exactement une fois, sinon rien n'est écrit.
Relançable : un fichier déjà modifié est laissé tel quel. Le fichier d'origine est conservé en .avant_prefere."""
import shutil, sys

REMPLACEMENTS = [
    ("//   difficile : thème difficile (clé = n° d'émission) ; qualite :",
     "//   prefere : émission préférée (clé = n° d'émission) ; difficile : thème difficile (clé = n° d'émission) ; qualite :"),
    ("const ETQ_RE = {difficile: /^\\d{1,5}$/,", "const ETQ_RE = {prefere: /^\\d{1,5}$/, difficile: /^\\d{1,5}$/,"),
    ('const etqMarque = e => (etqDate("difficile", e.n) ?',
     'const etqMarque = e => (etqDate("prefere", e.n) ? \'<span class="eco-ok" title="Préféré">★ </span>\' : "") + (etqDate("difficile", e.n) ?'),
    ('const ecoFiltre = e => !ecoMode || (ecoMode === "dif" ?',
     'const ecoFiltre = e => !ecoMode || (ecoMode === "pre" ? !!etqDate("prefere", e.n) : ecoMode === "dif" ?'),
    ('<div class="eco-etiq"><label class="eco-case"><input type="checkbox" data-etq="difficile"',
     '<div class="eco-etiq"><label class="eco-case"><input type="checkbox" data-etq="prefere" ${etqDate("prefere", n) ? "checked" : ""}> Préféré</label><label class="eco-case"><input type="checkbox" data-etq="difficile"'),
    ('<option value="dif">difficiles</option>', '<option value="pre">préférés</option><option value="dif">difficiles</option>'),
]

def main(chemins):
    if not chemins:
        sys.exit(__doc__)
    for ch in chemins:
        s = open(ch, encoding="utf-8").read()
        if 'data-etq="prefere"' in s:
            print(f"{ch} : déjà modifié, rien à faire"); continue
        for ancien, nouveau in REMPLACEMENTS:
            n = s.count(ancien)
            if n != 1:
                sys.exit(f"{ch} : texte attendu {'absent' if n == 0 else 'en ' + str(n) + ' exemplaires'} : {ancien[:70]!r}\nRien n'a été écrit (le fichier a changé depuis l'écriture de ce script).")
            s = s.replace(ancien, nouveau)
        shutil.copy2(ch, ch + ".avant_prefere")
        open(ch, "w", encoding="utf-8").write(s)
        print(f"{ch} : « préféré » ajouté ({len(REMPLACEMENTS)} remplacements) ; copie dans {ch}.avant_prefere")

if __name__ == "__main__":
    main(sys.argv[1:])
