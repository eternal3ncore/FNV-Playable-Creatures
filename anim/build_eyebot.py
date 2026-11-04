"""Eyebot animation set for Playable Creatures (+ 2HR / 2HA / 2HH / 2HL like 1HP).
usage: python3 build_eyebot.py <eyebot anim dir> <human ref dir (ref_male)> <zetan ref dir> <out dir>
The eyebot (Creatures\\Eyebot) has its own Idle, Forward / Backward / Left / Right / FastForward, turns, 1HP aim (+up /
down), 1HP AttackRight (+up / down, _SL / _SR) and 1HP Equip / Unequip, and no limbs to animate. Every group the
player needs is made from those, with the group's sequence name, length, cycle and text keys taken from a reference:
  * 1HP (all aims / attacks / IS / loops / reloads / jams / holster): the vanilla human file (ref_male) - timing,
    Hit / Fire / reload sound keys; prn / Enum / footstep keys dropped (no hand; the weapon is never drawn);
  * H2H (aim, swings, power attacks, equips): the Zetan's deployed files (Zetan bark / footstep keys dropped);
  * mt: its own locomotion; FastBackward / FastLeft / FastRight = its Backward / Left / Right at twice the root speed
    (half the length); JumpLoop / JumpLand (+ directions) = its idle hover with the Zetan's timing;
  * every group also as a sneak copy (the eyebot doesn't crouch).
Holster files key only the stand-in Weapon node (static). Channel data: aims / reloads / jams = its 1HP aim (up / down variant by suffix); attacks = its 1HP AttackRight
(up / down) shifted so its Hit lands on the reference's Hit; equip / unequip = its own files as they are. Each channel
is resampled at 30 fps over the new length (linear keys)."""
import os, re, shutil, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KF, KFEval, Skeleton
from holster_fix import KFFile
from hip_spine_fix import drop_channel, retarget_channel

SRC, HREF, ZREF, OUT = sys.argv[1:5]
# a channel component the source leaves unkeyed (KFEval None: rotation-only / translation-only channels -
# most of the eyebot's limbs, and Neck1 which carries every limb) is the skeleton's bind value, as in the engine.
# Writing zero translation / identity rotation there instead puts the laser arm above the sphere, pointing sideways.
BIND = Skeleton(os.path.join(SRC, 'skeleton.nif')).local


def fill(name, tr, R):
    b = BIND.get(name)
    tr = (np.array(b[0], float) if b else np.zeros(3)) if tr is None else np.array(tr, float)
    R = (np.array(b[1], float) if b else np.eye(3)) if R is None else np.array(R, float)
    return tr, R
os.makedirs(OUT, exist_ok=True)
DROP = re.compile(r'^(prn:|enum:|m: |sound: pczetan|sound: npcdlc05alien)', re.I)


def hit_time(textkeys, keys=('hit',)):
    for key in keys:                                           # first key name found wins
        h = [t for t, v in textkeys if v.strip().lower() == key]
        if h: return h[0]
    return None


def build(src, out, seq, length, cycle, textkeys, shift=0.0, root_scale=1.0, fps=30):
    """channels of `src` resampled over [0, length] (source time = t + shift, clamped), sequence fields / keys set"""
    k = KFEval(src); kf = KFFile(out if os.path.exists(out) else src)
    n = max(2, int(round(length * fps)) + 1)
    ts = [length * i / (n - 1) for i in range(n)]
    for name in list(k.chan):
        if name not in [c for _, c in kf.cb]: continue
        keys = []
        for t in ts:
            st = min(max(t + shift, k.start), k.stop)
            tr, R = fill(name, *k.sample(st)[name])
            if name == 'Bip01': tr = tr * root_scale
            keys.append((t, tr, R))
        kf.set_channel(name, keys)
    f = kf.f; d = bytearray(f.blocks[kf.seq])
    nm, ncb, _ = struct.unpack_from('<iII', d, 0)
    struct.pack_into('<i', d, 0, f.str_index(seq))
    off = 12 + 29 * ncb
    w, tk, cyc, freq, st, sp = struct.unpack_from('<fiIfff', d, off)
    struct.pack_into('<fiIfff', d, off, w, tk, cycle, freq, 0.0, length)
    f.blocks[kf.seq] = bytes(d)
    tkn, = struct.unpack_from('<i', f.blocks[tk], 0)
    ent = sorted((min(max(t, 0.0), length), v) for t, v in textkeys)
    f.blocks[tk] = struct.pack('<iI', tkn, len(ent)) + b''.join(struct.pack('<fi', t, f.str_index(v)) for t, v in ent)
    kf.save(out)


def clean(tks): return [(t, v) for t, v in tks if not DROP.match(v.strip())]


S = lambda n: os.path.join(SRC, n)
src_hit = {n: hit_time(KF(S(n)).textkeys) for n in ('1hpattackright.kf', '1hpattackrightup.kf', '1hpattackrightdown.kf')}
made = []


