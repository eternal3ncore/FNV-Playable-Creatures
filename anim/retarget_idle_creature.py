"""Retarget the human furniture idle set (chair enter/exit x4 sides, seated loop + relax specials, stool) onto a
creature-race skeleton (Feral Ghoul, Super Mutant, ...). Generic version of retarget_idle.py (Zetan).

Same method as retarget_idle.py (world-space bone deltas, Bip01 entry path unscaled because the furniture marker sets
it, NonAccum height mapped seat->seat / stand->stand, 2-bone leg IK with ground contact). Creatures without a seated
pose of their own use the retargeted human seated loop and relax specials, so no seat blend is needed.
  stand height = the creature's own NonAccum height in its idle (accum root at the origin)
  seat height  = human seat + 25 % of the stand-height difference (a bigger body sits a little higher)
usage: python3 retarget_idle_creature.py <creature cfg> <skeleton.nif (with stand-ins)> <out_dir>"""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval, m2q, q2m, slerp
from rig import Creature, write_kf
import retarget_idle as RI

HUMAN_SIT = '/home/claude/fnv/human_sit/meshes/characters/_male/idleanims/'
JOBS = [(o, s, None) for o, s, _ in RI.JOBS] + [
    ('DynamicIdle_ChairSit.kf', 'dynamicidle_chairsit.kf', None),
    ('SitChairRelaxA.kf', 'sitchairrelaxa.kf', None),
    ('SitChairRelaxB.kf', 'sitchairrelaxb.kf', None),
    ('SitChairRelaxC.kf', 'sitchairrelaxc.kf', None)]

def stand_height(cfg):
    k = KFEval(os.path.join(cfg.ANIM_SRC, cfg.IDLE_KF)); p = k.sample(0.0)
    return float(p['Bip01 NonAccum'][0][2])

