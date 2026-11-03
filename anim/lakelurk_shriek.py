"""Lakelurk guns fire as its own shriek, from its mouth (as the deathclaw's mouth fire, but with the lakelurk's own
2HL shriek instead of a borrowed breath). Rewrites every gun-type file (1HP, 2HR, 2HA, 2HH, 2HL and their sneak copies;
equip / unequip / holster excepted - those stay its own claw equips) in an assembled Lakelurk folder, keeping each
file's sequence name, length, cycle and text keys (vanilla timing and weapon events):
  aims       its own shriek aim (2hlaim: crouched, head forward), looped over the file; Aim*Up / Down = the head chain
             (Neck1 + Head) pitched +-PITCH so the mouth follows the look
  attacks    its own shriek (2hlattackright: rear up, head thrust at 'Hit') time-warped so its Hit lands on the file's
             Hit / Fire key; the wind-up before it is shortened to what the file leaves (at least WIND seconds of the
             rear-up are kept when the file's Hit is early); sustained fire (AttackLoop, short files) holds the thrust
             with a small sway around the Hit
  reloads / jams / recoil / still files: the aim (their gun Sound: keys dropped)
  Weapon     the skeleton's Weapon node (under the right claw) keyed every frame onto the mouth (ProjectileNode_Sonic),
             +X level forward, scale 0.001: the gun model stays attached there unseen, so its own ProjectileNode and
             any node a script adds to it (3rd Person Aim Fix) are at the mouth
  priorities upper body ABOVE (aims 31 / attacks 40, as its own files), legs / pelvis / toes LEGS (25: under the
             walk's 30, so it walks while shrieking; over the idle's 20)
Its own 2hlaim.kf / 2hlattackright.kf are the sources (read from the vanilla folder) and are rewritten too (same motion,
Weapon channel added). Every melee / unarmed file's Weapon channel (equips and holsters included) gets scale 0.001
(melee weapons hidden - its claws are its weapons); thrown weapons / mines keep theirs.
The skeleton gets ProjectileNode on the head at the shriek's node (+Y = level forward in its shriek aim): the engine's
shot leaves it (found before the hidden gun's).
usage: python3 lakelurk_shriek.py <Lakelurk folder> <Skeleton.nif to patch> [--hide]"""
import os, re, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import Skeleton, KFEval
from rig import Creature, write_kf, rotm
from nifedit import NifFile
import importlib

GUNS = ('1hp', '2hr', '2ha', '2hh', '2hl')
HIDE = ('h2h', '1hm', '2hm') + GUNS
PITCH = 30.0
WIND = 0.45                       # seconds of the rear-up kept before an early Hit
SWAY = 0.12                       # sustained fire: +- seconds around the shriek's Hit
HIDE_SCALE = 0.001
AIM_UPPER, ATTACK_UPPER, LEGS = 31, 40, 25
LOWER = re.compile(r'^Bip01( NonAccum| Pelvis| [LR] (Thigh|Calf|Foot|Toe\d*))$')

cfg = importlib.import_module('creatures.lakelurk')
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


aim = KFEval(os.path.join(SRC, '2hlaim.kf'))
shriek = KFEval(os.path.join(SRC, '2hlattackright.kf'))
S_HIT = [t for t, k in shriek.textkeys if k == 'Hit'][0]
S_END = shriek.stop
BONES = [b[0] for b in shriek.blocks if b[0] not in ('Bip01', 'Weapon')]
for b in aim.blocks:
    if b[0] not in BONES and b[0] not in ('Bip01', 'Weapon'): BONES.append(b[0])

W0 = sk.fk(full(sk, aim.sample(0.0)))
B0 = W0['Bip01 NonAccum'][1]
fwd = W0['Bip01 Head'][0] - W0['Bip01 Pelvis'][0]; fwd[2] = 0; fwd /= np.linalg.norm(fwd)
UP = np.array([0, 0, 1.0]); LEFT = np.cross(UP, fwd)
# mouth point / frame in the head frame
ph0, Rh0 = W0['Bip01 Head']; ps0 = W0['ProjectileNode_Sonic'][0]
MOUTH = Rh0.T @ (ps0 - ph0)
X = Rh0.T @ fwd; Y = Rh0.T @ UP; Y -= X * np.dot(X, Y); Y /= np.linalg.norm(Y)
MOUTH_R = np.column_stack([X, Y, np.cross(X, Y)])
_y = Rh0.T @ fwd; _z = Rh0.T @ UP; _z -= _y * np.dot(_y, _z); _z /= np.linalg.norm(_z)
PROJ_R = np.column_stack([np.cross(_y, _z), _y, _z])


def set_world(loc, W, n, Rw):
    p = sk.parent[n]; loc[n] = (loc[n][0], W[p][1].T @ Rw)


def pose(sample, pitch=0.0):
    loc = full(sk, sample)
    W = sk.fk(loc)
    if pitch:
        lat = W['Bip01 NonAccum'][1] @ (B0.T @ LEFT)
        for n in ('Bip01 Neck1', 'Bip01 Head'):
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


def shriek_file(path):
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
        if kind == 'attack': smp = shriek.sample(min(shriek_time(t, L, hit, sustained), S_END))
        else: smp = aim.sample(t % aim.stop)
        frames.append((t, pose(smp, pitch)))
    up = ATTACK_UPPER if kind == 'attack' else AIM_UPPER
    bones = [(b, LEGS if LOWER.match(b) else up) for b in BONES] + [('Weapon', 55)]
    write_kf(cr, path, name, L, keys, frames, bones=bones, cycle=k.cycle)
    scale_weapon_written(path)


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
        if pre in GUNS and not re.match(r'^(sonnic)?(equip|unequip|holster)', rest):
            if not hide_only: shriek_file(p); nm += 1
        elif pre in HIDE:
            if scale_weapon(p): nh += 1
    if hide_only: sys.exit(print('weapon hidden in', nh))
    print('shriek files', nm, 'weapon hidden in', nh, 'skeleton ProjectileNode', patch_skeleton(skel))
    s2 = Skeleton(skel)
    for fn in ('2hraim.kf', '2hrattackleft.kf', '2hlattackright.kf', '1hpattackloop.kf'):
        if not os.path.exists(os.path.join(D, fn)): continue
        k = KFEval(os.path.join(D, fn)); t = next((t for t, x in k.textkeys if x in ('Hit', 'Fire')), 0.0)
        W = s2.fk(full(s2, k.sample(t))); d = W['ProjectileNode'][1][:, 1]
        print(fn, 'shot yaw %.1f pitch %.1f from' % (np.degrees(np.arctan2(d[0], d[1])), np.degrees(np.arcsin(d[2]))),
              np.round(W['ProjectileNode'][0], 1))
