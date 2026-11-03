"""Guns fire from the mouth, with the creature's own ranged attack (as the deathclaw's mouth fire, but each creature
uses its own animation): the Lakelurk's shriek (2hlaim / 2hlattackright), the Mirelurk's lunge (2hlaim / 2hlattackspin,
claws raised in its fighting stance). Rewrites every gun-type file (1HP, 2HR, 2HA, 2HH, 2HL and their sneak copies;
equip / unequip / holster excepted - those stay its own claw equips) in an assembled folder, keeping each file's
sequence name, length, cycle and text keys (vanilla timing and weapon events):
  aims       its own ranged aim, looped over the file; Aim*Up / Down = the neck / head pitched +-PITCH so the mouth
             follows the look
  attacks    its own ranged attack time-warped so its Hit / Fire lands on the file's Hit / Fire key; the wind-up before it
             is shortened to what the file leaves (at least WIND seconds of it are kept when the file's Hit is early);
             sustained fire (AttackLoop, short files) holds the attack with a small sway around its Hit
  reloads / jams / recoil / still files: the aim (their gun Sound: keys dropped)
  Weapon     the skeleton's Weapon node (under the right hand / claw) keyed every frame onto the mouth, +X level forward,
             scale 0.001: the gun model stays attached there unseen, so its own ProjectileNode and any node a script adds
             to it (3rd Person Aim Fix) are at the mouth
  priorities each bone keeps its source file's priority; legs / pelvis / tail / side legs (LEGS) at most 25, under the
             walk's 30, so it walks while firing
  prn keys   every 'prn:' text key in the folder names Bip01 R Hand (the Weapon node's parent; the lakelurk's own
             holster named Dummy01)
The sources are read from the vanilla folder; its own aim / attack files are rewritten too (same motion, Weapon channel
added). Every melee / unarmed file's Weapon channel (equips and holsters included) gets scale 0.001 (melee weapons
hidden - the claws are the weapons); thrown weapons / mines keep theirs.
The skeleton gets ProjectileNode on the head at the mouth (+Y = level forward in the aim): the engine's shot leaves it
when the hidden gun has none.
Grenades / mines (claw_attack): every 1GT / 1MD / 1LM aim = the claw aim, every throw / placement = the claw strike with
its Hit on the file's Release, the grenade in the right claw (shown); their equips hold it at the Weapon bind.
usage: python3 mouth_fire.py <creature> <folder> <Skeleton.nif to patch> [--hide | --throws]     creature = lakelurk | mirelurk
  --throws: only the grenade / mine files"""
import os, re, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import Skeleton, KFEval
from rig import Creature, write_kf, rotm
from nifedit import NifFile
from sound_keys import text_keys
import importlib

GUNS = ('1hp', '2hr', '2ha', '2hh', '2hl')
HIDE = ('h2h', '1hm', '2hm') + GUNS
PITCH = 30.0
WIND = 0.45                       # seconds of the wind-up kept before an early Hit
SWAY = 0.12                       # sustained fire: +- seconds around the attack's Hit
HIDE_SCALE = 0.001
LEGS = 25
# mouth: a node of the skeleton (the lakelurk's shriek node) or a point in the head frame, given as (forward, up) from
# the head node in the aim pose (the mirelurk's mouth, under the front of its head)
CREATURES = {
    # (claw_weapon_bind: its own files key Weapon under Dummy01, the vanilla parent - the grenade is put at the skeleton's
    # Weapon bind under the hand instead)
    'lakelurk': dict(cfg='lakelurk', aim='2hlaim.kf', attack='2hlattackright.kf', mouth_node='ProjectileNode_Sonic',
                     claw_aim='h2haim.kf', claw_attack='h2hattackright_jab.kf', claw_weapon_bind=True,
                     pitch_bones=('Bip01 Neck1', 'Bip01 Head'),
                     lower=r'^Bip01( NonAccum| Pelvis| [LR] (Thigh|Calf|Foot|Toe\d*))$'),
    # level_head: the attack's body motion with the aim's head orientation (the mirelurk's lunge rears the head 37 deg up:
    # the shots left that far above the crosshair line)
    # claw_throw: grenades / mines (1GT / 1MD / 1LM) aim with claw_aim and throw / place with claw_attack, its own claw
    # strike time-warped so its Hit lands on the file's Release; the grenade rides in the right pincer (Weapon as the strike
    # keys it, or the skeleton's), shown
    'mirelurk': dict(cfg='mirelurk', aim='2hlaim.kf', attack='2hlattackspin.kf', mouth_fu=(8.0, -6.0), level_head=True,
                     claw_aim='h2haim.kf', claw_attack='h2hattackright.kf',
                     pitch_bones=('Bip01 Neck', 'Bip01 Head'),
                     lower=r'^Bip01( NonAccum| Pelvis| [LR] (Thigh|Calf|Foot|Toe\d*)| Tail\d*| Ponytail\d+)$'),
}
SPEC = CREATURES[sys.argv[1]]
LOWER = re.compile(SPEC['lower'])
cfg = importlib.import_module('creatures.' + SPEC['cfg'])
cr = Creature(cfg); sk = cr.sk
SRC = cfg.ANIM_SRC


