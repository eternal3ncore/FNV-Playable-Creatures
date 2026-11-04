"""Ghost People unarmed forward power attack: a gas spray from the mask (replaces the Dead Money forward lunge).

The Ghost steps in on its leading (left) foot, rears its head back as it draws breath, then thrusts head and chest
forward and sprays gas from the respirator (one Hit), holds the spray with a short sweep, and steps back to where it
started (the accum root never moves: the actor ends where it began). Built on the Ghost's own skeleton from the H2H
stance (the first frame of its standing power attack = its H2H aim), so it blends like the other attacks:
  * pelvis (Bip01 NonAccum) forward / down, both feet planted by two-bone leg IK; the front foot lifts and steps
  * spine lean, neck / head pitch (rear back, then thrust), head held on the target during the spray
  * arms swept back and out to the sides (two-bone arm IK, targets in the leaning torso frame), hands opened
  * the spray: the skeleton's PCGhostMaskSpray particle system (build_skel_ghost.py, on Bip01 Head at the respirator,
    emitter off at rest) switched on for the spray by this file - controlled blocks NiPSysEmitterCtlr EmitterActive
    (on SPRAY_ON .. SPRAY_OFF) and BirthRate - as the Dead Money idle drives the ghost's breath
  * text keys: start, attack vocal, footsteps (Enum: Left / Right as the vanilla file's), the spray sound, Hit, end
Sneak: the same motion on the sneak stance's frame.
Also writes h2hattackcustom1power (+ sneak) = the Dead Money lunge renamed: the unarmed forward perk move plays
Custom1 instead of AttackForwardPower, and the gas effect fires on AttackForwardPower only (EAMT 0x5D).
Sources: --src <folder> with the Dead Money forward power attack and the standing power attack (+ sneak copies) as
shipped before this file replaced them (anim_backup: ghost_spray_src).
usage: python3 -P ghost_spray.py <Ghost anim folder (out)> --src <source folder> [--render out.png]"""
import os, sys, struct, importlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval, q2m, m2q, slerp
from rig import Creature, write_kf, rotm, align, orth, smooth
from nifedit import NifFile

LENGTH = 1.6
HIT = 0.60
SPRAY_ON, SPRAY_OFF = 0.55, 0.92        # emitter active (s)
BIRTH = 160.0                            # particles / s while on
SPRAY_NODE = 'PCGhostMaskSpray'          # particle system in the skeleton
SPRAY_SOUND = 'PCGhostGasSprayHiss'      # SOUN editor id (GhostPeople plugin)
MASK = np.array([2.5, 13.0, 0.0])        # respirator front, Bip01 Head space (+X up the neck, +Y face, +Z left)
MASK_DIR = np.array([-0.25, 1.0, 0.0]) / np.hypot(0.25, 1.0)    # spray direction there (a little below the face line)
SPRAY_PITCH = 4.0                        # deg above level at the spray
STEP = 24.0                              # front foot step (units, forward)
LIFT = 7.0                               # front foot lift at mid-step
PELVIS = (0.0, 13.0, -2.0)               # pelvis shift at full extension (actor frame: +Y forward, +Z up)
# hands at the spray: down at the sides and a little back - direction from the shoulder (actor axes at the stance: +X right,
# +Y forward, +Z up), REACH from it; they swing round the shoulder from the guard, elbows carried with them (+ POLE back)
ARM = {'R': (0.30, -0.45, -0.84), 'L': (-0.30, -0.45, -0.84)}
REACH = 31.0
POLE = {'R': (4.0, -8.0, 0.0), 'L': (-4.0, -8.0, 0.0)}

cfg = importlib.import_module('creatures.ghost'); cr = Creature(cfg); sk = cr.sk


def env(t, a, b): return smooth((t - a) / (b - a))


