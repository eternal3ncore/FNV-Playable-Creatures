"""Deathclaw guns fire from its mouth (user: no feasible gun holds for its claws - hide the gun, open the mouth as if
firing from it, adapted from the fire gecko's breath). Rewrites every gun-type file (1HP, 2HR, 2HA, 2HH, 2HL and
their sneak copies; equip / unequip / holster excepted - those stay its own claw equips) in an assembled Deathclaw
folder, keeping each file's sequence name, length, cycle and text keys (vanilla timing and weapon events):
  body       its own unarmed aim (h2haim, claws ready), looped over the file
  Aim*Up/Down the head chain (Neck1 + Head) pitched +-PITCH so the mouth follows the look
  attacks    the fire gecko's 2hlattackspin (rear back, jaw wide open at 'Fire', sway, close at 'Loop'): its Spine4 /
             Neck2 / Head motion as body-frame rotations on the deathclaw's Spine2 / Neck1 / Head (canonical
             forward / left / up frames, so the two rigs' bone axes don't matter), its jaw angle x JAW_SCALE on
             Bip01 Ponytail3 (the deathclaw's lower jaw); time-warped so the gecko's 'Fire' lands on the file's
             Hit / Fire key; looping attacks (AttackLoop, short files) hold the open, swaying part
  reloads / jams / recoil: the aim, mouth closed (their gun Sound: keys dropped)
  Weapon     the skeleton's Weapon node (under the right hand; prn keys removed - a prn moves only the model) keyed every
             frame onto the mouth, +X along the mouth (level in the neutral aim, the barrel axis of the human guns), scale
             0.001: the gun model stays attached there unseen, so it, its own ProjectileNode and any node a script adds
             to it (3rd Person Aim Fix's Pr0jM) are at the mouth; the engine's shot leaves the skeleton's ProjectileNode
             (on the head at the mouth, found first)
Also: every melee / unarmed / gun file's Weapon channel (equips and holsters included) gets scale 0.001 (melee
weapons hidden - its claws are its weapons); thrown weapons / mines keep theirs.
usage: python3 deathclaw_mouth.py <Deathclaw folder> <Skeleton.nif to patch (adds ProjectileNode)> [--hide]
  --hide: only the Weapon scale on the non-mouth files (run again after the passes that add files, e.g. blockhit)"""
import os, re, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import Skeleton, KFEval, m2q, q2m, slerp
from rig import Creature, write_kf, rotm
from holster_fix import KFFile
from nifedit import NifFile
import importlib

G = '/home/claude/fnv/creature_src_gecko/gecko/'
GUNS = ('1hp', '2hr', '2ha', '2hh', '2hl')
HIDE = ('h2h', '1hm', '2hm') + GUNS
PITCH = 32.0                      # aim up / down: head chain pitch
JAW_SCALE = 0.6                   # gecko gape 73 deg -> 44 deg on the deathclaw's jaw
MOUTH = np.array([30.0, 6.0, 0.0])   # head-local point between the jaws (snout tip x 32.6, lower jaw tip (34.5, 11))
MAP = [('Bip01 Spine4', 'Bip01 Spine2'), ('Bip01 Neck2', 'Bip01 Neck1'), ('Bip01 Head', 'Bip01 Head')]
HIDE_SCALE = 0.001

cfg = importlib.import_module('creatures.deathclaw')
cr = Creature(cfg); sk = cr.sk
gs = Skeleton(G + 'skeleton.nif')


def full(skel, sample):
    out = {}
    for n in skel.order:
        t, R, _ = skel.local[n]
        if n in sample:
            if sample[n][0] is not None: t = sample[n][0]
            if sample[n][1] is not None: R = sample[n][1]
        out[n] = (np.array(t, float), np.array(R, float))
    out['Bip01'] = (np.zeros(3), np.eye(3))      # accum root at the actor origin
    return out


def canon(W, pelvis, head, na):
    """canonical forward / left / up axes expressed in the NonAccum (body) frame"""
    B = W[na][1]
    f = W[head][0] - W[pelvis][0]; f[2] = 0; f /= np.linalg.norm(f)
    u = np.array([0, 0, 1.0]); l = np.cross(u, f)
    return B.T @ np.column_stack([f, l, u])


