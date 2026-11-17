#!/usr/bin/env python3
"""Site privé : quand on déplace la barre de position du lecteur, le texte surligné suit le curseur pendant le glissement
et se recale (en défilant jusqu'à la phrase) au relâchement, même si « Suivre » est décoché.

Usage : python3 ajouter_curseur_prive.py <dossier site_construction>
À lancer après ajouter_restant_prive.py. Modifie prive_lecteur.js (copie .avant_curseur), puis relancer build_prive.py.
N'écrit rien si un texte attendu a changé ; sans effet si déjà appliqué."""
import sys, os, shutil

JS = [
 ('const i = lecIndexPhrase(lecVersMono(t));',
  'const i = lecIndexPhrase(lecVersMono(L.glisse ? lecQ(".lec-pos").value / 1000 * dur : t));   // pendant le glissement : phrase du curseur'),
 ('if (lecQ(".lec-suivre").checked) tx.scrollTop',
  'if (L.glisse || L.forcer || lecQ(".lec-suivre").checked) tx.scrollTop'),
 ('lecQ(".lec-t0").textContent = lecT(pos.value / 1000 * lecDuree()); lecT1(); });',
  'lecQ(".lec-t0").textContent = lecT(pos.value / 1000 * lecDuree()); lecT1(); lecMaj(); });'),
 ('pos.addEventListener("change", () => { L.glisse = false; a.currentTime = pos.value / 1000 * lecDuree(); });',
  'pos.addEventListener("change", () => { L.glisse = false; a.currentTime = pos.value / 1000 * lecDuree(); L.cour = -2; L.forcer = true; try { lecMaj(); } finally { L.forcer = false; } });'),
]

def appliquer(chemin):
    s = open(chemin, encoding="utf-8").read()
    if "L.forcer" in s:
        print(chemin, ": déjà appliqué"); return None
    for a, b in JS:
        if s.count(a) != 1:
            sys.exit(f"{chemin} : texte attendu trouvé {s.count(a)} fois, rien n'est modifié :\n{a[:90]}")
        s = s.replace(a, b)
    return s

if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    cj = os.path.join(d, "prive_lecteur.js"); n = appliquer(cj)
    if n is not None:
        shutil.copy2(cj, cj + ".avant_curseur"); open(cj, "w", encoding="utf-8").write(n); print(cj, ": modifié")
