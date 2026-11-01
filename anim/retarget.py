"""Retarget a Bip01 creature's locomotion KF onto another Bip01 skeleton (e.g. feral ghoul run -> Ghost People).

Method (per frame):
  * root chain (Bip01, Bip01 NonAccum) copied, translations scaled by the leg-length ratio;
  * every other bone: world-space delta from the source bind pose applied to the target bind pose
    (W_dst = W_src_anim * W_src_bind^T * W_dst_bind), so bind differences in bone roll don't leak into the motion;
    bones the source doesn't have keep their target bind-local rotation; translations stay target bind-local;
  * legs: 2-bone IK puts each target ankle where the scaled source ankle is (relative to the ground root), knee
    plane from the delta pose, foot world rotation kept -> same stride, no extra foot slide;
  * optional 'strafe' (+90 left / -90 right): a crossover side-run. Pelvis and upper body stay facing forward
    (weapon aim layers key the spine relative to the pelvis, so a turned pelvis would turn the aim); only the ankle
    targets are rotated 90 deg about the pelvis centre (the two feet's paths end up one in front of the other, so
    the legs cross over instead of colliding), feet yawed a little toward the travel direction, root motion sideways.
usage: python3 retarget.py  (builds the Ghost run set into build/ghost_run/)"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import Skeleton, KFEval, m2q
from rig import Creature, write_kf

def rotz(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

def align(a, b):
    """minimal rotation taking unit vector a to unit vector b"""
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))

class Retarget:
    ROOTS = ('Bip01', 'Bip01 NonAccum')
    FEET = {f'Bip01 {s} Foot' for s in 'LR'}
    def __init__(s, src_skel, dst_skel, legs, namemap=None, skip=()):
        s.gs = Skeleton(src_skel); s.hs = Skeleton(dst_skel)
        s.legs = legs                                # [(thigh, calf, foot)] x2 (names in both rigs)
        s.map = dict(namemap or {})                  # dst name -> src name
        for n in s.hs.order:
            # only real skeleton bones: the file's top node ("Scene Root" = the actor's own 3D root, which carries
            # its world position/heading) and helper nodes such as "Weapon" must never be keyed
            # (same names in the ghoul skeleton: keying them snaps the player's root to identity = camera turned 90 deg).
            if n not in s.map and n in s.gs.local and n not in skip and n.startswith('Bip01'): s.map[n] = n
        s.Bg = s.gs.fk(); s.Bh = s.hs.fk()
        def leglen(sk, W, th, ft): return np.linalg.norm(W[th][0] - W[ft][0])
        s.ratio = np.mean([leglen(s.hs, s.Bh, th, ft) / leglen(s.gs, s.Bg, th, ft) for th, _, ft in legs])
        s.ankle_g = np.mean([s.Bg[ft][0][2] for _, _, ft in legs]); s.ankle_h = np.mean([s.Bh[ft][0][2] for _, _, ft in legs])

    clean_root = True
    @staticmethod
    def _root_axis(strafe):
        return np.array([1.0, 0, 0]) if strafe else np.array([0, 1.0, 0])     # travel axis of the accum root
    def _root0(s, k, strafe):
        if not hasattr(s, '_r0'): s._r0 = {}
        key = (id(k), strafe)
        if key not in s._r0:
            tt = k.sample(0)['Bip01'][0] * s.ratio
            if strafe: tt = rotz(strafe) @ tt
            s._r0[key] = float(np.dot(tt, s._root_axis(strafe)))
        return s._r0[key]
    def src_pose(s, k, t):
        smp = k.sample(t); loc = {}
        for n in s.gs.order:
            tt, R, _ = s.gs.local[n]
            if n in smp:
                if smp[n][0] is not None: tt = smp[n][0]
                if smp[n][1] is not None: R = smp[n][1]
            loc[n] = (np.array(tt, float), np.array(R, float))
        return loc

    @staticmethod
    def fk(sk, loc):
        W = {}
        for n in sk.order:
            t, R = loc[n]; p = sk.parent[n]
            if p is None: W[n] = (t.copy(), R.copy())
            else: pp, pR = W[p]; W[n] = (pp + pR @ t, pR @ R)
        return W

    def frame(s, k, t, strafe=0.0, foot_yaw=25.0, stride=0.88):
        hs, gs, r = s.hs, s.gs, s.ratio
        gl = s.src_pose(k, t); Wg = s.fk(gs, gl)
        # target world rotations (delta method) and locals
        loc = {}; Wr = {}
        for n in hs.order:
            p = hs.parent[n]; tb, Rb, _ = hs.local[n]
            src = s.map.get(n)
            if p is None:                                     # scene root of the skeleton file
                loc[n] = (np.array(tb, float), np.array(Rb, float)); Wr[n] = np.array(Rb, float); continue
            if n in s.ROOTS:
                tt = gl[n][0] * r; R = gl[n][1]
                if n == 'Bip01' and strafe: tt = rotz(strafe) @ tt * np.array([stride, stride, 1.0])
                loc[n] = (tt, R)
                Wr[n] = R if p is None else Wr[p] @ R
                continue
            if src is not None:
                Rw = Wg[src][1] @ s.Bg[src][1].T @ s.Bh[n][1]
            else:
                Rw = Wr[p] @ Rb
            if strafe and n in s.FEET: Rw = rotz(foot_yaw if strafe > 0 else -foot_yaw) @ Rw
            Wr[n] = Rw
            loc[n] = (np.array(tb, float), Wr[p].T @ Rw)
        # Character convention (human runs, Ghost walk): the accum root carries only the forward/side travel, starting
        # at 0, with x and z of a forward run at 0; any sway/bob lives in NonAccum. The ghoul keys a lateral wobble
        # into Bip01 itself; move it to NonAccum (Bip01 is unrotated, so world positions don't change).
        rootw = loc['Bip01'][0].copy()                   # Bip01's parent (Scene Root) is the identity
        if s.clean_root:
            bt = loc['Bip01'][0].copy(); keep = s._root_axis(strafe) * bt
            y0 = s._root0(k, strafe)
            nt = loc['Bip01 NonAccum'][0] + (bt - keep) + s._root_axis(strafe) * y0
            loc['Bip01'] = (keep - s._root_axis(strafe) * y0, loc['Bip01'][1]); loc['Bip01 NonAccum'] = (nt, loc['Bip01 NonAccum'][1])
        W = s.fk(hs, loc)
        # leg IK: ankle targets from the scaled source (relative to the ground root)
        rootg = Wg['Bip01'][0]; rooth = rootw
        Ryaw = rotz(strafe) if strafe else np.eye(3)
        piv = (Wg['Bip01 NonAccum'][0] - rootg) * r
        for th, ca, ft in s.legs:
            d = Wg[ft][0] - rootg
            d = np.array([d[0] * r, d[1] * r, (d[2] - s.ankle_g) * r + s.ankle_h])
            if strafe:   # foot paths turned 90 deg about the pelvis centre (horizontal only)
                h = Ryaw @ np.array([d[0] - piv[0], d[1] - piv[1], 0.0]) * stride   # shorter strides stay within reach
                d = np.array([piv[0] + h[0], piv[1] + h[1], d[2]])
            s._ik(loc, th, ca, ft, rooth + d, pole=np.array([0, 1.0, 0]) if strafe else None)
        return loc, Wg

    def _ik(s, loc, th, ca, ft, T, pole=None):
        hs = s.hs
        W = s.fk(hs, loc)
        P0 = W[th][0]; K0 = W[ca][0]
        l1 = np.linalg.norm(hs.local[ca][0]); l2 = np.linalg.norm(hs.local[ft][0])
        dv = T - P0; dist = np.clip(np.linalg.norm(dv), abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
        u = dv / np.linalg.norm(dv)
        pole = (K0 - P0) if pole is None else pole                   # side-run: knees always point forward
        v = pole - u * np.dot(pole, u)
        if np.linalg.norm(v) < 1e-6: v = np.array([0, 1.0, 0]) - u * u[1]
        v /= np.linalg.norm(v)
        cosA = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
        K = P0 + l1 * (cosA * u + np.sqrt(max(0, 1 - cosA * cosA)) * v)
        foot_w = W[ft][1]                                              # keep the retargeted foot orientation
        pR = W[hs.parent[th]][1]
        Rth = align(W[th][1] @ hs.local[ca][0], K - P0) @ W[th][1]
        loc[th] = (loc[th][0], pR.T @ Rth)
        Rca0 = Rth @ loc[ca][1]
        Rca = align(Rca0 @ hs.local[ft][0], (P0 + u * dist) - K) @ Rca0
        loc[ca] = (loc[ca][0], Rth.T @ Rca)
        loc[ft] = (loc[ft][0], Rca.T @ foot_w)

GHOST_SKEL = '/home/claude/fnv/ghost_src/meshes/nvdlc01/creatures/ghosts/skeleton.nif'
GHOUL = '/home/claude/fnv/ghoul_src/'
LEGS = [('Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot'), ('Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot')]
THUMBS = {f'Bip01 {s} Thumb1{b}': f'Bip01 {s} Finger0{b2}' for s in 'LR' for b, b2 in (('', ''), ('1', '1'), ('2', '2'))}
FOOT = {'m:L': 'Sound: NPCGhostFootLeft', 'm:R': 'Sound: NPCGhostFootRight'}

def keys_for(k):
    out = []
    for t, s in k.textkeys:
        if s.startswith('Enum:'): continue                 # creature foot/aux enums: no meaning on a Character
        out.append((t, s))
        if s in FOOT: out.append((t, FOOT[s]))
    return sorted(out, key=lambda x: x[0])

def build(out_dir, fps=30):
    import creatures.ghost as cfg
    cr = Creature(cfg)
    rt = Retarget(GHOUL + 'skeleton.nif', GHOST_SKEL, LEGS, THUMBS, skip=('Bip01 Head2', 'Bip01 Footsteps'))
    bones = [(n, 30) for n in rt.hs.order if (n in rt.map or n in rt.ROOTS or n == 'Bip01 Neck1')]
    assert all(n.startswith('Bip01') for n, _ in bones), [n for n, _ in bones if not n.startswith('Bip01')]
    os.makedirs(out_dir, exist_ok=True)
    jobs = [('mtfastforward.kf', 'locomotion/mtfastforward.kf', 'FastForward', 0),
            ('mtfastbackward.kf', 'locomotion/mtfastbackward.kf', 'FastBackward', 0),
            ('mtfastleft.kf', 'locomotion/mtfastforward.kf', 'FastLeft', 90),
            ('mtfastright.kf', 'locomotion/mtfastforward.kf', 'FastRight', -90)]
    report = []
    for out, src, seq, strafe in jobs:
        k = KFEval(GHOUL + src); L = k.stop; n = int(round(L * fps)) + 1
        frames = []
        for i in range(n):
            t = L * i / (n - 1)
            loc, _ = rt.frame(k, t, strafe)
            frames.append((t, loc))
        write_kf(cr, os.path.join(out_dir, out), seq, L, keys_for(k), frames, bones=bones, cycle=0)
        report.append((out, seq, L, len(frames)))
    return rt, report

if __name__ == '__main__':
    rt, rep = build(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/fnv/build/ghost_run')
    print('leg ratio %.3f  ankle src %.2f dst %.2f' % (rt.ratio, rt.ankle_g, rt.ankle_h))
    for r in rep: print(r)
