"""Max Payne 2 style shootdodge dives for the human skeleton (characters\\_male), as the directional jump groups:
JumpLoopLeft / Right / Backward (the dive in the air) and JumpLandLeft / Right / Backward (the landing and the get-up),
for mt (unarmed / holstered) and sneakmt. Because they are jump animations the engine lets the player attack in the air
as in any jump; the dive keys the root, pelvis, legs (and for the back dive the spine / neck) above every weapon file's
lower-body priority, and the arms low (ARM_PRIO, below every weapon stance), so a drawn weapon keeps its hold / aim /
attack on top of the dive.

Side dive (Left / Right): the whole body rolls ROLL_SIDE about the forward axis at the pelvis - head leading in the travel
direction, legs trailing - and tilts TILT_SIDE face-up about the body's long axis. Rolling about the forward axis keeps the
chest (and so a drawn weapon's aim) facing forward: the gun is held on its side, as in the game. Back dive: the body pitches
PITCH_BACK backward (head to the rear, legs forward and up) and curls the spine CURL_BACK forward so the chest still faces
forward. Unarmed, the arms reach forward as if aiming two pistols.
Loop: standing -> dive pose over TAKEOFF s, then held (CLAMP, so a long fall keeps the pose instead of restarting).
Land: the body drops onto its side / back (IMPACT s), lies (to RISE0), then rolls back up onto its feet (feet planted by
leg IK through a crouch) and ends on the idle's first frame.
usage: python3 -P dive.py <out folder> [--render out.png] [--prefixes 1hp,2hr,...]"""
import os, sys, types, importlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval, q2m, m2q, slerp
from rig import Creature, write_kf, rotm, align, orth, smooth

REF = '/home/claude/fnv/ref_jump/meshes/characters/_male'
_g = importlib.import_module('creatures.ghost')
cfg = types.SimpleNamespace(**{k: getattr(_g, k) for k in dir(_g) if k.isupper()})
cfg.SKELETON = '/home/claude/fnv/meshes/characters/_male/skeleton.nif'
cfg.ANIM_SRC = REF; cfg.TEMPLATE_KF = 'mtjumplandleft.kf'; cfg.IDLE_KF = 'locomotion/mtidle.kf'
cr = Creature(cfg); sk = cr.sk

TAKEOFF = 0.30; LOOP_LEN = 0.90
IMPACT = 0.14; RISE0 = 0.42; RISE1 = 0.98; LAND_LEN = 1.00
ROLL_SIDE = 82.0; TILT_SIDE = 18.0; TILT_LAND = 40.0          # deg
PITCH_BACK = 78.0; CURL_BACK = 46.0
AIR_Z = {'side': 58.0, 'back': 56.0}                            # pelvis height in the air (actor origin = the jumping actor)
GROUND_Z = {'side': 13.0, 'back': 12.0}                         # pelvis height lying on the ground
FLOOR = 0.4                                                     # min height of any bone above the floor while lying
LOW_PRIO = 60                                                   # root / pelvis / legs: above every weapon file (max 57)
SPINE_PRIO = 32                                                 # back dive spine / neck / head: above the aims' 30
ARM_PRIO = 22                                                   # arms: above the idles (20), below every weapon stance
X, Y, Z = np.eye(3)
LEGS = [f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot', 'Toe0')]
ROOT = ['Bip01 NonAccum', 'Bip01 Pelvis']
SPINE = ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2', 'Bip01 Neck', 'Bip01 Neck1', 'Bip01 Head']


def fk(loc):
    W = {}
    for nm in sk.order:
        t, R = loc[nm]; p = sk.parent[nm]
        W[nm] = (t.copy(), R.copy()) if p is None else (W[p][0] + W[p][1] @ t, W[p][1] @ R)
    return W


def full(smp):
    loc = {}
    for nm in sk.order:
        t, R, _ = sk.local[nm]
        if nm in smp:
            if smp[nm][0] is not None: t = smp[nm][0]
            if smp[nm][1] is not None: R = smp[nm][1]
        loc[nm] = (np.array(t, float), orth(np.array(R, float)))
    loc['Bip01'] = (np.zeros(3), np.eye(3))
    return loc


def world_rot(loc, nm, Rw):
    W = fk(loc); loc[nm] = (loc[nm][0], W[sk.parent[nm]][1].T @ (Rw @ W[nm][1]))


def two_bone(loc, a_nm, b_nm, c_nm, target, pole):
    """2-bone IK (thigh / calf / foot or upper arm / forearm / hand): the end of b (c's origin) onto target"""
    W = fk(loc); S, E, G = W[a_nm][0], W[b_nm][0], W[c_nm][0]
    a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
    d = target - S; dist = np.linalg.norm(d); dn = d / dist
    dc = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.999)
    cosA = (a * a + dc * dc - b * b) / (2 * a * dc)
    pv = pole - S; pv = pv - dn * np.dot(pv, dn); pv /= np.linalg.norm(pv)
    En = S + dn * a * cosA + pv * a * np.sqrt(max(0.0, 1 - cosA * cosA))
    loc[a_nm] = (loc[a_nm][0], W[sk.parent[a_nm]][1].T @ (align(E - S, En - S) @ W[a_nm][1]))
    W = fk(loc); E, G = W[b_nm][0], W[c_nm][0]
    loc[b_nm] = (loc[b_nm][0], W[a_nm][1].T @ (align(G - E, S + dn * dc - E) @ W[b_nm][1]))