def full(skel, sample):
    out = {}
    for n in skel.order:
        t, R, _ = skel.local[n]
        if n in sample:
            if sample[n][0] is not None: t = sample[n][0]
            if sample[n][1] is not None: R = sample[n][1]
        out[n] = (np.array(t, float), np.array(R, float))
    out['Bip01'] = (np.zeros(3), np.eye(3))
    return out


aim = KFEval(os.path.join(SRC, SPEC['aim']))
shriek = KFEval(os.path.join(SRC, SPEC['attack']))
S_HIT = [t for t, k in shriek.textkeys if k in ('Hit', 'Fire')][0]
S_END = shriek.stop
PRIO = {'aim': {b[0]: b[2] for b in aim.blocks}, 'attack': {b[0]: b[2] for b in shriek.blocks}}
BONES = [b[0] for b in shriek.blocks if b[0] not in ('Bip01', 'Weapon')]
for b in aim.blocks:
    if b[0] not in BONES and b[0] not in ('Bip01', 'Weapon'): BONES.append(b[0])

W0 = sk.fk(full(sk, aim.sample(0.0)))
B0 = W0['Bip01 NonAccum'][1]
fwd = W0['Bip01 Head'][0] - W0['Bip01 Pelvis'][0]; fwd[2] = 0; fwd /= np.linalg.norm(fwd)
UP = np.array([0, 0, 1.0]); LEFT = np.cross(UP, fwd)
# mouth point / frame in the head frame
ph0, Rh0 = W0['Bip01 Head']
if 'mouth_node' in SPEC: ps0 = W0[SPEC['mouth_node']][0]
else: ps0 = ph0 + SPEC['mouth_fu'][0] * fwd + SPEC['mouth_fu'][1] * UP
MOUTH = Rh0.T @ (ps0 - ph0)
X = Rh0.T @ fwd; Y = Rh0.T @ UP; Y -= X * np.dot(X, Y); Y /= np.linalg.norm(Y)
MOUTH_R = np.column_stack([X, Y, np.cross(X, Y)])
_y = Rh0.T @ fwd; _z = Rh0.T @ UP; _z -= _y * np.dot(_y, _z); _z /= np.linalg.norm(_z)
PROJ_R = np.column_stack([np.cross(_y, _z), _y, _z])


def set_world(loc, W, n, Rw):
    p = sk.parent[n]; loc[n] = (loc[n][0], W[p][1].T @ Rw)


def pose(sample, pitch=0.0, head_from=None):
    loc = full(sk, sample)
    W = sk.fk(loc)
    if head_from is not None:                      # the aim's head orientation (world) on the attack's body
        Wa = sk.fk(full(sk, head_from)); set_world(loc, W, 'Bip01 Head', Wa['Bip01 Head'][1]); W = sk.fk(loc)
    if pitch:
        lat = W['Bip01 NonAccum'][1] @ (B0.T @ LEFT)
        for n in SPEC['pitch_bones']:
            W = sk.fk(loc); set_world(loc, W, n, rotm(lat, -pitch / 2) @ W[n][1])
    W = sk.fk(loc); ph, Rh = W['Bip01 Head']; pw, Rw = W[sk.parent['Weapon']]
    loc['Weapon'] = (Rw.T @ (ph + Rh @ MOUTH - pw), Rw.T @ Rh @ MOUTH_R)
    return loc


def kind_of(name):
    n = name.lower()
    if n.startswith('aim'): return 'aim'
    if n.startswith('attack'): return 'attack'
    return 'still'


def pitch_of(name):
    n = name.lower().split('_')[0]
    return PITCH if n.endswith('up') else -PITCH if n.endswith('down') else 0.0