def curves(t):
    """motion parameters at time t"""
    step_in = env(t, 0.04, 0.34); step_out = env(t, 0.98, 1.30)
    foot = step_in - step_out
    swing = np.sin(np.pi * np.clip((t - 0.04) / 0.30, 0, 1)) + np.sin(np.pi * np.clip((t - 0.98) / 0.32, 0, 1))
    pel = env(t, 0.06, 0.48) - env(t, 0.94, 1.38)
    rear = env(t, 0.18, 0.46) - env(t, 0.46, 0.58)          # head back as it draws breath
    thrust = env(t, 0.46, 0.60) - env(t, 0.96, 1.42)        # head / chest forward for the spray
    arms = env(t, 0.06, 0.56) - env(t, 0.96, 1.50)
    hold = np.clip((t - HIT) / (0.94 - HIT), 0, 1) if HIT <= t <= 0.94 else 0.0
    sweep = 8.0 * np.sin(2 * np.pi * hold) * (1 - hold)      # a short side-to-side of the spray
    return dict(foot=foot, swing=swing, pel=pel, rear=rear, thrust=thrust, arms=arms, sweep=sweep)


def leg_ik(loc, fk, side, target, Rfoot, pole):
    th, ca, ft = f'Bip01 {side} Thigh', f'Bip01 {side} Calf', f'Bip01 {side} Foot'
    W = fk(loc); S, E, G = W[th][0], W[ca][0], W[ft][0]
    a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
    d = target - S; dist = np.linalg.norm(d); dn = d / dist
    dc = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.999)
    cosA = (a * a + dc * dc - b * b) / (2 * a * dc)
    pv = pole - S; pv = pv - dn * np.dot(pv, dn); pv /= np.linalg.norm(pv)
    En = S + dn * a * cosA + pv * a * np.sqrt(max(0.0, 1 - cosA * cosA))
    loc[th] = (loc[th][0], W[sk.parent[th]][1].T @ (align(E - S, En - S) @ W[th][1]))
    W = fk(loc); E, G = W[ca][0], W[ft][0]
    loc[ca] = (loc[ca][0], W[th][1].T @ (align(G - E, S + dn * dc - E) @ W[ca][1]))
    W = fk(loc); loc[ft] = (loc[ft][0], W[ca][1].T @ Rfoot)


def arm_ik(loc, fk, side, target, pole):
    """two-bone arm IK on a hinge: the forearm turns only about the elbow's own axis (its bend axis in the stance, in the
    upper arm's frame), so the IK never rolls the forearm; the upper arm takes direction + the plane through the pole"""
    _, ua, fa, hand = cr.arm[side]
    W = fk(loc); S, E, G = W[ua][0], W[fa][0], W[hand][0]
    Ru, Rf = W[ua][1], W[fa][1]
    a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
    ul = Ru.T @ (E - S) / a; fl = Ru.T @ (G - E) / b                      # bone directions in the upper arm's frame
    hl = np.cross(ul, fl); hl /= np.linalg.norm(hl)                        # elbow hinge, upper arm frame
    d = target - S; dist = np.linalg.norm(d); dn = d / dist
    dc = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.995)
    cosA = (a * a + dc * dc - b * b) / (2 * a * dc)
    pv = pole - S; pv = pv - dn * np.dot(pv, dn); pv /= np.linalg.norm(pv)
    En = S + dn * a * cosA + pv * a * np.sqrt(max(0.0, 1 - cosA * cosA))
    u = (En - S) / a; f = (S + dn * dc - En); f /= np.linalg.norm(f)
    h = np.cross(u, f); h /= np.linalg.norm(h)
    A_l = np.column_stack([ul, hl, np.cross(ul, hl)]); A_w = np.column_stack([u, h, np.cross(u, h)])
    Ru_new = A_w @ A_l.T
    loc[ua] = (loc[ua][0], W[sk.parent[ua]][1].T @ Ru_new)
    W = fk(loc); fcur = (W[hand][0] - W[fa][0]); fcur /= np.linalg.norm(fcur)
    ang = np.degrees(np.arctan2(np.dot(np.cross(fcur, f), h), np.dot(fcur, f)))
    loc[fa] = (loc[fa][0], W[ua][1].T @ (rotm(h, ang) @ W[fa][1]))