def blend(a, b, w, names):
    out = dict(a)
    for nm in names:
        ta, Ra = a[nm]; tb, Rb = b[nm]
        qa, qb = m2q(Ra), m2q(Rb)
        if np.dot(qa, qb) < 0: qb = -qb
        out[nm] = (ta + (tb - ta) * w, q2m(slerp(qa, qb, w)))
    return out


class Dive:
    def __init__(s, kind, base):
        s.kind = kind                                   # 'L', 'R', 'B'
        s.side = kind in 'LR'; s.d = -1.0 if kind == 'L' else 1.0
        s.base = base; s.W0 = fk(base)
        s.feet = {k: (s.W0[f'Bip01 {k} Foot'][0].copy(), s.W0[f'Bip01 {k} Foot'][1].copy()) for k in 'LR'}
        s.na0 = base['Bip01 NonAccum']

    def root_rot(s, w, tilt):
        if s.side: return rotm(X, tilt * w) @ rotm(Y, s.d * ROLL_SIDE * w)
        return rotm(X, PITCH_BACK * w)

    def body(s, w, legs_w, tilt, z, aim_w, settle=0.0):
        """the dive pose at amount w (0 = standing base, 1 = full dive)"""
        loc = {k: (v[0].copy(), v[1].copy()) for k, v in s.base.items()}
        # legs (in the upright body frame): side - trailing, a little bent, staggered; back - thrown forward and up
        if s.side:
            lead, trail = ('L', 'R') if s.kind == 'L' else ('R', 'L')
            bends = {lead: (16, -36), trail: (6, -20)}
        else:
            bends = {'L': (26, -42), 'R': (12, -26)}
        for k, (hip, knee) in bends.items():
            world_rot(loc, f'Bip01 {k} Thigh', rotm(X, hip * legs_w))       # + = hip flexion (knee forward)
            world_rot(loc, f'Bip01 {k} Calf', rotm(X, knee * legs_w))        # - = knee bend (foot back)
            world_rot(loc, f'Bip01 {k} Foot', rotm(X, -14 * legs_w))       # toes pointed
        if s.side:
            # spread the legs a touch along the travel line, the trailing one further out
            world_rot(loc, f'Bip01 {trail} Thigh', rotm(Y, s.d * 8 * legs_w))
        else:
            # curl the trunk forward (sit-up) so the chest faces forward again, chin down
            for nm, f in (('Bip01 Spine', 0.30), ('Bip01 Spine1', 0.35), ('Bip01 Spine2', 0.35)):
                world_rot(loc, nm, rotm(X, -CURL_BACK * f * w))
            world_rot(loc, 'Bip01 Neck', rotm(X, -0.5 * (PITCH_BACK - CURL_BACK) * w))
            world_rot(loc, 'Bip01 Head', rotm(X, -0.4 * (PITCH_BACK - CURL_BACK) * w))
        # the whole body about the pelvis (Bip01 NonAccum): roll / pitch, then the pelvis to its height
        t0, R0 = s.na0
        loc['Bip01 NonAccum'] = (np.array([t0[0], t0[1], z]), s.root_rot(w, tilt) @ R0)
        # arms: reach forward as if aiming (world-space targets after the body turn: straight ahead of the shoulders)
        if aim_w > 0:
            aimed = {k: (v[0].copy(), v[1].copy()) for k, v in loc.items()}
            W = fk(aimed)
            mid = 0.5 * (W['Bip01 R UpperArm'][0] + W['Bip01 L UpperArm'][0])
            for k, sg in (('R', 1.0), ('L', -1.0)):
                _, ua, fa, hand = cr.arm[k]
                sh = W[ua][0]
                tgt = mid + np.array([sg * 4.0, 44.0, -6.0 + settle])
                pole = sh + np.array([sg * 14.0, 0.0, -14.0])
                two_bone(aimed, ua, fa, hand, tgt, pole)
                # hand level, palm in (as on a pistol grip): the hand's +X (along the fingers) forward
                W2 = fk(aimed); Rh = W2[hand][1]
                aimed[hand] = (aimed[hand][0], W2[fa][1].T @ (align(Rh @ X, Y) @ Rh))
            arm_names = [n for k in 'LR' for n in cr.arm[k][1:]]
            loc = blend(loc, aimed, aim_w, arm_names)
        return loc

    def loop(s, t):
        w = smooth(t / TAKEOFF)
        drift = smooth((t - TAKEOFF) / (LOOP_LEN - TAKEOFF)) if t > TAKEOFF else 0.0
        tilt = (TILT_SIDE + 4.0 * drift) if s.side else 0.0
        z0 = s.na0[0][2]; za = AIR_Z['side' if s.side else 'back']
        return s.body(w, w, tilt, z0 + (za - z0) * w - 2.0 * drift, w)

    def land(s, t):
        k = 'side' if s.side else 'back'
        imp = smooth(t / IMPACT)
        g = smooth((t - RISE0) / (RISE1 - RISE0)) if t > RISE0 else 0.0
        bounce = 3.0 * np.sin(np.pi * np.clip((t - IMPACT) / 0.2, 0, 1)) * (1 - g)
        z_lie = AIR_Z[k] + (GROUND_Z[k] - AIR_Z[k]) * imp + bounce
        z0 = s.na0[0][2]
        tilt = (TILT_SIDE + 4.0 + (TILT_LAND - TILT_SIDE - 4.0) * imp) if s.side else 0.0
        w = 1.0 - g
        # pelvis: from lying up through a crouch (z rises slower at first) to standing
        z = z_lie + (z0 - z_lie) * g ** 1.4
        loc = s.body(w, w, tilt * w if g > 0 else tilt, z, 1.0 - smooth(g / 0.7))
        wf = 0.0
        if g > 0:
            # feet onto the ground at their standing spots as the body comes up (knees forward)
            ik = {kk: (v[0].copy(), v[1].copy()) for kk, v in loc.items()}
            for side in 'LR':
                p, Rf = s.feet[side]
                knee = fk(ik)[f'Bip01 {side} Calf'][0] + np.array([0, 40.0, 0])
                two_bone(ik, f'Bip01 {side} Thigh', f'Bip01 {side} Calf', f'Bip01 {side} Foot', p, knee)
                W = fk(ik); ik[f'Bip01 {side} Foot'] = (ik[f'Bip01 {side} Foot'][0], W[f'Bip01 {side} Calf'][1].T @ Rf)
            wf = smooth((g - 0.15) / 0.35)
            loc = blend(loc, ik, wf, LEGS)
        if t >= RISE1:
            return {kk: (v[0].copy(), v[1].copy()) for kk, v in s.base.items()}
        # nothing below the floor while lying / rising: the pelvis lifted so the lowest bone (feet, toes, head, hands) stays
        # FLOOR above the ground (the actor origin; the standing toes are 0.5 up)
        W = fk(loc); low = min(W[n][0][2] for n in sk.order if n.startswith('Bip01 ') and n != 'Bip01 NonAccum')
        lift = max(0.0, FLOOR - low)
        if lift > 0:
            tt, R = loc['Bip01 NonAccum']; loc['Bip01 NonAccum'] = (tt + np.array([0, 0, lift]), R)
        return loc


