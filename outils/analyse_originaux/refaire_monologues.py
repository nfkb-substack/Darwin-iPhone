#!/usr/bin/env python3
"""Refait les monologues 32, 33 et 38 à partir des NOUVEAUX originaux (téléchargés chez Radio France),
avec exactement les coupes de l'ancien traitement (cache d'analyse sauvegardé dans _analyse/, durée de l'ancien
original). 33 : le nouvel original a 37 s de plus en fin de fichier ; la durée de référence (ancienne) les écarte."""
import sys, os, csv, glob, shutil
os.chdir(os.path.expanduser('~/mnt/Darwin'))
sys.path.insert(0, '.')
import monologue_seul as ms
B = '_avant_remplacement_20261115'
for n in sys.argv[1:]:
    ancien = glob.glob(f'{B}/original/{n}-original-*.mp3')[0]
    nouveau = glob.glob(f'original/{n}-original-*.mp3')[0]
    rows = list(csv.reader(open(glob.glob(f'{B}/_analyse/{n}-original-*.segments.csv')[0], encoding='utf-8')))[2:]
    segs = [ms.Segment(l, float(d), float(f)) for l, d, f in rows]
    duree_ref, _ = ms.sonde('ffprobe', ancien)
    duree_new, bps = ms.sonde('ffprobe', nouveau)
    plan = ms.construire_plan(ms.normaliser(segs, duree_ref), duree_ref, ms.MUSIQUE_MIN, ms.FUSION, ms.MARGE,
                              ms.FONDU, ms.BLOCS_ATTENDUS, ms.PAUSE, ms.REPRISE_VOLUME, ms.REPRISE_DUREE)
    dest = 'monologue/' + os.path.basename(nouveau).replace('-original-', '-monologue-', 1)
    print(f'{n} : ancien {duree_ref:.1f} s, nouveau {duree_new:.1f} s, durée prévue {plan.duree_sortie:.1f} s', flush=True)
    ms.couper('ffmpeg', ms.Path(nouveau), ms.Path(dest), plan, ms.choisir_debit(bps, 'auto'))
    ms.copier_etiquettes(ms.Path(nouveau), ms.Path(dest))
    d, _ = ms.sonde('ffprobe', ms.Path(dest))
    print(f'   → {dest} : {d:.1f} s ({os.path.getsize(dest)/1e6:.1f} Mo)', flush=True)
    # cache pour le nouvel original (mêmes segments), afin qu'un futur --ecraser garde les mêmes coupes
    cache = ms.Path('monologue/_analyse') / (ms.Path(nouveau).stem + '.segments.csv')
    ms.ecrire_cache(cache, segs, os.path.getsize(nouveau))