def shriek_time(t, L, hit, sustained):
    if sustained: return S_HIT + SWAY * np.sin(2 * np.pi * t / L)
    h = hit if hit is not None else min(0.1, 0.2 * L)
    t0 = max(0.0, S_HIT - max(WIND, h))                     # where the wind-up starts
    if t <= h: return t0 + (S_HIT - t0) * (t / h if h > 0 else 1.0)
    return S_HIT + (S_END - S_HIT) * ((t - h) / max(L - h, 1e-6))


def mouth_file(path):
    k = KFEval(path); name = k.name; L = k.stop; kind = kind_of(name)
    keys = [(t, s) for t, s in k.textkeys if not s.lower().startswith('prn')]
    if kind == 'still': keys = [(t, s) for t, s in keys if not s.lower().startswith('sound')]
    keys = sorted(keys, key=lambda x: (x[0], x[1] != 'start', x[1] == 'end'))
    pitch = pitch_of(name)
    hit = next((t for t, s in keys if s in ('Hit', 'Fire')), None)
    sustained = kind == 'attack' and (L < 0.5 or 'loop' in name.lower())
    n = max(2, int(round(L * 30)) + 1); frames = []
    for i in range(n):
        t = L * i / (n - 1)
        hf = None
        if kind == 'attack':
            smp = shriek.sample(min(shriek_time(t, L, hit, sustained), S_END))
            if SPEC.get('level_head'): hf = aim.sample(t % aim.stop)
        else: smp = aim.sample(t % aim.stop)
        frames.append((t, pose(smp, pitch, hf)))
    src = PRIO['attack' if kind == 'attack' else 'aim']; dflt = max(src.values())
    bones = [(b, min(src.get(b, dflt), LEGS) if LOWER.match(b) else src.get(b, dflt)) for b in BONES] + [('Weapon', 55)]
    write_kf(cr, path, name, L, keys, frames, bones=bones, cycle=k.cycle)
    scale_weapon_written(path)


THROWN = ('1gt', '1md', '1lm')
if 'claw_attack' in SPEC:
    claw_aim = KFEval(os.path.join(SRC, SPEC['claw_aim'])); claw = KFEval(os.path.join(SRC, SPEC['claw_attack']))
    C_HIT = [t for t, k in claw.textkeys if k == 'Hit'][0]
    CPRIO = {'aim': {b[0]: b[2] for b in claw_aim.blocks}, 'attack': {b[0]: b[2] for b in claw.blocks}}


def claw_file(path):
    """a grenade / mine file: aims = the claw aim, throws / placements = the claw strike with its Hit on the Release"""
    k = KFEval(path); name = k.name; L = k.stop; n_ = name.lower()
    kind = 'attack' if n_.startswith('attackthrow') or n_.startswith('placemine') else 'aim' if n_.startswith('aim') else None
    if kind is None: return False
    keys = sorted([(t, s) for t, s in k.textkeys if not s.lower().startswith('prn')], key=lambda x: (x[0], x[1] != 'start', x[1] == 'end'))
    pitch = pitch_of(name)
    rel = next((t for t, s in keys if s == 'Release'), None)
    src = claw if kind == 'attack' else claw_aim
    bind_weapon = SPEC.get('claw_weapon_bind') or 'Weapon' not in CPRIO[kind]
    n = max(2, int(round(L * 30)) + 1); frames = []
    for i in range(n):
        t = L * i / (n - 1)
        if kind == 'attack':
            h = rel if rel is not None else 0.5 * L
            ts = C_HIT * (t / h) if t <= h else C_HIT + (claw.stop - C_HIT) * ((t - h) / max(L - h, 1e-6))
            smp = claw.sample(min(ts, claw.stop))
        else: smp = claw_aim.sample(t % claw_aim.stop)
        loc = full(sk, smp); W = sk.fk(loc)
        if pitch:
            lat = W['Bip01 NonAccum'][1] @ (B0.T @ LEFT)
            for nb in SPEC['pitch_bones']:
                W = sk.fk(loc); set_world(loc, W, nb, rotm(lat, -pitch / 2) @ W[nb][1])
        if bind_weapon: loc['Weapon'] = (np.array(sk.local['Weapon'][0], float), np.array(sk.local['Weapon'][1], float))
        frames.append((t, loc))
    pr = CPRIO[kind]; dflt = max(pr.values())
    bones = [(b, min(pr.get(b, dflt), LEGS) if LOWER.match(b) else pr.get(b, dflt)) for b in pr if b not in ('Bip01', 'Weapon')]
    bones.append(('Weapon', 55))           # always keyed, scale 1: a gun file left it hidden at the mouth
    write_kf(cr, path, name, L, keys, frames, bones=bones, cycle=k.cycle)
    return True


