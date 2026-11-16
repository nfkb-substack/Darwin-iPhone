#!/usr/bin/env python3
"""Site privé : un appui sur le temps de droite du lecteur bascule entre durée totale et temps restant (retenu dans le navigateur).

Usage : python3 ajouter_restant_prive.py <dossier site_construction>
Modifie prive_lecteur.js et prive_lecteur.css (copies .avant_restant), puis relancer build_prive.py.
N'écrit rien si un texte attendu a changé ; sans effet si déjà appliqué."""
import sys, os, shutil

JS = [
 ('<span class="lec-tm lec-t1">0:00</span>',
  '<button type="button" class="lec-tm lec-t1" aria-label="Durée totale. Cliquer pour afficher le temps restant.">0:00</button>'),
 ('function lecMaj() {',
  '''function lecT1() {                                      // temps de droite : durée totale ou temps restant (appui pour basculer)
  const b = lecQ(".lec-t1"), dur = lecDuree(), rest = !!L.restant && dur > 0, t = L.glisse ? lecQ(".lec-pos").value / 1000 * dur : (L.a.currentTime || 0);
  b.textContent = rest ? "\\u2212" + lecT(dur - t) : lecT(dur);
  b.setAttribute("aria-label", rest ? "Temps restant. Cliquer pour afficher la durée totale." : "Durée totale. Cliquer pour afficher le temps restant.");
}
function lecMaj() {'''),
 ('  lecQ(".lec-t1").textContent = lecT(dur);\n', '  lecT1();\n'),
 ('lecQ(".lec-t0").textContent = lecT(pos.value / 1000 * lecDuree()); });',
  'lecQ(".lec-t0").textContent = lecT(pos.value / 1000 * lecDuree()); lecT1(); });'),
 ('  const play = lecQ(".lec-play"), pos = lecQ(".lec-pos");\n',
  '''  try { L.restant = localStorage.getItem("darwin-lec-restant") === "1"; } catch (e) {}
  lecQ(".lec-t1").addEventListener("click", () => { L.restant = !L.restant; try { localStorage.setItem("darwin-lec-restant", L.restant ? "1" : "0"); } catch (e) {} lecT1(); });
  const play = lecQ(".lec-play"), pos = lecQ(".lec-pos");\n'''),
]
CSS = [
 ('#lec .lec-tm {', '#lec button.lec-t1 { background: none; border: 0; margin: 0; padding: 4px 2px; font-family: inherit; cursor: pointer; white-space: nowrap; }\n#lec .lec-tm {'),
]

def appliquer(chemin, remplacements):
    s = open(chemin, encoding="utf-8").read()
    if "lecT1" in s or "button.lec-t1" in s:
        print(chemin, ": déjà appliqué"); return None
    for a, b in remplacements:
        if s.count(a) != 1:
            sys.exit(f"{chemin} : texte attendu trouvé {s.count(a)} fois, rien n'est modifié :\n{a[:90]}")
        s = s.replace(a, b)
    return s

if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    cj, cc = os.path.join(d, "prive_lecteur.js"), os.path.join(d, "prive_lecteur.css")
    nj, nc = appliquer(cj, JS), appliquer(cc, CSS)
    for c, n in ((cj, nj), (cc, nc)):
        if n is not None:
            shutil.copy2(c, c + ".avant_restant"); open(c, "w", encoding="utf-8").write(n); print(c, ": modifié")
