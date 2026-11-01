"""Toes below the floor. The Swampfolk Tracker / Bruiser sneak idle (human sneak kneel retargeted onto
its bigger feet) kneels with the right toe 17 units under the floor; every sneak file that doesn't key the legs plays
that idle's legs, and sneak_fix copied the same crouch into the sneak aims / equips. Per file that keys a foot and per
key time: where the toe (Bip01 <side> Toe0) is below TRIGGER (-1), the foot is turned about the ankle, the least amount that
lifts the toe to FLOOR (horizontal direction kept; the top of the foot lies on the floor, as in a kneel).
Only the Foot channel changes (new interpolator / data blocks, resampled at 30 fps where corrected); the knee, ankle
position and every other bone are untouched. Heights are measured as the game places the body: accum root (Bip01) at
0, unkeyed bones from the race's idle (sneak files: sneakmtidle, already corrected first).
usage: python3 foot_ground.py <race folder> <file,file,...|--sneak> [--apply]"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile, times
from sneak_fix import orth

FLOOR = 0.5
TRIGGER = -1.0                       # toes between TRIGGER and FLOOR are left as they are
SIDES = ('L', 'R')


def align(u, v):
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    c = float(np.dot(u, v)); ax = np.cross(u, v); s = np.linalg.norm(ax)
    if s < 1e-9: return np.eye(3)
    ax /= s; K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def world(sk, s, under):
    pose = dict(under); pose.update(s)
    pose = {n: v for n, v in pose.items() if n in sk.local}
    pose['Bip01'] = (np.zeros(3), pose['Bip01'][1] if 'Bip01' in pose and pose['Bip01'][1] is not None else np.eye(3))
    return sk.fk(pose)


def fix_file(sk, path, under):
    k = KFEval(path); feet = [sd for sd in SIDES if f'Bip01 {sd} Foot' in k.chan]
    if not feet: return None, 0.0
    ts = times(k); out = {}; worst = 0.0
    for sd in feet:
        F, T = f'Bip01 {sd} Foot', f'Bip01 {sd} Toe0'
        par = sk.parent[F]; keys = []; changed = False
        for t in ts:
            s = k.sample(t); W = world(sk, s, under)
            a, Rf = W[F]; tp = W[T][0]; v = tp - a
            tr = s[F][0] if s[F][0] is not None else sk.local[F][0]
            Rl = s[F][1] if s[F][1] is not None else sk.local[F][1]
            if tp[2] < TRIGGER:
                worst = min(worst, tp[2]); L = np.linalg.norm(v)
                dz = max(FLOOR - a[2], -L * 0.999)
                h = v[:2]; hn = np.linalg.norm(h)
                h = h / hn if hn > 1e-6 else np.array([0.0, -1.0])
                v2 = np.array([*(h * np.sqrt(max(L * L - dz * dz, 0.0))), dz])
                Rw = align(v, v2) @ Rf
                Rl = orth(W[par][1].T @ Rw); changed = True
            keys.append((t, np.array(tr), np.array(Rl)))
        if changed:
            if all(np.allclose(keys[0][2], x[2], atol=1e-5) for x in keys): keys = [keys[0]]
            out[F] = keys
    if not out: return None, worst
    kf = KFFile(path)
    for F, keys in out.items(): kf.set_channel(F, keys)
    return kf, worst


def run(folder, files, apply=False):
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    rep = []; n = 0
    idle = 'sneakmtidle.kf'
    mt = KFEval(os.path.join(folder, 'mtidle.kf')).sample(0)
    # 1) the sneak idle itself (over the standing idle for anything it doesn't key)
    if idle in files:
        kf, w = fix_file(sk, os.path.join(folder, idle), mt)
        if kf:
            n += 1; rep.append(f'{idle}: toe {w:.1f} -> {FLOOR}')
            if apply: kf.save()
            else: kf.save('/tmp/_foot_ground_idle.kf')
    ip = os.path.join(folder, idle) if apply else ('/tmp/_foot_ground_idle.kf' if os.path.exists('/tmp/_foot_ground_idle.kf') else os.path.join(folder, idle))
    under_s = KFEval(ip).sample(0)
    for f in files:
        if f == idle: continue
        under = under_s if os.path.basename(f).lower().startswith('sneak') else mt
        kf, w = fix_file(sk, os.path.join(folder, f), under)
        if kf:
            n += 1; rep.append(f'{f}: toe {w:.1f} -> {FLOOR}')
            if apply: kf.save()
    rep.append(f'{n} files corrected')
    return rep


if __name__ == '__main__':
    folder = sys.argv[1]
    if sys.argv[2] == '--sneak':
        files = sorted(f for f in os.listdir(folder) if f.lower().startswith('sneak') and f.lower().endswith('.kf'))
        files += sorted(os.path.join('Locomotion', f) for f in os.listdir(os.path.join(folder, 'Locomotion'))
                        if f.lower().startswith('sneak') and f.lower().endswith('.kf')) if os.path.isdir(os.path.join(folder, 'Locomotion')) else []
    else:
        files = sys.argv[2].split(',')
    for line in run(folder, files, apply='--apply' in sys.argv): print(line)
