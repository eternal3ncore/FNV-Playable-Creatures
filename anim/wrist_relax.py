"""Neutral wrist for throws and mine placing: the R Hand keeps its holding grip relative to the forearm (its local
rotation in the race's hold aim of the same variant, 1GT / 1MD / 1LM aim at t=0) through the whole file, instead of
holding the item at the plan's world orientation while the arm swings (audit: wrist bent ~160-178 deg).
A grenade / mine has no aiming direction. Applied only to files listed (generated ones; never the races' own throws).
--idle: the grip is the creature's relaxed idle wrist (mtidle t=0) - for races whose grenade / mine hold is itself
procedural (Zetan, swampfolk, trog); also applies to their 1GT / 1MD / 1LM aims.
usage: python3 wrist_relax.py <folder> <file,file,...> [--idle]"""
import sys, os, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval
import hinge_fix as H
folder = sys.argv[1]; files = [f for f in sys.argv[2].split(',') if f]
n = 0
for fn in files:
    m = re.match(r'^(sneak)?(1gt|1md|1lm)(attackthrow|placemine|aim)\d?(up|down|is|isup|isdown)?\.kf$', fn.lower())
    if not m: continue
    suf = m.group(4) or ''
    aim = next((os.path.join(folder, f'{m.group(2)}aim{s}.kf') for s in (suf, suf.replace('is', ''), '') if os.path.exists(os.path.join(folder, f'{m.group(2)}aim{s}.kf'))), None)
    if m.group(3) == 'aim' and '--idle' not in sys.argv: continue
    a = KFEval(os.path.join(folder, 'mtidle.kf') if '--idle' in sys.argv else aim).sample(0)
    if 'Bip01 R Hand' not in a or a['Bip01 R Hand'][1] is None: continue
    Rg = np.asarray(a['Bip01 R Hand'][1], float)
    k = KFEval(os.path.join(folder, fn)); L = k.stop
    if 'Bip01 R Hand' not in {b[0] for b in k.blocks}: continue
    nf = max(2, int(round(L * 30)) + 1); keys = []
    for i in range(nf):
        t = L * i / (nf - 1); s = k.sample(t)
        keys.append((t, np.asarray(s['Bip01 R Hand'][0], float), Rg))
    H.write_tracks(os.path.join(folder, fn), {'Bip01 R Hand': keys}, 65); n += 1
print(n, 'files: wrist neutral')
