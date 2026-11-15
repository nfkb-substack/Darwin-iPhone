import sys, os, glob, csv
sys.path.insert(0, os.path.expanduser('~'))
from cmp import *
import numpy as np
B = '_avant_remplacement_20261115'
old = glob.glob(f'{B}/original/35-original-*.mp3')[0]; new = glob.glob('_retelechargement_20261115/35-original-*.mp3')[0]
a, b = env(old, '35_old'), env(new, '35_new')
print('durées', len(a)/FR, len(b)/FR)
W = 20*FR
print('décalage tous les 60 s :')
res = []
for t in range(60, int(len(b)/FR) - 25, 60):
    i = t*FR; lo = max(0, i-5*FR); hi = min(len(b), i+W+5*FR)
    k, r = ncc_best(a[i:i+W], b[lo:hi]); res.append((t, (lo+k-i)/FR, r))
print('   ' + ' '.join(f'{t//60}:{t%60:02d}={o:+.2f}({r:.2f})' for t, o, r in res))
# pauses : moyenne glissante de 0,6 s de l'enveloppe de l'ANCIEN, entre 24:00 et 26:00 (le nouveau couvre jusqu'à 26:36)
lo, hi = 1440*FR, 1560*FR
m = int(0.6*FR)
sm = np.convolve(a, np.ones(m)/m, mode='valid')
seg = sm[lo:hi]
ref = np.median(a[lo:hi])
idx = np.argsort(seg)[:400]
cands = []
for k in idx:
    t = (lo + k + m/2)/FR
    if all(abs(t - c[0]) > 3 for c in cands): cands.append((t, seg[k]))
    if len(cands) == 5: break
print('médiane enveloppe', round(float(ref), 2), '; pauses candidates (instant ancien, niveau moyen 0,6 s) :', [(round(t, 2), round(float(v), 2)) for t, v in cands])
