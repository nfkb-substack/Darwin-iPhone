import sys, glob, os
sys.path.insert(0, os.path.expanduser('~')); sys.path.insert(0, os.path.expanduser('~/mnt/Darwin/Darwin-iPhone/outils'))
import cmp, cbr
FR = cmp.FR
B = '_avant_remplacement_20261115'
for n in sys.argv[1:]:
    old = glob.glob(f'{B}/monologue/{n}-monologue-*.mp3')[0]; new = glob.glob(f'monologue/{n}-monologue-*.mp3')[0]
    a, b = cmp.env(old, f'{n}_mono_old'), cmp.env(new, f'{n}_mono_new')
    W, S = 45 * FR, 5 * FR; offs = []; faibles = 0
    for t in range(0, len(a) - W, 90 * FR):
        lo = max(0, t - S); hi = min(len(b), t + W + S)
        k, r = cmp.ncc_best(a[t:t+W], b[lo:hi])
        if r < 0.6: faibles += 1
        else: offs.append((lo + k - t) / FR)
    vbr, ent, deb, tag = cbr.analyse(new)
    print(f'{n}: fenêtres {len(offs)+faibles}, corrélation faible {faibles}, décalage min/max {min(offs):+.2f}/{max(offs):+.2f} s ; durée {cbr.duree(old):.1f} → {cbr.duree(new):.1f} ; VBR={vbr} en-tête={ent} débits={deb}')
