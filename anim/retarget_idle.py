"""Retarget the human furniture (chair / stool) idle set onto the Zetan skeleton.

Why: FNV looks furniture animations up in the idle tree that belongs to the actor's *skeleton folder*
(IdleManager, key "<skeleton folder>\\IdleAnims"). A creature-race player has no tree there, so the sit request finds
no entry animation, the engine aborts halfway and leaves the player locked in "want to sit" (the chair freeze). The
ESP now carries a tree per creature skeleton folder; this script makes the Zetan's animations for it.

The player is a Character, so the files follow the *Character* furniture convention (entry frame: actor at the entry
point facing the seat; seated frame: actor at the seat facing out). Mothership Zeta's alien chair enter/exit use the
creature convention (180 deg apart) and only exist for the front entry, so the enter/exit set is retargeted from the
human files for all four entry sides and the stool; the seated loop stays the alien's own (DynamicIdle_AliensSit) and
every chair enter blends into that pose over its last BLEND s (every exit starts from it), so there is no pop.

Method per frame (human source -> Zetan):
  * Bip01 (accum root): copied unscaled - the entry path length is set by the furniture marker, not by the body.
  * Bip01 NonAccum: x/y copied, height mapped linearly through (human seat -> Zetan seat, human stand -> Zetan stand).
  * other Bip01 bones: world-space delta from the source bind (W_dst = W_src * Bsrc^T * Bdst); alien thumb = Finger0.
  * legs: 2-bone IK; ankle target = Zetan pelvis + (source ankle - source pelvis) * leg ratio horizontally, height
    above ground * leg ratio (ground contact kept); foot keeps its retargeted world rotation.
usage: python3 retarget_idle.py <out_dir>"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import Skeleton, KFEval, m2q, q2m
from rig import Creature, write_kf
from retarget import Retarget, align

HUMAN_SKEL = '/home/claude/fnv/ref_weap/skeleton.nif'
HUMAN_SIT = '/home/claude/fnv/human_sit/meshes/characters/_male/idleanims/'
ALIEN_IDLE = '/home/claude/fnv/assets/meshes/dlc05/creatures/alien/idleanims/'
LEGS = [('Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot'), ('Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot')]
THUMBS = {f'Bip01 {s} Finger0{b}': f'Bip01 {s} Thumb1{b}' for s in 'LR' for b in ('', '1', '2')}
# NonAccum height anchors: (human, Zetan). Seat = the alien's own seated idle (38.3) vs the human's (36.8).
Z_SEAT = (36.85, 38.3)
Z_STAND = (67.4, 63.9)
BLEND = 0.5

def slerp(q0, q1, u):
    d = float(np.dot(q0, q1))
    if d < 0: q1 = -q1; d = -d
    if d > 0.9995: q = q0 + u * (q1 - q0); return q / np.linalg.norm(q)
    th = np.arccos(d); s = np.sin(th)
    return (np.sin((1 - u) * th) * q0 + np.sin(u * th) * q1) / s

class IdleRetarget(Retarget):
    def __init__(s, src_skel, dst_skel):
        Retarget.__init__(s, src_skel, dst_skel, LEGS, THUMBS, skip=('Bip01 Footsteps',))
        s.clean_root = False
        s.pel_g = s.Bg['Bip01 Pelvis'][0]; s.pel_h = s.Bh['Bip01 Pelvis'][0]
    @staticmethod
    def map_z(z):
        (hs, zs), (hS, zS) = Z_SEAT, Z_STAND
        return zs + (z - hs) * (zS - zs) / (hS - hs)
    def frame(s, k, t):
        hs, gs, r = s.hs, s.gs, s.ratio
        gl = s.src_pose(k, t); Wg = s.fk(gs, gl)
        loc = {}; Wr = {}
        for n in hs.order:
            p = hs.parent[n]; tb, Rb, _ = hs.local[n]
            if p is None:
                loc[n] = (np.array(tb, float), np.array(Rb, float)); Wr[n] = np.array(Rb, float); continue
            if n == 'Bip01':
                loc[n] = (gl[n][0].copy(), gl[n][1].copy()); Wr[n] = Wr[p] @ gl[n][1]; continue
            if n == 'Bip01 NonAccum':
                tt = gl[n][0].copy(); tt[2] = s.map_z(tt[2])
                loc[n] = (tt, gl[n][1].copy()); Wr[n] = Wr[p] @ gl[n][1]; continue
            src = s.map.get(n)
            Rw = Wg[src][1] @ s.Bg[src][1].T @ s.Bh[n][1] if src is not None else Wr[p] @ Rb
            Wr[n] = Rw
            loc[n] = (np.array(tb, float), Wr[p].T @ Rw)
        W = s.fk(hs, loc)
        pg = Wg['Bip01 Pelvis'][0]; ph = W['Bip01 Pelvis'][0]
        # ankle heights measured from the accum root (Bip01): in game it sits at the actor origin. Files that don't
        # key Bip01 (seated loops) sample the human bind height (67.8) there; measuring from the skeleton origin
        # would scale that offset too (feet off the ground by 67.8 * (ratio - 1) in those files).
        zg = Wg['Bip01'][0][2]; zh = W['Bip01'][0][2]
        for th, ca, ft in s.legs:
            d = Wg[ft][0] - pg
            T = np.array([ph[0] + d[0] * r, ph[1] + d[1] * r, zh + s.ankle_h + (Wg[ft][0][2] - zg - s.ankle_g) * r])
            s._ik(loc, th, ca, ft, T)
        return loc

def keys_of(k):
    return [(t, x) for t, x in k.textkeys]

def pose_locals(path, t=0.0):
    k = KFEval(path); return k.sample(t)

def blend_into(frames, target, t0, t1, bones, rising=True):
    """blend bone locals toward the target pose between t0..t1 (smoothstep). The target is the alien seated idle, which
    is in the seated frame; enter/exit files are in the entry frame (heading 180 deg apart), so the target's NonAccum
    rotation is turned 180 deg about z. Bip01 (the entry path) is never blended."""
    Rz180 = np.diag([-1.0, -1.0, 1.0])
    tgt = {n: (None if v[0] is None else np.array(v[0], float), None if v[1] is None else np.array(v[1], float)) for n, v in target.items()}
    if 'Bip01 NonAccum' in tgt and tgt['Bip01 NonAccum'][1] is not None:
        tgt['Bip01 NonAccum'] = (None, Rz180 @ tgt['Bip01 NonAccum'][1])        # height/offset stay the retarget's own
    out = []
    for t, loc in frames:
        u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
        u = min(1.0, max(0.0, u)); u = u if rising else 1.0 - u
        u = u * u * (3 - 2 * u)                         # smoothstep
        if u <= 0: out.append((t, loc)); continue
        nl = dict(loc)
        for n in bones:
            if n == 'Bip01' or n not in tgt: continue
            tt, R = loc[n]; ttg, Rg = tgt[n]
            if Rg is not None: R = q2m(slerp(m2q(R), m2q(Rg), u))
            if ttg is not None and n != 'Bip01 NonAccum': tt = tt + (ttg - tt) * u
            nl[n] = (tt, R)
        out.append((t, nl))
    return out

# (output file, source human file, sequence name, cycle, chair?)  chair enters blend into / exits start from the alien seat
JOBS = [
    ('Chair_ForwardEnter.kf', 'chair_forwardenter.kf', 'enter'),
    ('Chair_LeftEnter.kf', 'chair_leftenter.kf', 'enter'),
    ('Chair_RightEnter.kf', 'chair_rightenter.kf', 'enter'),
    ('Chair_BackEnter.kf', 'chair_backenter.kf', 'enter'),
    ('Chair_ForwardExit.kf', 'chair_forwardexit.kf', 'exit'),
    ('Chair_LeftExit.kf', 'chair_leftexit.kf', 'exit'),
    ('Chair_RightExit.kf', 'chair_rightexit.kf', 'exit'),
    ('Chair_BackExit.kf', 'chair_backexit.kf', 'exit'),
    ('StoolEnter.kf', 'stoolenter.kf', None),
    ('StoolExit.kf', 'stoolexit.kf', None),
    ('DynamicIdle_SitStool.kf', 'dynamicidle_sitstool.kf', None),
]

def build(out_dir, fps=30):
    import creatures.zetan as cfg
    cr = Creature(cfg)
    rt = IdleRetarget(HUMAN_SKEL, '/home/claude/fnv/build/meshes/PlayableCreatures/Zetan/Skeleton.nif')
    seat = pose_locals(ALIEN_IDLE + 'dynamicidle_alienssit.kf', 0.0)
    os.makedirs(out_dir, exist_ok=True)
    rep = []
    for out, src, kind in JOBS:
        k = KFEval(HUMAN_SIT + src); L = k.stop; n = int(round(L * fps)) + 1
        keyed = {b[0] for b in k.blocks}
        prio = max(b[2] for b in k.blocks)
        frames = [(L * i / (n - 1), rt.frame(k, L * i / (n - 1))) for i in range(n)]
        names = [nm for nm in rt.hs.order if nm.startswith('Bip01') and (nm in ('Bip01', 'Bip01 NonAccum') or rt.map.get(nm) in keyed)]
        if 'Bip01' not in keyed: names = [nm for nm in names if nm != 'Bip01']        # loops don't key the accum root
        if kind == 'enter': frames = blend_into(frames, seat, L - BLEND, L, names, rising=True)
        if kind == 'exit': frames = blend_into(frames, seat, 0.0, BLEND, names, rising=False)
        assert all(nm.startswith('Bip01') for nm in names)
        write_kf(cr, os.path.join(out_dir, out), k.name, L, keys_of(k), frames, bones=[(nm, prio) for nm in names], cycle=k.cycle)
        rep.append((out, k.name, round(L, 2), k.cycle, prio, len(names)))
    return rt, rep

if __name__ == '__main__':
    rt, rep = build(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/fnv/build/zetan_idle')
    print('leg ratio %.3f ankle src %.2f dst %.2f' % (rt.ratio, rt.ankle_g, rt.ankle_h))
    for r in rep: print(r)
