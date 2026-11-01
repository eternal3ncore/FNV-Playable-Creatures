"""Legs that ride on the spine. In the feral ghoul and swampfolk (Brawler / Scrapper / Creeper) rigs the
thighs are children of Bip01 Spine (the hip bone); Bip01 Pelvis is a leaf. Their vanilla animations key Spine and the
legs together. The generated upper-body animations (aims, attacks, reloads, jams, throws...) key Spine too (at the
standing idle's value) but not the legs, so in game the legs come from the idle / locomotion while their hip comes
from the gun file: in sneak (crouched idle, different hip) the lower legs swing forward and float. And sneak_fix
which assumed thighs under the pelvis, re-aimed Spine of the sneak copies of full-body files to the standing
orientation with the legs hanging from it (Swampfolk sneak reloads: toes up to 44 under the floor).
  1. upper-body files (key Spine, no thigh): the Spine channel is dropped, so the hip and legs are always the idle's /
     locomotion's; Bip01 Spine1 is re-solved per frame to keep the world transform the file gave it, measured on the
     idle's hip (standing files: mtidle t=0, sneak files: sneakmtidle t=0). If the file doesn't key Spine1, the Spine
     entry is re-targeted to Spine1.
  2. sneak copies of full-body files (--crouch, run on the pre-sneak_fix originals): NonAccum, Pelvis, Spine and the
     legs = sneakmtidle t=0; Spine1 re-solved to keep the standing file's world orientation (aim direction).
usage: python3 hip_spine_fix.py <race folder> [--crouch file,file,...] [--apply]"""
import os, re, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile, times
from sneak_fix import orth, fix_file as crouch_file

HIP, UP = 'Bip01 Spine', 'Bip01 Spine1'


def fk_world(sk, pose, upto):
    """world (p, R) of `upto` for pose name -> (t, R) (missing / None = bind)"""
    chain = []; n = upto
    while n is not None: chain.append(n); n = sk.parent.get(n)
    p = np.zeros(3); R = np.eye(3)
    for n in reversed(chain):
        if n not in sk.local: continue
        t, r = (pose.get(n) or (None, None))
        t = sk.local[n][0] if t is None else t; r = sk.local[n][1] if r is None else r
        if n == 'Bip01': t = np.zeros(3)                     # accum root at the actor origin
        p = p + R @ np.asarray(t); R = R @ np.asarray(r)
    return p, R


def drop_channel(kf, name):
    f = kf.f; d = f.blocks[kf.seq]
    nm, ncb, sz = struct.unpack_from('<iII', d, 0)
    keep = [d[12 + 29 * k: 12 + 29 * (k + 1)] for k in range(ncb) if kf.cb[k][1] != name]
    f.blocks[kf.seq] = struct.pack('<iII', nm, len(keep), sz) + b''.join(keep) + d[12 + 29 * ncb:]
    kf.cb = [(12 + 29 * i, n) for i, (o, n) in enumerate([c for c in kf.cb if c[1] != name])]


def retarget_channel(kf, old, new):
    f = kf.f; d = bytearray(f.blocks[kf.seq])
    o = [o for o, n in kf.cb if n == old][0]
    struct.pack_into('<i', d, o + 9, f.str_index(new)); f.blocks[kf.seq] = bytes(d)
    kf.cb = [(oo, new if n == old else n) for oo, n in kf.cb]


def upper_fix(sk, path, under):
    k = KFEval(path)
    if HIP not in k.chan or any('Thigh' in n for n in k.chan): return None, 0.0
    hip_u = under.get(HIP, (None, None))
    keys = []; dev = 0.0
    for t in times(k):
        s = k.sample(t)
        P = dict(under); P.update(s)
        p1, R1 = fk_world(sk, P, UP)                         # Spine1 world as the file has it
        P2 = dict(P); P2[HIP] = hip_u
        pp, Rp = fk_world(sk, P2, HIP)                       # the idle's hip
        tr = Rp.T @ (p1 - pp); Rl = orth(Rp.T @ R1)
        keys.append((t, tr, Rl))
        a = s[HIP][1] if s[HIP][1] is not None else sk.local[HIP][1]
        b = hip_u[1] if hip_u[1] is not None else sk.local[HIP][1]
        dev = max(dev, np.degrees(np.arccos(np.clip((np.trace(np.asarray(a).T @ np.asarray(b)) - 1) / 2, -1, 1))))
    if all(np.allclose(keys[0][1], x[1], atol=1e-4) and np.allclose(keys[0][2], x[2], atol=1e-5) for x in keys): keys = [keys[0]]
    kf = KFFile(path)
    if UP in k.chan:
        kf.set_channel(UP, keys); drop_channel(kf, HIP)
    else:
        retarget_channel(kf, HIP, UP); kf.set_channel(UP, keys)
    return kf, dev


def lower_set(sk):
    kids = {}
    for n, p in sk.parent.items(): kids.setdefault(p, []).append(n)
    low = {'Bip01 NonAccum', 'Bip01 Pelvis', HIP}
    stack = [c for c in kids.get(HIP, []) if 'Thigh' in c]
    while stack:
        n = stack.pop()
        if n.startswith('Bip01'): low.add(n)
        stack += kids.get(n, [])
    return low


def run(folder, crouch_files=(), apply=False):
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    assert 'Thigh' in ' '.join(c for c, p in sk.parent.items() if p == HIP), 'thighs are not under Bip01 Spine in this rig'
    mt = KFEval(os.path.join(folder, 'mtidle.kf')).sample(0)
    ks = KFEval(os.path.join(folder, 'sneakmtidle.kf')); sn = dict(mt); sn.update(ks.sample(ks.start))
    rep = []
    low = lower_set(sk); crouch = {n: v for n, v in sn.items() if n in low}
    for f in crouch_files:
        kf, lowk, upk = crouch_file(sk, os.path.join(folder, f), crouch, low, [UP])
        if apply: kf.save()
        rep.append(f'crouch {f}: lower {len(lowk)} bones, upper root {upk}')
    n = 0
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith('.kf'): continue
        under = sn if f.lower().startswith('sneak') else mt
        p = os.path.join(folder, f)
        kf, dev = upper_fix(sk, p, under)
        if kf is None: continue
        n += 1
        if apply: kf.save()
        rep.append(f'{f}: Spine dropped (keyed hip differed from the idle by up to {dev:.0f} deg)')
    rep.append(f'{len(crouch_files)} crouched, {n} upper-body files without Spine')
    return rep


if __name__ == '__main__':
    folder = sys.argv[1]
    cf = sys.argv[sys.argv.index('--crouch') + 1].split(',') if '--crouch' in sys.argv else []
    for line in run(folder, cf, apply='--apply' in sys.argv): print(line)