def build(cfgname, skel, out_dir, fps=30):
    cfg = importlib.import_module('creatures.' + cfgname)
    cr = Creature(cfg)
    hz = stand_height(cfg)
    hs, _ = RI.Z_SEAT[0], None
    RI.Z_STAND = (RI.Z_STAND[0], hz)
    # cfg.SIT_SEAT_OFFSET overrides the seat offset: a crouched creature (trog, idle NonAccum 20) sits at the
    # human seat height instead of 25 % of its (negative) stand difference below it
    RI.Z_SEAT = (RI.Z_SEAT[0], RI.Z_SEAT[0] + getattr(cfg, 'SIT_SEAT_OFFSET', 0.25 * (hz - RI.Z_STAND[0])))
    rt = RI.IdleRetarget(RI.HUMAN_SKEL, skel)
    # piecewise height map: chair seat and bar-stool seat keep their world height (+ the creature's seat offset),
    # standing maps to the creature's own standing height
    (hs, zs), (hS, zS) = RI.Z_SEAT, RI.Z_STAND
    H_STOOL = 54.55                                  # human NonAccum height on a bar stool (dynamicidle_sitstool)
    pts = [(hs, zs), (H_STOOL, H_STOOL + (zs - hs)), (hS, zS)]
    def map_z(z):
        if z <= pts[0][0]: return z + (zs - hs)
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            if z <= a1: return b0 + (z - a0) * (b1 - b0) / (a1 - a0)
        return z + (zS - hS)
    rt.map_z = map_z
    # tail (deathclaw): the human sitting tilts the accum node and pelvis back, which would swing the tail down through
    # the seat and the floor. Its root keeps the world direction it has in the creature's own idle, turned only with
    # the body's heading (yaw of the accum node's lateral axis), so it lies back along the floor behind the seat.
    tail = [n for n in getattr(cfg, 'SIT_TAIL', ()) if n in rt.hs.local]
    if tail:
        ip = KFEval(os.path.join(cfg.ANIM_SRC, cfg.IDLE_KF)).sample(0.0); ip.pop('Bip01', None)
        Wi = rt.hs.fk(ip)
        def heading(R):
            v = R[:, 1]; return np.arctan2(v[1], v[0])
        h0 = heading(Wi['Bip01 NonAccum'][1])
        kids = [n for n in rt.hs.order if n.startswith('Bip01 Tail') and n not in tail]     # keyed by its idle
    hand_min = getattr(cfg, 'SIT_HAND_MIN', None)
    if tail or hand_min is not None:
        _frame = rt.frame
        def rot(axis, a):
            x, y, z = axis / np.linalg.norm(axis); c, s_ = np.cos(a), np.sin(a); C = 1 - c
            return np.array([[c + x*x*C, x*y*C - z*s_, x*z*C + y*s_], [y*x*C + z*s_, c + y*y*C, y*z*C - x*s_],
                             [z*x*C - y*s_, z*y*C + x*s_, c + z*z*C]])
        def frame(k, t):
            loc = _frame(k, t); W = rt.fk(rt.hs, loc); g = W['Bip01'][0][2]
            if tail:
                a = heading(W['Bip01 NonAccum'][1]) - h0
                Y = rot(np.array([0, 0, 1.0]), a)
                lat = W['Bip01 NonAccum'][1][:, 1].copy(); lat[2] = 0
                def low(th):
                    L = dict(loc)
                    for n in tail: L[n] = (loc[n][0], W[rt.hs.parent[n]][1].T @ rot(lat, th) @ Y @ Wi[n][1])
                    for n in kids: L[n] = (ip[n][0] if n in ip and ip[n][0] is not None else loc[n][0], ip[n][1] if n in ip else loc[n][1])
                    Wt = rt.fk(rt.hs, L); return min(Wt[n][0][2] for n in kids + tail) - g, L
                # lowered with the seat, it would reach under the floor: pitch the root up until it clears it by 2
                z0, L0 = low(0.0); th = 0.0
                if z0 < 2.0:
                    sgn = 1.0 if low(0.1)[0] > z0 else -1.0
                    lo_, hi_ = 0.0, 1.2
                    for _ in range(24):
                        m = (lo_ + hi_) / 2
                        if low(sgn * m)[0] < 2.0: lo_ = m
                        else: hi_ = m
                    th = sgn * hi_
                L = low(th)[1]
                for n in tail: loc[n] = L[n]
                W = rt.fk(rt.hs, loc)
            if hand_min is not None:
                # long arms on a human-sized seated pose reach the floor. Below hand_min the arm settles into a rest:
                # upper arm down at the side, forearm forward along the thigh (blended in over 20 units, 2-bone IK)
                for side in 'LR':
                    hn = f'Bip01 {side} Hand'; un = f'Bip01 {side} UpperArm'; fn = f'Bip01 {side} Forearm'
                    H = W[hn][0].copy(); d = hand_min - (H[2] - g)
                    if d > 0:
                        w = min(1.0, d / 20.0)
                        fw = W[cr.head][0] - W['Bip01 Pelvis'][0]; fw[2] = 0; fw /= max(np.linalg.norm(fw), 1e-6)
                        lat = np.array([-fw[1], fw[0], 0.0])
                        if np.dot(W[un][0] - W[cr.head][0], lat) < 0: lat = -lat
                        l1 = np.linalg.norm(rt.hs.local[fn][0]); l2 = np.linalg.norm(rt.hs.local[hn][0])
                        up = np.array([0, 0, 1.0])
                        E = W[un][0] + lat * 0.25 * l1 - up * 0.9 * l1          # elbow beside the hip
                        R = E + fw * 0.95 * l2 + up * 0.15 * l2                  # hand forward over the thigh
                        rt._ik(loc, un, fn, hn, H * (1 - w) + R * w, pole=(E - W[un][0]) + fw * 0.1)
                        # wrist straightened toward the rest (claws forward, not hanging into the floor)
                        q0 = m2q(loc[hn][1]); q1 = m2q(np.array(rt.hs.local[hn][1], float))
                        loc[hn] = (loc[hn][0], q2m(slerp(q0, q1, w)))
                        W = rt.fk(rt.hs, loc)
            return loc
        rt.frame = frame
    os.makedirs(out_dir, exist_ok=True)
    rep = []
    for out, src, _ in JOBS:
        k = KFEval(HUMAN_SIT + src); L = k.stop; n = int(round(L * fps)) + 1
        keyed = {b[0] for b in k.blocks}
        prio = max(b[2] for b in k.blocks)
        frames = [(L * i / (n - 1), rt.frame(k, L * i / (n - 1))) for i in range(n)]
        names = [nm for nm in rt.hs.order if nm.startswith('Bip01') and (nm in ('Bip01', 'Bip01 NonAccum') or rt.map.get(nm) in keyed)]
        if 'Bip01' not in keyed: names = [nm for nm in names if nm != 'Bip01']
        names += tail
        for side in ('L', 'R') if hand_min is not None else ():
            names += [n for n in (f'Bip01 {side} UpperArm', f'Bip01 {side} Forearm', f'Bip01 {side} Hand') if n not in names]
        # cfg.SIT_OWN_ARMS: the arms are left out (clavicles and everything below them), so its own standing idle keeps
        # playing on them while it sits (the protectron's rigid arms, bent by the human sitting pose, went into its body)
        if getattr(cfg, 'SIT_OWN_ARMS', False):
            arm = set()
            for root in ('Bip01 L Clavicle', 'Bip01 R Clavicle'):
                stack = [root]
                while stack:
                    n = stack.pop(); arm.add(n); stack += [c for c, p in rt.hs.parent.items() if p == n]
            names = [nm for nm in names if nm not in arm]
        write_kf(cr, os.path.join(out_dir, out), k.name, L, RI.keys_of(k), frames, bones=[(nm, prio) for nm in names], cycle=k.cycle)
        rep.append((out, k.name, round(L, 2), k.cycle, prio, len(names)))
    return rt, rep, RI.Z_SEAT, RI.Z_STAND

if __name__ == '__main__':
    rt, rep, zs, zt = build(sys.argv[1], sys.argv[2], sys.argv[3])
    print('leg ratio %.3f ankle src %.2f dst %.2f seat %s stand %s' % (rt.ratio, rt.ankle_g, rt.ankle_h, zs, zt))
    for r in rep: print(r)
