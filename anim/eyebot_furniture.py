"""Eyebot furniture idles: the human chair (4 sides) / stool enter + exit, seated loop and relax specials, turned into
the eyebot settling onto the seat. It follows the human's entry path (Bip01) and heading, its hover height mapped from
the human's hip height (standing -> its own hover, chair seat -> resting on a chair seat, stool seat -> resting on a
stool); every other bone holds its idle pose at t=0, so it sits unanimated (no bob, no antenna sway).
usage: python3 eyebot_furniture.py <out dir> [creature cfg]   (default eyebot_sit; the mirelurk uses it too: its
SPHERE_LOW = its own head height, so it climbs up and stands on the seat in its idle pose)"""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval, Skeleton
from rig import Creature, write_kf
import retarget_idle as RI, retarget_idle_creature as RC

cfg = importlib.import_module('creatures.' + (sys.argv[2] if len(sys.argv) > 2 else 'eyebot_sit'))
cr = Creature(cfg)
CHAIR_SEAT, STOOL_SEAT = 30.0, 46.0          # vanilla chair / bar-stool seat heights (human hip node 36.85 / 54.55 seated)
def heading(R):
    v = R[:, 1]; return np.arctan2(v[1], v[0])
def rz(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

def build(out_dir, fps=30):
    sk = cr.sk
    ip = KFEval(os.path.join(cfg.ANIM_SRC, cfg.IDLE_KF)).sample(0.0)
    idle_keyed = [n for n in sk.order if n in ip and n not in ('Bip01', 'Bip01 NonAccum')]
    loc0 = {}
    for n in sk.order:
        t, R, _ = sk.local[n]
        if n in ip:
            if ip[n][0] is not None: t = ip[n][0]
            if ip[n][1] is not None: R = ip[n][1]
        loc0[n] = (np.array(t, float), np.array(R, float))
    W0 = sk.fk(loc0); g0 = W0['Bip01'][0][2]
    hover = W0[cfg.BONES['head']][0][2] - g0                      # head (sphere) height above the floor
    na_z0 = loc0['Bip01 NonAccum'][0][2]
    pts = [(RI.Z_SEAT[0], CHAIR_SEAT + cfg.SPHERE_LOW), (54.55, STOOL_SEAT + cfg.SPHERE_LOW), (RI.Z_STAND[0], hover)]
    def height(z):
        if z <= pts[0][0]: return pts[0][1] + (z - pts[0][0])
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            if z <= a1: return b0 + (z - a0) * (b1 - b0) / (a1 - a0)
        return hover + (z - pts[-1][0])
    hi = KFEval('/home/claude/fnv/ref_male/1hmidle.kf').sample(0.0)
    h_ref = heading(np.array(hi['Bip01 NonAccum'][1], float))
    os.makedirs(out_dir, exist_ok=True); rep = []
    for out, src, _ in RC.JOBS:
        k = KFEval(RC.HUMAN_SIT + src); L = k.stop; n = int(round(L * fps)) + 1
        keyed = {b[0] for b in k.blocks}; prio = max(b[2] for b in k.blocks)
        frames = []
        for i in range(n):
            t = L * i / (n - 1); s = k.sample(t); loc = dict(loc0)
            if 'Bip01' in keyed and 'Bip01' in s:
                bt, bR = s['Bip01']; loc['Bip01'] = (np.array(bt if bt is not None else loc0['Bip01'][0], float),
                                                     np.array(bR if bR is not None else loc0['Bip01'][1], float))
            nt, nR = s['Bip01 NonAccum']
            nt = np.array(nt, float); nR = np.array(nR, float)
            a = heading(nR) - h_ref
            loc['Bip01 NonAccum'] = (np.array([nt[0], nt[1], na_z0 + height(nt[2]) - hover]), rz(a) @ loc0['Bip01 NonAccum'][1])
            frames.append((t, loc))
        names = (['Bip01'] if 'Bip01' in keyed else []) + ['Bip01 NonAccum'] + idle_keyed
        write_kf(cr, os.path.join(out_dir, out), k.name, L, RI.keys_of(k), frames, bones=[(nm, prio) for nm in names], cycle=k.cycle)
        rep.append((out, k.name, round(L, 2), round(min(height(KFEval(RC.HUMAN_SIT + src).sample(L * j / 20)['Bip01 NonAccum'][0][2]) for j in range(21)), 1)))
    return hover, rep

if __name__ == '__main__':
    hover, rep = build(sys.argv[1])
    print('hover %.1f' % hover)
    for r in rep: print(r)
