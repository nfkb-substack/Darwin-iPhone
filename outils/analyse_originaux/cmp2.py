import sys, os, numpy as np
sys.path.insert(0, os.path.expanduser('~'))
from cmp import *
def module(e):    # part de l'énergie de l'enveloppe dans 2–8 Hz (rythme des syllabes) : élevée pour la parole
    e = e - e.mean(); P = np.abs(np.fft.rfft(e * np.hanning(len(e))))**2; f = np.fft.rfftfreq(len(e), 1/FR)
    return float(P[(f>=2)&(f<=8)].sum() / (P[(f>=0.3)&(f<=10)].sum() + 1e-9))
def r_a(a, b, t, off, w):
    i, j = int(t*FR), int((t+w)*FR); k = int((t+off)*FR)
    if k < 0 or k + (j-i) > len(b): return 0.0
    x, y = a[i:j]-a[i:j].mean(), b[k:k+(j-i)]-b[k:k+(j-i)].mean()
    d = np.sqrt((x*x).sum()*(y*y).sum()); return float((x*y).sum()/d) if d > 1e-6 else 0.0
def analyser(n):
    _, da, db, res = comparer(n)
    old = glob.glob(f'original/{n}-original-*.mp3')[0]; new = glob.glob(f'_retelechargement_20261115/{n}-original-*.mp3')[0]
    a, b = env(old, f'{n}_old'), env(new, f'{n}_new')
    pts = [(t,o) for t,o,r in res if o is not None]
    out = [f'n° {n} (ancien {da/60:.1f} min, nouveau {db/60:.1f} min)']
    base = np.mean([module(b[int(t*FR):int((t+60)*FR)]) for t,_ in pts[2:8]])
    for (t1,o1),(t2,o2) in zip(pts, pts[1:]):
        if abs(o2-o1) < 1.5: continue
        bord = None
        for p in np.arange(t1, t2+60, 3.0):
            if r_a(a, b, p, o1, 12) < 0.5 and r_a(a, b, p, o2, 12) > 0.5 or (p > t1+60 and r_a(a,b,p,o2,12) > 0.6): bord = p; break
        if bord is None: bord = (t1+t2)/2
        ins = (bord+o1, bord+o2)       # bloc inséré, en temps de la NOUVELLE version
        seg = b[int(ins[0]*FR):int(ins[1]*FR)]
        m = module(seg) if len(seg) > 10*FR else None
        out.append(f'   bloc inséré de {o2-o1:.0f} s vers {bord/60:.1f} min (ancien) : nouvelle version, de {int(ins[0]//60)}:{int(ins[0]%60):02d} à {int(ins[1]//60)}:{int(ins[1]%60):02d}' + (f' ; rythme de parole {m:.2f} (parole normale ≈ {base:.2f})' if m is not None else ''))
    if pts:
        fin = db - (da + pts[-1][1])
        if abs(fin) > 3: out.append(f'   en plus, {fin:+.0f} s à la fin de la nouvelle version (après {int(pts[-1][0]//60)} min de l\'ancienne)')
    return '\n'.join(out)
if __name__ == '__main__':
    for n in sys.argv[1:]: print(analyser(int(n))); print()
