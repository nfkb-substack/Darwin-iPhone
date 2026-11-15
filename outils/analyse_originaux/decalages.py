"""Décalage nouveau - ancien mesuré au début et à la fin de chaque partie conservée de l'ancien monologue."""
import sys, os, glob, csv
sys.path.insert(0, os.path.expanduser('~'))
from cmp import *          # env, ncc_best, FR ; chdir ~/mnt/Darwin
sys.path.insert(0, '.')
import monologue_seul as ms
W = 30 * FR
def mesure(a, b, t):          # fenêtre ancienne [t, t+30 s] -> décalage, corrélation
    i = int(t * FR)
    if i < 0 or i + W > len(a): return None, 0.0
    lo = max(0, i - 15 * FR); hi = min(len(b), i + W + 200 * FR)
    k, r = ncc_best(a[i:i+W], b[lo:hi])
    return (lo + k - i) / FR, r
def gardes_anciens(n):
    cache = glob.glob(f'monologue/_analyse/{n}-original-*.segments.csv')[0]
    rows = list(csv.reader(open(cache, encoding='utf-8')))[2:]
    segs = [ms.Segment(l, float(d), float(f)) for l, d, f in rows]
    duree = float(next(r for r in csv.DictReader(open('suivi_monologues.csv', encoding='utf-8-sig'), delimiter=';') if r['fichier'].split('-')[0] == n)['duree_origine_s'])
    plan = ms.construire_plan(ms.normaliser(segs, duree), duree, ms.MUSIQUE_MIN, ms.FUSION, ms.MARGE, ms.FONDU, ms.BLOCS_ATTENDUS, ms.PAUSE, ms.REPRISE_VOLUME, ms.REPRISE_DUREE)
    return plan, duree
if __name__ == '__main__':
    for n in sys.argv[1:]:
        old = glob.glob(f'original/{n}-original-*.mp3')[0]; new = glob.glob(f'_retelechargement_20261115/{n}-original-*.mp3')[0]
        a, b = env(old, f'{n}_old'), env(new, f'{n}_new')
        plan, duree = gardes_anciens(n)
        print(f'n° {n} : ancien {len(a)/FR/60:.2f} min, nouveau {len(b)/FR/60:.2f} min, coupes anciennes ' + ' | '.join(f'{ms.fmt_t(x)}-{ms.fmt_t(y)}' for x, y in plan.coupes))
        for i, (g0, g1) in enumerate(plan.gardes):
            d0, r0 = mesure(a, b, g0 + 1 if g1 - g0 > 40 else g0)
            d1, r1 = mesure(a, b, g1 - 31 if g1 - g0 > 40 else g0)
            f = lambda d, r: 'inconnu' if d is None else f'{d:+.2f} s (r={r:.2f})'
            print(f'   partie {i+1} [{ms.fmt_t(g0)} → {ms.fmt_t(g1)}] début {f(d0, r0)} ; fin {f(d1, r1)}')