def frames_of(fn, length, fps=30):
    n = int(round(length * fps)) + 1
    return [(length * i / (n - 1), fn(length * i / (n - 1))) for i in range(n)]


def bones_for(kind):
    b = [(n, LOW_PRIO) for n in ROOT + LEGS]
    if kind == 'B': b += [(n, SPINE_PRIO) for n in SPINE]
    b += [(n, ARM_PRIO) for k in 'LR' for n in cr.arm[k][1:]]
    return [x for x in b if x[0] in sk.local]


NAMES = {'L': 'Left', 'R': 'Right', 'B': 'Backward'}


def build(out, prefix, base, render=None):
    made = []
    for kind in 'LRB':
        dv = Dive(kind, base)
        for grp, fn, length, keys in (
                ('JumpLoop', dv.loop, LOOP_LEN, [(0.0, 'start'), (LOOP_LEN, 'end')]),
                ('JumpLand', dv.land, LAND_LEN, [(0.0, 'start'), (0.85, 'Enum: Left'), (0.95, 'Enum: Right'), (LAND_LEN, 'end')])):
            frames = frames_of(fn, length)
            name = f'{prefix}{grp}{NAMES[kind]}'.lower() + '.kf'
            seq = f'{grp}{NAMES[kind]}'                       # the engine takes the group from the sequence name
            write_kf(cr, os.path.join(out, name), seq, length, keys, frames, bones=bones_for(kind), cycle=2)
            # checks: the land ends on the base pose, feet on the ground while rising
            W = fk(frames[-1][1]); Wb = fk(base)
            err = max(np.linalg.norm(W[n][0] - Wb[n][0]) for n in ('Bip01 Head', 'Bip01 L Foot', 'Bip01 R Foot'))
            made.append((name, len(frames), round(err, 3)))
            if render and kind in 'LB':
                from render import draw
                ts = [0, length * 0.25, length * 0.5, length * 0.75, length]
                draw(sk, [fk(fn(t)) for t in ts], [f'{name} t={t:.2f}' for t in ts], render.replace('.png', f'_{name[:-3]}.png'))
    return made


if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    render = sys.argv[sys.argv.index('--render') + 1] if '--render' in sys.argv else None
    stand = full(KFEval(os.path.join(REF, 'locomotion/mtidle.kf')).sample(0))
    crouch = full(KFEval(os.path.join(REF, 'sneakmtidle.kf')).sample(0))
    for prefix, base in (('mt', stand), ('sneakmt', crouch)):
        for m in build(out, prefix, base, render if prefix == 'mt' else None): print(m)