# ---- gecko breath: per-time body-frame deltas of the mapped bones + jaw angle
gk_spin = KFEval(G + '2hlattackspin.kf')
gk_aim = full(gs, KFEval(G + '2hlaim.kf').sample(0))
Wg0 = gs.fk(gk_aim)
Cg = canon(Wg0, 'Bip01 Pelvis', 'Bip01 Head', 'Bip01 NonAccum')
G_FIRE = [t for t, k in gk_spin.textkeys if k == 'Fire'][0]
G_LOOP = [t for t, k in gk_spin.textkeys if k == 'Loop'][0]
G_END = gk_spin.stop

def jaw_angle(W):
    Rh = W['Bip01 Head'][1]; Rj = W['Bip01 Jaw'][1]
    return np.degrees(np.arccos(np.clip((np.trace(Rh.T @ Rj) - 1) / 2, -1, 1)))
JAW0 = jaw_angle(Wg0)

def _raw(t):
    W = gs.fk(full(gs, gk_spin.sample(t)))
    B = W['Bip01 NonAccum'][1]; B0 = Wg0['Bip01 NonAccum'][1]
    out = {}
    for gb, db in MAP:
        d = (B.T @ W[gb][1]) @ (B0.T @ Wg0[gb][1]).T
        out[db] = Cg.T @ d @ Cg                     # canonical-frame delta from its aim
    return out, W

# the gecko aims with its head 34 deg down and lifts it level to breathe; the deathclaw aims level, so while the mouth
# is open the deltas are taken from the gecko's breathing pose (REF) instead - the shot leaves level - and the side to
# side sway is damped (SWAY: the shots follow the mouth); eased in over the wind-up and out over the close
G_REF = G_FIRE + 0.1
SWAY = 0.4
_ref = _raw(G_REF)[0]
CORR = {db: _ref[db].T for db in _ref}
def _smooth(u): u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)
def _blend(R, w):                                     # rotation R scaled by w (slerp from identity)
    return q2m(slerp(np.array([1.0, 0, 0, 0]), m2q(R), w))
def gecko_at(t):
    raw, W = _raw(t)
    if t <= G_FIRE: w = _smooth(t / G_FIRE)
    elif t <= G_LOOP: w = 1.0
    else: w = 1.0 - _smooth((t - G_LOOP) / (G_END - G_LOOP))
    out = {db: _blend(_blend(CORR[db], w) @ raw[db], 1.0 - (1.0 - SWAY) * w) for db in raw}
    return out, max(0.0, jaw_angle(W) - JAW0) * JAW_SCALE

# ---- deathclaw aim (h2haim) base
dc_aim = KFEval(os.path.join(sys.argv[1], 'h2haim.kf'))
aim_bones = {b[0]: b[2] for b in dc_aim.blocks}
def dc_base(t):
    return full(sk, dc_aim.sample(t % dc_aim.stop))
Wd0 = sk.fk(dc_base(0.0))
Cd = canon(Wd0, 'Bip01 Pelvis', 'Bip01 Head', 'Bip01 NonAccum')

# mouth frame (Weapon local under Bip01 Head): +X = level forward in the neutral aim, +Y = up
Rh0 = Wd0['Bip01 Head'][1]
fwd = Wd0['Bip01 NonAccum'][1] @ Cd[:, 0]; up = np.array([0, 0, 1.0])
X = Rh0.T @ fwd; Y = Rh0.T @ up; Y -= X * np.dot(X, Y); Y /= np.linalg.norm(Y); Z = np.cross(X, Y)
MOUTH_R = np.column_stack([X, Y, Z])

def set_world(loc, W, n, Rw):
    p = sk.parent[n]; loc[n] = (loc[n][0], W[p][1].T @ Rw)

def pose(t, pitch=0.0, breath=None):
    loc = dc_base(t)
    W = sk.fk(loc)
    if breath is not None:
        deltas, jaw, (hp, hy) = breath
        B = W['Bip01 NonAccum'][1]; Wh = W['Bip01 Head'][1].copy()
        for gb, db in MAP:
            if db == 'Bip01 Head': continue
            Dd = Cd @ deltas[db] @ Cd.T                       # body-frame delta on the deathclaw
            target = B @ Dd @ (B.T @ W[db][1])
            set_world(loc, W, db, target); W = sk.fk(loc)
        # the head keeps the aim's orientation plus a small rear-back / sway: the shot follows the mouth
        lat = B @ Cd[:, 1]; up = B @ Cd[:, 2]
        set_world(loc, W, 'Bip01 Head', rotm(up, hy) @ rotm(lat, -hp) @ Wh); W = sk.fk(loc)
        jt, jR = loc['Bip01 Ponytail3']; loc['Bip01 Ponytail3'] = (jt, rotm([0, 0, 1.0], jaw) @ jR)
    if pitch:
        lat = W['Bip01 NonAccum'][1] @ Cd[:, 1]                 # left axis: + pitch lifts the head
        for n in ('Bip01 Neck1', 'Bip01 Head'):
            W = sk.fk(loc); set_world(loc, W, n, rotm(lat, -pitch / 2) @ W[n][1])
    # the skeleton's Weapon node (under the right hand) keyed onto the mouth: a gun model attached there (scale 0.001,
    # unseen) and any node a script adds to it start the shot from the mouth too
    W = sk.fk(loc); ph, Rhd = W['Bip01 Head']; pw, Rw = W[sk.parent['Weapon']]
    loc['Weapon'] = (Rw.T @ (ph + Rhd @ MOUTH - pw), Rw.T @ Rhd @ MOUTH_R)
    return loc