def from_ref(ref_path, prefix):
    k = KF(ref_path); base = os.path.basename(ref_path); g = base[len(prefix):-3].lower()
    var = 'up' if g.endswith('up') else ('down' if g.endswith('down') else '')
    tks = clean(k.textkeys)
    if g in ('equip', 'unequip'):
        shutil.copyfile(S(f'1hp{g}.kf'), os.path.join(OUT, base)); made.append(base); return
    if g.startswith('attack') or g.startswith('placemine'):   # throws / mine placing: Release lands on its zap's Hit
        src = S(f'1hpattackright{var}.kf'); sh = hit_time(KF(src).textkeys); rh = hit_time(tks, ('hit', 'release'))
        shift = (sh - rh) if (sh is not None and rh is not None) else 0.0
    else:                                                     # aims, reloads, jams, holster, block / recoil
        src = S(f'1hpaim{var}.kf'); shift = 0.0
    build(src, os.path.join(OUT, base), k.name, k.stop, k.cycle, tks, shift)
    made.append(base)


# guns from the human set: 1HP, and (two-handed guns should work too) 2HR / 2HA / 2HH / 2HL - the same
# laser-arm motion for every gun type (no hands; the gun is never drawn and its shot leaves the emitter's ProjectileNode)
# (grenades and mines too, no special animations):
# 1GT / 1MD / 1LM the same way - aims = its aim, AttackThrow* / PlaceMine* = its zap with the human Release on its Hit
for f in sorted(os.listdir(HREF)):
    m = re.match(r'^(1hp|2hr|2ha|2hh|2hl|1gt|1md|1lm).*\.kf$', f)
    if m and not re.search(r'handgrip|jump|turn', f): from_ref(os.path.join(HREF, f), m.group(1))
for f in sorted(os.listdir(ZREF)):                             # H2H from the Zetan (aims, swings, powers, equips)
    if re.match(r'^h2h(aim|attack|equip|unequip|holster).*\.kf$', f): from_ref(os.path.join(ZREF, f), 'h2h')

# mt: own locomotion + fast variants + jumps
for f in ('mtidle.kf', 'mtforward.kf', 'mtbackward.kf', 'mtleft.kf', 'mtright.kf', 'mtfastforward.kf', 'mtturnleft.kf', 'mtturnright.kf'):
    shutil.copyfile(S(f), os.path.join(OUT, f)); made.append(f)
for g, src in (('FastBackward', 'mtbackward.kf'), ('FastLeft', 'mtleft.kf'), ('FastRight', 'mtright.kf')):
    k = KF(S(src)); L = k.stop / 2.0                           # same distance in half the time = twice the speed
    kk = KFEval(S(src))
    # resample at double speed: source time = 2t
    out = os.path.join(OUT, f'mt{g.lower()}.kf')
    kf = KFFile(S(src)); n = int(round(L * 30)) + 1; ts = [L * i / (n - 1) for i in range(n)]
    for name in list(kk.chan):
        keys = []
        for t in ts:
            tr, R = fill(name, *kk.sample(min(2 * t, kk.stop))[name])
            keys.append((t, tr, R))
        kf.set_channel(name, keys)
    kf.save(out)
    build(out, out, g, L, k.cycle, [(0.0, 'start'), (L, 'end')])
    made.append(os.path.basename(out))
for f in sorted(os.listdir(ZREF)):
    if re.match(r'^mtjump.*\.kf$', f):
        k = KF(os.path.join(ZREF, f)); build(S('mtidle.kf'), os.path.join(OUT, f), k.name, k.stop, k.cycle, clean(k.textkeys)); made.append(f)

# the stand-in Weapon node's bind rotation in our skeleton (build_skel_eyebot local +Y = the emitter's +X)
WEAPON_BIND = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)
# holster (played while the weapon is put away): key only the stand-in Weapon node (static, at its bind), so the
# idle / locomotion keep driving the body - a human holster keys only the Weapon node too
for f in [m for m in made if m.endswith('holster.kf')]:
    p = os.path.join(OUT, f); kf = KFFile(p); names = [n for _, n in kf.cb]
    for n in names[1:]: drop_channel(kf, n)
    retarget_channel(kf, names[0], 'Weapon')
    k = KF(p); kf.set_channel('Weapon', [(0.0, np.zeros(3), WEAPON_BIND)]); kf.save(p)

# sneak copies of everything
for f in list(made):
    shutil.copyfile(os.path.join(OUT, f), os.path.join(OUT, 'sneak' + f))
print(len(made), 'groups +', len(made), 'sneak copies ->', OUT)
import robot_melee; robot_melee.run(OUT)          # 1HM / 2HM = its H2H moves (weapon_hide.py --race hides the weapon)
