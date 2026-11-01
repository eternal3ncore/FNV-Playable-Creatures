"""Vanilla human sneak locomotion on a human-proportioned creature skeleton, keeping the creature's character.
usage: python3 sneak_human.py <creature cfg> <human sneak dir> <out dir> [arm weight, 0 own .. 1 human; 0.35]

Legs, pelvis and root motion: the human sneak files retargeted (retarget_idle.IdleRetarget: world-space bone deltas,
leg IK with ground contact, accum root copied so the travel speed is the vanilla sneak speed; NonAccum height scaled
by the leg-length ratio). Torso: the retargeted human spine, leaned further forward (constant per file) when the human
lean is less than the creature's own idle hunch - the sneak never stands straighter than the creature does. Neck: the
creature's own; head: the creature idle's world orientation (gaze ahead). Arms: the retargeted human arm world
orientations blended (slerp, per bone local) with the creature idle's arm pose - the creature's own arm carriage with
some of the human swing.
Text keys (footsteps), length and cycle are the human file's; the accum root is keyed only where the human file keys it
(in game it is the actor origin; unkeyed it would sample the skeleton's bind height).
v1 scaled the NonAccum height by (creature idle height / human standing height): the ghost idle is already crouched,
so the sneak idle sat on the ground; and it stacked the creature idle spine on the human sneak pelvis (over-hunched)."""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval, m2q, q2m
from rig import Creature, Rig, write_kf, rotm
import retarget_idle as RI

X = np.array([1.0, 0, 0])

def _fk(cr, loc):
    W = {}
    for nm in cr.sk.order:
        t, R = loc[nm]; p = cr.sk.parent[nm]
        W[nm] = (t.copy(), R.copy()) if p is None else (W[p][0] + W[p][1] @ t, W[p][1] @ R)
    return W

def lean(W):
    d = W['Bip01 Neck'][0] - W['Bip01 Pelvis'][0]
    return np.degrees(np.arctan2(d[1], d[2]))

def build(cfgname, src_dir, out, w_arm=0.35, fps=30, only=None):
    cfg = importlib.import_module('creatures.' + cfgname); cr = Creature(cfg)
    rt = RI.IdleRetarget(RI.HUMAN_SKEL, cfg.SKELETON)
    rt.map_z = lambda z: z * rt.ratio
    base = Rig(cr, base_kf=cfg.IDLE_KF).base                 # creature idle locals (accum at the origin)
    acc = cfg.ACCUM_ROOT
    base[acc] = (np.zeros(3), np.eye(3))
    Wb = _fk(cr, base); lean_own = lean(Wb)
    b = cfg.BONES
    spine = [n for n in cr.spine if n in cr.sk.local]
    neck = [n for n in b.get('neck', []) if n in cr.sk.local]
    armb = []
    for side in ('L', 'R'): armb += [n for n in list(cr.arm[side]) + list(cr.fingers[side]) if n in cr.sk.local]
    os.makedirs(out, exist_ok=True)
    done = []
    for fn in sorted(os.listdir(src_dir)):
        if not fn.lower().startswith('sneakmt') or 'jump' in fn.lower(): continue
        if only and fn.lower() not in only: continue
        k = KFEval(os.path.join(src_dir, fn)); L = k.stop; n = max(2, int(round(L * fps)) + 1)
        keyed_acc = acc in k.sample(0) and k.sample(0)[acc][0] is not None
        raw = []
        for i in range(n):
            t = L * i / (n - 1)
            loc = rt.frame(k, t)
            for nm in cr.sk.order:
                if nm not in loc: loc[nm] = base[nm]
            if not keyed_acc:                                   # accum root = actor origin
                W = _fk(cr, loc); z0 = W[acc][0][2]
                loc[acc] = (np.zeros(3), np.eye(3))
            raw.append((t, loc))
        lh = np.mean([lean(_fk(cr, l)) for _, l in raw])
        extra = max(0.0, lean_own - lh)
        frames = []
        for t, loc in raw:
            W0 = _fk(cr, loc)
            for nm in spine:
                W = _fk(cr, loc); p = cr.sk.parent[nm]
                loc[nm] = (loc[nm][0], W[p][1].T @ rotm(X, -extra / len(spine)) @ W[nm][1])
            for nm in neck: loc[nm] = (loc[nm][0], base[nm][1].copy())
            W = _fk(cr, loc); p = cr.sk.parent[cr.head]
            loc[cr.head] = (loc[cr.head][0], W[p][1].T @ Wb[cr.head][1])
            hum = {}
            for nm in cr.sk.order:                              # human arm: retargeted world rotation kept
                if nm in armb:
                    W = _fk(cr, loc); p = cr.sk.parent[nm]
                    loc[nm] = (loc[nm][0], W[p][1].T @ W0[nm][1]); hum[nm] = loc[nm][1]
            for nm in armb:                                     # blend toward the creature's own arm pose
                loc[nm] = (loc[nm][0], q2m(RI.slerp(m2q(base[nm][1]), m2q(hum[nm]), w_arm)))
            frames.append((t, loc))
        prio = max(p for _, _, p in k.blocks) if k.blocks else 30
        bones = [(nm, prio) for nm in cr.sk.order
                 if (nm.startswith('Bip01') or nm == cr.weapon) and (nm != acc or keyed_acc)]
        write_kf(cr, os.path.join(out, fn), k.name, L, list(k.textkeys), frames, bones=bones, cycle=k.cycle)
        done.append((fn, k.name, round(L, 2), round(lh, 1), round(extra, 1)))
    return done

if __name__ == '__main__':
    for d in build(sys.argv[1], sys.argv[2], sys.argv[3], *[float(a) for a in sys.argv[4:5]]): print(d)
