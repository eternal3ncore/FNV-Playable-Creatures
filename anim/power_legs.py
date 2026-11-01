"""Directional power attacks slide. The player keeps moving during a power attack (a side power attack is
done while strafing), and the creatures' own directional power attacks that key the legs planted (no root travel)
hold the feet still while the actor moves = slide (Super Mutant unarmed side power attacks). The human ones
take a step in the direction of travel. Fix: such files (Forward / Back / Left / Right power, root travel < LUNGE,
standing and sneak) stop keying the lower body - accum root, NonAccum, Pelvis, Footsteps, the legs - so the
movement animation (strafe / walk / sneak) drives the legs and the attack plays above it. Lunges (root travel
>= LUNGE: the creature's own charges / leaps) are left alone. Rigs whose thighs hang on Bip01 Spine (ghoul,
swampfolk, trog, tunneler): Spine is dropped too and Spine1 re-solved on the idle's hip (hip_spine_fix.upper_fix).
usage: python3 power_legs.py <race folder> [--apply]"""
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile
from hip_spine_fix import drop_channel, upper_fix, HIP

LUNGE = 60.0
PAT = re.compile(r'^(sneak)?(h2h|1hm|2hm)attack(forward|back|left|right)power\.kf$', re.I)


def root_travel(sk, k):
    b0 = None; tr = 0.0
    for t in np.linspace(k.start, k.stop, 15):
        s = k.sample(t); W = sk.fk({n: v for n, v in s.items() if n in sk.local})
        if b0 is None: b0 = W['Bip01'][0]
        tr = max(tr, float(np.linalg.norm((W['Bip01'][0] - b0)[:2])))
    return tr


def lower_bones(sk):
    kids = {}
    for n, p in sk.parent.items(): kids.setdefault(p, []).append(n)
    low = {'Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis', 'Bip01 Footsteps'}
    stack = [n for n in sk.local if 'Thigh' in n]
    while stack:
        n = stack.pop()
        if n.startswith('Bip01'): low.add(n)
        stack += kids.get(n, [])
    return low


def run(folder, apply=False):
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    hip_rig = any('Thigh' in c for c, p in sk.parent.items() if p == HIP)
    low = lower_bones(sk)
    mt = KFEval(os.path.join(folder, 'mtidle.kf')).sample(0)
    sn = dict(mt); ks = KFEval(os.path.join(folder, 'sneakmtidle.kf')); sn.update(ks.sample(ks.start))
    rep = []; n = 0
    for f in sorted(os.listdir(folder)):
        if not PAT.match(f): continue
        p = os.path.join(folder, f); k = KFEval(p)
        keyed = [c for c in k.chan if c in low]
        if not any('Thigh' in c for c in keyed): continue
        tr = root_travel(sk, k)
        if tr >= LUNGE: rep.append(f'{f}: lunge (root {tr:.0f}) - kept'); continue
        kf = KFFile(p)
        for c in keyed: drop_channel(kf, c)
        n += 1
        if not apply: rep.append(f'{f}: root {tr:.0f}, drop {len(keyed)} lower-body channels'); continue
        kf.save()
        msg = f'{f}: root {tr:.0f}, dropped {len(keyed)} lower-body channels'
        if hip_rig:
            kf2, dev = upper_fix(sk, p, sn if f.lower().startswith('sneak') else mt)
            if kf2: kf2.save(); msg += f'; Spine dropped, Spine1 re-solved (hip was {dev:.0f} deg off the idle)'
        rep.append(msg)
    rep.append(f'{n} files')
    return rep


if __name__ == '__main__':
    for line in run(sys.argv[1], apply='--apply' in sys.argv): print(line)
