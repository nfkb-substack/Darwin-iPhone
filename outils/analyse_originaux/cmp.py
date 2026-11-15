import subprocess, glob, os, re, sys, json, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
os.chdir(os.path.expanduser('~/mnt/Darwin'))
CACHE = os.path.expanduser('~/env'); os.makedirs(CACHE, exist_ok=True)
FR = 20          # images d'enveloppe par seconde
def env(f, nom):
    c = f'{CACHE}/{nom}.npy'
    if os.path.exists(c): return np.load(c)
    p = subprocess.run(['ffmpeg','-nostdin','-v','error','-i',f,'-ac','1','-ar','8000','-af','highpass=f=300,lowpass=f=3000','-f','s16le','-'],capture_output=True)
    x = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32)
    n = 8000//FR; m = len(x)//n
    e = np.log10(np.sqrt((x[:m*n].reshape(m,n)**2).mean(1)) + 1.0)
    np.save(c, e); return e
def ncc_best(a, B):
    """a : fenêtre (L,), B : zone de recherche ; renvoie (décalage en images, corrélation)."""
    L = len(a); a = a - a.mean(); na = np.sqrt((a*a).sum())
    if na < 1e-6 or len(B) < L: return 0, 0.0
    cs = np.concatenate([[0], np.cumsum(B)]); cs2 = np.concatenate([[0], np.cumsum(B*B)])
    s = cs[L:] - cs[:-L]; s2 = cs2[L:] - cs2[:-L]
    var = np.maximum(s2 - s*s/L, 1e-9)
    N = 1 << (len(B)+L).bit_length()
    corr = np.fft.irfft(np.fft.rfft(B, N) * np.conj(np.fft.rfft(a, N)), N)[:len(B)-L+1]
    r = corr / (na*np.sqrt(var))
    k = int(np.argmax(r)); return k, float(r[k])
def comparer(n):
    old = glob.glob(f'original/{n}-original-*.mp3')[0]; new = glob.glob(f'_retelechargement_20261115/{n}-original-*.mp3')[0]
    a, b = env(old, f'{n}_old'), env(new, f'{n}_new')
    res = []; W = 60*FR; S = 400*FR; pas = 120*FR; dec = 0
    for t in range(0, len(a)-W, pas):
        centre = t + dec
        lo = max(0, centre - S); hi = min(len(b), centre + W + S)
        k, r = ncc_best(a[t:t+W], b[lo:hi])
        if r > 0.45:
            off = lo + k - t; res.append((t/FR, off/FR, r)); dec = off
        else: res.append((t/FR, None, r))
    return n, len(a)/FR, len(b)/FR, res
def resume(n, da, db, res):
    pts = [(t,o) for t,o,r in res if o is not None]
    out = f'n° {n} : ancien {da/60:.1f} min, nouveau {db/60:.1f} min ; fenêtres reconnues {len(pts)}/{len(res)}'
    seg = []
    for t,o in pts:
        if seg and abs(o-seg[-1][2]) < 0.6: seg[-1][1] = t; seg[-1][3] += 1
        else: seg.append([t,t,o,1])
    lignes = []
    for a_,b_,o,k in seg: lignes.append(f'     de {a_/60:5.1f} à {b_/60+1/60:5.1f} min (ancien) : nouveau = ancien {o:+.1f} s  [{k} fenêtres]')
    manque = [t for t,o,r in res if o is None]
    if manque: lignes.append('     non reconnu autour de : ' + ', '.join(f'{t/60:.0f} min' for t in manque[:10]) + (' …' if len(manque)>10 else ''))
    return out + '\n' + '\n'.join(lignes)
if __name__ == '__main__':
    ns = [int(x) for x in sys.argv[1:]]
    with ThreadPoolExecutor(4) as ex:
        for n, da, db, res in ex.map(comparer, ns): print(resume(n, da, db, res)); print()
