"""Compares original vs hinge-fixed KFs: end position / orientation error, elbow / knee shift, off-hinge before / after.
usage: python3 hinge_verify.py <orig folder> <fixed folder> <audit json> [files...]"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval, Skeleton
import hinge_fix as H
o, fx, aj = sys.argv[1:4]; files = sys.argv[4:]
sk = Skeleton(os.path.join(o, 'Skeleton.nif')); idle = KFEval(os.path.join(o, 'mtidle.kf')).sample(0)
rng = json.load(open(aj))['hinge_range']
chains = [H.Chain(sk, idle, c, rng[c[1]]) for c in H.CHAINS if c[1] in rng]
def loc(s_, nm):
    tr = s_[nm][0] if nm in s_ and s_[nm][0] is not None else (idle[nm][0] if nm in idle and idle[nm][0] is not None else sk.local[nm][0])
    R = s_[nm][1] if nm in s_ and s_[nm][1] is not None else (idle[nm][1] if nm in idle and idle[nm][1] is not None else sk.local[nm][1])
    return np.array(tr, float), np.array(R, float)
def chain_pose(s_, ch):
    tu, Ru = loc(s_, ch.u); th, Rh = loc(s_, ch.h); te, Re = loc(s_, ch.e)
    return tu + Ru @ th, tu + Ru @ (th + Rh @ te), Ru @ Rh @ Re, H.hinge_split(ch.Rh0.T @ Rh)
worst = {}
for f in files:
    a = KFEval(os.path.join(o, f)); b = KFEval(os.path.join(fx, f)); L = a.stop
    for i in range(31):
        t = L * i / 30; sa = a.sample(t); sb = b.sample(t)
        for ch in chains:
            Ea, Wa, Ha, (pa, oa) = chain_pose(sa, ch); Eb, Wb, Hb, (pb, ob) = chain_pose(sb, ch)
            dw = np.linalg.norm(Wa - Wb); dr = np.degrees(np.arccos(np.clip((np.trace(Ha.T @ Hb) - 1) / 2, -1, 1))); de = np.linalg.norm(Ea - Eb)
            k = (f, ch.h.replace('Bip01 ', ''))
            w = worst.setdefault(k, [0, 0, 0, 0, 0, 1e9, -1e9])
            w[0] = max(w[0], dw); w[1] = max(w[1], dr); w[2] = max(w[2], de); w[3] = max(w[3], oa); w[4] = max(w[4], ob); w[5] = min(w[5], pb); w[6] = max(w[6], pb)
print('%-34s %-12s %8s %8s %8s %8s %8s  %s' % ('file', 'chain', 'endpos', 'endrot', 'elbow', 'offBefore', 'offAfter', 'hinge range after'))
for (f, c), w in sorted(worst.items()):
    print('%-34s %-12s %8.2f %8.2f %8.2f %8.1f %8.2f  [%d, %d]' % (f, c, *w[:5], w[5], w[6]))
