"""Sneak crouch fix. Many sneak<type><group>.kf files are copies of the standing file (build_creature's
"sneak copies of stance-independent groups", own creature files), and they key the pelvis / legs at standing height,
so the creature stands up while the group plays (aims, attacks, reloads, equips...). Vanilla human sneak files key the
legs too, but crouched. For every sneak file whose pelvis (accum root at 0, height = NonAccum) is nearer the standing
idle than the sneak idle (sneak_audit.py):
  lower body  = NonAccum, Bip01 Pelvis and its descendants -> the race's sneakmtidle first frame (its own crouch)
  upper body  = the roots of the upper chain (Bip01 Spine etc., children of NonAccum / Pelvis outside the lower set):
                local rotation re-solved each frame so their WORLD orientation stays the standing file's -> aim direction,
                swings, reloads unchanged, only lowered with the crouch
Only those channels change (new interpolator blocks). Groups without a sneak version (not movement / Death / Hurt)
get one: the standing file copied under the sneak name, then fixed the same way.
usage: python3 sneak_fix.py <race folder> [types] [--apply]"""
import os, re, shutil, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile, times
from sneak_audit import scan, pelvis_z, TYPES, MOVE

SKIP_NEW = re.compile(r'(Death|_Hurt$)', re.I)
MOVE_L = {m.lower() for m in MOVE}               # movement groups (some files name them in lower case: 'forward', 'backWard')


def lower_set(sk):
    kids = {}
    for n, p in sk.parent.items(): kids.setdefault(p, []).append(n)
    upper_roots = [c for c in kids.get('Bip01 Pelvis', []) + kids.get('Bip01 NonAccum', []) if 'Spine' in c]
    up = set()
    stack = list(upper_roots)
    while stack:
        n = stack.pop(); up.add(n); stack += kids.get(n, [])
    low = {'Bip01 NonAccum', 'Bip01 Pelvis'}
    stack = list(kids.get('Bip01 Pelvis', []))
    while stack:
        n = stack.pop()
        if n in up: continue
        if n.startswith('Bip01'): low.add(n)           # biped bones only (grafted FX / weapon nodes under the pelvis stay)
        stack += kids.get(n, [])
    return low, upper_roots


def orth(M):
    """nearest rotation (the skeleton's bind matrices are slightly non-orthonormal; m2q needs a clean one)"""
    U, _, Vt = np.linalg.svd(M); R = U @ Vt
    if np.linalg.det(R) < 0: U[:, -1] *= -1; R = U @ Vt
    return R


def world_R(sk, pose, name):
    """world rotation of `name` (accum root rotation included), pose: name -> (t, R)"""
    chain = []
    n = name
    while n is not None:
        chain.append(n); n = sk.parent.get(n)
    R = np.eye(3)
    for n in reversed(chain):
        if n not in sk.local: continue
        r = pose[n][1] if n in pose and pose[n][1] is not None else sk.local[n][1]
        R = R @ r
    return R


def fix_file(sk, path, crouch, low, uroots):
    k = KFEval(path); ts = times(k)
    keyed = set(k.chan)
    lowk = [n for n in low if n in keyed and n in crouch]      # only bones the crouch pose has
    upk = [n for n in uroots if n in keyed]
    kf = KFFile(path)
    for n in lowk:
        t, R = crouch[n]
        if t is None: t = sk.local[n][0]
        if R is None: R = sk.local[n][1]
        kf.set_channel(n, [(k.start, np.array(t), np.array(R))])
    for n in upk:
        keys = []
        par = sk.parent[n]
        for t in ts:
            s = k.sample(t)
            new = dict(s); new.update({b: crouch[b] for b in lowk if b in crouch})
            Rw = world_R(sk, s, n)                               # standing world orientation
            Rp = world_R(sk, new, par)                           # crouched parent
            tr = s[n][0] if s[n][0] is not None else sk.local[n][0]
            keys.append((t, np.array(tr), orth(Rp.T @ Rw)))
        if all(np.allclose(keys[0][2], x[2], atol=1e-5) for x in keys): keys = [keys[0]]
        kf.set_channel(n, keys)
    return kf, lowk, upk


def run(folder, types, apply=False):
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif')); G = scan(folder)
    low, uroots = lower_set(sk)
    zst = pelvis_z(sk, os.path.join(folder, G[(False, 'mt', 'Idle')][0]))
    sidle = os.path.join(folder, G[(True, 'mt', 'Idle')][0]); zsn = pelvis_z(sk, sidle)
    ks = KFEval(sidle); crouch = {n: v for n, v in ks.sample(ks.start).items() if n in low}
    mid = (zst + zsn) / 2; rep = []; n_fix = n_new = 0
    for T in types:
        # missing sneak groups -> copies of the standing files
        for (s, t, g), files in list(G.items()):
            if s or t != T or g.lower() in MOVE_L or SKIP_NEW.search(g) or (True, t, g) in G: continue
            for f in files:
                d, fn = os.path.split(f); new = os.path.join(d, 'sneak' + fn)
                rep.append(f'new {new} (copy of {f})'); n_new += 1
                if apply: shutil.copyfile(os.path.join(folder, f), os.path.join(folder, new))
                G.setdefault((True, t, g), []).append(new)
        for (s, t, g), files in G.items():
            if not s or t != T: continue
            for f in files:
                p = os.path.join(folder, f)
                if not os.path.exists(p): continue          # dry run: new copies don't exist yet
                z = pelvis_z(sk, p)
                if z is None or z <= mid: continue
                kf, lowk, upk = fix_file(sk, p, crouch, low, uroots)
                if apply: kf.save()
                n_fix += 1
                rep.append(f'{f}: pelvis {z:.0f} -> crouch {zsn:.0f} (lower {len(lowk)} bones, upper roots {upk})')
    rep.append(f'standing {zst:.1f} sneak {zsn:.1f}; fixed {n_fix}, new {n_new}')
    return rep


if __name__ == '__main__':
    folder = sys.argv[1]
    types = sys.argv[2].split(',') if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else TYPES
    for line in run(folder, types, apply='--apply' in sys.argv): print(line)