def world_rot(loc, fk, nm, Rw_delta):
    """turn bone nm by a world-space rotation about its own origin"""
    W = fk(loc); loc[nm] = (loc[nm][0], W[sk.parent[nm]][1].T @ (Rw_delta @ W[nm][1]))


def build(src, stance, out, render=None):
    ev = KFEval(src); st = KFEval(stance)
    prio = {b[0]: b[2] for b in st.blocks}; prio.update({b[0]: b[2] for b in ev.blocks})
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
    def fk(loc):
        W = {}
        for nm in sk.order:
            t, R = loc[nm]; p = sk.parent[nm]
            W[nm] = (t.copy(), R.copy()) if p is None else (W[p][0] + W[p][1] @ t, W[p][1] @ R)
        return W
    base = full(st.sample(st.start))          # the H2H stance (the standing power attack's first frame = the H2H aim)
    W0 = fk(base)
    feet = {s: (W0[f'Bip01 {s} Foot'][0].copy(), W0[f'Bip01 {s} Foot'][1].copy()) for s in 'LR'}
    front = 'L' if feet['L'][0][1] > feet['R'][0][1] else 'R'
    hands = {s: W0[cr.arm[s][3]][0].copy() for s in 'LR'}
    spray_hands = {s: W0[cr.arm[s][1]][0] + REACH * np.array(ARM[s]) / np.linalg.norm(ARM[s]) for s in 'LR'}
    knee = {s: W0[f'Bip01 {s} Calf'][0] + np.array([0, 25.0, 0]) for s in 'LR'}
    fingers = [n for s in 'LR' for n in cr.fingers[s] if n in sk.local]
    X = np.array([1.0, 0, 0])
    _d = W0['Bip01 Head'][1] @ MASK_DIR; P0 = np.degrees(np.arcsin(_d[2]))      # the stance's face pitch

    def pose(t):
        c = curves(t); loc = {k: (v[0].copy(), v[1].copy()) for k, v in base.items()}
        # pelvis
        na = 'Bip01 NonAccum'; loc[na] = (loc[na][0] + np.array(PELVIS) * c['pel'], loc[na][1])
        # spine: lean (forward = rotation about +X by a negative angle), the rear-back straightens it a little
        lean = 6.0 * c['pel'] - 5.0 * c['rear'] + 12.0 * c['thrust']
        for nm, w in (('Bip01 Spine', 0.3), ('Bip01 Spine1', 0.35), ('Bip01 Spine2', 0.35)):
            world_rot(loc, fk, nm, rotm(X, -lean * w))
        # neck forward / head back up: the head juts out and the mask stays on the target; head rears back first
        neck = -14.0 * c['rear'] + 20.0 * c['thrust']
        world_rot(loc, fk, 'Bip01 Neck', rotm(X, -neck * 0.5)); world_rot(loc, fk, 'Bip01 Neck1', rotm(X, -neck * 0.5))
        # head: the face (the respirator's spray direction) pitched up as it rears back, then on the target at the
        # spray (SPRAY_PITCH: a standing human's chest at unarmed reach), with a short side-to-side sweep
        W = fk(loc); d = W['Bip01 Head'][1] @ MASK_DIR
        want = P0 + (14.0 - P0) * c['rear'] * (1 - c['thrust']) + (SPRAY_PITCH - P0) * c['thrust']
        side = np.cross(d, [0, 0, 1.0]); side /= np.linalg.norm(side)
        world_rot(loc, fk, 'Bip01 Head', rotm([0, 0, 1.0], c['sweep']) @ rotm(side, want - np.degrees(np.arcsin(d[2]))))
        # shoulders up on the breath, forward on the spray
        for s, sg in (('R', 1), ('L', -1)):
            world_rot(loc, fk, f'Bip01 {s} Clavicle', rotm([0, 1.0, 0], sg * 6.0 * c['rear']) @ rotm(X, -8.0 * c['thrust']))
        # arms back and out, in the leaning torso's frame
        W = fk(loc); Tw = W['Bip01 Spine2'][1] @ W0['Bip01 Spine2'][1].T; T0 = W0['Bip01 Spine2'][0]
        for s in 'LR':
            sh = W0[cr.arm[s][1]][0]; v0 = hands[s] - sh; v1 = spray_hands[s] - sh; u = c['arms']
            n0, n1 = np.linalg.norm(v0), np.linalg.norm(v1); a = np.arccos(np.clip(np.dot(v0, v1) / (n0 * n1), -1, 1))
            dv = (np.sin((1 - u) * a) * v0 / n0 + np.sin(u * a) * v1 / n1) / np.sin(a)     # the hand swings round the shoulder
            vt = dv * (n0 + (n1 - n0) * u); tgt = W['Bip01 Spine2'][0] + Tw @ (sh + vt - T0)
            # elbow: the stance's elbow carried round with the hand (least upper-arm roll), a little further back
            pole = sh + align(v0, vt) @ (W0[cr.arm[s][2]][0] - sh) + np.array(POLE[s]) * u
            arm_ik(loc, fk, s, tgt, W['Bip01 Spine2'][0] + Tw @ (pole - T0))
        # open hands
        for nm in fingers:
            loc[nm] = (loc[nm][0], q2m(slerp(m2q(base[nm][1]), m2q(orth(sk.local[nm][1])), 0.85 * c['arms'])))
        # feet: the back foot stays, the front foot steps
        for s in 'LR':
            p, R = feet[s]
            if s == front:
                p = p + np.array([0, STEP * c['foot'], LIFT * c['swing']])
                R = rotm(X, -12.0 * c['swing']) @ R          # toe down as it lifts
            leg_ik(loc, fk, s, p, R, knee[s] + (np.array([0, STEP * c['foot'], 0]) if s == front else 0))
        return loc

    global DBG; DBG = dict(pose=pose, fk=fk, W0=W0)          # for checks from the shell
    fps = 30; n = int(round(LENGTH * fps)) + 1
    frames = [(LENGTH * i / (n - 1), pose(LENGTH * i / (n - 1))) for i in range(n)]
    # the arms' IK rolls the forearm about its own line as the hand swings past the shoulder (up to ~30 deg a frame):
    # smoothed in time (binomial, 3 passes, the first / last frames kept = the stance) - the hands are free, nothing to hit
    arm_bones = [nm for s in 'LR' for nm in sk.order if nm in base and (nm in cr.arm[s][1:] or (f'{s} Fore' in nm) or
                 (f'{s}UpArm' in nm) or nm in cr.fingers[s])]
    for _ in range(3):
        qs = {nm: [m2q(loc[nm][1]) for _, loc in frames] for nm in arm_bones}
        for nm, Q in qs.items():
            for i in range(1, n - 1):
                a, b, c_ = Q[i - 1], Q[i], Q[i + 1]
                a = a if np.dot(a, b) >= 0 else -a; c_ = c_ if np.dot(c_, b) >= 0 else -c_
                q = (a + 2 * b + c_) / 4; frames[i][1][nm] = (frames[i][1][nm][0], q2m(q / np.linalg.norm(q)))
    # check: the feet are where they should be
    errs = []
    for t, loc in frames:
        W = fk(loc); c = curves(t)
        for s in 'LR':
            want = feet[s][0] + (np.array([0, STEP * c['foot'], LIFT * c['swing']]) if s == front else 0)
            errs.append(np.linalg.norm(W[f'Bip01 {s} Foot'][0] - want))
    keys = [(0.0, 'start'), (0.0, 'Sound: PCGhostAttackVox'), (0.30, f'Enum: {"Left" if front == "L" else "Right"}'),
            (SPRAY_ON - 0.02, f'Sound: {SPRAY_SOUND}'), (HIT, 'Hit'), (HIT + 1e-5, 'Decal: 0'),
            (1.28, f'Enum: {"Left" if front == "L" else "Right"}'), (LENGTH, 'end')]
    bones = [(nm, prio.get(nm, 45)) for nm in sk.order if nm in prio and nm in base]
    seq = ev.name
    write_kf(cr, out, seq, LENGTH, keys, frames, bones=bones)
    add_emitter(out, SPRAY_NODE, [(0.0, 0), (SPRAY_ON, 1), (SPRAY_OFF, 0), (LENGTH, 0)], BIRTH, max(prio.values()))
    print(os.path.basename(out), seq, 'front foot', front, 'max foot error %.2f' % max(errs), len(bones), 'bones')
    if render:
        from render import draw
        ts = (0.0, 0.3, 0.46, HIT, 0.8, 1.2, LENGTH)
        draw(sk, [fk(pose(t)) for t in ts], [f't={t:.2f}' for t in ts], render)
    return frames


