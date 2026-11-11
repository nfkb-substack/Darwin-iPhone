#!/usr/bin/env python3
"""Fabrique site/catalogue.json à partir des données déjà publiques de l'index (labo_data.json) :
une ligne par diffusion (n°, date, titre, première diffusion ou rediffusion, lien Radio France) et, pour les
émissions indexées, le résumé de la fiche. Aucun texte transcrit."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
D = json.load(open(src, encoding="utf-8"))
eps = D["eps"]
out = []
for a in D["A"]:
    e = {"n": a["n"], "d": a["d"], "t": a["t"]}
    if not a.get("f"):
        e["p"] = a.get("p")                      # n° de la première diffusion
    x = a.get("x")
    if x is not None:
        e["r"] = eps[x]["r"]
        if eps[x].get("u"): e["u"] = eps[x]["u"]
    if a.get("u"): e["u"] = a["u"]
    out.append(e)
json.dump({"genere": D.get("genere"), "eps": out}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(out), "diffusions,", sum(1 for e in out if "r" in e), "résumés,", sum(1 for e in out if "p" in e), "rediffusions")
