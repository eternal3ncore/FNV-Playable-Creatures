"""Procedural jump animations on the creature's own skeleton (standing pose = cfg.IDLE_KF at t=0).
Loop = airborne tuck (legs folded, arms out for balance), Land = impact crouch with the root lowered so the
feet stay on the ground, directional variants lean / stride. Priority 30 like the vanilla jumps, so a drawn
weapon's aim (higher priority) keeps the arms on the weapon."""
import numpy as np
from rig import Rig, rotm, smooth, lerp
from kf import KFEval

LAT = np.array([1.0, 0, 0]); FWD = np.array([0, 1.0, 0]); UP = np.array([0, 0, 1.0])
DEF = dict(thL=0, thR=0, caL=0, caR=0, ftL=0, ftR=0, lean=0, side=0, arms=0, elbow=0, crouch=0)

class Keys:
    def __init__(s, keys):
        s.k = []; cur = dict(DEF)
        for u, kv in keys: cur = dict(cur); cur.update(kv); s.k.append((u, cur))
    def at(s, u):
        k = s.k
        if u <= k[0][0]: return k[0][1]
        for (u0, a), (u1, b) in zip(k, k[1:]):
            if u <= u1:
                w = smooth((u - u0) / (u1 - u0)) if u1 > u0 else 1.0
                return {x: lerp(a[x], b[x], w) for x in a}
        return k[-1][1]

def jump_pose(rig, P):
    cr = rig.cr; b = cr.cfg.BONES; loc = dict(rig.base)
    # cfg.JUMP_SCALE scales the leg / torso angles (a crouched creature such as the trog folds far less)
    js = getattr(cr.cfg, 'JUMP_SCALE', 1.0)
    if js != 1.0: P = {k: (v * js if k in ('thL', 'thR', 'caL', 'caR', 'ftL', 'ftR', 'lean') else v) for k, v in P.items()}
    def wrot(nm, R):
        W = rig.fk(loc); rig.set_world_rot(loc, W, nm, R @ W[nm][1])
    # legs: thigh flex (knee forward +), calf fold (negative = heel back), foot
    for side, th, ca, ft in (('L', P['thL'], P['caL'], P['ftL']), ('R', P['thR'], P['caR'], P['ftR'])):
        thigh, calf, foot = b['leg_' + side][:3]
        wrot(thigh, rotm(LAT, th)); wrot(calf, rotm(LAT, ca)); wrot(foot, rotm(LAT, ft))
    # torso lean (forward +) and side lean (right +)
    n = max(1, len(cr.spine) - 1)
    for nm in cr.spine[1:]:
        wrot(nm, rotm(LAT, -P['lean'] / n) @ rotm(FWD, P['side'] / n))
    # arms out/up for balance (+), elbows bent
    for side, sgn in (('L', 1), ('R', -1)):
        _, ua, fa, _ = cr.arm[side]
        wrot(ua, rotm(FWD, sgn * P['arms'])); wrot(fa, rotm(LAT, P['elbow']))
    # crouch: lower the root so the lowest foot keeps its standing height
    if P['crouch'] > 1e-4:
        W = rig.fk(loc)
        f0 = min(rig.W0[b['leg_L'][2]][0][2], rig.W0[b['leg_R'][2]][0][2])
        f1 = min(W[b['leg_L'][2]][0][2], W[b['leg_R'][2]][0][2])
        t, R = loc[b['root']]
        loc[b['root']] = (t - np.array([0, 0, (f1 - f0) * P['crouch']]), R)
    return loc

TUCK = dict(thL=48, thR=40, caL=-82, caR=-74, ftL=28, ftR=26, lean=8, arms=28, elbow=20)
LOOPS = {
    'JumpLoop':         [(0, TUCK), (.5, dict(TUCK, thL=43, thR=45, caL=-76, caR=-80, arms=32)), (1, TUCK)],
    'JumpLoopForward':  [(0, dict(TUCK, thL=55, thR=5, caL=-80, caR=-55, lean=14)), (.5, dict(TUCK, thL=50, thR=10, caL=-78, caR=-60, lean=15, arms=32)),
                         (1, dict(TUCK, thL=55, thR=5, caL=-80, caR=-55, lean=14))],
    'JumpLoopBackward': [(0, dict(TUCK, thL=40, thR=40, caL=-45, caR=-45, lean=-8, arms=38)), (.5, dict(TUCK, thL=44, thR=38, caL=-50, caR=-42, lean=-9, arms=42)),
                         (1, dict(TUCK, thL=40, thR=40, caL=-45, caR=-45, lean=-8, arms=38))],
    'JumpLoopLeft':     [(0, dict(TUCK, side=-10)), (.5, dict(TUCK, side=-12, arms=34)), (1, dict(TUCK, side=-10))],
    'JumpLoopRight':    [(0, dict(TUCK, side=10)), (.5, dict(TUCK, side=12, arms=34)), (1, dict(TUCK, side=10))],
}
IMPACT = dict(thL=42, thR=42, caL=-70, caR=-70, ftL=28, ftR=28, lean=18, arms=18, elbow=15, crouch=1)
def land(extra):
    I = dict(IMPACT, **extra)
    return [(0, dict(TUCK, crouch=0)), (.18, I), (.42, dict(I, thL=25, thR=25, caL=-42, caR=-42, ftL=17, ftR=17, lean=10, arms=8)), (1, dict(DEF))]
LANDS = {'JumpLand': land({}), 'JumpLandForward': land(dict(lean=24)), 'JumpLandBackward': land(dict(lean=4)),
         'JumpLandLeft': land(dict(side=-8)), 'JumpLandRight': land(dict(side=8))}
DEFAULT_LEN = {'JumpLoop': 1.3333, 'JumpLand': 0.7667}

def jump_bones(cr):
    b = cr.cfg.BONES
    names = [b['root'], b['pelvis']] + b['leg_L'] + b['leg_R'] + list(cr.spine) + b.get('neck', []) + [cr.head]
    # bones between the root and the pelvis (the trog's 'Bip' carries its hip height) are keyed too
    p = cr.sk.parent.get(b['pelvis'])
    while p and p != b['root']: names.append(p); p = cr.sk.parent.get(p)
    for side in ('L', 'R'): names += list(cr.arm[side])
    return [(n, 30) for n in names if n in cr.sk.local]

def build(cr):
    """yields (group, rig, Keys, cycle)"""
    rig = Rig(cr, base_pose=KFEval(cr.path(cr.cfg.IDLE_KF)).sample(0))
    for group, keys, cyc in [(g, k, 0) for g, k in LOOPS.items()] + [(g, k, 2) for g, k in LANDS.items()]:
        yield group, rig, Keys(keys), cyc
