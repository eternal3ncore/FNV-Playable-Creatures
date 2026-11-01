"""Wrist clamp for generated gun animations: where the weapon hand bends past the creature's own range (audit limit),
its local rotation is eased (slerp, per frame, the least amount needed) toward the hand's rotation in the weapon's
plain aim of the same type - the gun tilts a little less in the reload / jam, the wrist stays in range.
usage: python3 wrist_clamp.py <folder> <audit json (after the hinge fix)>"""
import sys, os, re, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval, Skeleton, m2q, q2m
import audit_twist as A, hinge_fix as H, retarget_idle as RI
folder, aj = sys.argv[1], sys.argv[2]
rep = json.load(open(aj))
lim = max(f['lim'] for f in rep['flags'] if f.get('bone') == 'Bip01 R Hand' and f.get('kind') == 'swing') if any(
    f.get('bone') == 'Bip01 R Hand' and f.get('kind') == 'swing' for f in rep['flags']) else None
files = sorted({f['file'] for f in rep['flags'] if f.get('bone') == 'Bip01 R Hand' and f.get('kind') == 'swing'})
if not files: print('nothing to clamp'); sys.exit()
sk = Skeleton(os.path.join(folder, 'Skeleton.nif')); ax = A.axes(sk)
idle = KFEval(os.path.join(folder, 'mtidle.kf')).sample(0)
R0 = np.asarray(idle['Bip01 R Hand'][1] if idle.get('Bip01 R Hand') and idle['Bip01 R Hand'][1] is not None else sk.local['Bip01 R Hand'][1], float)
target = lim - 2.0; n = 0
for fn in files:
    m = re.match(r'^(sneak)?(h2h|1hm|2hm|1hp|2hr|2ha|2hh|2hl|1gt|1md|1lm)', fn.lower())
    if not m: continue
    aim = os.path.join(folder, f'{m.group(2)}aim.kf')
    if not os.path.exists(aim): continue
    Ra = KFEval(aim).sample(0).get('Bip01 R Hand')
    if not Ra or Ra[1] is None: continue
    Ra = np.asarray(Ra[1], float)
    if A.swing_twist(R0.T @ Ra, ax['Bip01 R Hand'])[1] > target: continue      # the aim itself is beyond: leave
    k = KFEval(os.path.join(folder, fn)); L = k.stop; nf = max(2, int(round(L * 30)) + 1); keys = []
    for i in range(nf):
        t = L * i / (nf - 1); s = k.sample(t); tr, R = s['Bip01 R Hand']; R = np.asarray(R, float)
        if A.swing_twist(R0.T @ R, ax['Bip01 R Hand'])[1] > target:
            lo, hi = 0.0, 1.0
            for _ in range(20):
                u = (lo + hi) / 2; Ru = q2m(RI.slerp(m2q(R), m2q(Ra), u))
                if A.swing_twist(R0.T @ Ru, ax['Bip01 R Hand'])[1] > target: lo = u
                else: hi = u
            R = q2m(RI.slerp(m2q(R), m2q(Ra), hi))
        keys.append((t, np.asarray(tr, float), R))
    H.write_tracks(os.path.join(folder, fn), {'Bip01 R Hand': keys}, 65); n += 1
print(n, 'files wrist-clamped (limit %d)' % lim)