def weapon_bind(path):
    """a grenade / mine equip / unequip / holster: Weapon held at the skeleton's bind under the hand, scale 1"""
    from holster_fix import KFFile
    kf = KFFile(path)
    if not any(n == 'Weapon' for _, n in kf.cb): return False
    kf.set_channel('Weapon', [(0.0, np.asarray(sk.local['Weapon'][0], float), np.asarray(sk.local['Weapon'][1], float))])
    kf.save(path); return True


def scale_weapon_written(path):
    f = NifFile(path)
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = f.blocks[bi]; ncb = struct.unpack_from('<I', b, 4)[0]; o = 12
    for _ in range(ncb):
        ii, _, pr, nm = struct.unpack_from('<iiBi', b, o); o += 29
        if f.strings[nm] == 'Weapon':
            ib = bytearray(f.blocks[ii]); struct.pack_into('<f', ib, 28, HIDE_SCALE); f.blocks[ii] = bytes(ib)
    open(path, 'wb').write(f.to_bytes())


def scale_weapon(path):
    from holster_fix import KFFile
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
    b = bytearray(f.blocks[ii]); struct.pack_into('<f', b, 28, HIDE_SCALE); f.blocks[ii] = bytes(b)
    kf.save(path); return True


def prn_to_hand(path):
    f = NifFile(path); i, name, keys = text_keys(f)
    if i is None or not any(s.strip().lower().startswith('prn') and 'r hand' not in s.lower() for _, s in keys): return False
    out = [(t, 'prn: Bip01 R Hand' if s.strip().lower().startswith('prn') else s) for t, s in keys]
    f.blocks[i] = struct.pack('<iI', name, len(out)) + b''.join(struct.pack('<fi', t, f.str_index(s)) for t, s in out)
    open(path, 'wb').write(f.to_bytes()); return True


def patch_skeleton(path):
    f = NifFile(path)
    if f.find('ProjectileNode') is not None: return 'present'
    f.add_node(f.find('Bip01 Head'), 'ProjectileNode', tuple(float(x) for x in MOUTH),
               tuple(float(x) for x in PROJ_R.reshape(-1)), flags=524302)
    open(path, 'wb').write(f.to_bytes()); return 'added'


if __name__ == '__main__':
    D = sys.argv[2]; skel = sys.argv[3]; hide_only = '--hide' in sys.argv[4:]; throws_only = '--throws' in sys.argv[4:]
    nm = nh = nt = 0
    npr = sum(prn_to_hand(os.path.join(d, f)) for d, _, fs in os.walk(D) for f in fs if f.lower().endswith('.kf'))
    for fn in sorted(os.listdir(D)):
        m = re.match(r'^(sneak)?(h2h|1hm|2hm|1hp|2hr|2ha|2hh|2hl|1gt|1md|1lm)(.*)\.kf$', fn, re.I)
        if not m: continue
        pre = m.group(2).lower(); rest = m.group(3).lower()
        p = os.path.join(D, fn)
        if pre in GUNS and not re.match(r'^(sonnic)?(equip|unequip|holster)', rest):
            if not hide_only and not throws_only: mouth_file(p); nm += 1
        elif pre in THROWN and 'claw_attack' in SPEC and not hide_only:
            if re.match(r'^(equip|unequip|holster)', rest): weapon_bind(p)
            else: nt += claw_file(p)
        elif pre in HIDE:
            if scale_weapon(p): nh += 1
    if hide_only: sys.exit(print('weapon hidden in', nh, 'prn keys moved to the hand in', npr))
    print('mouth-fire files', nm, 'claw throws', nt, 'weapon hidden in', nh, 'prn keys moved to the hand in', npr, 'skeleton ProjectileNode', patch_skeleton(skel))
    s2 = Skeleton(skel)
    for fn in ('2hraim.kf', '2hrattackleft.kf', '2haattackloop.kf', '2hlattackright.kf', '1hpattackloop.kf'):
        if not os.path.exists(os.path.join(D, fn)): continue
        k = KFEval(os.path.join(D, fn)); t = next((t for t, x in k.textkeys if x in ('Hit', 'Fire')), 0.0)
        W = s2.fk(full(s2, k.sample(t))); d = W['ProjectileNode'][1][:, 1]
        print(fn, 'shot yaw %.1f pitch %.1f from' % (np.degrees(np.arctan2(d[0], d[1])), np.degrees(np.arcsin(d[2]))),
              np.round(W['ProjectileNode'][0], 1))
