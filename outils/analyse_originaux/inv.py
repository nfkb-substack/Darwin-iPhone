import subprocess, json, sys, os, re, glob, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
os.chdir(os.path.expanduser('~/mnt/Darwin'))
SORTIE = os.path.expanduser('~/inv_orig.jsonl')
fait = set()
if os.path.exists(SORTIE):
    fait = {json.loads(l)['f'] for l in open(SORTIE)}
def analyser(f):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','stream=sample_rate,channels:format=duration,bit_rate,size','-of','json',f],capture_output=True,text=True)
    j = json.loads(r.stdout); s = j['streams'][0]; fm = j['format']
    dur = float(fm['duration']); sr = int(s['sample_rate'])
    ss = max(0, dur/2 - 20)
    p = subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',str(ss),'-t','40','-i',f,'-ac','1','-ar','44100','-f','s16le','-'],capture_output=True)
    x = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32)
    cut = None; niv = None
    if len(x) > 44100*5:
        N = 4096; n = (len(x)//N)*N; fr = x[:n].reshape(-1,N)*np.hanning(N)
        P = (np.abs(np.fft.rfft(fr,axis=1))**2).mean(axis=0); db = 10*np.log10(P+1e-9)
        fq = np.fft.rfftfreq(N,1/44100)
        # lissage par bandes de 250 Hz
        b = np.arange(0,22050,250); m = np.array([db[(fq>=a)&(fq<a+250)].mean() for a in b])
        ref = np.median(m[(b>=300)&(b<=3000)]); plan = np.median(m[b>=21000])
        # fréquence de coupure : dernière bande dont le niveau dépasse le plancher + 12 dB
        seuil = plan + 12
        idx = np.where(m > seuil)[0]; cut = int(b[idx[-1]]+250) if len(idx) else 0
        niv = round(float(ref-plan),1)
    return dict(f=f, n=int(re.match(r'(?:original|monologue)/(\d+)-',f)[1]), sr=sr, ch=int(s['channels']), br=int(fm.get('bit_rate',0))//1000, dur=round(dur,1), cut=cut, dyn=niv)
fs = sorted(glob.glob('original/*.mp3'), key=lambda f:int(re.match(r'original/(\d+)-',f)[1]))
reste = [f for f in fs if f not in fait]
fin = time.time()+95
with open(SORTIE,'a') as out:
    k=0
    while reste and time.time()<fin:
        lot, reste = reste[:8], reste[8:]
        with ThreadPoolExecutor(4) as ex:
            for r in ex.map(analyser, lot):
                out.write(json.dumps(r)+'\n'); k+=1
        out.flush()
print('analysés', k, 'restants', len(reste))