REAR = 15.0                 # head lift while drawing breath (deg)
BOB = (2.0, 3.0)            # open-mouth pitch / yaw sway (deg)
def head_sched(t, h, end_open, L, sustained):
    if sustained:                                  # one sway cycle per loop, smaller on fast loops (0.2 s automatic fire)
        a = min(1.0, L / 0.8)
        return a * BOB[0] * np.sin(2 * np.pi * t / L), a * BOB[1] * np.sin(2 * np.pi * t / L + 1.0)
    if t <= h: return REAR * np.sin(np.pi * (t / h if h > 0 else 1.0)), 0.0
    if t <= end_open:
        u = (t - h); return BOB[0] * np.sin(2 * np.pi * u / 0.8), BOB[1] * np.sin(2 * np.pi * u / 1.1)
    return 0.0, 0.0

# ---- classify + write
def keys_of(k): return [(t, s) for t, s in k.textkeys]

def group_kind(name):
    n = name.lower()
    if n.startswith('aim'): return 'aim'
    if n.startswith('attack'): return 'attack'
    return 'still'

def pitch_of(name):
    n = name.lower().split('_')[0]
    return PITCH if n.endswith('up') else -PITCH if n.endswith('down') else 0.0

PRIO_UPPER = 45
UPPER = {'Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2', 'Bip01 Neck', 'Bip01 Neck1', 'Bip01 Head', 'Bip01 Ponytail1',
         'Bip01 Ponytail2', 'Bip01 Ponytail3', 'Bip01 Brain'}

def scale_weapon(path, scale):
    """Weapon interpolator scale (any interpolator type: a static NiTransformInterpolator replaces it)"""
    kf = KFFile(path)
    if not any(n == 'Weapon' for _, n in kf.cb): return False
    k = KFEval(path); s0 = k.sample(k.start).get('Weapon')
    t, R, _ = sk.local['Weapon']
    if s0 is not None:
        if s0[0] is not None: t = s0[0]
        if s0[1] is not None: R = s0[1]
    kf.set_channel('Weapon', [(0.0, np.asarray(t, float), np.asarray(R, float))])
    f = kf.f; ii = len(f.blocks) - 1
    assert f.types[f.btype[ii]] == 'NiTransformInterpolator'
    b = bytearray(f.blocks[ii]); struct.pack_into('<f', b, 28, scale); f.blocks[ii] = bytes(b)
    kf.save(path); return True

def mouth_file(path):
    k = KFEval(path); name = k.name; L = k.stop; kind = group_kind(name)
    keys = [(t, s) for t, s in keys_of(k) if not s.lower().startswith('prn')]
    if kind == 'still': keys = [(t, s) for t, s in keys if not s.lower().startswith('sound')]
    keys = sorted(keys, key=lambda x: (x[0], x[1] != 'start', x[1] == 'end'))
    pitch = pitch_of(name)
    n = max(2, int(round(L * 30)) + 1)
    hit = next((t for t, s in keys if s in ('Hit', 'Fire')), None)
    loop = next((t for t, s in keys if s == 'Loop'), None)
    sustained = kind == 'attack' and (L < 0.5 or 'loop' in name.lower())
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        br = None
        if kind == 'attack':
            if sustained:
                tg = 0.5 + (G_LOOP - 0.5) * (t / L)                     # the open, swaying part
            else:
                h = hit if hit is not None else min(0.1, L * 0.2)
                close = min(G_END - G_LOOP, 0.3 * L)
                end_open = loop if loop is not None else L - close
                if t <= h: tg = G_FIRE * (t / h if h > 0 else 1)
                elif t <= end_open: tg = G_FIRE + (G_LOOP - G_FIRE) * ((t - h) / max(end_open - h, 1e-6))
                else: tg = G_LOOP + (G_END - G_LOOP) * ((t - end_open) / max(L - end_open, 1e-6))
            d, jaw = gecko_at(tg)
            if sustained: hs = head_sched(t, 0, L, L, True)
            else: hs = head_sched(t, h, end_open, L, False)
            br = (d, jaw, hs)
        frames.append((t, pose(t, pitch, br)))
    bones = [(b, PRIO_UPPER if b in UPPER else p) for b, p in aim_bones.items() if b != 'Bip01' and b != 'Weapon']
    if 'Bip01 Ponytail3' not in aim_bones: bones.append(('Bip01 Ponytail3', PRIO_UPPER))
    bones.append(('Weapon', 55))
    write_kf(cr, path, name, L, keys, frames, bones=bones, cycle=k.cycle)
    scale_weapon_written(path)

