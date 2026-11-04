"""Hands to the mouth: a source animation's hand path, taken relative to its mouth, put on a creature by 2-bone arm IK.
Used for drinking (the human ActWaterSource: the left hand scoops water to the mouth) and eating (the human / spore
carrier cannibal: both hands to the mouth) on creatures whose body comes from elsewhere (their idle + a bend, or a
retargeted crouch).
  palm    = creature mouth + (source palm - source mouth) x arm-length ratio, pushed out to CLEAR(race) from the head
            joint; palm = 0.6 of the way from the wrist to the finger bases (the Zetan's 13-unit palm: aiming its wrist
            where the human's goes put its long fingers through its head); the wrist target = palm - hand rot x palm
            offset (claws / pincers: the wrist itself)
  elbow   = 2-bone IK, pole = creature shoulder + (source elbow - source shoulder) x 2 (elbows out, not into the torso)
  hand    = the source hand's world rotation carried over by the rigs' bind difference (W_src Bsrc^T Bdst), or kept
            as the creature's own hand-in-forearm rotation for claws / pincers (ROT_OWN)
  fingers = the source's local finger rotations where both rigs have the bone (humanoid hands)
Mouth points: actor-frame offsets from Bip01 Head in the standing pose (MOUTH), carried with the head (Zetan: the face
surface from its skinned mesh, 16 in front of the head joint; the old 9 was inside the head).
Big heads (HEAD_SHAPE): the wrist target moved to the nearest point that keeps every hand / finger point outside the
head's enclosing ellipsoid (head_shape.py) and the wrist within reach.
Ramps (w < 1): arm and fingers slerped from the creature's own local pose, the hand from its own world rotation.
Arm reach is soft-limited (tanh above 0.9 of the arm): a hard clamp slid the out-of-reach hand around and jittered."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kf import Skeleton, KFEval

HUMAN_SKEL = '/home/claude/fnv/ref_weap/skeleton.nif'
HUMAN_STAND = ('/home/claude/fnv/ref_act/actwatersource.kf', 2.7)    # the human standing upright (end of the drink)
SPORE_SKEL = '/home/claude/fnv/ref_act/idles/Tunneler/Skeleton.nif'      # spore carrier = the tunneler skeleton
MOUTH = {'human': (0, 9, -4), 'spore': (0, 5, -1),
         'Ghost': (0, 9, -4), 'Ghoul': (0, 8, -3), 'GlowingOne': (0, 8, -3), 'Swampfolk': (0, 8, -2), 'Hillfolk': (0, 8, -2),
         'Zetan': (0, 16, 2), 'SuperMutant': (0, 11, -3), 'Nightkin': (0, 11, -3), 'SuperMutantDC': (0, 11, -3),
         'Trog': (0, 5, -1), 'Tunneler': (0, 5, -1), 'Deathclaw': (0, 24, -8), 'Mirelurk': (0, 8, -6), 'Lakelurk': (0, 10, 2)}
CLEAR = {'Zetan': 16.0, 'Deathclaw': 22.0, 'Mirelurk': 16.0, 'Lakelurk': 14.0, 'SuperMutant': 12.0, 'Nightkin': 12.0,
         'SuperMutantDC': 12.0}                                            # min hand-to-head-joint distance (default 9)
ROT_OWN = {'Deathclaw', 'Mirelurk', 'Lakelurk'}
LAG = 2.0                        # weight of last frame's wrist in the head-clearance solve (2: jitter sum 126, 0.5: 196)
# heads big enough for the fingers to reach into: the minimum-volume ellipsoid enclosing the head (+ jaw, lips, eyelids)
# vertices of the skinned body mesh, in Bip01 Head space ((x-c)^T A (x-c) = 1); hand and finger points are kept outside
# (Zetan: dlc05alien1.nif, 818 vertices; its arm (25) is 31 from its face, so hands aimed at the mouth stopped in it)
HEAD_SHAPE = {'Zetan': ((8.12, 3.1, -0.08), ((0.00543, 0.00066, 0.00001), (0.00066, 0.00559, 0.0), (0.00001, 0.0, 0.00915)))}


def fk(sk, loc):
    W = {}
    for n in sk.order:
        t, R = loc[n]; p = sk.parent[n]
        W[n] = (t.copy(), R.copy()) if p is None else (W[p][0] + W[p][1] @ t, W[p][1] @ R)
    return W


def orth(R):
    """the nearest rotation (sampled keys can come back scaled / sheared: unnormalised quaternion blends; a Zetan
    forearm at det 0.64 made the arm IK and the hand flip 180 deg between frames)"""
    U, _, Vt = np.linalg.svd(np.asarray(R, float)); M = U @ Vt
    if np.linalg.det(M) < 0: U[:, -1] *= -1; M = U @ Vt
    return M


def local_pose(sk, smp, root_identity=True):
    loc = {}
    for n in sk.order:
        t, R, _ = sk.local[n]
        if n in smp:
            if smp[n][0] is not None: t = smp[n][0]
            if smp[n][1] is not None: R = smp[n][1]
        loc[n] = (np.array(t, float), orth(R))
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
        def palm(sk, sd):                                             # the cup of the hand, in hand space: 0.6 of
            for f in ('Finger2', 'Finger1', 'Finger0'):                   # the way to the finger bases (the Zetan palm
                n = f'Bip01 {sd} {f}'                                     # is 13 long, the human's 4: the wrist put
                if n in sk.local and sk.parent[n] == f'Bip01 {sd} Hand':  # where the human's goes swept its fingers
                    return 0.6 * np.array(sk.local[n][0], float)          # across its face)
            return np.zeros(3)
        s.palm_g = {sd: palm(s.gs, sd) for sd in 'LR'}
        s.palm_d = {sd: (np.zeros(3) if name in ROT_OWN else palm(s.ds, sd)) for sd in 'LR'}
        if name in ROT_OWN: s.palm_g = {sd: np.zeros(3) for sd in 'LR'}
        s.shape = HEAD_SHAPE.get(name); s.prev_wrist = {}
        s.rot_mode = 'world'          # the source hand's world rotation (Bip01 rigs share hand axes; checked: finger direction dot 0.98-1.0)

    def _clear_head(s, loc, sd, tgt, S):
        """the wrist target nearest the wanted one with every hand / finger point outside the head ellipsoid and the
        wrist within 0.9 of the arm (SLSQP, started from the previous frame's answer so the hand moves continuously)"""
        from scipy.optimize import minimize
        ua, fa, h = s.arm[sd]; W = fk(s.ds, loc); G = W[h][0]
        pts = [W[n][0] - G for n in s.ds.order if n == h or n.startswith(f'Bip01 {sd} Finger')]
        for n in s.ds.order:                                   # segment midpoints too (long Zetan bones)
            p = s.ds.parent[n]
            if n.startswith(f'Bip01 {sd} Finger') and p is not None: pts.append((W[n][0] + W[p][0]) / 2 - G)
        pts = np.array(pts); ph, Rhd = W['Bip01 Head']; c = np.array(s.shape[0]); A = np.array(s.shape[1])
        R = 0.9 * (np.linalg.norm(W[fa][0] - S) + np.linalg.norm(G - W[fa][0]))
        def e(x):
            L = (x + pts - ph) @ Rhd - c; return np.einsum('ij,jk,ik->i', L, A, L) - 1.03
        x0 = s.prev_wrist.get(sd, tgt)
        if np.all(e(tgt) >= 0) and np.linalg.norm(tgt - S) <= R: s.prev_wrist[sd] = tgt; return tgt
        lam = 0.0 if sd not in s.prev_wrist else LAG                 # outside an ellipsoid is not convex: a pull
        def f(x): return float((x - tgt) @ (x - tgt) + lam * (x - x0) @ (x - x0))   # to last frame's answer keeps
        def df(x): return 2 * (x - tgt) + 2 * lam * (x - x0)                        # it from hopping sides
        r = minimize(f, x0, jac=df, method='SLSQP',
                     constraints=[{'type': 'ineq', 'fun': e}, {'type': 'ineq', 'fun': lambda x: R * R - float((x - S) @ (x - S))}],
                     options={'maxiter': 500, 'ftol': 1e-10})
        x = r.x; s.prev_wrist[sd] = x; return x

    def src(s, ev, t):
        return fk(s.gs, local_pose(s.gs, ev.sample(t)))

    def ik(s, loc, sd, target, pole):
        ua, fa, h = s.arm[sd]; W = fk(s.ds, loc)
        S = W[ua][0]; E = W[fa][0]; G = W[h][0]
        a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
        d = target - S; dist = np.linalg.norm(d); dn = d / dist
        top = (a + b) * 0.995; knee = (a + b) * 0.9            # soft reach limit: the elbow never snaps straight (a
        dc = dist if dist <= knee else knee + (top - knee) * np.tanh((dist - knee) / (top - knee))   # target out of
        dc = max(dc, abs(a - b) + 1e-3)                          # reach sliding along the clamp jittered the arm)
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
            keep = {n: loc[n][1].copy() for n in (ua, fa, h) + tuple(s.fingers[sd])}; Wh0 = W[h][1].copy()
            own_hand = keep[h]
            mg = Wg['Bip01 Head'][0] + Wg['Bip01 Head'][1] @ s.mg
            md = W['Bip01 Head'][0] + W['Bip01 Head'][1] @ s.md
            if s.name in ROT_OWN: Rh = None
            elif s.rot_mode == 'world': Rh = Wg[h][1]
            else: Rh = Wg[h][1] @ s.Bg[h][1].T @ s.Bdb[h][1]
            # the palm goes where the source's palm goes relative to its mouth; the wrist follows from the hand rotation
            pal = md + (Wg[h][0] + Wg[h][1] @ s.palm_g[sd] - mg) * s.k
            hd = W['Bip01 Head'][0]; v = pal - hd; dv = np.linalg.norm(v)
            if dv < s.clear: pal = hd + (v / max(dv, 1e-6)) * s.clear
            off = Rh @ s.palm_d[sd] if Rh is not None else np.zeros(3)
            tgt = pal - off
            pole = W[ua][0] + (Wg[fa][0] - Wg[ua][0]) * 2.0
            def place(tgt):
                s.ik(loc, sd, tgt, pole)
                W = fk(s.ds, loc)
                loc[h] = (loc[h][0], W[fa][1].T @ (W[fa][1] @ own_hand if Rh is None else Rh))
                if s.name not in ROT_OWN:
                    for n in s.fingers[sd]:
                        if n in gl: loc[n] = (loc[n][0], gl[n][1])
            place(tgt)
            if s.shape is not None and Rh is not None:
                tgt = s._clear_head(loc, sd, tgt, W[ua][0])
                place(tgt)
            W = fk(s.ds, loc)
            if w < 1:      # ramps: the arm and fingers eased from their own local pose (a lerped target left the IK's
                           # elbow, which jumped at w = 0); the hand in world space from its own world rotation, the
                           # shortest way (between local rotations the way round swapped mid-ramp: a Trog's wrist
                           # turned 69 deg in one frame)
                for n, R in keep.items():
                    if n != h: loc[n] = (loc[n][0], _slerpm(R, loc[n][1], w))
                W2 = fk(s.ds, loc)
                loc[h] = (loc[h][0], W2[fa][1].T @ _slerpm(Wh0, W[fa][1] @ loc[h][1], w))
        return loc


def _slerpm(A, B, w):
    from kf import m2q, q2m, slerp
    return q2m(slerp(m2q(A), m2q(B), w))
