#!/usr/bin/env python3
"""Refait les monologues 30, 31, 34, 36, 37 à partir des nouveaux originaux, dont la musique est plus longue ou le début
différent. Pour chaque partie conservée de l'ancien monologue [g0, g1], le décalage nouveau - ancien est mesuré par corrélation
d'enveloppe sur les 30 premières secondes de la partie ; la partie est reprise dans le nouvel original à [g0 + décalage,
g1 + décalage] (même durée qu'avant). Le monologue garde ainsi exactement la chronologie de l'ancien (les sous-titres ne changent pas).
Début du fichier plus court (décalage négatif, ex. bande-annonce absente) : silence de même durée en tête.
Usage : refaire_monologues_3.py 30 31 34 36 37"""
import sys, os, csv, glob, json, subprocess
os.chdir(os.path.expanduser('~/mnt/Darwin'))
sys.path.insert(0, os.path.expanduser('~')); sys.path.insert(0, '.')
import decalages as dc
from cmp import env, FR
import monologue_seul as ms
B = '_avant_remplacement_20261115'
sortie_json = {}
for n in sys.argv[1:]:
    ancien = glob.glob(f'{B}/original/{n}-original-*.mp3')[0]
    nouveau = glob.glob(f'original/{n}-original-*.mp3')[0]
    rows = list(csv.reader(open(glob.glob(f'{B}/_analyse/{n}-original-*.segments.csv')[0], encoding='utf-8')))[2:]
    segs = [ms.Segment(l, float(a), float(b)) for l, a, b in rows]
    duree_ref, _ = ms.sonde('ffprobe', ancien)
    duree_new, bps = ms.sonde('ffprobe', nouveau)
    plan = ms.construire_plan(ms.normaliser(segs, duree_ref), duree_ref, ms.MUSIQUE_MIN, ms.FUSION, ms.MARGE, ms.FONDU,
                              ms.BLOCS_ATTENDUS, ms.PAUSE, ms.REPRISE_VOLUME, ms.REPRISE_DUREE)
    a, b = env(ancien, f'{n}_old'), env(nouveau, f'{n}_new')
    gardes, infos, pad = [], [], 0.0
    for i, (g0, g1) in enumerate(plan.gardes):
        long = g1 - g0 > 40
        d0, r0 = dc.mesure(a, b, g0 + 1 if long else g0)
        if d0 is None or r0 < 0.6:                       # début de fichier : fenêtre trop pauvre -> repli plus loin dans la partie
            d0, r0 = dc.mesure(a, b, g0 + 20)
        if d0 is None or r0 < 0.6: raise SystemExit(f'{n} partie {i+1} : décalage introuvable (r={r0:.2f})')
        d0 = round(d0 * 20) / 20
        debut, fin = g0 + d0, g1 + d0
        if debut < 0:
            pad = -debut; debut = 0.0
        fin = min(fin, duree_new)
        gardes.append((debut, fin)); infos.append((g0, g1, d0, r0))
    if abs(plan.duree_sortie - (sum(y - x for x, y in gardes) + ms.PAUSE * (len(gardes) - 1) + pad)) > 0.3:
        print(f'   ⚠ durée prévue différente : {plan.duree_sortie:.1f} contre {sum(y - x for x, y in gardes) + ms.PAUSE * (len(gardes) - 1) + pad:.1f}')
    print(f'{n} : ancien {duree_ref:.1f} s, nouveau {duree_new:.1f} s, silence en tête {pad:.2f} s', flush=True)
    for (g0, g1, d0, r0), (x, y) in zip(infos, gardes):
        print(f'   {ms.fmt_t(g0)}-{ms.fmt_t(g1)} : décalage {d0:+.2f} s (r={r0:.2f}) -> nouvel original {x:.2f} à {y:.2f} s')
    filtre = ms.construire_filtre(gardes, gardes[-1][1], plan.fondu, ms.PAUSE, ms.REPRISE_VOLUME, ms.REPRISE_DUREE)
    sortie = '[out]'
    if pad > 0.01:
        filtre += f";[out]adelay={int(round(pad * 1000))}:all=1[dec]"; sortie = '[dec]'
    dest = 'monologue/' + os.path.basename(nouveau).replace('-original-', '-monologue-', 1); part = dest + '.part'
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', nouveau, '-filter_complex', filtre, '-map', sortie,
           '-map_metadata', '0', '-id3v2_version', '3', '-c:a', 'libmp3lame', '-b:a', ms.choisir_debit(bps, 'auto'), '-f', 'mp3', part]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(r.stderr[-500:])
    os.replace(part, dest); ms.copier_etiquettes(ms.Path(nouveau), ms.Path(dest))
    dd, _ = ms.sonde('ffprobe', ms.Path(dest))
    print(f'   → {dest} : {dd:.1f} s (ancien monologue : {plan.duree_sortie:.1f} s)', flush=True)
    sortie_json[n] = {'pad': pad, 'gardes': [{'ancien': [g0, g1], 'decalage': d0, 'nouveau': [x, y]} for (g0, g1, d0, r0), (x, y) in zip(infos, gardes)]}
    json.dump(sortie_json, open(f'{B}/decalages_{"_".join(sys.argv[1:])}.json', 'w'), indent=1)