def scale_weapon_written(path):
    """write_kf wrote the Weapon interpolator with scale 1: set HIDE_SCALE in place"""
    f = NifFile(path)
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = f.blocks[bi]; ncb = struct.unpack_from('<I', b, 4)[0]; o = 12
    for _ in range(ncb):
        ii, _, pr, nm = struct.unpack_from('<iiBi', b, o); o += 29
        if f.strings[nm] == 'Weapon':
            ib = bytearray(f.blocks[ii]); struct.pack_into('<f', ib, 28, HIDE_SCALE); f.blocks[ii] = bytes(ib)
    open(path, 'wb').write(f.to_bytes())

# ProjectileNode on the head at the mouth: a prn key moves only the weapon MODEL, the skeleton's Weapon node stays under
# the right hand, so a node under Weapon fired from beside the hand. +Y = the actor's heading in the neutral aim (the
# aim stance faces ~3.5 deg off it), +Z up; aim up / down and the breath pitch it with the head.
_y = Rh0.T @ np.array([0, 1.0, 0]); _z = Rh0.T @ np.array([0, 0, 1.0]); _z -= _y * np.dot(_y, _z); _z /= np.linalg.norm(_z)
PROJ_R = np.column_stack([np.cross(_y, _z), _y, _z])

def patch_skeleton(path):
    f = NifFile(path)
    if f.find('ProjectileNode') is not None: return 'present'
    f.add_node(f.find('Bip01 Head'), 'ProjectileNode', tuple(float(x) for x in MOUTH),
               tuple(float(x) for x in PROJ_R.reshape(-1)), flags=524302)
    open(path, 'wb').write(f.to_bytes()); return 'added'

if __name__ == '__main__':
    D = sys.argv[1]; skel = sys.argv[2]; hide_only = '--hide' in sys.argv[3:]
    nm = nh = 0
    for fn in sorted(os.listdir(D)):
        m = re.match(r'^(sneak)?(h2h|1hm|2hm|1hp|2hr|2ha|2hh|2hl|1gt|1md|1lm)(.*)\.kf$', fn, re.I)
        if not m: continue
        pre = m.group(2).lower(); rest = m.group(3).lower()
        p = os.path.join(D, fn)
        if pre in GUNS and not re.match(r'^(equip|unequip|holster)', rest):
            if not hide_only: mouth_file(p); nm += 1
        elif pre in HIDE:
            if scale_weapon(p, HIDE_SCALE): nh += 1
    if hide_only: sys.exit(print('weapon hidden in', nh))
    print('mouth files', nm, 'weapon hidden in', nh, 'skeleton ProjectileNode', patch_skeleton(skel))
    # check: the shot (ProjectileNode +Y) in the actor frame, neutral aim and at the first attack's Hit
    s2 = Skeleton(skel)
    for fn in ('2hraim.kf', '2hrattackleft.kf'):
        k = KFEval(os.path.join(D, fn)); t = next((t for t, x in k.textkeys if x in ('Hit', 'Fire')), 0.0)
        W = s2.fk(full(s2, k.sample(t))); d = W['ProjectileNode'][1][:, 1]
        print(fn, 'shot yaw %.1f pitch %.1f from' % (np.degrees(np.arctan2(d[0], d[1])), np.degrees(np.arcsin(d[2]))),
              np.round(W['ProjectileNode'][0], 1), 'parent', s2.parent['ProjectileNode'])
