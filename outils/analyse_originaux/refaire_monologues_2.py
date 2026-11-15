#!/usr/bin/env python3
"""Variante de refaire_monologues.py avec un décalage constant : usage  refaire_monologues_2.py 42:0 43:3.5
Décalage d > 0 : le nouvel original est en avance de d secondes sur l'ancien (nouveau = ancien - d). Les coupes sont
décalées de -d et d secondes de silence sont ajoutées au début, pour que le monologue garde exactement la chronologie
de l'ancien (donc celle des sous-titres)."""
import sys, os, csv, glob, subprocess
os.chdir(os.path.expanduser('~/mnt/Darwin'))
sys.path.insert(0, '.')
import monologue_seul as ms
B = '_avant_remplacement_20261115'
for arg in sys.argv[1:]:
    n, d = arg.split(':'); d = float(d)
    ancien = glob.glob(f'{B}/original/{n}-original-*.mp3')[0]
    nouveau = glob.glob(f'original/{n}-original-*.mp3')[0]
    rows = list(csv.reader(open(glob.glob(f'{B}/_analyse/{n}-original-*.segments.csv')[0], encoding='utf-8')))[2:]
    segs = [ms.Segment(l, float(a) - d, float(b) - d) for l, a, b in rows]
    segs = [ms.Segment(s.label, max(s.debut, 0.0), s.fin) for s in segs if s.fin > 0]
    duree_ref, _ = ms.sonde('ffprobe', ancien)
    duree_new, bps = ms.sonde('ffprobe', nouveau)
    duree = duree_ref - d
    plan = ms.construire_plan(ms.normaliser(segs, duree), duree, ms.MUSIQUE_MIN, ms.FUSION, ms.MARGE, ms.FONDU,
                              ms.BLOCS_ATTENDUS, ms.PAUSE, ms.REPRISE_VOLUME, ms.REPRISE_DUREE)
    dest = 'monologue/' + os.path.basename(nouveau).replace('-original-', '-monologue-', 1)
    print(f'{n} : ancien {duree_ref:.1f} s, nouveau {duree_new:.1f} s, décalage {d} s, durée prévue {plan.duree_sortie + d:.1f} s', flush=True)
    filtre = ms.construire_filtre(plan.gardes, plan.duree, plan.fondu, plan.pause, plan.reprise_volume, plan.reprise_duree)
    sortie = '[out]'
    if d > 0:
        filtre += f";[out]adelay={int(round(d * 1000))}:all=1[dec]"; sortie = '[dec]'
    part = dest + '.part'
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', nouveau, '-filter_complex', filtre,
           '-map', sortie, '-map_metadata', '0', '-id3v2_version', '3', '-c:a', 'libmp3lame', '-b:a', ms.choisir_debit(bps, 'auto'), '-f', 'mp3', part]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(r.stderr[-400:])
    os.replace(part, dest)
    ms.copier_etiquettes(ms.Path(nouveau), ms.Path(dest))
    dd, _ = ms.sonde('ffprobe', ms.Path(dest))
    print(f'   → {dest} : {dd:.1f} s ({os.path.getsize(dest)/1e6:.1f} Mo)', flush=True)
    ms.ecrire_cache(ms.Path('monologue/_analyse') / (ms.Path(nouveau).stem + '.segments.csv'),
                    [ms.Segment(l, float(a), float(b)) for l, a, b in rows], os.path.getsize(nouveau))
