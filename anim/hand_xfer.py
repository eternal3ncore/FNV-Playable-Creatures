"""Hands to the mouth: a source animation's hand path, taken relative to its mouth, put on a creature by 2-bone arm IK.
Used for drinking (the human ActWaterSource: the left hand scoops water to the mouth) and eating (the human / spore
carrier cannibal: both hands to the mouth) on creatures whose body comes from elsewhere (their idle + a bend, or a
retargeted crouch).
  target  = creature mouth + (source hand - source mouth) x arm-length ratio, pushed out to CLEAR(race) from the head
            joint (big heads / long fingers: the Zetan's fingers went into its head)
  elbow   = 2-bone IK, pole = creature shoulder + (source elbow - source shoulder) x 2 (elbows out, not into the torso)
  hand    = the source hand's world rotation carried over by the rigs' bind difference (W_src Bsrc^T Bdst), or kept
            as the creature's own hand-in-forearm rotation for claws / pincers (ROT_OWN)
  fingers = the source's local finger rotations where both rigs have the bone (humanoid hands)
Mouth points: actor-frame offsets from Bip01 Head in the standing pose (MOUTH), carried with the head."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kf import Skeleton, KFEval

HUMAN_SKEL = '/home/claude/fnv/ref_weap/skeleton.nif'
HUMAN_STAND = ('/home/claude/fnv/ref_act/actwatersource.kf', 2.7)    # the human standing upright (end of the drink)
SPORE_SKEL = '/home/claude/fnv/ref_act/idles/Tunneler/Skeleton.nif'      # spore carrier = the tunneler skeleton
MOUTH = {'human': (0, 9, -4), 'spore': (0, 5, -1),
         'Ghost': (0, 9, -4), 'Ghoul': (0, 8, -3), 'GlowingOne': (0, 8, -3), 'Swampfolk': (0, 8, -2), 'Hillfolk': (0, 8, -2),
         'Zetan': (0, 9, 3), 'SuperMutant': (0, 11, -3), 'Nightkin': (0, 11, -3), 'SuperMutantDC': (0, 11, -3),
         'Trog': (0, 5, -1), 'Tunneler': (0, 5, -1), 'Deathclaw': (0, 24, -8), 'Mirelurk': (0, 8, -6), 'Lakelurk': (0, 10, 2)}
CLEAR = {'Zetan': 16.0, 'Deathclaw': 22.0, 'Mirelurk': 16.0, 'Lakelurk': 14.0, 'SuperMutant': 12.0, 'Nightkin': 12.0,
         'SuperMutantDC': 12.0}                                            # min hand-to-head-joint distance (default 9)
ROT_OWN = {'Deathclaw', 'Mirelurk', 'Lakelurk'}
HEADR = {'Zetan': 16.0}          # finger bones kept this far from the head joint (the hand turned at the wrist): the
                                 # Zetan's long fingers pointed up into its cranium with the human hand-at-mouth rotation


def fk(sk, loc):
    W = {}
    for n in sk.order:
        t, R = loc[n]; p = sk.parent[n]
        W[n] = (t.copy(), R.copy()) if p is None else (W[p][0] + W[p][1] @ t, W[p][1] @ R)
    return W


def local_pose(sk, smp, root_identity=True):
    loc = {}
    for n in sk.order:
        t, R, _ = sk.local[n]
        if n in smp:
            if smp[n][0] is not None: t = smp[n][0]
            if smp[n][1] is not None: R = smp[n][1]
        loc[n] = (np.array(t, float), np.array(R, float))
    if root_identity and (smp.get('Bip01') is None or smp['Bip01'][1] is None): loc['Bip01'] = (loc['Bip01'][0], np.eye(3))
    return loc


def align(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.9999:
        ax = np.cross(a, [1, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1, 0]); ax /= np.linalg.norm(ax)
        return 2 * np.outer(ax, ax) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


class HandXfer:
    def __init__(s, src_skel, src_mouth, dst_skel, name, dst_base_loc, src_kf, sides=('L', 'R'), src_ref=None):
        s.gs = Skeleton(src_skel); s.ds = Skeleton(dst_skel); s.name = name; s.sides = sides
        s.arm = {sd: tuple(f'Bip01 {sd} {b}' for b in ('UpperArm', 'Forearm', 'Hand')) for sd in 'LR'}
        s.src_kf = src_kf
        rk, rt_ = src_ref or (src_kf, 0.0)                            # a standing frame of the source (its own root
        s.Bg = fk(s.gs, local_pose(s.gs, KFEval(rk).sample(rt_)))     # convention; the bind alone faces sideways)
        s.Bd = fk(s.ds, dst_base_loc)                                     # creature standing pose (its idle)
        bd = {n: (np.array(s.ds.local[n][0], float), np.array(s.ds.local[n][1], float)) for n in s.ds.order}
        bd['Bip01'] = (bd['Bip01'][0], np.eye(3)); s.Bdb = fk(s.ds, bd)   # creature bind (for the rotation transfer)
        s.mg = s.Bg['Bip01 Head'][1].T @ np.asarray(src_mouth, float)
        s.md = s.Bd['Bip01 Head'][1].T @ np.asarray(MOUTH[name], float)
        def armlen(W, sd):
            ua, fa, h = s.arm[sd]; return np.linalg.norm(W[fa][0] - W[ua][0]) + np.linalg.norm(W[h][0] - W[fa][0])
        s.k = np.mean([armlen(s.Bd, sd) / armlen(s.Bg, sd) for sd in 'LR'])
        s.clear = CLEAR.get(name, 9.0)
        def ang(A, B): return np.degrees(np.arccos(np.clip((np.trace(A.T @ B) - 1) / 2, -1, 1)))
        s.fingers = {sd: [n for n in s.ds.order if n.startswith(f'Bip01 {sd} Finger') and n in s.gs.local
                          and ang(np.array(s.ds.local[n][1], float), np.array(s.gs.local[n][1], float)) < 15] for sd in 'LR'}
        s.rot_mode = 'world'          # the source hand's world rotation (Bip01 rigs share hand axes; checked: finger direction dot 0.98-1.0)

    def src(s, ev, t):
        return fk(s.gs, local_pose(s.gs, ev.sample(t)))

    def ik(s, loc, sd, target, pole):
        ua, fa, h = s.arm[sd]; W = fk(s.ds, loc)
        S = W[ua][0]; E = W[fa][0]; G = W[h][0]
        a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
        d = target - S; dist = np.linalg.norm(d); dc = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.995); dn = d / dist
        cA = (a * a + dc * dc - b * b) / (2 * a * dc)
        pv = pole - S; pv = pv - dn * np.dot(pv, dn)
        if np.linalg.norm(pv) < 1e-6: pv = np.cross(dn, [1.0, 0, 0])
        pv /= np.linalg.norm(pv)
        En = S + dn * (a * cA) + pv * (a * np.sqrt(max(0.0, 1 - cA * cA)))
        def setw(n, Rw):
            loc[n] = (loc[n][0], W[s.ds.parent[n]][1].T @ Rw)
        setw(ua, align(E - S, En - S) @ W[ua][1]); W = fk(s.ds, loc)
        E = W[fa][0]; G = W[h][0]
        setw(fa, align(G - E, S + dn * dc - E) @ W[fa][1])
        return loc

    def apply(s, loc, ev, t, w=1.0, sides=None):
        """loc: creature local pose (modified); w: 0..1 blend of the hand transfer"""
        if w <= 0: return loc
        Wg = s.src(ev, t); gl = local_pose(s.gs, ev.sample(t))
        for sd in (sides or s.sides):
            ua, fa, h = s.arm[sd]
            W = fk(s.ds, loc)
            own_hand = loc[h][1].copy()
            mg = Wg['Bip01 Head'][0] + Wg['Bip01 Head'][1] @ s.mg
            md = W['Bip01 Head'][0] + W['Bip01 Head'][1] @ s.md
            tgt = md + (Wg[h][0] - mg) * s.k
            hd = W['Bip01 Head'][0]; v = tgt - hd; dv = np.linalg.norm(v)
            if dv < s.clear: tgt = hd + (v / max(dv, 1e-6)) * s.clear
            cur = W[h][0]; tgt = cur + (tgt - cur) * w
            pole = W[ua][0] + (Wg[fa][0] - Wg[ua][0]) * 2.0
            s.ik(loc, sd, tgt, pole)
            W = fk(s.ds, loc)
            if s.name in ROT_OWN: Rh = W[fa][1] @ own_hand
            elif s.rot_mode == 'world': Rh = Wg[h][1]
            else: Rh = Wg[h][1] @ s.Bg[h][1].T @ s.Bdb[h][1]
            # blend with the creature's own hand rotation by w
            Rown = W[fa][1] @ own_hand
            q = _slerpm(Rown, Rh, w)
            loc[h] = (loc[h][0], W[fa][1].T @ q)
            if s.name not in ROT_OWN:
                for n in s.fingers[sd]:
                    if n in gl: loc[n] = (loc[n][0], _slerpm(loc[n][1], gl[n][1], w))
            r = HEADR.get(s.name)
            if r:
                fing = [n for n in s.ds.order if n.startswith(f'Bip01 {sd} Finger')]
                for _ in range(12):
                    W = fk(s.ds, loc); hd = W['Bip01 Head'][0]; wr = W[h][0]
                    tips = [W[n][0] for n in fing]
                    dmin = min(np.linalg.norm(p - hd) for p in tips) if tips else r
                    if dmin >= r: break
                    tip = np.mean(tips, 0) - wr; ax = np.cross(tip, hd - wr)
                    if np.linalg.norm(ax) < 1e-6: break
                    ax /= np.linalg.norm(ax); a = -np.radians(10)
                    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
                    Rr = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
                    loc[h] = (loc[h][0], W[fa][1].T @ Rr @ W[h][1])
        return loc


def _slerpm(A, B, w):
    from kf import m2q, q2m, slerp
    return q2m(slerp(m2q(A), m2q(B), w))