def add_emitter(path, node, active_keys, birth, prio):
    """controlled blocks for a particle system's NiPSysEmitterCtlr: EmitterActive (constant-step bool keys) and BirthRate"""
    f = NifFile(path); si = f.str_index
    seq_i = next(i for i, b in enumerate(f.btype) if f.types[b] == 'NiControllerSequence')
    bd = f.add_block('NiBoolData', struct.pack('<II', len(active_keys), 5) + b''.join(struct.pack('<fB', t, v) for t, v in active_keys))
    bi = f.add_block('NiBoolInterpolator', struct.pack('<Bi', 2, bd))
    fi = f.add_block('NiFloatInterpolator', struct.pack('<fi', birth, -1))
    d = f.blocks[seq_i]; nm, ncb, arr = struct.unpack_from('<iII', d, 0)
    cbs = d[12:12 + 29 * ncb]; tail = d[12 + 29 * ncb:]
    for interp, var in ((fi, 'BirthRate'), (bi, 'EmitterActive')):
        cbs += struct.pack('<iiBiiiii', interp, -1, prio, si(node), -1, si('NiPSysEmitterCtlr'), si('NiPSysBoxEmitter:0'), si(var))
    # HeadTrack extra data 100 while it plays, as every Dead Money attack file keys it
    ht = f.add_block('NiFloatInterpolator', struct.pack('<fi', 100.0, -1))
    cbs += struct.pack('<iiBiiiii', ht, -1, prio, si('Bip01 Head'), -1, si('NiFloatExtraDataController'), si('HeadTrack'), -1)
    f.blocks[seq_i] = struct.pack('<iII', nm, ncb + 3, arr) + cbs + tail
    open(path, 'wb').write(f.to_bytes())


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    folder = a[0]; render = sys.argv[sys.argv.index('--render') + 1] if '--render' in sys.argv else None
    src_dir = sys.argv[sys.argv.index('--src') + 1] if '--src' in sys.argv else folder
    from power_fill import renamed
    for sn in ('', 'sneak'):
        # the unarmed forward perk move (Custom1, e.g. Legion Assault) keeps the Dead Money lunge: the gas only fires on
        # the EAMT group (AttackForwardPower), so a spray played as Custom1 would knock nobody down
        renamed(os.path.join(src_dir, f'{sn}h2hattackforwardpower.kf'), os.path.join(folder, f'{sn}h2hattackcustom1power.kf'), 'AttackCustom1Power')
        build(os.path.join(src_dir, f'{sn}h2hattackforwardpower.kf'), os.path.join(src_dir, f'{sn}h2hattackpower.kf'),
              os.path.join(folder, f'{sn}h2hattackforwardpower.kf'), render=(render.replace('.png', f'_{sn or "stand"}.png') if render else None))
