#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Réencode en CBR 128 kbit/s les mp3 à débit variable (VBR).

Pourquoi : sur iPhone, un saut dans un mp3 VBR passe par la table Xing (résolution de 1 %) et tombe quelques secondes à côté ;
le texte surligné suit la position annoncée, donc il se décale par rapport à la voix. En CBR (entête Info), le saut est exact.

Détection : débits des trames sur deux fenêtres (début et milieu du fichier) ; plus d'un débit = VBR. Les fichiers déjà en CBR,
avec ou sans entête, ne sont pas touchés.

Sans option : liste seulement. Avec --appliquer : pour chaque VBR, réencode dans un dossier temporaire, vérifie (même durée à
0,2 s près, un seul débit, entête Info, pochette conservée), puis range l'original dans <sauvegarde>/<dossier>/ et met le nouveau
fichier à sa place, sous le même nom. Rien n'est supprimé ; le journal est <sauvegarde>/journal.txt.

    python3 cbr.py ~/Music/Darwin/monologue ~/Music/Darwin/original                      # liste
    python3 cbr.py ~/Music/Darwin/monologue ~/Music/Darwin/original --appliquer --jobs 3
"""
import argparse, datetime, os, re, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

BR = {1: {1: [0,32,64,96,128,160,192,224,256,288,320,352,384,416,448], 2: [0,32,48,56,64,80,96,112,128,160,192,224,256,320,384],
          3: [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320]},
      2: {1: [0,32,48,56,64,80,96,112,128,144,160,176,192,224,256], 2: [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160],
          3: [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160]}}
SR = {1: [44100, 48000, 32000], 2: [22050, 24000, 16000], 3: [11025, 12000, 8000]}
FENETRE = 1_500_000


def en_tete(b, i):
    """(longueur, débit, fréquence) de la trame en i, ou None."""
    if i + 4 > len(b) or b[i] != 0xFF or (b[i+1] & 0xE0) != 0xE0:
        return None
    ver = {3: 1, 2: 2, 0: 3}.get((b[i+1] >> 3) & 3); lay = {3: 1, 2: 2, 1: 3}.get((b[i+1] >> 1) & 3)
    bi = b[i+2] >> 4; si = (b[i+2] >> 2) & 3; pad = (b[i+2] >> 1) & 1
    if ver is None or lay is None or bi in (0, 15) or si == 3:
        return None
    br = BR[1 if ver == 1 else 2][lay][bi] * 1000; sr = SR[ver][si]
    ln = (144 * br // sr + pad) if (lay == 3 and ver == 1) or lay == 2 else (72 * br // sr + pad) if lay == 3 else (12 * br // sr + pad) * 4
    return ln, br, sr


def debits(b, debut):
    """Débits des trames successives depuis `debut` (resynchronise sur une chaîne de 4 trames valides)."""
    i, n = debut, len(b)
    while i < n - 8:
        h = en_tete(b, i); ok = h is not None
        if ok:
            j = i
            for _ in range(3):
                j += en_tete(b, j)[0]
                if en_tete(b, j) is None: ok = False; break
        if ok: break
        i += 1
    out = []
    while i < n - 4:
        h = en_tete(b, i)
        if h is None: break
        out.append(h[1]); i += h[0]
    return out


def taille_tag(b):
    return 10 + (((b[6] & 0x7f) << 21) | ((b[7] & 0x7f) << 14) | ((b[8] & 0x7f) << 7) | (b[9] & 0x7f)) if b[:3] == b'ID3' else 0


def analyse(chemin):
    """-> (vbr, entête, débits distincts, taille du tag). La 1re trame (Xing/Info) est ignorée."""
    taille = os.path.getsize(chemin)
    with open(chemin, 'rb') as f:
        tag = taille_tag(f.read(10)); f.seek(tag); debut = f.read(FENETRE); milieu = b''
        if taille > tag + 3 * FENETRE:
            f.seek(tag + (taille - tag) // 2); milieu = f.read(FENETRE)
    h = debut[:400]; entete = 'Xing' if b'Xing' in h else 'Info' if b'Info' in h else 'VBRI' if b'VBRI' in h else None
    dist = sorted(set(debits(debut, 0)[1:]) | set(debits(milieu, 0) if milieu else []))
    return len(dist) > 1, entete, dist, tag


def duree(chemin):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', chemin], capture_output=True, text=True)
    return float(r.stdout.strip())


def a_pochette(chemin):
    with open(chemin, 'rb') as f:
        n = taille_tag(f.read(10)); f.seek(0); return b'APIC' in f.read(n or 10)


def convertir(src, tmp):
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-map', '0:a', '-map', '0:v?', '-c:a', 'libmp3lame', '-b:a', '128k',
           '-c:v', 'copy', '-map_metadata', '0', '-id3v2_version', '3', '-write_xing', '1', tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr.strip()[-300:])


def traiter(src, dossier, sauve, tmpdir, verrou, journal):
    nom = os.path.basename(src); tmp = os.path.join(tmpdir, dossier + '__' + nom)
    try:
        d0 = duree(src); poch = a_pochette(src)
        convertir(src, tmp)
        d1 = duree(tmp); vbr, entete, dist, _ = analyse(tmp)
        if abs(d1 - d0) > 0.2: raise RuntimeError(f'durée {d0:.2f} -> {d1:.2f} s')
        if vbr or entete != 'Info': raise RuntimeError(f'résultat non CBR (entête {entete}, débits {dist})')
        if poch and not a_pochette(tmp): raise RuntimeError('pochette perdue')
        dest = os.path.join(sauve, dossier); os.makedirs(dest, exist_ok=True)
        ancien = os.path.getsize(src)
        shutil.move(src, os.path.join(dest, nom)); shutil.move(tmp, src)
        msg = f'ok     {dossier}/{nom}  {ancien/1e6:.1f} -> {os.path.getsize(src)/1e6:.1f} Mo  durée {d0:.2f} -> {d1:.2f} s'
    except Exception as e:
        if os.path.exists(tmp): os.remove(tmp)
        msg = f'ÉCHEC  {dossier}/{nom}  {e}'
    with verrou:
        print(msg, flush=True); journal.write(msg + '\n'); journal.flush()
    return msg.startswith('ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dossiers', nargs='+'); ap.add_argument('--appliquer', action='store_true'); ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--max', type=int, default=0, help='traiter au plus N fichiers par lancement (reprise : relancer, les fichiers faits ne sont plus VBR)')
    ap.add_argument('--sauvegarde', default=None, help='défaut : <dossier parent>/_avant_cbr_AAAAMMJJ')
    a = ap.parse_args()
    a.dossiers = [os.path.abspath(os.path.expanduser(d)) for d in a.dossiers]
    liste = []
    for d in a.dossiers:
        for nom in sorted(os.listdir(d), key=lambda x: (int(re.match(r'(\d+)-', x).group(1)) if re.match(r'(\d+)-', x) else 10**9, x)):
            if not nom.lower().endswith('.mp3') or nom.startswith('.'): continue
            p = os.path.join(d, nom)
            try: vbr, entete, dist, tag = analyse(p)
            except Exception as e: print('illisible', p, e); continue
            if vbr: liste.append((os.path.basename(d), p))
    total = len(liste)
    if a.max: liste = liste[:a.max]
    print(f'{total} fichier(s) VBR :', ', '.join(re.match(r'(\d+)-', os.path.basename(p)).group(1) + ('m' if 'monologue' in d else 'o') for d, p in liste), flush=True)
    if not a.appliquer: print('(liste seulement ; ajouter --appliquer pour réencoder)'); return
    sauve = a.sauvegarde or os.path.join(os.path.dirname(a.dossiers[0]), '_avant_cbr_' + datetime.date.today().strftime('%Y%m%d'))
    os.makedirs(sauve, exist_ok=True); tmpdir = os.path.join(sauve, '_tmp'); os.makedirs(tmpdir, exist_ok=True)
    verrou = threading.Lock(); bons = 0
    with open(os.path.join(sauve, 'journal.txt'), 'a', encoding='utf-8') as journal, ThreadPoolExecutor(a.jobs) as ex:
        futs = [ex.submit(traiter, p, d, sauve, tmpdir, verrou, journal) for d, p in liste]
        for f in as_completed(futs): bons += f.result()
    print(f'terminé : {bons}/{len(liste)} réencodés. Originaux rangés dans {sauve}', flush=True)


if __name__ == '__main__':
    main()
