"""sneak_lower.py: every sneak*.kf of a
folder whose accum child (Bip01 NonAccum) is keyed gets that channel's height lowered by DZ (all its frames, resampled
at 30 fps onto linear keys; rotation / x / y unchanged); files that don't key it take the lowered sneak idle / locomotion.
usage: python3 -P sneak_lower.py <folder> <dz> [node]"""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))); sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from holster_fix import KFFile
from kf import KFEval
d, dz = sys.argv[1], float(sys.argv[2]); node = sys.argv[3] if len(sys.argv) > 3 else 'Bip01 NonAccum'
n = 0
for f in sorted(os.listdir(d)):
    if not (f.lower().startswith('sneak') and f.lower().endswith('.kf')): continue
    p = os.path.join(d, f); kf = KFFile(p)
    if node not in [c for _, c in kf.cb]: continue
    k = KFEval(p); L = k.stop - k.start; N = max(2, int(round(L * 30)) + 1)
    keys = []
    for j in range(N):
        t = k.start + L * j / (N - 1); tr, R = k.sample(t)[node]
        tr = np.array(tr, float); tr[2] += dz; keys.append((t, tr, np.array(R, float)))
    kf.set_channel(node, keys); kf.save(p); n += 1
print(n, 'sneak files lowered by', dz, 'on', node)
