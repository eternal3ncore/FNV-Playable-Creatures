"""Mirelurk furniture idles: it settles its shell onto the seat (a crab's sitting). The human chair (4 sides) / stool
enter + exit, seated loop and relax specials give the entry path (Bip01) and heading; its own idle keeps playing on
top; the body height follows the human's hip height (standing -> its own standing height, chair seat -> belly on a
chair seat, stool seat -> belly on a bar stool), and as the body drops its legs fold to keep the feet on the floor
(2-bone IK thigh / calf / foot to where the idle puts the feet, knees forward).
Replaces the "stands on the seat" set (eyebot_furniture.py): it read as standing and floating up onto the seat.
usage: python3 mirelurk_sit.py <out dir>"""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval
from rig import Creature, write_kf, align, rotm
import retarget_idle as RI, retarget_idle_creature as RC, loco2

CHAIR_SEAT, STOOL_SEAT = 30.0, 46.0          # vanilla chair / bar-stool seat heights (human hip node 36.85 / 54.55 seated)
BELLY = 14.0                                 # NonAccum (shell centre) above the seat when sitting
cfg = importlib.import_module('creatures.mirelurk')
cr = Creature(cfg); sk = cr.sk; B = cfg.BONES


def heading(R):
    v = R[:, 1]; return np.arctan2(v[1], v[0])


def rz(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def full(sample):
    out = {}
    for n in sk.order:
        t, R, _ = sk.local[n]
        if n in sample:
            if sample[n][0] is not None: t = sample[n][0]
            if sample[n][1] is not None: R = sample[n][1]
        out[n] = (np.array(t, float), np.array(R, float))
    return out


idle = KFEval(os.path.join(cfg.ANIM_SRC, cfg.IDLE_KF))
loc0 = full(idle.sample(0.0)); loc0['Bip01'] = (np.zeros(3), np.eye(3))
na_z0 = float(loc0['Bip01 NonAccum'][0][2])                     # its standing NonAccum height
pts = [(RI.Z_SEAT[0], CHAIR_SEAT + BELLY), (54.55, STOOL_SEAT + BELLY), (RI.Z_STAND[0], na_z0)]


def height(z):
    if z <= pts[0][0]: return pts[0][1] + (z - pts[0][0])
    for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
        if z <= a1: return b0 + (z - a0) * (b1 - b0) / (a1 - a0)
    return na_z0 + (z - pts[-1][0])


def build(out_dir, fps=30):
    keyed = [b[0] for b in idle.blocks if b[0] not in ('Bip01', 'Bip01 NonAccum')]
    hi = KFEval('/home/claude/fnv/ref_male/1hmidle.kf').sample(0.0)
    h_ref = heading(np.array(hi['Bip01 NonAccum'][1], float))
    os.makedirs(out_dir, exist_ok=True); rep = []
    for out, src, _ in RC.JOBS:
        k = KFEval(RC.HUMAN_SIT + src); L = k.stop; n = int(round(L * fps)) + 1
        hkeyed = {b[0] for b in k.blocks}; prio = max(b[2] for b in k.blocks)
        frames = []; low = 1e9
        for i in range(n):
            t = L * i / (n - 1); s = k.sample(t)
            loc = full(idle.sample(t % idle.stop))
            # its idle in place (accum root at the origin) - where the feet stand
            loc['Bip01'] = (np.zeros(3), np.eye(3)); W0 = sk.fk(loc)
            feet = {sd: (W0[B['leg_' + sd][2]][0].copy(), W0[B['leg_' + sd][2]][1].copy(), W0[B['leg_' + sd][1]][0].copy())
                    for sd in 'LR'}
            # the drop: NonAccum lowered to the mapped height, in place
            nt, nR = s['Bip01 NonAccum']; nt = np.array(nt, float)
            z = height(nt[2]); dz = float(loc['Bip01 NonAccum'][0][2]) - z
            rt, rR = loc['Bip01 NonAccum']
            loc['Bip01 NonAccum'] = (rt - np.array([0, 0, dz]), rR)
            for sd in 'LR':
                th, ca, ft = B['leg_' + sd][:3]
                pos, rot, knee = feet[sd]
                loco2._leg_ik(sk, loc, th, ca, ft, pos, rot, knee + np.array([0, 40.0, -dz]))
            # then the human's entry path (Bip01) and heading (NonAccum turned about z, x / y from the human)
            if 'Bip01' in hkeyed and 'Bip01' in s:
                bt, bR = s['Bip01']
                loc['Bip01'] = (np.array(bt if bt is not None else (0, 0, 0), float), np.array(bR if bR is not None else np.eye(3), float))
            a = heading(np.array(nR, float)) - h_ref
            rt, rR = loc['Bip01 NonAccum']
            loc['Bip01 NonAccum'] = (np.array([nt[0], nt[1], rt[2]]), rz(a) @ rR)
            low = min(low, z); frames.append((t, loc))
        names = (['Bip01'] if 'Bip01' in hkeyed else []) + ['Bip01 NonAccum'] + keyed
        write_kf(cr, os.path.join(out_dir, out), k.name, L, RI.keys_of(k), frames, bones=[(nm, prio) for nm in names], cycle=k.cycle)
        rep.append((out, k.name, round(L, 2), round(low, 1)))
    return rep


if __name__ == '__main__':
    for r in build(sys.argv[1]): print(r)
